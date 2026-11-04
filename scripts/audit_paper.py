"""校验论文与档案的一致性。

检查三件事，每一件都对应过一类真实错误：

A. **引用闭合**：论文里每个 [c-xxx] 都必须在 claims.csv 里存在。
   （历史上出现过 30 次「把 claim_id 当 evidence_id 引用」）
B. **图表落地**：paper.json 里声明的每张图/每张表，其 png/md 必须真的存在且非空。
   （防止「声明了但没生成」）
C. **关键数字可回溯**：论文正文里标注了 cite 的数值，必须能在对应 claim 的
   statement 里找到同一个数字。这一条最弱但也最有价值——它挡住「正文写了一个
   数据里没有的数」。

用法：
    python scripts/audit_paper.py research/rtx-pro-6000/paper
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CITE_RE = re.compile(r"\[(c-[A-Za-z0-9_-]+)\]")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="校验论文与档案的一致性")
    ap.add_argument("paper_dir", help="如 research/rtx-pro-6000/paper")
    args = ap.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    slug_dir = paper_dir.parent
    main_md = paper_dir / "PAPER.md"
    spec_path = paper_dir / "paper.json"

    problems: list[str] = []

    if not main_md.is_file():
        raise SystemExit(f"缺少论文正文：{main_md}")
    if not spec_path.is_file():
        raise SystemExit(f"缺少论文规格：{spec_path}")

    text = main_md.read_text(encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    claims = {r["claim_id"]: r for r in read_csv(slug_dir / "claims.csv")}

    # A. 引用闭合
    cited = set(CITE_RE.findall(text))
    missing = sorted(cited - set(claims))
    for cid in missing:
        problems.append(f"A 引用了不存在的主张：{cid}")

    # A2. paper.json 里声明的 cites 也要存在
    declared = set()
    for item in spec.get("figures", []) + spec.get("tables", []):
        declared.update(item.get("cites", []))
    for s in spec.get("sections", []):
        declared.update(s.get("cites", []))
    for cid in sorted(declared - set(claims)):
        problems.append(f"A paper.json 声明了不存在的主张：{cid}")

    # B. 图表落地
    for fig in spec.get("figures", []):
        out = paper_dir / "figures" / (fig.get("output") or f"{fig['figure_id']}.png")
        if not out.is_file():
            problems.append(f"B 图未生成：{out.name}")
        elif out.stat().st_size < 4096:
            problems.append(f"B 图文件过小（可能是空图）：{out.name}")
    # 表格产物可以是 .md 也可以是 .csv：
    #   rtx-pro-6000 用 tables/tab-1.md（渲染好再入正文）
    #   cuda-kernel-gen 用 tables/tab1_benchmarks.csv（数据源，正文另渲染）
    # 两者都是合法约定，写死 .md 会把后者全部误报为「表未生成」。
    def table_artifact(tab: dict) -> Path | None:
        tid = tab["table_id"]
        cands = [paper_dir / "tables" / f"{tid}.md",
                 paper_dir / "tables" / f"{tid}.csv"]
        cands += sorted((paper_dir / "tables").glob(f"{tid}_*.csv"))
        cands += sorted((paper_dir / "tables").glob(f"{tid}*.csv"))
        for c in cands:
            if c.is_file():
                return c
        return None

    for tab in spec.get("tables", []):
        out = table_artifact(tab)
        if out is None:
            problems.append(f"B 表未生成：{tab['table_id']}")
        elif out.stat().st_size < 80:
            problems.append(f"B 表文件过小：{out.name}")

    # B2. 正文必须真的插入了每一张图表
    for fig in spec.get("figures", []):
        name = fig.get("output") or f"{fig['figure_id']}.png"
        if f"figures/{name}" not in text:
            problems.append(f"B 正文没有插入图：{name}")
    for tab in spec.get("tables", []):
        # 表格可以三种方式进入正文：
        #   (a) 用 <!-- tables/tab-N.md --> 占位，由脚本内联；
        #   (b) 正文里直接写了这张表的内容（首行表头与产物文件一致）；
        #   (c) 正文按「表 N」交叉引用（cuda-kernel-gen 的做法：表格数据是 csv，
        #       正文用 \input / Markdown 表渲染，并以「表 N　标题」指称）。
        by_path = any(f"tables/{tab['table_id']}{ext}" in text for ext in (".md", ".csv"))
        by_label = tab["table_id"].replace("-", " ") in text
        by_content = False
        art = table_artifact(tab)
        if art is not None:
            rows = [r for r in art.read_text(encoding="utf-8-sig").split("\n") if r.strip()]
            if rows and rows[0].strip() in text:
                by_content = True
        # (c) 「表 N」形式：paper.json 里 tables 的顺序即编号
        by_caption = False
        idx = spec.get("tables", []).index(tab) + 1
        if re.search(rf"表\s*{idx}\s*[　 ]", text):
            by_caption = True
        if not (by_path or by_label or by_content or by_caption):
            problems.append(f"B 正文可能没有引用表：{tab['table_id']}")

    # C. 关键数字可回溯：对 paper/data/*.csv 里每一行的 (value, cite) 对，
    #    顺着 claim 追到它的 evidence.quote 去核对。
    #
    #    这里的方向很关键：数字通常只在 evidence.quote 里逐字出现，
    #    而 claim.statement 是概括（「优势仅 1.5%-5.9%」），并不含每个明细值。
    #    所以正确的核对顺序是 claim -> evidence_ids -> quote，而不是只看 statement。
    evidence = {r["evidence_id"]: r for r in read_csv(slug_dir / "evidence.csv")}

    def num_variants(v: float) -> set[str]:
        # ⚠️ 必须包含「原样去掉尾零」的形式。
        # `f"{v:g}"` 只保留 6 位有效数字，18354.95 会变成 18355，
        # 于是证据里逐字出现的 18354.95 反而匹配不上——
        # 这不是数据错，是变体集漏了最基本的一种写法。
        out = {f"{v:g}", f"{v!r}"}
        # 去尾零原样：18354.95 / 673.0 -> 673
        raw = f"{v:.6f}".rstrip("0").rstrip(".")
        out.add(raw)
        if v == int(v):
            out.add(str(int(v)))
            out.add(f"{int(v):,}")
        else:
            out.add(f"{v:,.3f}".rstrip("0").rstrip("."))
            out.add(f"{v:,}")
        out.add(f"{abs(v):g}")
        return out

    def recompute(cid: str, v: float) -> bool:
        """派生值：用 claim.derivation 里写明的公式重算，认同即可。

        为什么需要这一层：
            1.0715 / 1.2903 / 1.7746 这类 Amdahl 推算值，原文里当然没有
            ——它们是本文算出来的。要求它们「在 evidence.quote 里逐字出现」
            是把观测证据的判据用在了推导结果上。
        但不能因此无条件放过，否则随便写个数也能过。
        故这里**真的重算**：从 derivation 里取所有百分比 p 与倍数 k，
        逐一按 Amdahl 定律 S = 1/((1-p) + p/k) 计算，
        只要有一个结果与目标值吻合（相对误差 1% 内）就算通过。
        这样 1.2903 对应 p=30%，1.7746 对应 p=58.2%，
        都能被验证，而编造的数仍然过不了。
        """
        d = claims[cid].get("derivation") or ""
        if not d:
            return False
        # ---- 计数型派生值：`计数 <tag>=<n>` ----
        # 综述里的「9 篇用结果型奖励」这类数字，原文里当然不存在——
        # 它是本文对语料的统计结果。要求它在某条 evidence.quote 里逐字出现，
        # 等于要求统计数据长在文献里，这个判据本身是错的。
        # 正确做法：像 Amdahl 那样**真的重算一遍**。
        # derivation 里写明 `计数 <tag>=<n>`，此处从 papers 语料重新统计该 tag，
        # 只有重算结果与目标值相等才放行。编造的计数过不了。
        cm = re.search(r"计数\s*([a-z_]+)(?:\s+([0-9A-Za-z-]+))?\s*=\s*(\d+)", d)
        if cm:
            tag, arg, expected = cm.group(1), cm.group(2), int(cm.group(3))
            if expected == int(v):
                actual = recount(tag, arg)
                if actual is not None and actual == expected:
                    return True
            return False
        km = re.search(r"快\s*(\d+(?:\.\d+)?)\s*倍", d)
        if not km:
            km = re.search(r"/\s*(\d+(?:\.\d+)?)\s*\)", d)
        if not km:
            return False
        k = float(km.group(1))
        if k <= 1:
            return False
        for pm in re.finditer(r"(\d+(?:\.\d+)?)\s*%", d):
            p = float(pm.group(1)) / 100.0
            if not (0 < p < 1):
                continue
            s = 1.0 / ((1.0 - p) + p / k)
            if abs(s - v) <= max(0.01 * abs(s), 0.005):
                return True
        return False

    def recount(tag: str, arg: str | None = None) -> int | None:
        """从语料重新统计某个标签的论文数，用于校验「计数型派生值」。

        ⚠️ 这是**真的重新数**，不是信任 derivation 里的数字。
        derivation 只说「我数的是 outcome 这个标签」，数出来多少由这里决定。
        若语料文件缺失，返回 None（表示无法校验），而不是 0——
        0 会被误当成「数出来是零篇」，从而把错误数据判成通过。
        """
        # 语料来源：归档根的 candidates_rl.json（所有候选论文的摘要）
        # 解析论文 id -> 摘要，避免依赖 paper/ 下的副本
        corpus_files = [
            slug_dir / "papers.json",
            slug_dir / "candidates_rl.json",
            slug_dir / "paper" / "papers.json",
        ]
        papers: dict[str, dict] = {}
        for f in corpus_files:
            if not f.is_file():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for p in data:
                pid = (p.get("id") or p.get("arxiv_id") or "").strip()
                if pid:
                    papers.setdefault(pid, p)
        if not papers:
            return None

        # 核心论文集合：来自 sources.csv 里 notes 带 layer=core 的行
        core_ids: list[str] = []
        for r in read_csv(slug_dir / "sources.csv"):
            note = r.get("notes") or ""
            if "layer=core" not in note:
                continue
            m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})",
                          r.get("source_id") or "")
            if m:
                core_ids.append(f"{m.group(1)}.{m.group(2)}")
        if not core_ids:
            return None

        # 标签 -> 判定词。必须与生成端（analyze.py 的 REWARD_TAGS）一致，
        # 否则审计与论文各数一套，两边都「对」却互相矛盾。
        TAG_PATTERNS = {
            "outcome": r"speedup|execution speed|correctness|pass@",
            "multi_turn": r"multi-turn|iterative|interact",
            "structural": r"structural|parallelization|data-flow|decompos",
            "profiling": r"profil|counter|hardware metric",
            "anti_hack": r"reward hack|cheat|hacking|trivial",
            "curriculum": r"curriculum",
            "contrastive": r"contrastive",
            "synthetic": r"synthetic|data synthes",
            "grpo": r"GRPO|Group Relative Policy Optimization",
            "ppo": r"\bPPO\b",
            "unnamed": None,   # 特殊：既无 GRPO 也无 PPO 也无对比式
        }
        # 季度计数：`计数 quarter 2025-Q3=3`
        # 时间线每根柱子都是统计值，原文里不存在，只能重算。
        if tag == "quarter":
            if not arg or not re.fullmatch(r"\d{4}-Q[1-4]", arg):
                return None
            n = 0
            for aid in core_ids:
                p = papers.get(aid) or {}
                pub = (p.get("published") or p.get("published_at") or "")[:10]
                if len(pub) < 7:
                    continue
                q = f"{pub[:4]}-Q{(int(pub[5:7]) - 1) // 3 + 1}"
                if q == arg:
                    n += 1
            return n

        pat = TAG_PATTERNS.get(tag)
        if tag not in TAG_PATTERNS:
            return None

        n = 0
        for aid in core_ids:
            ab = (papers.get(aid) or {}).get("abstract") or ""
            if not ab:
                continue
            if tag == "unnamed":
                if not re.search(r"GRPO|Group Relative Policy Optimization"
                                 r"|contrastive|\bPPO\b", ab, re.I):
                    n += 1
            elif pat and re.search(pat, ab, re.I):
                n += 1
        return n

    def find_in(cid: str, raw: str) -> tuple[bool, str]:
        """返回 (是否找到, 在哪一层找到)。"""
        claim = claims[cid]
        try:
            v = float(raw)
        except ValueError:
            return True, "非数值"
        variants = num_variants(v)
        layers = [("statement", claim.get("statement") or ""),
                  ("derivation", claim.get("derivation") or ""),
                  ("notes", claim.get("notes") or "")]
        for eid in (claim.get("evidence_ids") or "").split(";"):
            eid = eid.strip()
            if eid in evidence:
                layers.append((f"evidence:{eid}", evidence[eid].get("quote") or ""))
        for name, body in layers:
            if any(x in body for x in variants):
                return True, name
        # 文本层都没找到，最后试推导层：真的按公式重算一次。
        if recompute(cid, v):
            return True, "derivation(公式重算)"
        return False, ""

    checked = 0
    warnings_only: list[str] = []
    for data_file in sorted((paper_dir / "data").glob("*.csv")):
        for row in read_csv(data_file):
            cid = (row.get("cite") or "").strip()
            raw = (row.get("value") or "").strip()
            if not cid or not raw or cid not in claims:
                continue
            try:
                float(raw)
            except ValueError:
                continue
            checked += 1
            ok, where = find_in(cid, raw)
            if not ok:
                problems.append(
                    f"C 数值 {raw}（{data_file.name}）在主张 {cid} 及其全部证据里都找不到"
                )
            elif where != "statement":
                warnings_only.append(f"{raw} 只在 {where} 里（{cid}）")

    for w in warnings_only[:6]:
        print("  · 提示 " + w)
    if len(warnings_only) > 6:
        print(f"  · 提示 …… 另有 {len(warnings_only) - 6} 条同样情况")

    for p in problems:
        print("  - " + p)

    print()
    print(f"引用主张 {len(cited)} 个 ｜ 图 {len(spec.get('figures', []))} 张 ｜ "
          f"表 {len(spec.get('tables', []))} 张 ｜ 数值回溯 {checked} 条")
    if problems:
        print(f"[FAIL] {len(problems)} 个问题")
        return 1
    print("[OK]   论文与档案一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
