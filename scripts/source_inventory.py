"""把所有归档的 sources.csv 汇成一份来源清单（docs/SOURCES.md）。

## 为什么要这个文件

每个 `research/<slug>/sources.csv` 只回答「这一篇用了哪些来源」。
但「这个项目目前一共搜过哪些地方」是个跨归档的问题，此前只能靠
`Get-ChildItem research/*/sources.csv` 再手工拼——拼出来的东西没人复核，
也没人知道有没有漏。

故这份清单是**现算的**，不是手写的：口径全部来自 sources.csv 的字段，
生成命令写在文件头，读的人可以自己跑一遍核对。

## 两个口径上的决定

1. **按 URL 去重，而不是按 source_id。**
   source_id 是归档内的局部命名（`src-arxiv-2502-10517`），同一篇论文在
   四个归档里就是四条记录、四个同名 id。若按 source_id 数，会得出
   「本项目有 853 个来源」这种虚高的数字。按 URL 归一化后去重，
   才是「实际碰过多少个不同的地方」。

2. **去重不合并 trust_tier / source_type。**
   若同一个 URL 在不同归档里被标了不同的类型或层级，那是一个真问题
   （同一条证据的强度取决于从哪个 id 数上去）。这里不替它裁决，
   只把冲突显式列出来——没有冲突也要把「查过、没有」写出来，
   否则读的人无法区分「一致」与「没查」。

## 用法

    python scripts/source_inventory.py           # 写 docs/SOURCES.md
    python scripts/source_inventory.py --check    # 只比对，不写（CI 用）
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
OUT = ROOT / "docs" / "SOURCES.md"

# 站点归并：把同一家的不同子域算作一个「来源站点」。
# 不归并的话，github.com / raw.githubusercontent.com / api.github.com
# 会分成三行，读起来像三个不同的信息源，实际是同一处。
SITE_MAP = {
    "github.com": "GitHub",
    "raw.githubusercontent.com": "GitHub",
    "api.github.com": "GitHub",
    "media.githubusercontent.com": "GitHub",
    "gist.github.com": "GitHub",
    "arxiv.org": "arXiv",
    "export.arxiv.org": "arXiv",
    "huggingface.co": "Hugging Face",
    "docs.nvidia.com": "NVIDIA",
    "developer.nvidia.com": "NVIDIA",
    "nvidia.com": "NVIDIA",
    "www.nvidia.com": "NVIDIA",
    "blogs.nvidia.com": "NVIDIA",
    "forums.developer.nvidia.com": "NVIDIA 开发者论坛",
    "docs.vllm.ai": "vLLM",
    "vllm.ai": "vLLM",
    "docs.sglang.io": "SGLang",
    "www.spec.org": "SPEC",
    "spec.org": "SPEC",
}

# 归并之后仍要给出说明的站点。没列到的站点会显示为空说明——
# 这是刻意的：宁可留空，也不要给一个没核过的判断。
SITE_NOTE = {
    "arXiv": "预印本；有 arXiv id 即可复现",
    "GitHub": "代码仓库与 README；raw / api / media 四类子域已归并",
    "NVIDIA": "厂商自有文档与博客",
    "NVIDIA 开发者论坛": "实测帖；单条可信度低，需交叉核对",
    "Hugging Face": "模型卡与数据集卡",
    "vLLM": "推理引擎官方文档",
    "SGLang": "推理引擎官方文档",
    "SPEC": "标准基准组织的公开测试结果",
}

TYPE_LABEL = {
    "academic": "学术（论文 / 预印本）",
    "community": "社区（论坛 / 个人实测）",
    "official": "官方（厂商或项目自己的文档）",
    "independent": "独立第三方（媒体 / 独立评测）",
    "vendor": "厂商（产品与营销材料）",
    "vendor-adjacent": "厂商周边（合作方 / 生态）",
    "press": "新闻稿 / 报道",
    "review": "评测媒体",
    "retail": "零售页面",
}

TIER_LABEL = {
    "primary": "primary（自行产生观测）",
    "secondary": "secondary（转述他人）",
    "tertiary": "tertiary（聚合，无原始观测）",
}


def display_url(url: str) -> str:
    """把 file:// 转成本仓库内的相对路径。

    `cuda-kernel-gen` 有一条来源是本文自建的审计表，登记成
        file:///D:/github/DeepResearchRSI/research/cuda-kernel-gen/claims_audit.csv
    它在 sources.csv 里是**正确的一手证据**（license=internal、
    self-built），但原样写进面向读者的清单有两个问题：
      1. `D:/github/...` 是某台机器的本地路径，换台机器就打不开；
      2. 它把绝对路径写进了公开文档。
    故渲染时转成仓库相对路径——读者 clone 之后能直接找到这个文件。
    sources.csv 本身不改：那是归档的原始记录。
    """
    if not url.lower().startswith("file:"):
        return url
    p = url[5:].lstrip("/")
    # 去掉盘符前缀（D:/github/DeepResearchRSI/）
    m = re.sub(r"^[A-Za-z]:/", "", p)
    marker = "DeepResearchRSI/"
    i = m.find(marker)
    rel = m[i + len(marker):] if i >= 0 else m
    return f"`{rel}`（仓库内文件）"


def site_of(url: str) -> str:
    if url.lower().startswith("file:"):
        return "本仓库（自建产物）"
    try:
        host = (urlsplit(url).netloc or "").lower()
    except ValueError:
        return "（无法解析）"
    if not host:
        return "（无域名）"
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return SITE_MAP.get(host, host)


def load() -> list[dict]:
    """读出全部来源行，附上所属归档。"""
    out: list[dict] = []
    for d in sorted(RESEARCH.iterdir()):
        f = d / "sources.csv"
        if not f.is_file():
            continue
        with f.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                row = {k: (v or "").strip() for k, v in row.items() if k}
                row["_archive"] = d.name
                out.append(row)
    return out


def key_of(url: str) -> str:
    return url.strip().lower().rstrip("/")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成来源清单 docs/SOURCES.md")
    ap.add_argument("--check", action="store_true", help="只比对，不写文件")
    args = ap.parse_args(argv)

    rows = load()
    if not rows:
        print("[FAIL] 没有读到任何 sources.csv")
        return 1

    # ---------- 聚合 ----------
    by_url: dict[str, dict] = {}
    dup_groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        k = key_of(r.get("url") or "")
        dup_groups[k].append(r)
        if k not in by_url:
            by_url[k] = {
                "url": r.get("url") or "",
                "title": r.get("title") or "（无标题）",
                "type": r.get("source_type") or "",
                "tier": r.get("trust_tier") or "",
                "publisher": r.get("publisher") or "",
                "published": r.get("published_at") or "",
                "site": site_of(r.get("url") or ""),
                "archives": [],
            }
        by_url[k]["archives"].append(r["_archive"])

    uniq = list(by_url.values())
    for u in uniq:
        u["archives"] = sorted(set(u["archives"]))

    type_c = collections.Counter(u["type"] for u in uniq)
    tier_c = collections.Counter(u["tier"] for u in uniq)
    site_c = collections.Counter(u["site"] for u in uniq)
    year_c = collections.Counter((u["published"] or "")[:4] or "（未标日期）"
                                 for u in uniq)

    per_archive = collections.Counter(r["_archive"] for r in rows)
    # 每归档自己的唯一 URL 数（含被他篇也收的）
    seen: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows:
        seen[r["_archive"]].add(key_of(r.get("url") or ""))
    per_archive_uniq = {a: len(s) for a, s in seen.items()}

    dup_only = {k: v for k, v in dup_groups.items() if len(v) > 1}
    conflicts = {
        k: v for k, v in dup_only.items()
        if len({(x.get("source_type"), x.get("trust_tier")) for x in v}) > 1
    }

    # 重复分两类，混在一起会得出错误的句子：
    #   cross  同一地址出现在**多个归档**里 —— 正常复用（一篇论文被两篇综述引）
    #   intra  同一归档内多个 source 共用**同一个地址** —— 一个仓库登记了 14 个文件
    # 早先把两类都按「记录条数」说成「出现在 N 个归档里」，把
    # rsi-inference-bench 的 14 个仓库文件说成「出现在 14 个归档里」——是错的。
    cross = {k: v for k, v in dup_only.items()
             if len({x["_archive"] for x in v}) > 1}
    intra = {k: v for k, v in dup_only.items()
             if len({x["_archive"] for x in v}) == 1}

    def n_arch(v: list[dict]) -> int:
        return len({x["_archive"] for x in v})

    # ---------- 渲染 ----------
    L: list[str] = []
    A = L.append

    A("# 来源清单：这个项目目前搜过哪些地方")
    A("")
    A("> **本文件由脚本生成，不要手改。**")
    A("> 生成：`python scripts/source_inventory.py`　"
      "｜校验：`python scripts/source_inventory.py --check`")
    A(f"> 生成时间：{date.today().isoformat()}　｜"
      f"数据源：`research/*/sources.csv`（{len(seen)} 个归档）")
    A("")
    A("## 0　先看结论")
    A("")
    A(f"共 **{len(rows)}** 条来源记录，按 URL 去重后是 **{len(uniq)}** 个不同的地址。")
    A("")
    extra = len(rows) - len(uniq)
    if extra > 0:
        widest = max(intra.items(), key=lambda kv: len(kv[1]), default=None)
        A(f"两者差 {extra} 条，来自两种**性质不同**的重复，不能混说：")
        A("")
        A(f"- **跨归档复用 {len(cross)} 组**：同一篇论文被两篇综述分别引用，"
          "本就该有两份记录（多出 "
          f"{sum(len(v) - 1 for v in cross.values())} 条）。")
        A(f"- **归档内同名 {len(intra)} 组**：同一个页面地址被登记成多个 "
          "source（多出 "
          f"{sum(len(v) - 1 for v in intra.values())} 条）。"
          "这是刻意的——一个仓库的 14 份文件是 14 个**独立**的证据来源，"
          "但共享同一个 URL。"
          + (f"最宽的一处是 `{widest[1][0]['_archive']}` 的 "
             f"{len(widest[1])} 份文件指向同一地址。" if widest else ""))
        A("")
        A("故「唯一地址数」应读作**不同的信息出处**，不是「不同的页面」。"
          "按 `source_id` 数会虚高，按 URL 数会低估同一仓库内的独立文件——"
          "两个数都得看，见第 6 节。")
    else:
        A("两者相等：目前没有地址被重复登记。")
    A("")
    top_site = site_c.most_common(3)
    A("按站点看，最集中的三处是 "
      + "、".join(f"{s}（{n} 条）" for s, n in top_site)
      + f"，合计占 {sum(n for _, n in top_site) / len(uniq) * 100:.0f}%。")
    A("")
    acad_share = type_c.get("academic", 0) / len(uniq) * 100
    A(f"按性质看，学术来源 {type_c.get('academic', 0)} 条（{acad_share:.0f}%）、"
      f"社区 {type_c.get('community', 0)} 条、"
      f"官方 {type_c.get('official', 0)} 条。")
    A("")
    A("⚠️ **一个必须注意的口径**：`academic` 占比高，不代表每一篇都是文献综述。"
      "`rsi-inference-bench` 这类归档的锚点根本没有论文（仓库 README 写 "
      "`Paper: coming soon`），它的来源是 `official`——工程仓库原文。"
      "只看总表会以为全项目都以 arXiv 为检索面。"
      "**逐归档的分布见第 1 节**，那一节才能看出这个差别。")
    A("")

    A("## 1　逐归档")
    A("")
    A("| 归档 | 记录数 | 唯一地址 | 主要性质 |")
    A("|---|---|---|---|")
    for a in sorted(per_archive):
        tc = collections.Counter(
            r.get("source_type") or "" for r in rows if r["_archive"] == a)
        main_type = "、".join(f"{TYPE_LABEL.get(k, k)} {v}"
                             for k, v in tc.most_common(2))
        uniq_n = per_archive_uniq[a]
        # 记录数明显多于唯一地址时标一个记号：说明这一篇有「同一页面登记成
        # 多个 source」的情况（如一个仓库的 14 份文件）。不标的话，
        # 读者会以为 22 与 9 之间丢了 13 条数据。
        mark = " ⚠️" if per_archive[a] - uniq_n >= 3 else ""
        A(f"| `{a}` | {per_archive[a]} | {uniq_n}{mark} | {main_type} |")
    A(f"| **合计** | **{len(rows)}** | **{len(uniq)}** | — |")
    A("")
    flagged = [a for a in per_archive if per_archive[a] - per_archive_uniq[a] >= 3]
    if flagged:
        A("⚠️ 带记号的行表示「记录数远多于唯一地址」——"
          "这些归档把一个仓库的多份文件登记成了多个 source，"
          "每一份都是独立的证据来源，但共用一个 URL。"
          "明细见第 6 节归档内同名那一类。")
        A("")

    A("## 2　按来源性质（`source_type`）")
    A("")
    A("| 性质 | 唯一地址 | 占比 | 含义 |")
    A("|---|---|---|---|")
    for t, n in type_c.most_common():
        A(f"| `{t}` | {n} | {n / len(uniq) * 100:.1f}% | "
          f"{TYPE_LABEL.get(t, '（未在枚举内）')} |")
    A("")
    A("枚举定义见 [data-model.md](./data-model.md)。"
      "未出现在表里的类型表示目前一条都没有。")
    A("")

    A("## 3　按信任层级（`trust_tier`）")
    A("")
    A("| 层级 | 唯一地址 | 含义 |")
    A("|---|---|---|")
    for t in ("primary", "secondary", "tertiary"):
        A(f"| {TIER_LABEL[t]} | {tier_c.get(t, 0)} | "
          f"{'自行测量/发布该事实的那一方' if t == 'primary' else ''}"
          f"{'转述别人的观测' if t == 'secondary' else ''}"
          f"{'只做索引聚合' if t == 'tertiary' else ''} |")
    A("")
    A("⚠️ `trust_tier` 与 `source_type` **正交**：厂商自己的产品文档是 "
      "`vendor` + `primary`（它确实最先产生那些参数）；"
      "媒体转述同一份参数是 `press` + `secondary`。"
      "把权威性当来源性质是最常见的误标，见 data-model.md 的说明。")
    A("")

    A("## 4　按站点")
    A("")
    A("| 站点 | 唯一地址 | 说明 |")
    A("|---|---|---|")
    for s, n in site_c.most_common():
        A(f"| {s} | {n} | {SITE_NOTE.get(s, '')} |")
    A("")

    A("## 5　按发布年份")
    A("")
    A("| 年份 | 唯一地址 |")
    A("|---|---|")
    for y, n in sorted(year_c.items(), key=lambda kv: (kv[0] == "（未标日期）", kv[0])):
        A(f"| {y} | {n} |")
    A("")
    A("「未标日期」多是产品文档与论坛帖——它们没有发布日，只有抓取日"
      "（`fetched_at`）。这一类不能拿来做时间线分析。")
    A("")

    A("## 6　重复登记与冲突")
    A("")
    A(f"**同一地址被重复登记：{len(dup_only)} 组**"
      f"（多出 {sum(len(v) - 1 for v in dup_only.values())} 条记录），"
      f"其中跨归档 {len(cross)} 组、归档内同名 {len(intra)} 组。")
    A("")
    A("跨归档的那一类是**正常的**：一篇论文被两篇综述同时引用，本就该有两份记录。"
      "不正常的是同一地址在不同归档里被标了不同的 `source_type` 或 "
      "`trust_tier`——那样同一条证据的强度就取决于「你从哪个 id 数上去」。")
    A("")
    if conflicts:
        A(f"**当前存在 {len(conflicts)} 组类型/层级冲突**，需要人工裁决：")
        A("")
        A("| 地址 | 归档 → 标注 |")
        A("|---|---|")
        for k, v in sorted(conflicts.items()):
            cells = "；".join(
                f"`{x['_archive']}` → {x.get('source_type')}/{x.get('trust_tier')}"
                for x in v)
            A(f"| {k} | {cells} |")
    else:
        A(f"**当前 0 组类型/层级冲突**"
          f"（{len(dup_only)} 组重复地址的标注全部一致）。"
          "这一行是查过之后写的，不是省略。")
    A("")
    A("### 6.1　跨归档复用（同一篇被多篇引用）")
    A("")
    reuse = {k: v for k, v in cross.items() if n_arch(v) >= 2}
    if reuse:
        A("被两个以上归档同时引用的（说明它是这一族的地基）：")
        A("")
        A("| 地址 | 归档数 | 归档 |")
        A("|---|---|---|")
        for k, v in sorted(reuse.items(), key=lambda kv: (-n_arch(kv[1]), kv[0]))[:40]:
            A(f"| {k} | {n_arch(v)} | {', '.join(sorted({x['_archive'] for x in v}))} |")
        if len(reuse) > 40:
            A(f"| …… | | 另有 {len(reuse) - 40} 组，见 sources.csv |")
    else:
        A("暂无跨归档复用的地址。")
    A("")
    A("### 6.2　归档内同名（同一页面登记成多个来源）")
    A("")
    if intra:
        A("这些不是错误，但要知道「唯一地址数」为何低于「记录数」：")
        A("")
        A("| 归档 | 该地址下的来源数 | 地址 |")
        A("|---|---|---|")
        for k, v in sorted(intra.items(), key=lambda kv: -len(kv[1])):
            A(f"| `{v[0]['_archive']}` | {len(v)} | {k} |")
    else:
        A("暂无。")
    A("")

    A("## 7　全量清单")
    A("")
    A("按性质分组，组内按站点、再按标题排序。"
      "「归档」列写的是这条地址出现在哪些归档里——**一个地址只占一行**。")
    A("")
    order = [t for t, _ in type_c.most_common()]
    for t in order:
        group = sorted((u for u in uniq if u["type"] == t),
                       key=lambda u: (u["site"], u["title"].lower()))
        A(f"### {TYPE_LABEL.get(t, t)}（`{t}`，{len(group)} 条）")
        A("")
        A("| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |")
        A("|---|---|---|---|---|---|")
        for u in group:
            title = u["title"].replace("|", "\\|")
            if len(title) > 78:
                title = title[:77] + "…"
            pub = u["published"] or "—"
            if len(pub) > 10:
                pub = pub[:10]
            A(f"| {title} | {u['site']} | {pub} | {u['tier'] or '—'} | "
              f"{', '.join(u['archives'])} | {display_url(u['url'])} |")
        A("")

    text = "\n".join(L).rstrip() + "\n"

    if args.check:
        if not OUT.is_file():
            print(f"[FAIL] {OUT.relative_to(ROOT)} 不存在，先跑一次不带 --check")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(f"[FAIL] {OUT.relative_to(ROOT)} 与 sources.csv 不一致，需重新生成")
            return 1
        print(f"[OK]   {OUT.relative_to(ROOT)} 与 sources.csv 一致"
              f"（{len(uniq)} 个唯一地址 / {len(rows)} 条记录）")
        return 0

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"写入 {OUT.relative_to(ROOT)}")
    print(f"  {len(rows)} 条记录 → {len(uniq)} 个唯一地址"
          f"｜{len(per_archive)} 个归档｜{len(site_c)} 个站点"
          f"｜重复 {len(dup_only)} 组、冲突 {len(conflicts)} 组")
    return 0


if __name__ == "__main__":
    sys.exit(main())
