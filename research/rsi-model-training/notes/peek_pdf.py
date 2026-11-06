import pymupdf
d = pymupdf.open(r"D:\github\DeepResearchRSI\research\rsi-model-training\paper\PAPER.pdf")
print("pages", d.page_count)
for i in range(d.page_count):
    t = d[i].get_text()
    print(i+1, len(t), " / ".join(t.split("\n")[1:2])[:60])
print("="*40)
print(d[3].get_text()[:1200])
