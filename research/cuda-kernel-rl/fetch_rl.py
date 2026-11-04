"""专题检索入口：调用框架的 arXiv provider，不再自带一套抓取逻辑。

## 改了什么

原版（`fetch_rl.py` 的第一版）自己写了 requests + XML 解析 + 限速，
与 `cuda-kernel-gcn/paper/fetch_recent.py` 几乎逐行相同。

现在改为**只声明检索式**，抓取交给
`packages/providers/python/deepresearchrsi_providers/arxiv.py`。
这一版的价值不是「代码更短」，而是：
  - 限速、退避、429 处理只有一处实现，修一次全局生效
  - 解析出的字段形态与 `papers.json` 一致，合并时不需要再做转换
  - `since` 过滤、去重、`query` 回溯都在 provider 里，专题脚本不必重复

## 输出

`candidates_rl.json`：候选池，字段与 `papers.json` 同构 + `query` / `fetched_at`。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import (  # noqa: E402
    ArxivProvider,
    hits_to_records,
)

OUT = HERE / "candidates_rl.json"

# 多组检索式：并集比任何单组都全。
# 只搜 "reinforcement learning" AND "CUDA kernel" 会漏掉两类：
#   1. 摘要只讲 reward 设计、不出现 RL 字样的
#   2. 做 Triton / Ascend 而非 CUDA 的
QUERIES: list[str] = [
    'all:"reinforcement learning" AND all:"CUDA kernel"',
    'all:"reinforcement learning" AND all:Triton',
    'all:"reinforcement learning" AND all:"GPU kernel"',
    'all:RLVR AND all:kernel',
    'all:GRPO AND all:kernel',
    'all:"reward" AND all:"CUDA kernel" AND all:LLM',
    'all:"policy optimization" AND all:"kernel generation"',
    'all:"agentic RL" AND all:kernel',
    'all:"kernel generation" AND all:"reinforcement learning"',
    'all:"Triton" AND all:"fine-tuning" AND all:"kernel"',
]


def main() -> int:
    provider = ArxivProvider()
    hits = provider.search_many(QUERIES, limit=100)
    records = hits_to_records(hits)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    print(f"候选池 {len(records)} 篇 -> {OUT.name}")
    by_query: dict[str, int] = {}
    for r in records:
        by_query[r.get("query", "")] = by_query.get(r.get("query", ""), 0) + 1
    for q, n in sorted(by_query.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {q[:62]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
