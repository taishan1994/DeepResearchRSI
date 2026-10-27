"""修复 CSV 中因英寸符号（"）导致的列错位。

策略：按列数判断。多出列的行，把溢出部分并回 quote 列并转义英寸符号为 U+2033（双撇号）。
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

INCH = "\u2033"  # ″


def repair(path: Path) -> int:
    raw = path.read_text(encoding="utf-8-sig")
    reader = csv.reader(io.StringIO(raw))
    rows = [r for r in reader if r]
    header, body = rows[0], rows[1:]
    ncols = len(header)
    fixed = 0
    out_rows = []
    for r in body:
        if len(r) != ncols:
            # 把多出的片段合并回索引 3（quote 列），并把 " 换成 ″
            merged = r[:3] + [",".join(r[3:len(r) - 3])] + r[len(r) - 3:]
            if len(merged) != ncols:
                raise SystemExit(f"无法修复：{len(r)} 列 -> {len(merged)} 列，期望 {ncols}: {r[:4]}")
            merged[3] = merged[3].replace('"', INCH)
            r = merged
            fixed += 1
        out_rows.append([c.replace('"', INCH) if '"' in c else c for c in r])

    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(header)
    w.writerows(out_rows)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8-sig", newline="")
    tmp.replace(path)
    return fixed


if __name__ == "__main__":
    for p in sys.argv[1:]:
        n = repair(Path(p))
        print(f"{p}: 修复 {n} 行")
