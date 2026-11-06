"""把 PDF 的每一页渲染成 PNG，供人眼检查版面。

## 为什么需要

自动校验（check_latex）只查六件可量化的事：字数、缺字、溢出、填充率、
完整性、图注同页。它查不出「表挤成一条线」「图注和图隔了一页」
这类**看得见但测不出**的问题。渲染成图是最后一关。

用法：
    python notes/render_pages.py            # 全部页
    python notes/render_pages.py 1 3 5      # 指定页
"""
import sys
from pathlib import Path
import pymupdf

PDF = Path(__file__).resolve().parent.parent / "paper" / "latex" / "main.pdf"
OUT = Path(__file__).resolve().parent / "pages"


def main() -> int:
    doc = pymupdf.open(PDF)
    OUT.mkdir(exist_ok=True)
    want = [int(a) for a in sys.argv[1:]] or range(1, doc.page_count + 1)
    for n in want:
        pix = doc[n - 1].get_pixmap(dpi=110)
        p = OUT / ("p" + str(n) + ".png")
        pix.save(p)
        print(p.name, pix.width, "x", pix.height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
