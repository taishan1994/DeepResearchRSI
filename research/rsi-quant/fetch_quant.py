"""检索「模型量化的 RSI」相关来源。

## 与 rsi-serving / rsi-inference 的区别

rsi-inference 的对象是一段 GPU 程序，rsi-serving 的对象是整条推理链路。
量化的对象又不同：**权重与激活的表示**。它有一个前两者都没有的性质——
「更省」与「更准」是一对连续可调的权衡，而不是可分离的两件事。
故检索式必须围绕「谁能自动决定这个权衡」，而不是「谁能自动改代码」。

## 为什么按「量化的哪一段」分组

量化层的论文极少自称 RSI。它们自称 PTQ / QAT / mixed-precision search /
bit allocation / agent-based quantization。若只搜 self-improving 会全漏。
故按被自动化的那一段分组，再在 screen 阶段按「是否含可观测判定循环」筛。
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
    # A：位宽/混合精度的自动分配——量化最核心的「搜索」
    "A_alloc": [
        'all:"mixed-precision" AND all:"quantization" AND all:"LLM"',
        'all:"bit allocation" AND all:"quantization" AND all:"LLM"',
        'all:"quantization" AND all:"search" AND all:"layer" AND all:"sensitivity"',
        'all:"quantization" AND all:"Pareto" AND all:"accuracy" AND all:"efficiency"',
        'all:"post-training quantization" AND all:"automatic"'
    ],
    # B：agent 直接参与量化决策
    "B_agent": [
        'all:"agent" AND all:"quantization" AND all:"LLM"',
        'all:"LLM agent" AND all:"compression" AND all:"model"',
        'all:"agent" AND all:"mixed-precision" AND all:"deployment"',
        'all:"autonomous" AND all:"quantization"'
    ],
    # C：演化/强化学习驱动的量化策略搜索
    "C_evolve": [
        'all:"evolutionary" AND all:"quantization"',
        'all:"reinforcement learning" AND all:"quantization" AND all:"policy"',
        'all:"neural architecture search" AND all:"quantization" AND all:"bit"',
        'all:"self-evolving" AND all:"compression"'
    ],
    # D：KV cache / 激活量化——运行时那一半
    "D_kv": [
        'all:"KV cache" AND all:"quantization" AND all:"LLM"',
        'all:"activation quantization" AND all:"LLM" AND all:"outlier"',
        'all:"quantization" AND all:"long context" AND all:"KV"'
    ],
    # E：QAT 与「量化感知」的自动配方
    "E_qat": [
        'all:"quantization-aware training" AND all:"LLM"',
        'all:"quantization" AND all:"distillation" AND all:"LLM" AND all:"recovery"',
        'all:"low-bit" AND all:"LLM" AND all:"training" AND all:"accuracy"'
    ],
    # F：判据——量化到底怎么算「无损」
    "F_eval": [
        'all:"quantization" AND all:"benchmark" AND all:"evaluation" AND all:"LLM"',
        'all:"quantization" AND all:"accuracy" AND all:"perplexity" AND all:"discrepancy"',
        'all:"quantization" AND all:"reproducibility" AND all:"evaluation"',
        'all:"quantization" AND all:"calibration" AND all:"data" AND all:"sensitive"'
    ],
    # G：循环本身与失效模式（旁证）
    "G_loop": [
        'all:"self-improving" AND all:"model" AND all:"compression"',
        'all:"reward hacking" AND all:"optimization" AND all:"benchmark"',
        'all:"automated" AND all:"research" AND all:"machine learning" AND all:"agent"',
        'all:"LLM" AND all:"hardware" AND all:"co-design" AND all:"efficiency"'
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
    out = HERE / "candidates_quant.json"
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
