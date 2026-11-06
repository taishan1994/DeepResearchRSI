"""粗筛：把候选论文按「是否真的含一个可观测的改进循环」打分排序。

## 为什么需要两段筛

arXiv 检索式召回的是「关键词共现」，不是「主题相关」。几十组式子会召回
大量只沾一个词的论文（例如把 all:"Triton" 理解成海神）。若直接人工
读上千条标题，成本不可接受；若直接按关键词硬筛，又会漏掉换词的论文
（同一个循环有人叫 self-refine、有人叫 iterative optimization）。

故分两段：
  1. 本脚本按多信号加权排序，并把每条命中命中的信号打印出来，
     让人能核对「为什么它排在这里」；
  2. 人工只读前 150 条，逐条判定纳入与否并标 layer。
第 2 段的结果写进 included_rsi.json，是后续所有环节的唯一入口。

## 打分的三个维度

- 对象（objective）：改的是 kernel / 算子 / 图 / 配置 / 量化 / 调度
- 循环（loop）：有迭代、有反馈、有搜索/训练
- 自主（auto）：由 LLM/agent 驱动，而非传统自动调优（TVM autotune 之类）

三者都命中才算「RSI 相关工作」；只命中对象的是普通推理优化论文，
只命中循环的是通用 self-improve 论文。两者都是 adjacent，不是 core。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 对象：被优化的东西
OBJ = {
    "kernel": r"kernel|cuda|triton|gpu code|device code|ptx|warp|shared memory",
    "operator": r"operator|gemm|attention|flash|matmul|fused|primitive",
    "graph": r"computation graph|graph compil|tensor compil|intermediate representation",
    "config": r"config|autotun|tuning|hyperparameter|serving parameter",
    "quant": r"quantiz|low-bit|int4|int8|fp8|prun|sparsif",
    "serving": r"serving|scheduler|batching|prefill|decode|kv cache|throughput|latency slo",
    "parallel": r"paralleli[sz]|sharding|tensor parallel|pipeline parallel|distributed inference",
}

# 循环：改进是怎么发生的
LOOP = {
    "iterate": r"iterat|multi-turn|multi round|refine|repair|self-correct|feedback loop",
    "search": r"search|evolution|genetic|beam|monte carlo tree|explore",
    "rl": r"reinforcement learning|policy gradient|grpo|ppo|reward model",
    "agent": r"agent|tool use|tool-augmented|autonomous",
    "profiling": r"profil|nsight|counter|roofline|bottleneck",
}

# 自主：谁在改
AUTO = r"llm|large language model|language model|gpt|agent|neural"

# 明确排除：同形异义（RSI 在别的领域是遥感影像、重复性劳损……）
EXCLUDE = (r"remote sensing|resting[- ]state|recommender|repetitive strain|"
           r"hyperspectral|sar image|point cloud|medical image|"
           r"satellite image|protein|molecul|drug discovery|weather|climate|"
           r"traffic flow|speech recognition|text-to-speech|image generation|"
           r"video generation")

# 已知的推理性能天花板工作：不是 RSI，但提供「端到端收益上限」的分母
CEILING = (r"cublas|flashattention|end-to-end|amdahl|roofline|speed-of-light|"
           r"upper bound|bottleneck analysis|characteriz")


def score(rec: dict) -> tuple[int, list[str]]:
    text = (rec["title"] + " " + rec["summary"]).lower()
    hits: list[str] = []
    s = 0
    if re.search(EXCLUDE, text):
        return -99, ["EXCLUDED"]
    for name, pat in OBJ.items():
        if re.search(pat, text):
            hits.append("obj:" + name)
            s += 2
    for name, pat in LOOP.items():
        if re.search(pat, text):
            hits.append("loop:" + name)
            s += 2
    if re.search(AUTO, text):
        hits.append("auto:llm")
        s += 3
    # 标题命中权重更高：标题是作者的自我定位
    t = rec["title"].lower()
    for pat in ("kernel", "inference", "serving", "self-improv", "evolv", "agent"):
        if re.search(pat, t):
            s += 3
            hits.append("title:" + pat)
    if re.search(CEILING, text):
        hits.append("ceiling")
        s += 1
    return s, hits


def main() -> int:
    rows = json.loads((HERE / "candidates_rsi.json").read_text(encoding="utf-8"))
    scored = []
    for r in rows:
        s, hits = score(r)
        if s < 0:
            continue
        scored.append((s, hits, r))
    scored.sort(key=lambda x: (-x[0], x[2]["published"]))
    out = []
    for s, hits, r in scored:
        out.append({
            "score": s,
            "signals": hits,
            "arxiv_id": r["arxiv_id"],
            "title": r["title"],
            "published": r["published"],
            "summary": r["summary"],
            "url": r["url"],
            "group": r["group"],
        })
    (HERE / "screened_rsi.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")

    print(f"候选 {len(rows)}，去掉同形异义后 {len(out)}")
    n = 0
    for rec in out:
        n += 1
        if n > 160:
            break
        print(f'{rec["score"]:3d} {rec["arxiv_id"]} {rec["published"]} {rec["title"][:96]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
