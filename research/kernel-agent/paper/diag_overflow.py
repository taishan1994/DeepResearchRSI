"""诊断 PDF 里的行溢出：打印溢出的具体文字与坐标。

## 为什么单独做

`check_pdf.py` 只报「22 个片段越过右边界」，但不说**越的是什么**。
修排版时必须知道是正文、图注、表格还是公式——四者的修法完全不同。

## 判据

版心右边界 = 页宽 - 左右边距。A4 宽 595.28pt，margin=2.05cm=58.1pt，
故右边界约 537pt。超出的片段逐个打印：
  页码、x 终点、超出量、文字内容（截断到 40 字）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

PDF = Path(__file__).resolve().parent / "latex" / "main.pdf"


def main() -> int:
    doc = pymupdf.open(PDF)
    right_limit = doc[0].rect.width - 58.1
    print(f"页宽 {doc[0].rect.width:.1f}pt，右边界 {right_limit:.1f}pt\n")

    total = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        hits = []
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    x1 = span["bbox"][2]
                    if x1 > right_limit + 2.5:
                        hits.append((x1, span["text"]))
        if hits:
            print(f"--- 第 {pno + 1} 页：{len(hits)} 处 ---")
            for x1, txt in hits:
                total += 1
                over = x1 - right_limit
                print(f"  +{over:5.1f}pt  {txt[:56]}")
    print(f"\n合计 {total} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
