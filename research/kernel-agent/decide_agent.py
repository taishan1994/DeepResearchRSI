"""最终纳入判定：逐篇给出纳入/剔除理由（人工判读，脚本只记录）。

## 为什么最后一步必须人工

前两轮自动筛选已经证明：词频分不清「讲 GPU 加速的机器人巡检」与
「做 kernel 生成」。一筛保留 44 篇里混进了水下机器人、控制理论、
对话推理；二筛想用「同句共现」收紧，结果**一篇都没剔除**——
因为这些论文的摘要里确实有 `CUDA`、`Triton` 这类词。

这说明判据本身不对：不是词不够近，而是**主语不同**。
「我们用 CUDA 加速这个计算」与「我们让智能体生成 CUDA kernel」
在词汇上完全重叠，在语义上是两件事。

故最后一层由人判读。本文件把决策固化下来，便于复查与复现：
每个 ID 后写纳入层级与一句话理由。**理由必须能指向摘要里的具体表述**，
不能写「相关」这种空话。

## 层级

  core      智能体循环本身是研究对象（观测/动作/预算/失败恢复）
  adjacent  提供智能体所需的基础设施（profiling 工具、benchmark、执行环境）
  exclude   判为不相关，写明为什么
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- 人工判定表 ----
# 格式：arxiv_id -> (layer, 理由)
DECISIONS: dict[str, tuple[str, str]] = {
    # ===== core：智能体循环是研究对象 =====
    "2609.04523": ("core", "MaxKernel：TPU 上的 agentic kernel 生成，含规划与反馈"),
    "2608.21157": ("core", "HIERA：跨实现空间的工作负载感知规划，直接讲 agent 的决策"),
    "2610.27588": ("core", "知识引导的演化式 NPU kernel 生成，含工具与多轮"),
    "2602.12305": ("core", "OptiML：端到端程序合成 + CUDA 优化，含搜索"),
    "2511.06345": ("core", "PRAGMA：profiling 推理驱动的多智能体 kernel 优化"),
    "2511.01884": ("core", "CudaForge：硬件反馈驱动的 agent 框架"),
    "2509.07506": ("core", "Astra：多智能体 GPU kernel 性能优化"),
    "2510.16996": ("core", "STARK：agent 团队精炼 kernel"),
    "2610.36848": ("core", "Evolving Agent Teams：明确指出编码 agent 在真实 kernel 上陷局部最优"),
    "2609.30059": ("core", "KernelOPT：dispatch 感知的 agentic 搜索"),
    "2608.17071": ("core", "KernelArc：多智能体 GPU kernel 优化框架"),
    "2606.26758": ("core", "EGG：专家引导的 agent 框架"),
    "2603.10085": ("core", "KernelClaw：双记忆机制的多智能体框架"),
    "2603.07169": ("core", "让 LLM 像专家一样优化多场景 CUDA kernel"),
    "2604.01489": ("core", "CuTeGen：生成与优化的 agentic 框架"),
    "2608.14560": ("core", "Agentic Kernel Optimization：无需手工调优产出 SOTA kernel"),
    "2606.17518": ("core", "SpecGen：用推测式生成加速 agentic kernel 优化"),
    "2608.25570": ("core", "自演化 agent 做硬件 kernel 优化"),
    "2602.24286": ("core", "CUDA Agent：大规模 agentic RL"),
    "2607.04395": ("core", "NKI-Agent：Neuron kernel 的领域微调 + agentic 工具使用"),
    "2507.11948": ("core", "Kevin：多轮 RL，一轮即一次 agent 迭代"),
    "2610.38329": ("core", "多智能体 kernel 优化循环的案例研究（新加速器）"),
    "2511.13274": ("core", "KForge：生成 agent + 精炼 agent 的协作"),
    "2606.26453": ("core", "微 profiling 工具作为专家替身——反馈信号是核心贡献"),
    "2603.28342": ("core", "Kernel-Smith：演化式 kernel 优化的统一配方"),
    "2603.12440": ("core", "KernelFoundry：硬件感知的演化式优化"),

    # ===== adjacent：智能体所需的基础设施 =====
    "2502.10517": ("adjacent", "KernelBench：所有 agent 工作的评测基座"),
    "2605.04956": ("adjacent", "KernelBenchX：benchmark 扩展"),
    "2605.08467": ("adjacent", "CUDAHercules：硬件感知的专家级评测"),
    "2608.25124": ("adjacent", "FABRICA：CUDA->CSL 翻译，wafer-scale 场景"),
    "2608.01804": ("adjacent", "LEAP：环境反馈的剪枝，属 RL 训练侧"),
    "2607.20908": ("adjacent", "多轮 RL 的结构化奖励，属奖励设计侧"),
    "2610.23950": ("adjacent", "Ascend Triton 的上下文压实，属 RL 训练侧"),
    "2606.04847": ("adjacent", "MusaCoder：Moore Threads 全栈训练"),
    "2510.26144": ("adjacent", "FM Agent：通用多智能体框架，kernel 是应用之一"),

    # ===== exclude：不相关，写明原因 =====
    "2611.04096": ("exclude", "HJ 可达性用于机器人控制，GPU 只是加速手段"),
    "2610.26106": ("exclude", "水下多机器人巡检的 GPU 常驻流水线，与 kernel 生成无关"),
    "2610.18083": ("exclude", "AReaL-RSI：递归自我改进的调度，不涉及 kernel"),
    "2610.13494": ("exclude", "MLE agents 的会话交替，任务是 ML 工程而非 kernel"),
    "2610.11858": ("exclude", "agent 技能演化的故障定位，通用软件工程"),
    "2603.14769": ("exclude", "POLCA：随机生成式优化，应用是 prompt 与 agent 本身"),
    "2506.11108": ("exclude", "多轮对话与思维链推理，借 vLLM 做推理加速"),
    "2610.20563": ("exclude", "自动科研中的遗忘机制，无 kernel 内容"),
    "2604.08590": ("exclude", "AlphaLab：通用自主科研框架，未特化到 kernel"),
}


def main() -> int:
    d = json.loads((HERE / "screened2_agent.json").read_text(encoding="utf-8"))
    rows = d["kept"]
    by_id = {r["arxiv_id"]: r for r in rows}

    missing = [a for a in by_id if a not in DECISIONS]
    unknown = [a for a in DECISIONS if a not in by_id]

    print(f"二筛后 {len(rows)} 篇；判定表 {len(DECISIONS)} 条")
    if missing:
        print(f"\n[!] 有 {len(missing)} 篇未判定（必须逐篇给理由）：")
        for a in missing:
            print(f"    {a}  {by_id[a]['title'][:70]}")
    if unknown:
        print(f"\n[!] 判定表里的 {len(unknown)} 个 ID 不在候选里：{unknown}")

    tiers = {"core": [], "adjacent": [], "exclude": []}
    for aid, (layer, why) in DECISIONS.items():
        if aid in by_id:
            tiers[layer].append((aid, by_id[aid], why))

    print(f"\ncore {len(tiers['core'])} 篇、adjacent {len(tiers['adjacent'])} 篇、"
          f"exclude {len(tiers['exclude'])} 篇")

    out = {
        "core": [{"arxiv_id": a, **r, "why": w} for a, r, w in tiers["core"]],
        "adjacent": [{"arxiv_id": a, **r, "why": w}
                     for a, r, w in tiers["adjacent"]],
        "exclude": [{"arxiv_id": a, "title": r["title"], "why": w}
                    for a, r, w in tiers["exclude"]],
    }
    (HERE / "included_agent.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print("写入 included_agent.json")
    return 0 if not missing and not unknown else 1


if __name__ == "__main__":
    raise SystemExit(main())
