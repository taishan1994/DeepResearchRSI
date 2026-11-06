import pymupdf
d = pymupdf.open(r"D:\github\DeepResearchRSI\research\rsi-model-training\paper\latex\main.pdf")
for i in (8,9):
    print("="*16,"page",i+1)
    print(repr(d[i].get_text()[:1500]))
