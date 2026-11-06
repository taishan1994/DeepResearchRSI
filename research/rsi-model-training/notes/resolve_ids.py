"""按 arXiv ID 批量核对：候选 ID 是否真实存在，标题是否与预期一致。

为什么需要这一步：本项目的历史教训是「记忆里的论文 ID 会把两篇论文混成一篇」。
故凡是不在检索池里的经典工作，都必须回到 arXiv 元数据核对标题，
而不是凭印象写进 sources.csv。
"""
from __future__ import annotations
import json, sys, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))
import requests
from deepresearchrsi_providers.arxiv import NS  # noqa: E402
import xml.etree.ElementTree as ET

IDS = """2203.14465 2401.10020 2407.19594 2505.03335 2401.01335 2212.08073 2308.08998
2403.09629 2402.06457 2408.02666 2406.15609 2502.06258 2506.13131 2505.22954 2410.04444
2506.10943 2411.03322 2404.19733 2508.05004 2510.03610 2511.16043 2505.20286 2504.15228
2408.08435 2309.16797 2309.03409 2309.08532 2406.07496 2310.03714 2303.17651 2303.11366
2305.16291 2409.07429 2502.18449 2411.02337 2504.20073 2401.00812 2508.17297 2410.05080
2509.19349 2512.18552 2508.14029 2510.14943 2601.22513 2510.08977 2305.17493 2404.01413
2607.07663 2610.35193 2610.27610 2610.27465 2610.38266 2610.33624 2611.01736 2611.02797
2610.25858 2610.30009 2610.38392 2610.32026 2611.04035 2611.01304 2610.32770 2610.39417
2501.xxxxx 2502.12110 2408.03314 2504.13837""".split()

def fetch(ids):
    out = []
    for i in range(0, len(ids), 20):
        chunk = ids[i:i+20]
        r = requests.get("https://export.arxiv.org/api/query",
                         params={"id_list": ",".join(chunk), "max_results": 50}, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        for e in root.findall("a:entry", NS):
            aid = (e.find("a:id", NS).text or "").strip().rsplit("/", 1)[-1]
            out.append({
                "id": aid,
                "title": " ".join((e.find("a:title", NS).text or "").split()),
                "published": (e.find("a:published", NS).text or "")[:10],
                "updated": (e.find("a:updated", NS).text or "")[:10],
                "abstract": " ".join((e.find("a:summary", NS).text or "").split()),
                "authors": [a.find("a:name", NS).text for a in e.findall("a:author", NS)][:6],
            })
    return out

recs = fetch([i for i in IDS if "." in i and not i.startswith("2501.x")])
print("resolved", len(recs), "of", len(IDS))
(HERE / "_resolved.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
for r in sorted(recs, key=lambda x: x["published"]):
    print(f'{r["published"]} {r["id"]:12s} {r["title"][:95]}')
