"""硬核对：把 claims.csv 里每条主张的数值与 cite 逐条对回证据原文。

## 它与 scripts/audit_paper.py 的区别

audit_paper.py 核对的是 paper/data/*.csv 里的数值；本脚本核对的是
claims.csv 的 statement 里的数值。两者查的是不同文件，都会漂：
论文的数据层可以完全正确，而 claims 的陈述句里写了一个错数——
那种错误只出现在报告与论文的正文叙述里。

## 判据

对每条主张，逐个提取 statement 里的数字（百分比、倍数、计数），
然后要求它出现在：claim 的 evidence/quotes、derivation 或 notes 之一。
找不到就报错。这条判据很弱（同一个数可以来自别处），但它能挡住
最常见的错误：把 1.32x 写成 2.32x。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")


def read_csv(p: Path) -> list[dict[str, str]]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def variants(raw: str) -> set[str]:
    try:
        v = float(raw)
    except ValueError:
        return {raw}
    out = {f"{v:g}", raw}
    if v == int(v):
        out.add(str(int(v)))
        out.add(f"{int(v):,}")
    else:
        out.add(f"{v:.2f}".rstrip("0").rstrip("."))
    return out


def main() -> int:
    claims = read_csv(HERE / "claims.csv")
    evidence = {r["evidence_id"]: r for r in read_csv(HERE / "evidence.csv")}
    bad = 0
    checked = 0
    for c in claims:
        body = " ".join([c.get("statement") or "", c.get("derivation") or "",
                         c.get("notes") or ""])
        qtext = " ".join(evidence[e]["quote"] for e in
                          (c.get("evidence_ids") or "").split(";")
                          if e.strip() in evidence)
        hay = body.replace(",", "") + " " + qtext.replace(",", "")
        for m in NUM_RE.finditer(c.get("statement") or ""):
            raw = m.group(1)
            vs = variants(raw)
            checked += 1
            if not any(v in hay for v in vs):
                print(f"  [?] {c['claim_id']}: 数值 {raw} 在证据/推导/备注里都找不到")
                bad += 1
    print(f"\n核对 {checked} 个数值，可疑 {bad} 个")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
