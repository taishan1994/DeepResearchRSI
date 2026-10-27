"""安全地追加 CSV 行：读入 → 校验列数 → 写临时文件 → 替换。

不用 DictWriter，避免表头 BOM/引号不一致导致的字段丢失。
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path


def append_rows(csv_path: Path, new_rows_path: Path) -> int:
    raw = csv_path.read_text(encoding="utf-8-sig")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    header_line = lines[0]
    body = lines[1:]

    ncols = len(next(csv.reader(io.StringIO(header_line))))

    new_lines = [
        ln for ln in new_rows_path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()
    ]
    for i, ln in enumerate(new_lines, 1):
        got = len(next(csv.reader(io.StringIO(ln))))
        if got != ncols:
            raise SystemExit(f"第 {i} 行列数为 {got}，期望 {ncols}：{ln[:100]}")

    out = header_line + "\n" + "\n".join(body + new_lines) + "\n"
    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    tmp.write_text(out, encoding="utf-8-sig", newline="")
    tmp.replace(csv_path)
    return len(new_lines)


if __name__ == "__main__":
    target = Path(sys.argv[1])
    src = Path(sys.argv[2])
    n = append_rows(target, src)
    print(f"追加 {n} 行到 {target}")
