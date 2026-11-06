"""专题检索：模型训练的 RSI（递归自我改进 / 自我进化）。

只声明检索式，抓取交给框架的 arXiv provider（限速、退避、429 只有一处实现）。

## 检索式设计

「RSI」在文献里有三种写法，只搜字面词会漏掉大半：
  1. 字面词：recursive self-improvement / self-improving
  2. 机制词：self-rewarding、self-play、self-training、self-evolving、自我生成课程
  3. 效果词：self-evolution、bootstrapping、absolute zero、无监督自举

故 16 组式子的并集，比任何单组都全。输出的 `query` 字段记录每篇被哪条式子召回，
用于事后评估「检索式是否够全」。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import ArxivProvider, hits_to_records  # noqa: E402

OUT = HERE / "candidates_rsi.json"

QUERIES: list[str] = [
    'all:"recursive self-improvement"',
    'all:"self-improving" AND all:"language model"',
    'all:"self-improving" AND all:LLM',
    'all:"self-rewarding"',
    'all:"self-play" AND all:"language model"',
    'all:"self-training" AND all:LLM AND all:reasoning',
    'all:"self-evolving" AND all:agent',
    'all:"self-evolution" AND all:"large language model"',
    'all:"iterative self-improvement"',
    'all:"absolute zero" AND all:reasoning',
    'all:RLVR AND all:"self-improvement"',
    'all:"self-generated" AND all:curriculum',
    'all:"bootstrapping" AND all:reasoning AND all:LLM',
    'all:"data flywheel" OR all:"self-improving loop"',
    'all:"model collapse" AND all:"synthetic data"',
    'all:"self-improvement" AND all:"reward model"',
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
        q = r.get("query", "")
        by_query[q] = by_query.get(q, 0) + 1
    for q, n in sorted(by_query.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {q[:70]}")
    print("最早", min(r["published"] for r in records) if records else "-",
          "最晚", max(r["published"] for r in records) if records else "-")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
