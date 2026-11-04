"""粗筛候选：把 180 篇里真正讲「kernel 生成智能体」的挑出来。

## 为什么必须粗筛

11 组检索式命中 180 篇，其中 176 篇「含智能体特征」——
这个数字本身就说明检索式太宽：`agent` 与 `kernel` 在别的语境里
各自都很常见（LLM agent 是当下热词，kernel 在 ML 里到处出现）。

若不筛，纳入 20 篇里会混进「用 agent 做数据清洗」这类工作，
而读者无从判断。

## 三级判定

  A. 必须与 GPU kernel 强相关（题名/摘要出现 CUDA/Triton/GPU kernel/等）
  B. 必须有智能体循环（工具调用、环境反馈、多轮迭代、多智能体之一）
  C. 排除同名不同义（统计学 kernel）与方向相反（用 RL 训模型但不带工具）

只保留 A 且 B 且非 C。判据写在下面，逐条可复查。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --- A: 强相关的 kernel 语境 ---
KERNEL_STRONG = re.compile(
    r"\b(cuda|triton|gpu kernel|kernel generation|kernel optimization"
    r"|gpu program|sass|ptx|ascend|npu kernel|hip kernel|opencl)\b", re.I)

# --- B: 智能体循环的构成要件 ---
AGENT_STRONG = [
    ("tool", r"\b(tool[- ]augmented|tool use|tool calling|toolkit|tools? \()\b"),
    ("feedback", r"\b(compiler feedback|execution feedback|runtime feedback"
                 r"|profiling feedback|error message|hardware feedback)\b"),
    ("multiturn", r"\b(multi[- ]turn|iterative refinement|iterative optimization"
                  r"|self[- ]repair|self[- ]refine|reflexion)\b"),
    ("multiagent", r"\b(multi[- ]agent|agent team|team of agents|collaborat"
                   r"|debate)\b"),
    ("search", r"\b(tree search|best[- ]of[- ]n|beam search|monte carlo"
               r"|explore[- ]exploit)\b"),
    ("planning", r"\b(planning|planner|decompos\w+ task|subgoal)\b"),
]
AGENT_RES = [(k, re.compile(p, re.I)) for k, p in AGENT_STRONG]

# --- C: 排除 ---
EXCLUDE = [
    ("统计学 kernel", re.compile(
        r"\b(gaussian kernel|rbf kernel|convolution kernel|kernel function"
        r"|kernel method|kernel regression|kernel density)\b", re.I)),
    ("纯 RL 训练无工具", re.compile(
        r"\b(reinforcement learning|policy gradient|grpo|ppo)\b", re.I)),
]


def main() -> int:
    src = HERE / "candidates_agent.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    print(f"候选 {len(rows)} 篇\n")

    kept, dropped = [], []
    for r in rows:
        blob = (r["title"] + " " + (r.get("summary") or "")).lower()

        a = bool(KERNEL_STRONG.search(blob))
        hits = [k for k, pat in AGENT_RES if pat.search(blob)]
        c_reasons = [name for name, pat in EXCLUDE if pat.search(blob)]

        # 排除规则只对「仅靠 RL」生效：若同时有明确的工具/反馈/多轮，
        # 说明它确实是智能体系统（RL 只是训练手段），予以保留。
        real_c = []
        for name in c_reasons:
            if name == "纯 RL 训练无工具":
                if not any(k in hits for k in ("tool", "feedback", "multiturn")):
                    real_c.append(name)
            else:
                real_c.append(name)

        ok = a and len(hits) >= 1 and not real_c
        rec = dict(r)
        rec["_kernel_strong"] = a
        rec["_agent_signals"] = hits
        rec["_excluded"] = real_c
        (kept if ok else dropped).append(rec)

    kept.sort(key=lambda r: len(r["_agent_signals"]), reverse=True)
    print(f"保留 {len(kept)} 篇，剔除 {len(dropped)} 篇\n")
    print("=== 保留（按智能体信号数降序，前 40）===")
    for r in kept[:40]:
        print(f"  {r['arxiv_id']}  [{'+'.join(r['_agent_signals'])}]")
        print(f"      {r['title'][:82]}")

    # 剔除里挑几个看看为什么
    print("\n=== 剔除样例（前 10）===")
    for r in dropped[:10]:
        why = []
        if not r["_kernel_strong"]:
            why.append("非 kernel 语境")
        if not r["_agent_signals"]:
            why.append("无智能体要件")
        if r["_excluded"]:
            why.extend(r["_excluded"])
        print(f"  {r['arxiv_id']}  [{'; '.join(why)}]  {r['title'][:56]}")

    out = HERE / "screened_agent.json"
    out.write_text(json.dumps({"kept": kept, "dropped": len(dropped)},
                              ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n写入 {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
