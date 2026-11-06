"""生成参考文献节：从 sources.csv 取被正文实际引用的来源，输出 references.tex。

## 为什么要脚本生成

文献表是最容易出错的地方：标题抄漏一个词、链接少一位数字、53 条里漏掉一条，
肉眼都看不出来，而读者一点就发现。故直接从 CSV 生成，不经过人手。

## 为什么只列被引用的

sources.csv 有 53 条，全部列上会让参考文献变成堆砌。按
claim -> evidence -> source 反查，只列真正支撑了某条主张的来源，
再与正文里实际出现的 [c-*] 取交集——正文没提的主张，不该在文献表里出现。

## 编号与正文的对应

正文里的 [c-xxx] 是**主张**编号，不是文献编号；文献表按首次出现顺序编号。
两级各司其职：主张是可争议的判断，文献是它引用的原文。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent   # research/rsi-model-training
LATEX = HERE / "paper" / "latex"
PAPER = HERE / "paper" / "PAPER.md"


def esc(t: str) -> str:
    t = t.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"),
                 ("$", r"\$")):
        t = t.replace(a, b)
    return t


def arxiv_id(source_id: str) -> str:
    sid = source_id.replace("src-arxiv-", "")
    m = re.match(r"(\d{4})-(\d{4,5})$", sid)
    return m.group(1) + "." + m.group(2) if m else sid


def main() -> int:
    src = {r["source_id"]: r for r in csv.DictReader(
        (HERE / "sources.csv").open(encoding="utf-8-sig", newline=""))}
    ev = {r["evidence_id"]: r for r in csv.DictReader(
        (HERE / "evidence.csv").open(encoding="utf-8-sig", newline=""))}
    claims = {r["claim_id"]: r for r in csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8-sig", newline=""))}

    text = PAPER.read_text(encoding="utf-8")
    cited = set(re.findall(r"\[(c-[A-Za-z0-9_-]+)\]", text))

    # claim -> evidence -> source，只保留正文真的引用了的主张
    used: dict[str, set[str]] = {}
    for cid in cited:
        c = claims.get(cid)
        if not c:
            continue
        for eid in [x.strip() for x in (c.get("evidence_ids") or "").split(";")]:
            e = ev.get(eid)
            if e and e["source_id"] in src:
                used.setdefault(e["source_id"], set()).add(cid)

    # 按首次出现顺序排：先扫正文里的主张，记录其来源的首次命中位置，
    # 避免按字母序排出一份与论证无关的清单。
    order: list[str] = []
    for m in re.finditer(r"\[(c-[A-Za-z0-9_-]+)\]", text):
        c = claims.get(m.group(1))
        if not c:
            continue
        for eid in [x.strip() for x in (c.get("evidence_ids") or "").split(";")]:
            e = ev.get(eid)
            sid = e["source_id"] if e else None
            if sid in used and sid not in order:
                order.append(sid)

    lines = [r"\section*{参考文献}", r"\begingroup", r"\scriptsize",
             r"\setlength{\parindent}{0pt}", r"\setlength{\parskip}{1.6pt}",
             r"\begin{refs}"]
    # ⚠️ 只有当「被引用的」少于「归档的」时，才需要解释差额去了哪。
    # 本档当前是 53/53 全被引用，写「其余为检索记录」会凭空暗示有未列出的来源。
    extra = len(src) - len(order)
    tail = ("其余为检索与筛选过程的记录。" if extra > 0
            else "即归档全部。")
    lines.append(
        r"\noindent 下列 " + str(len(order)) + r" 个来源被正文实际引用；"
        r"归档共 " + str(len(src)) + r" 个（\texttt{sources.csv}），" + tail +
        r"每条标题后的方括号是它支撑的主张编号。"
        r"\par")
    lines.append(r"\vspace{3pt}")

    for i, sid in enumerate(order, 1):
        s = src[sid]
        aid = arxiv_id(sid)
        cids = sorted(used[sid])
        tags = " ".join("[" + c + "]" for c in cids)
        lines.append(
            "[" + str(i) + "] " + esc(s["title"])
            + r" \href{" + s["url"] + r"}{\texttt{arXiv:" + aid + "}}"
            + " " + esc(tags) + r"\par")

    lines.append(r"\end{refs}")
    lines.append(r"\endgroup")

    LATEX.mkdir(parents=True, exist_ok=True)
    out = LATEX / "references.tex"
    out.write_text(NL.join(lines) + NL, encoding="utf-8", newline=NL)
    print(f"[OK]   references.tex  {len(order)} 个来源（归档 {len(src)}）")
    return 0


NL = chr(10)

if __name__ == "__main__":
    raise SystemExit(main())
