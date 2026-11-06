"""补齐不在候选池里的经典工作：按 arXiv ID 直接取元数据。

这些 id 是在检索阶段用标题检索（ti:"..."）找到的，未进入 16 组关键词式子的并集。
把补取过程单独成一个脚本，是为了让「哪些论文是检索之外补进来的」这件事留下痕迹
——否则补进来的部分会被误读成「检索式覆盖到了」。
"""
from __future__ import annotations
import json
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
NS = {"a": "http://www.w3.org/2005/Atom"}
API = "https://export.arxiv.org/api/query"

IDS = ["2503.00735", "2506.01716", "2511.10395", "2507.21046",
       "2508.07407", "2412.14352", "2502.04780"]

r = requests.get(API, params={"id_list": ",".join(IDS), "max_results": 20}, timeout=60)
r.raise_for_status()
out = []
for e in ET.fromstring(r.text).findall("a:entry", NS):
    aid = (e.find("a:id", NS).text or "").strip().rsplit("/", 1)[-1]
    out.append({
        "id": aid,
        "title": " ".join((e.find("a:title", NS).text or "").split()),
        "published": (e.find("a:published", NS).text or "")[:10],
        "updated": (e.find("a:updated", NS).text or "")[:10],
        "abstract": " ".join((e.find("a:summary", NS).text or "").split()),
        "authors": [a.find("a:name", NS).text for a in e.findall("a:author", NS)][:6],
    })
(HERE / "_resolved_extra.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("补取", len(out), "篇")
for x in out:
    print(f'  {x["published"]} {x["id"]:12s} {x["title"][:80]}')
