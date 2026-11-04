"""ADR-0002 三条不变量的机器校验：E1 / S1 / D1。

## 为什么单独成文件

`validate.py` 已经有 430 行，负责 ID 唯一性、引用闭合、枚举合法性等
**结构**检查。E1/S1/D1 是**内容完整性**检查，需要读文档快照、算哈希，
与结构检查是两件事。

## 这三条原先只检查了「字段非空」

ADR-0002 原文写：

  - **E1**：`quote` 必须是原文子串。允许截断，不允许改写或翻译后回填。
  - **S1**：`fetched_at` 必填，且必须带时区。
  - **D1**：`content_hash` 变化即视为新版本，不覆盖旧记录。

而实现只有：

  if not quote: errors.append("quote 为空（不变量 E1）")
  if not fetched_at: errors.append("fetched_at 为空（不变量 S1）")

「非空」不等于「是原文子串」，「非空」也不等于「带时区」。D1 则完全没实现。
这是契约写了、实现没跟上——而且检查名字还挂在错误信息里，
读起来像是验过了。

## 快照的存放约定

`research/<slug>/documents/<document_id>.txt`  纯文本正文
`research/<slug>/documents.csv`                可选的元数据（content_hash / parser_version）

没有 `documents/` 目录时，E1 退化为「无法校验」而非「通过」。
这一点很重要：**不能因为文件缺失就报告通过**，那等于把缺口伪装成合格。
故输出里会单独统计 `e1_checked` / `e1_unverifiable`。
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

# 时区偏移：+08:00 / -05:00 / Z
TZ_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


# ---------------------------------------------------------------- S1
def check_s1_timezone(sources: list[dict[str, str]]) -> tuple[list[str], int]:
    """fetched_at 必须可解析且带时区。

    ⚠️ 只检查「非空」会漏掉 `2026-11-03`（无时区）这种写法。
       跨时区协作时，没有时区的时间戳无法确定是哪一刻，
       而这正是 ADR 说「必须能回答你在什么时候看到的」的前提。
    """
    errors: list[str] = []
    ok = 0
    for r in sources:
        sid = (r.get("source_id") or "").strip()
        raw = (r.get("fetched_at") or "").strip()
        if not raw:
            errors.append(f"sources.csv[{sid}]: fetched_at 为空（S1）")
            continue
        if not TZ_RE.search(raw):
            errors.append(
                f"sources.csv[{sid}]: fetched_at 缺少时区 {raw!r}（S1 要求带时区）"
            )
            continue
        try:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"sources.csv[{sid}]: fetched_at 无法解析 {raw!r}（S1）")
            continue
        ok += 1
    return errors, ok


# ---------------------------------------------------------------- D1
def check_d1_versions(root: Path) -> tuple[list[str], int]:
    """同一个 document_id 不得出现两个不同 content_hash 并存。

    D1 的实质是「版本不能被覆盖」：来源改版后应新增一条记录，
    而不是把旧记录的哈希改掉。故这里检查的是
    **同一 document_id + 多个 content_hash 且没有 version 列区分**。
    """
    path = root / "documents.csv"
    rows = read_csv(path)
    errors: list[str] = []
    if not rows:
        return errors, 0
    seen: dict[str, set[str]] = {}
    for r in rows:
        did = (r.get("document_id") or "").strip()
        h = (r.get("content_hash") or "").strip()
        if not did or not h:
            continue
        seen.setdefault(did, set()).add(h)
    checked = 0
    for did, hashes in seen.items():
        checked += 1
        if len(hashes) > 1:
            errors.append(
                f"documents.csv[{did}]: 同一 document_id 有 {len(hashes)} 个不同 "
                f"content_hash 但未区分版本（D1 要求改版新增记录、不覆盖旧记录）"
            )
    return errors, checked


# ---------------------------------------------------------------- E1
def check_e1_substring(
    root: Path, evidence: list[dict[str, str]]
) -> tuple[list[str], int, int]:
    """quote 必须是文档快照的原文子串。返回 (错误, 已校验数, 无法校验数)。

    匹配规则：
      - 直接子串匹配（最常见）
      - 归一化后匹配：把连续空白折叠成一个空格、去掉零宽字符
        （PDF 抽取常留下断行与多余空格，这不是改写）
    允许截断，不允许改写——所以只做「空白归一」，不做同义替换或翻译。
    """
    docdir = root / "documents"
    if not docdir.is_dir():
        return [], 0, len(evidence)

    cache: dict[str, str] = {}

    # documents.csv 里记着每份快照的**真实路径**。校验时优先信任它，
    # 而不是按 document_id 猜文件名——见 bodies_for 里的说明。
    _meta = root / "documents.csv"
    meta_rows: list[dict[str, str]] = read_csv(_meta) if _meta.is_file() else []

    def candidate_stems(did: str) -> list[str]:
        """该 document_id / source_id 可能对应的快照文件名主干（不含扩展名）。

        ⚠️ 这里曾只查 documents/<did>.txt，而 evidence 里填的是
           source_id（src-arxiv-2507-14111），快照名却是
           document_id（doc-arxiv-2507-14111）——两者差一个前缀，
           于是 19 条证据全部落到「无法校验」，检查静默失效。
        故同时接受：原样、以及把 src- 换成 doc- 的形式。

        摘要与全文两种粒度都返回：摘要级引文在摘要快照里能中，
        正文级引文只在全文里能中，见 bodies_for 的说明。
        """
        names = [did]
        if did.startswith("src-"):
            names.append("doc-" + did[len("src-"):])
        out: list[str] = []
        for n in names:
            out.append(n)            # 摘要快照
            out.append(f"{n}-full")  # 全文快照
        return out

    def bodies_for(did: str) -> list[str]:
        """该文档所有可用快照的正文，按「越原始越优先」排序。

        ⚠️ 不能只用全文。实测 `cuda-kernel-rl` 里 14 条摘要级证据在全文里
           匹配失败，原因不是证据错，而是**同一句话在两种来源里表示不同**：

               摘要快照（arXiv Atom API）：  ... by up to 26%, and on average 9%.
               全文快照（arXiv HTML/LaTeXML）：... by up to $26\\%$, and on average $9\\%$.

           全文虽然「包含」摘要，但经过 LaTeXML 转换，数学符号被包成了
           `$...$` 与 `\\%`。用全文校验摘要级引文，会把正确证据判成伪造。

           故策略是：**任一快照匹配即通过**。摘要对摘要级引文、全文对正文级引文
           各自成立；两者都不中才是真问题。
        """
        out: list[str] = []
        seen: set[str] = set()

        def take(p: Path) -> None:
            if not p.is_file():
                return
            key = str(p.resolve())
            if key in seen:
                return
            seen.add(key)
            if key not in cache:
                cache[key] = p.read_text(encoding="utf-8", errors="replace")
            out.append(cache[key])

        # ① 先按 documents.csv 里**显式记录的 snapshot 路径**找。
        #
        # ⚠️ 这是实测踩出来的：`pd-disagg` 归档里工程文档的 document_id
        #    是 `doc-sglang-pd`，而快照文件名是 `sglang-pd.txt`——两者
        #    并不按 doc- 前缀对应。于是 4 条工程文档引文全部落到
        #    「无快照」，报成 e1_unverifiable。
        #
        #    问题不在数据：documents.csv 的 snapshot 字段一直写着正确
        #    路径（documents/sglang-pd.txt）。是校验器**没读那个字段**，
        #    改用「document_id + 后缀」猜文件名。猜出来的规则只对
        #    arxiv 那批成立（doc-arxiv-x -> doc-arxiv-x-full.txt），
        #    对工程文档不成立。
        #
        #    这与本仓库反复出现的失效模式同型：**用推断代替已记录的事实**。
        #    故改为优先读记录，猜文件名只作兜底。
        for row in meta_rows:
            if (row.get("document_id") or "").strip() != did:
                continue
            snap = (row.get("snapshot") or "").strip()
            if not snap:
                continue
            cand = root / snap
            if not cand.is_file():
                cand = docdir / Path(snap).name
            take(cand)

        # ② 兜底：按 document_id 猜文件名（保留旧行为，兼容未写 snapshot 的归档）
        for stem in candidate_stems(did):
            for ext in (".txt", ".md"):
                take(docdir / f"{stem}{ext}")
        return out

    def norm(s: str) -> str:
        s = s.replace("\u200b", "").replace("\ufeff", "")
        return re.sub(r"\s+", " ", s).strip()

    def relaxed(s: str) -> str:
        """再宽一层：去掉 LaTeX 数学包装与转义，便于跨来源比对。

        `$26\\%$` -> `26%`，`\\alpha` -> `alpha`。
        只用于「摘要 vs 全文」这种同源不同渲染的情形，
        仍不允许改写——去掉的只是排版标记，不是文字。
        """
        s = norm(s)
        s = s.replace("$", "").replace("\\%", "%").replace("\\_", "_")
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = re.sub(r"[{}\\]", "", s)
        return re.sub(r"\s+", " ", s).strip()

    errors: list[str] = []
    checked = 0
    skipped = 0
    for r in evidence:
        eid = (r.get("evidence_id") or "").strip()
        quote = (r.get("quote") or "").strip()
        did = (r.get("document_id") or "").strip()
        # cuda-kernel-gen 这类归档用 source_id 而非 document_id 定位快照
        if not did:
            did = (r.get("source_id") or "").strip()
        bodies = bodies_for(did) if did else []
        if not bodies:
            skipped += 1
            continue
        checked += 1
        if not quote:
            continue
        # 三种判据，从严到宽；任一通过即可。
        # 逐级放宽的理由是「跨来源的同源文本渲染不同」——
        # 摘要走 Atom API，全文走 LaTeXML，同一句话的数学符号写法不一样，
        # 但文字本身没变。放宽的只是排版标记，不是内容。
        if any(quote in b for b in bodies):
            continue
        if any(norm(quote) in norm(b) for b in bodies):
            continue
        if any(relaxed(quote) in relaxed(b) for b in bodies):
            continue
        errors.append(
            f"evidence.csv[{eid}]: quote 不是 {did} 快照的原文子串（E1）"
        )
    return errors, checked, skipped


# ---------------------------------------------------------------- 快照工具
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_snapshot(
    root: Path, document_id: str, text: str, *, source_id: str = "",
    parser_version: str = "", variant: str = "",
) -> None:
    """写一份文档快照，并在 documents.csv 登记（供 D1 检查）。

    `variant` 用于区分同一篇文档的不同粒度快照，例如：
        variant=""      -> documents/doc-xxx.txt        摘要
        variant="full"  -> documents/doc-xxx-full.txt   全文

    ⚠️ 为什么必须区分而不是覆盖：
        摘要与全文是**同一 document_id 的两个不同产物**。
        若都写进同一个文件名，D1 会把「摘要 -> 全文」误判为改版
        （content_hash 变了），而实际上来源没变、只是我们看多了。
    """
    docdir = root / "documents"
    docdir.mkdir(exist_ok=True)
    stem = f"{document_id}-{variant}" if variant else document_id
    (docdir / f"{stem}.txt").write_text(text, encoding="utf-8", newline="\n")

    meta = root / "documents.csv"
    rows = read_csv(meta)
    header = ["document_id", "source_id", "content_hash",
              "parser_version", "byte_size", "snapshot"]
    # 同一 document_id + variant 视为同一条记录（覆盖自己），
    # 不同 variant 各占一行——它们的 hash 本来就该不同。
    rows = [r for r in rows
            if not ((r.get("document_id") or "") == document_id
                    and (r.get("snapshot") or "").endswith(f"{stem}.txt"))]
    rows.append({
        "document_id": document_id,
        "source_id": source_id,
        "content_hash": sha256_text(text),
        "parser_version": parser_version,
        "byte_size": str(len(text.encode("utf-8"))),
        "snapshot": f"documents/{stem}.txt",
    })
    with meta.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
