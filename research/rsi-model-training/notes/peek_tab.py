from pathlib import Path
import pymupdf
HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent
d = pymupdf.open(ARCHIVE / "paper" / "latex" / "main.pdf")
for i in range(d.page_count):
    t = d[i].get_text()
    if "表" in t and ("上下文" in t or "阶段" in t or "失效" in t):
        print("="*14,"page",i+1)
        print(t[:1400])
        break
print("### table captions across doc:")
allt = "".join(d[i].get_text() for i in range(d.page_count))
import re
for m in re.finditer(r"表\s*\d+[^\n]{0,60}", allt):
    print("  ", m.group(0)[:80])
