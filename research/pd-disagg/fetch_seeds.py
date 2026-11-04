"""补抓奠基工作并合并进候选集。

## 为什么需要这一步

第一轮检索用 `all:"disaggregated prefill"` 这类**主题词**，命中 201 篇，
但**奠基工作的原始论文一篇都没进来**：

    Splitwise   2311.18677  （2023-11，最早提出 phase splitting）
    DistServe   2401.09670  （2024-01，提出 goodput 指标 + 分离）
    Sarathi     2403.02310  （chunked prefill 的代表作）
    Llumnix     2406.03243  （动态调度，对比分离与否）
    Mooncake    2407.00079  （KVCache 为中心的分离架构）

原因：这些论文的标题不含 "disaggregated prefill" 这类词组，
而检索式要求词组精确匹配。它们只在**别人的引文里**出现。

## 教训

主题词检索会系统性漏掉**开创性工作**——因为术语是它们发明的，
当时还不流行。补法是：从已命中论文的**参考文献**里反向找高频引用。
这里用按标题直接检索作为近似（更快，且这几个名字已知）。

## 做法

按标题检索 8 个已知系统名，合并进 candidates_pd.json，
并标记 `_seed=True` 以便统计「反向检索贡献了多少」。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import ArxivProvider  # noqa: E402

HERE = Path(__file__).resolve().parent

# 已知的开创性/关键系统（按标题检索）
SEEDS = [
    "DistServe",
    "Splitwise",
    "Sarathi-Serve",
    "Llumnix",
    "Mooncake",
    "TetriServe",
    "Sturgeon",
    "KV cache disaggregation",
]

# 明确排除的同名不同义（检索会命中）
JUNK_TITLE = [
    "nucleotide substitution",     # 分子生物学
    "Dummy Encoding",              # 统计学
    "Edge-Cloud Inference",        # 同名但不同问题（边缘云，非 PD 分离）
]


def main() -> int:
    p = ArxivProvider()
    queries = [f'ti:"{s}"' for s in SEEDS]
    print(f"按标题检索 {len(queries)} 个系统名…")
    hits = p.search_many(queries, limit=40)

    src = HERE / "candidates_pd.json"
    existing = json.loads(src.read_text(encoding="utf-8"))
    by_id = {r["arxiv_id"]: r for r in existing}
    before = len(by_id)

    added = []
    for h in hits:
        title_l = h.title.lower()
        if any(j.lower() in title_l for j in JUNK_TITLE):
            continue
        if not (h.published or "")[:4] in ("2023", "2024", "2025", "2026"):
            continue
        if h.arxiv_id in by_id:
            by_id[h.arxiv_id]["_seed"] = True
            continue
        rec = {
            "arxiv_id": h.arxiv_id,
            "title": h.title,
            "published": h.published,
            "summary": h.abstract,
            "url": h.url,
            "query": h.query,
            "_seed": True,
        }
        by_id[h.arxiv_id] = rec
        added.append(rec)

    rows = sorted(by_id.values(), key=lambda r: r["published"], reverse=True)
    src.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")

    print(f"\n原 {before} 篇 -> 现 {len(rows)} 篇"
          f"（新增 {len(added)} 篇奠基工作）")
    for r in sorted(added, key=lambda x: x["published"]):
        print(f"  + {r['arxiv_id']}  {r['published'][:10]}  {r['title'][:64]}")

    missing = [s for s in SEEDS
               if not any(s.lower() in r["title"].lower() for r in rows)]
    if missing:
        print(f"\n[!] 仍未找到：{missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
