"""检索「端到端推理优化的 RSI」相关来源。

## 与 rsi-inference 的区别

rsi-inference 检索的是「谁来写 kernel」；这里检索的是「谁来改整条推理链路」：
投机解码、调度、批处理、KV 管理、量化、并行策略。这两件事的反馈信号完全不同——
kernel 的判据是一个数（比 PyTorch 快几倍），端到端的判据是一组统计量（配对运行的
增益下界、无损失配率、SLO 违约率）。故检索式必须重写，不能复用。

## 为什么按「机制」而不是按「自我改进」分组

端到端层的论文很少自称 RSI。它们自称 "autonomous"、"automatic"、"discovery"、
"co-design"。若只搜 self-improving 会漏掉绝大多数。故按被优化的机制分组，
再在 screen 阶段按「是否含一个可观测的判定循环」筛。
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import ArxivProvider  # noqa: E402

HERE = Path(__file__).resolve().parent

GROUPS = {
    "A_spec": [
        'all:"speculative decoding" AND all:"automatic"',
        'all:"speculative decoding" AND all:"agent"',
        'all:"speculative decoding" AND all:"lossless"',
        'all:"draft model" AND all:"automatic" AND all:"LLM"',
        'all:"speculative" AND all:"throughput" AND all:"optimization"',
    ],
    "B_serving": [
        'all:"LLM serving" AND all:"automatic" AND all:"optimization"',
        'all:"LLM inference" AND all:"agent" AND all:"optimization"',
        'all:"serving system" AND all:"LLM" AND all:"auto-tuning"',
        'all:"inference system" AND all:"LLM" AND all:"co-design"',
        'all:"SLO" AND all:"LLM" AND all:"scheduling" AND all:"optimization"',
    ],
    "C_discovery": [
        'all:"autonomous" AND all:"system" AND all:"LLM" AND all:"optimization"',
        'all:"algorithm discovery" AND all:"LLM"',
        'all:"LLM" AND all:"system optimization" AND all:"search"',
        'all:"configuration" AND all:"tuning" AND all:"LLM inference"',
        'all:"code agent" AND all:"performance" AND all:"system"',
    ],
    "D_quant": [
        'all:"quantization" AND all:"LLM" AND all:"automatic" AND all:"search"',
        'all:"quantization" AND all:"inference" AND all:"accuracy" AND all:"efficiency"',
        'all:"KV cache" AND all:"LLM" AND all:"optimization" AND all:"automatic"',
    ],
    "E_loop": [
        'all:"self-improving" AND all:"system"',
        'all:"self-evolving" AND all:"agent" AND all:"code"',
        'all:"evolutionary" AND all:"LLM" AND all:"optimization"',
        'all:"reward hacking" AND all:"benchmark"',
        'all:"benchmark" AND all:"contamination" AND all:"LLM" AND all:"code"',
    ],
}

LIMIT = 100
SINCE = date(2025, 1, 1)


def main() -> int:
    p = ArxivProvider()
    rows: list[dict] = []
    seen: set[str] = set()
    total = 0
    for group, queries in GROUPS.items():
        print(f"=== {group}: {len(queries)} ===")
        for q in queries:
            try:
                hits = p.search(q, limit=LIMIT, since=SINCE)
            except Exception as exc:  # noqa: BLE001
                print(f"  [!] {q}: {str(exc)[:70]}")
                continue
            total += len(hits)
            print(f"  {len(hits):3d}  {q}")
            for h in hits:
                if h.arxiv_id in seen:
                    continue
                seen.add(h.arxiv_id)
                rows.append({
                    "arxiv_id": h.arxiv_id,
                    "title": h.title,
                    "published": h.published,
                    "updated": h.updated,
                    "authors": h.authors,
                    "summary": h.abstract,
                    "url": h.url,
                    "query": h.query,
                    "group": group,
                })
            time.sleep(0.2)

    rows.sort(key=lambda r: r["published"], reverse=True)
    out = HERE / "candidates_serving.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n累计 {total}，去重 {len(rows)} -> {out.name}")
    by: dict[str, int] = {}
    for r in rows:
        by[r["published"][:4]] = by.get(r["published"][:4], 0) + 1
    print("按年：", dict(sorted(by.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
