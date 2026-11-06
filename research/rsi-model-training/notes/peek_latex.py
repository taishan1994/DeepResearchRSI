import pymupdf, re
d = pymupdf.open(r"D:\github\DeepResearchRSI\research\rsi-model-training\paper\latex\main.pdf")
CJK = re.compile(r"[\u4e00-\u9fff]")
for i in range(d.page_count):
    t = d[i].get_text()
    print(i+1, len(CJK.findall(t)), "imgs", len(d[i].get_images()))
print("="*30)
print(d[0].get_text()[:900])
