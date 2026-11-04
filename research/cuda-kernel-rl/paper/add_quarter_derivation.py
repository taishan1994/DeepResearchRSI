"""给时间线图补季度口径的 derivation。

## 为什么需要单独一支

其它图（奖励形态、算法分布）的数字是「某个标签有几篇」，
一条 derivation 可以覆盖多个值（`计数 outcome=9；计数 multi_turn=9`）。

时间线不一样：它的每个值对应**不同的季度**，是同一口径下的 7 个取值。
故每条都要写明自己的季度：

    计数 quarter 2025-Q1=1；计数 quarter 2025-Q3=3；……

审计会逐条重算：数该季度发表的 core 论文数。

## 一个容易被忽视的点

derivation 里的数字若写死，审计只是核对「derivation 的数字 == 图里的数字」，
两者可以一起错。故审计端是**独立从 papers.json 重算**的，
derivation 里的数字只用来做第一道筛选（省掉大部分无意义的重算）。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    # 从 analysis.json 取时间线（唯一数据源）
    a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    tl = a["timeline"]
    parts = "；".join(f"计数 quarter {t['quarter']}={t['count']}" for t in tl)

    path = ROOT / "claims.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = list(rows[0].keys())

    changed = 0
    for r in rows:
        if r["claim_id"] != "c-kernel-rl-fit":
            continue
        cur = (r.get("derivation") or "").strip()
        if "计数 quarter" in cur:
            continue
        r["derivation"] = (cur + "；" + parts) if cur else parts
        changed += 1

    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"已为时间线补 {len(tl)} 个季度口径")
    print(f"  改动主张 {changed} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
