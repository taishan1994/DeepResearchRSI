"""检索「推理优化中的 RSI」相关来源：arXiv 论文 + 关键工程报告。

## 为什么检索式要分五组

「模型推理优化的 RSI」不是 arXiv 上的一个分类，而是三个圈子的交集：

  A. 推理性能：kernel、serving、量化、调度
  B. 代码智能体：写 kernel 的 agent、编译器的 agent
  C. 自我改进：self-improving / self-evolving / 反馈闭环

任一圈子单独检索都会捞回大量不相关的论文，故按组分别检索、分别打标签，
再在 screen 阶段按「是否真的包含一个可观测的改进循环」筛。

## 命中门槛

只看 2024-01 之后。理由：LLM 驱动的 kernel/系统自动优化在 2024 年之前
基本不存在（AlphaCode 级的代码生成尚不能产出可编译的高性能 kernel）。
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
    "A_kernel": [
        'all:"CUDA kernel" AND all:"large language model"',
        'all:"GPU kernel" AND all:"LLM"',
        'all:"kernel generation" AND all:"LLM"',
        'all:"Triton" AND all:"agent"',
        'all:"kernel optimization" AND all:"automated"',
        'all:"high-performance kernel" AND all:"agent"',
    ],
    "B_system": [
        'all:"LLM inference" AND all:"optimization" AND all:"agent"',
        'all:"LLM serving" AND all:"automatic" AND all:"configuration"',
        'all:"compiler" AND all:"LLM" AND all:"optimization" AND all:"agent"',
        'all:"quantization" AND all:"LLM" AND all:"search"',
        'all:"speculative decoding" AND all:"automatic"',
        'all:"operator" AND all:"LLM" AND all:"generation" AND all:"compiler"',
    ],
    "C_selfimprove": [
        'all:"self-improving" AND all:"code"',
        'all:"self-evolving" AND all:"agent"',
        'all:"self-refine" AND all:"code generation"',
        'all:"iterative refinement" AND all:"LLM" AND all:"code"',
        'all:"reward hacking" AND all:"code"',
        'all:"test-time" AND all:"scaling" AND all:"code"',
    ],
    "D_rl": [
        'all:"reinforcement learning" AND all:"code generation" AND all:"LLM"',
        'all:"GRPO" AND all:"code"',
        'all:"execution feedback" AND all:"LLM" AND all:"optimization"',
        'all:"verifier" AND all:"code" AND all:"reinforcement learning"',
    ],
    "E_evolve": [
        'all:"evolutionary" AND all:"code" AND all:"LLM"',
        'all:"AlphaEvolve"',
        'all:"program search" AND all:"LLM"',
        'all:"LLM" AND all:"performance engineering"',
    ],
}

LIMIT = 100
SINCE = date(2024, 1, 1)


def main() -> int:
    p = ArxivProvider()
    rows: list[dict] = []
    seen: set[str] = set()
    total_hits = 0
    for group, queries in GROUPS.items():
        print(f"=== {group}：{len(queries)} 组式子 ===")
        for q in queries:
            try:
                hits = p.search(q, limit=LIMIT, since=SINCE)
            except Exception as exc:  # noqa: BLE001
                print(f"  [!] {q}: {str(exc)[:80]}")
                continue
            total_hits += len(hits)
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
    out = HERE / "candidates_rsi.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n累计命中 {total_hits}，去重后 {len(rows)} 篇 -> {out.name}")
    by_year: dict[str, int] = {}
    for r in rows:
        by_year[r["published"][:4]] = by_year.get(r["published"][:4], 0) + 1
    print("按年：", dict(sorted(by_year.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
