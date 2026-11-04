r"""生成参考文献节，让论文的每个来源可点击。

## 为什么必须加

第一次编译出的 PDF 有 0 条超链接、正文 0 处 URL。而论文开头声称
「46 篇论文 + 17 份官方文档」。读者无从核对任何一条。

这在本仓库的语境下是硬伤：整条流水线的核心价值就是「可回溯」，
而论文自己却不可回溯。

## 做法

从 sources.csv 生成 reference.tex：
  · 论文按 arXiv id 排序，官方文档按 publisher 分组
  · 每条带 \href 到原始 URL
  · 只列**被正文实际引用**的 claim 所依赖的来源，
    避免把 63 条全列上而其中一半与论证无关

## 为什么只列被引用的

sources.csv 有 63 条，但 c-* 六条主张用到的证据只覆盖其中一部分。
全列会让参考文献变成堆砌。故按 evidence -> source 反查，
只列真正支撑了某条主张的来源。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LATEX = HERE / "paper" / "latex"


def main() -> int:
    src = {r["source_id"]: r
           for r in csv.DictReader(
               (HERE / "sources.csv").open(encoding="utf-8", newline=""))}
    evidence = {r["evidence_id"]: r
                for r in csv.DictReader(
                    (HERE / "evidence.csv").open(encoding="utf-8",
                                                 newline=""))}
    claims = list(csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline="")))

    used_sids: set[str] = set()
    for c in claims:
        for eid in [x for x in c["evidence_ids"].split(";") if x]:
            e = evidence.get(eid)
            if e:
                used_sids.add(e["source_id"])

    papers, docs = [], []
    for sid in used_sids:
        s = src.get(sid)
        if not s:
            continue
        if s["source_type"] == "academic":
            papers.append(s)
        else:
            docs.append(s)

    def esc(t: str) -> str:
        t = t.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
        t = t.replace("#", r"\#")
        return t

    papers.sort(key=lambda s: s["published_at"] or "")
    docs.sort(key=lambda s: (s["publisher"], s["source_id"]))

    lines = [r"\section*{参考文献}", r"\begingroup",
             r"\footnotesize", r"\setlength{\parindent}{0pt}",
             r"\setlength{\parskip}{2.5pt}", ""]

    # 说明：只列被正文实际引用的来源。
    # 不说这句，读者会以为归档只有 23 个来源，而实际是 63 个——
    # 差额是检索与筛选过程的记录，留在 sources.csv 但不进参考文献。
    lines.append(r"\noindent 以下仅列\textbf{被正文实际引用}的来源（"
                 + str(len(used_sids)) + r" 个）；归档共 "
                 + str(len(src)) + r" 个来源，其余为检索与筛选过程的记录。\par")
    lines.append(r"\vspace{4pt}")

    lines.append(r"\noindent\textbf{学术论文}（"
                 + str(len(papers)) + r" 篇）\par")
    lines.append(r"\vspace{2pt}")
    for i, s in enumerate(papers, 1):
        aid = s["source_id"].replace("src-arxiv-", "").replace("-", ".")
        # 只保留形如 2401.09670 的 id（把 4 位-4 位还原成点分）
        m = re.match(r"(\d{4})-(\d{4,5})$", s["source_id"].replace(
            "src-arxiv-", ""))
        if m:
            aid = m.group(1) + "." + m.group(2)
        lines.append(
            f"[{i}] " + esc(s["title"]) + r" \href{" + s["url"] + "}{"
            + r"\texttt{arXiv:" + aid + r"}}"
            + (" (" + s["published_at"] + ")" if s["published_at"] else "")
            + r"\par")

    lines.append(r"\vspace{6pt}")
    lines.append(r"\noindent\textbf{官方文档与实现}（"
                 + str(len(docs)) + r" 份）\par")
    lines.append(r"\vspace{2pt}")
    for i, s in enumerate(docs, 1):
        # publisher 常常已包含在 title 里（如 "NVIDIA: NIXL ..."），
        # 直接拼会变成 "NVIDIA：NVIDIA: NIXL ..."。
        # 故 title 已以 publisher 开头时不再重复。
        ttl = s["title"]
        head = (s["publisher"] + ":").lower()
        prefix = "" if ttl.lower().startswith(head) else esc(s["publisher"]) + r"："
        lines.append(
            f"[{i}] " + prefix + esc(ttl)
            + r" \href{" + s["url"] + "}{"
            + r"\texttt{" + esc(s["url"].replace('https://', '')[:52])
            + r"}}\par")

    lines.append(r"\endgroup")

    out = LATEX / "references.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"references.tex：{len(papers)} 篇论文 + {len(docs)} 份文档")

    # 挂到 body.tex 末尾
    bp = LATEX / "body.tex"
    b = bp.read_text(encoding="utf-8")
    if "references.tex" not in b:
        b = b.rstrip() + "\n\n\\input{references.tex}\n"
        bp.write_text(b, encoding="utf-8", newline="\n")
        print("body.tex：已追加 \\input{references.tex}")
    else:
        print("body.tex：references 已挂载")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
