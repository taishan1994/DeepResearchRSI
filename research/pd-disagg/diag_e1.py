"""定位 e1_unverifiable 的 4 条证据。

## 为什么要单独查

validate 返回 `e1_unverifiable=4`，但只给总数，不说哪 4 条。
按本仓库的规矩，「未校验」必须能指认到具体条目——否则它和
「通过」在报告里长得一样，而这正是最危险的失效方式。

## 做法

复现 invariants 的匹配逻辑：对每条证据，在它的候选快照里找 quote
（含空白归一化）。找不到的即为 unverifiable，并打印差异位置。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))


def relaxed(s: str) -> str:
    """空白归一 + 去零宽字符（与 invariants 同义）。"""
    s = s.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    docs = {r["document_id"]: r
            for r in csv.DictReader(
                (ARCH / "documents.csv").open(encoding="utf-8", newline=""))}
    ev = list(csv.DictReader(
        (ARCH / "evidence.csv").open(encoding="utf-8", newline="")))

    missing = []
    for r in ev:
        did = r["document_id"]
        names = [did]
        if did.startswith("src-"):
            names.append("doc-" + did[len("src-"):])
        bodies = []
        for n in names:
            for suf in ("", "-full"):
                p = ARCH / "documents" / f"{n}{suf}.txt"
                if p.is_file():
                    bodies.append(p.read_text(encoding="utf-8",
                                              errors="replace"))
        if not bodies:
            missing.append((r["evidence_id"], did, "无快照"))
            continue

        q = relaxed(r["quote"])
        hit = any(q in relaxed(b) for b in bodies)
        if not hit:
            # 找最长公共前缀，定位从哪开始不同
            b = relaxed(bodies[0])
            lo, hi = 0, min(len(q), len(b))
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if q[:mid] in b:
                    lo = mid
                else:
                    hi = mid - 1
            missing.append((r["evidence_id"], did,
                            f"前 {lo} 字符匹配，之后分歧"))

    print(f"共 {len(ev)} 条证据，无法校验 {len(missing)} 条")
    for eid, did, why in missing:
        print(f"  {eid}  {did}  {why}")
        row = next(x for x in ev if x["evidence_id"] == eid)
        print(f"      引文前 120: {row['quote'][:120]}")
        print(f"      引文后 80:  {row['quote'][-80:]}")
        print(f"      出处: {row['note'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
