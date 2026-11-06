from pathlib import Path
import pymupdf
HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent
d = pymupdf.open(ARCHIVE / "paper" / "latex" / "main.pdf")
for i in (8,9):
    print("="*16,"page",i+1)
    print(repr(d[i].get_text()[:1500]))
