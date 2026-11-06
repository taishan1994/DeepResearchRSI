"""统计口径的唯一实现：analysis.json 里的每个数字都由这里从 CSV 重算。

## 为什么统计必须单独成文件

论文正文、图、表三处都要用同一批数字。若各自统计一次，
迟早出现「正文说 27 篇、图里画 25 篇」这类内部矛盾，而两边都能各自「正确」。
故：tally 只在这里做一次，其他文件一律读 analysis.json。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
labels = __import__("csv").DictReader((HERE / "corpus_labels.csv").open(encoding="utf-8-sig"))
rows = list(labels)

def quarter(d: str) -> str:
    return f"{d[:4]}-Q{(int(d[5:7]) - 1) // 3 + 1}"

layer = Counter(r["layer"] for r in rows)
reward = Counter(r["reward"] for r in rows if r["reward"] != "na")
metric = Counter(r["metric"] for r in rows)
year = Counter(r["published"][:4] for r in rows)

# 分层随时间的迁移：每年各层新增多少篇
by_year_layer: dict[str, Counter] = defaultdict(Counter)
for r in rows:
    by_year_layer[r["published"][:4]][r["layer"]] += 1

# 权重层内部的奖励形态随时间的迁移
by_year_reward: dict[str, Counter] = defaultdict(Counter)
for r in rows:
    if r["reward"] != "na":
        by_year_reward[r["published"][:4]][r["reward"]] += 1

tl = Counter(quarter(r["published"]) for r in rows)

out = {
    "as_of": "2026-11-05",
    "corpus": {
        "n": len(rows),
        "earliest": min(r["published"] for r in rows),
        "latest": max(r["published"] for r in rows),
        "fetched": "2026-11-05",
    },
    "counts": {
        "layer": dict(sorted(layer.items(), key=lambda kv: -kv[1])),
        "reward": dict(sorted(reward.items(), key=lambda kv: -kv[1])),
        "metric": dict(sorted(metric.items(), key=lambda kv: -kv[1])),
        "year": dict(sorted(year.items())),
    },
    "timeline": dict(sorted(tl.items())),
    "by_year_layer": {y: dict(sorted(c.items())) for y, c in sorted(by_year_layer.items())},
    "by_year_reward": {y: dict(sorted(c.items())) for y, c in sorted(by_year_reward.items())},
}
(HERE / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
print(json.dumps(out["counts"], ensure_ascii=False, indent=1))
print("timeline", out["timeline"])
