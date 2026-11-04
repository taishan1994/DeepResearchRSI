"""为「kernel 生成智能体」专题检索 arXiv。

## 与已有两个归档的边界（重要）

- `cuda-kernel-gen`（36 篇）：kernel **生成**的方法谱系，偏模型与评测。
- `cuda-kernel-rl`（20 篇）：kernel 生成中的**强化学习**，偏奖励设计。
- 本专题（`kernel-agent`）：**智能体**——即「模型 + 工具 + 环境反馈 + 多轮控制流」
  这一整套系统。关注点不是「模型怎么写出 kernel」，而是
  「系统怎么在编译、测速、profiling 的反馈下把 kernel 迭代到可用」。

三者交集会有重叠（如 CUDA Agent、Kevin 都涉及），但视角不同：
本专题要问的是**智能体循环的设计**——观测什么、动作空间多大、反馈信号来自哪、
轮次预算怎么花、失败怎么恢复。

## 检索式设计

不用「agent + kernel」这类宽词，因为它会召回大量「用 agent 做别的事」。
改为从**智能体的构成要件**出发，每要件一组检索式：

  1. 工具使用：tool-augmented / tool use + kernel
  2. 环境反馈：compiler feedback / execution feedback / profiling + kernel
  3. 多轮迭代：iterative refinement / self-repair / multi-turn + kernel
  4. 多智能体：multi-agent / team of agents + kernel
  5. 规划搜索：planning / tree search / best-of-n + kernel
  6. 端到端系统：agent framework / agentic + GPU kernel
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import ArxivProvider  # noqa: E402

HERE = Path(__file__).resolve().parent

QUERIES = [
    # 工具使用
    'all:"tool-augmented" AND all:"kernel"',
    'all:"tool use" AND all:"GPU kernel"',
    # 环境反馈
    'all:"compiler feedback" AND all:"kernel generation"',
    'all:"execution feedback" AND all:"GPU kernel"',
    'all:"profiling" AND all:"kernel optimization" AND all:"LLM"',
    # 多轮迭代
    'all:"iterative refinement" AND all:"GPU kernel"',
    'all:"self-repair" AND all:"kernel"',
    'all:"multi-turn" AND all:"CUDA kernel"',
    # 多智能体 / 规划
    'all:"multi-agent" AND all:"GPU kernel"',
    'all:"agent" AND all:"CUDA kernel optimization"',
    # 端到端系统
    'all:"agentic" AND all:"kernel"',
]


def main() -> int:
    p = ArxivProvider()
    print(f"检索 {len(QUERIES)} 组式子…")
    hits = p.search_many(QUERIES, limit=120)

    # 只保留 2025 年以后——该方向 2025 才成形
    rows = []
    for h in hits:
        if not (h.published or "").startswith(("2025", "2026")):
            continue
        rows.append({
            "arxiv_id": h.arxiv_id,
            "title": h.title,
            "published": h.published,
            "summary": h.abstract,
            "query": h.query,
        })

    rows.sort(key=lambda r: r["published"], reverse=True)
    out = HERE / "candidates_agent.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")

    print(f"命中 {len(hits)}，2025 年后 {len(rows)} 篇 -> {out.name}")

    # 粗看一下与「智能体」强相关的有多少
    kw = ["agent", "agentic", "multi-turn", "tool", "feedback",
          "iterative", "refine", "search", "repair", "team"]
    strong = [r for r in rows
              if any(k in (r["title"] + r["summary"]).lower() for k in kw[:6])]
    print(f"其中标题/摘要含智能体特征的：{len(strong)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
