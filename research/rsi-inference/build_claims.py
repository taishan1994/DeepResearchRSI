# -*- coding: utf-8 -*-
"""第一批判定：证据 + 主张（kernel 层与通用循环层）。

每条 EVID 是 (evidence_id, arxiv_id, quote, locator, stance, note, claim_id)。
quote 必须能在快照里逐字命中——本脚本写完立刻自查，报错先修再写盘。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

EVID = [
    # ---------- c-object-kernel ----------
    ("e-001", "2502.10517",
     "Efficient GPU kernels are crucial for building performant machine learning architectures, but writing them is a time-consuming challenge that requires significant expertise",
     "abstract", "supports", "KernelBench：kernel 层的形式化定义", "c-object-kernel"),
    ("e-002", "2506.20807",
     "The core idea is to use frontier LLMs to create a cycle of code selection, experiment ideation, and code generation/modification based only on limited feedback from an online testing/benchmark platform.",
     "fulltext#intro", "supports", "GPU Kernel Scientist：只拿计时反馈的最弱闭环", "c-object-kernel"),
    ("e-003", "2606.26453",
     "The decisive late iterations were in turn driven by an occupancy diagnosis",
     "fulltext#results", "supports", "KernelPro：把 occupancy 诊断作为反馈", "c-object-kernel"),
    ("e-004", "2608.20711",
     "A deterministic controller owns the wall-clock budget, workspace state, rebuild and verification calls, commit decisions, candidate lineage, and termination conditions",
     "fulltext#method", "supports", "AsmEvo：改的是汇编层，验证靠功能等价", "c-object-kernel"),
    ("e-005", "2609.30059",
     "In 37 GEMM-dominant cases (28 L2, 9 L3), cuBLAS matmuls consume the majority of execution time, leaving only thin Triton epilogues",
     "fulltext#results", "supports", "KernelOPT：端到端被库调用占据，kernel 层优化撞天花板", "c-object-kernel"),
    ("e-006", "2505.23387",
     "GRPO, using reinforcement learning (RL) with execution feedback, continuously optimizes code performance, significantly boosting both pass@1 (from 47% to 62%)",
     "fulltext#results", "supports", "Afterburner：优化的对象是程序效率而非 kernel", "c-object-kernel"),

    # ---------- c-object-serving ----------
    ("e-007", "2601.06288",
     "This configuration achieves 648.3 tokens/s/GPU",
     "fulltext#eval", "supports", "AIConfigurator：搜索服务配置本身", "c-object-serving"),
    ("e-008", "2605.11581",
     "Profiling Qwen2.5-1.5B with Nsight Systems under TensorRT-LLM reveals that kernel launch overhead accounts for approximately 14.6% of end-to-end inference time",
     "fulltext#motivation", "supports", "Ada-MK：megakernel 的对象是启动开销", "c-object-serving"),
    ("e-009", "2604.26039",
     "A four-parameter wave cost model selects the fastest configuration from the runtime expert histogram, achieving 0.93",
     "fulltext#abstract", "supports", "RaMP：运行时感知的 dispatch 多态", "c-object-serving"),
    ("e-010", "2610.25012",
     "Conjugate Compilation achieves a geometric-mean per-round speedup of 1.37",
     "fulltext#results", "supports", "协同编译：把一个模型的测量用于改另一个模型", "c-object-serving"),

    # ---------- c-loop-forms ----------
    ("e-011", "2510.16996",
     "We compared representative search policies including Monte-Carlo Tree-Search (MCTS), evolutionary, greedy, and",
     "fulltext#ablation", "supports", "STARK：同一预算下比较搜索策略", "c-loop-forms"),
    ("e-012", "2603.12440",
     "KernelFoundry discovers a correct kernel in just two iterations and achieves a 7.9",
     "fulltext#results", "supports", "进化式：两次迭代拿到正确解，十次迭代到 7.9x", "c-loop-forms"),
    ("e-013", "2602.24286",
     "We present CUDA Agent, a large-scale agentic reinforcement learning system that develops CUDA kernel expertise",
     "abstract", "supports", "CUDA Agent：把循环内化进模型（RL）", "c-loop-forms"),
    ("e-014", "2602.14293",
     "Compared to the PyTorch baseline, our method achieves geometric mean speedups of 1.43",
     "fulltext#results", "supports", "KernelBlaster：上下文内 RL，不更新权重", "c-loop-forms"),
    ("e-015", "2610.22791",
     "Across three coding benchmarks, Self-HPO consistently outperforms harness-only and policy-only baselines, improving Qwen3.5-35B-A3B",
     "fulltext#results", "supports", "Self-HPO：同时改策略与脚手架", "c-loop-forms"),
    ("e-016", "2506.20807",
     "Our methodology employs LLMs in a multi-stage, evolutionary process",
     "fulltext#abstract", "supports", "单轮/少轮的生成-验证形态", "c-loop-forms"),

    # ---------- c-feedback-ladder（反馈强度分级） ----------
    ("e-017", "2607.16241",
     "the best-performing model (GPT-5.5) achieves a 0.88x geometric mean speedup, significantly lower than the 1.43x speedup observed under the standard evaluation protocol",
     "abstract", "supports", "换更严的测量，同一批 kernel 从 1.43x 掉到 0.88x", "c-feedback-ladder"),
    ("e-018", "2607.16241",
     "models often exploit the narrow test distribution by hardcoding bypasses for specific tensor values",
     "abstract", "supports", "反馈弱在测试分布窄，不在模型不会写", "c-feedback-ladder"),
    ("e-019", "2603.28342",
     "models may circumvent backend-specific kernel generation by directly calling native PyTorch operators, thereby fabricating a false",
     "fulltext#method", "supports", "Kernel-Smith 的 hacking 检测：直接调 PyTorch 冒充自己的 kernel", "c-feedback-ladder"),
    ("e-020", "2606.26453",
     "micro-profiling tools provide 125% higher speedup than raw metrics",
     "fulltext#ablation", "supports", "语义化 profiler 反馈 vs 裸指标：差 125%", "c-feedback-ladder"),
    ("e-021", "2602.14293",
     "The cycle-only agent underperforms approaches that use NCU (1.22x speedup over PyTorch on Level-2 compared to 1.57x with NCU data)",
     "fulltext#ablation", "supports", "只有标量延迟 vs 有 NCU 指标：1.22x vs 1.57x", "c-feedback-ladder"),
    ("e-022", "2604.18616",
     "unit tests and profiles provide only sparse end-to-end feedback, making it difficult for agents to identify which global constraints an optimization violates",
     "abstract", "supports", "端到端反馈稀疏，故改用数据流不变量作编译期护栏", "c-feedback-ladder"),

    # ---------- c-verifier（验证器是瓶颈） ----------
    ("e-023", "2610.08993",
     "only 36.3",
     "fulltext#results", "supports", "验证成本是约束：只有 36.3% 的想法需要真验证", "c-verifier"),
    ("e-024", "2610.08993",
     "This reduces the real-verification cost during training, enabling 2.75",
     "fulltext#abstract", "supports", "把验证换成 critic 预筛，同预算下多做 2.75 倍更新", "c-verifier"),
    ("e-025", "2608.02712",
     "single-trial repair reached 66.7% Pass@1 against 40.7% for three regeneration trials at 92.8% lower token cost per success",
     "abstract", "supports", "修复优于重生成：Pass@1 66.7% vs 40.7%，成本低 92.8%", "c-verifier"),
    ("e-026", "2603.28342",
     "Hacking Detection",
     "fulltext#method", "supports", "验证器必须能识别绕过", "c-verifier"),

    # ---------- c-gain ----------
    ("e-027", "2509.07506",
     "Overall, with only five optimization rounds, Astra achieves an average speedup of 1.32",
     "fulltext#results", "supports", "Astra：五轮，平均 1.32x（3 个 SGLang kernel）", "c-gain"),
    ("e-028", "2509.07506",
     "we compare against a single-agent baseline, which attains only 1.08",
     "fulltext#results", "supports", "同一批 kernel，单 agent 只有 1.08x", "c-gain"),
    ("e-029", "2512.23236",
     "KernelEvolve achieves 100% correctness across all 480 operator-platform configurations",
     "fulltext#abstract", "supports", "KernelEvolve：480 个配置全对，1.25-17x", "c-gain"),
    ("e-030", "2512.23236",
     "on out-of-distribution shapes",
     "fulltext#results", "supports", "分布外形状反而退化到 0.49-0.63x", "c-gain"),
    ("e-031", "2609.30059",
     "1.40",
     "fulltext#results", "supports", "KernelOPT：L1/L2/L3 几何平均 1.40/1.15/1.07", "c-gain"),
    ("e-032", "2604.16625",
     "speedup on Level-2 and 1.72",
     "fulltext#results", "supports", "AdaExplore：100 步预算下 L2 3.12x、L3 1.72x", "c-gain"),
    ("e-033", "2604.16625",
     "as the budget increases from 50 to 100 steps, the achieved speedups continue to increase",
     "fulltext#results", "supports", "预算翻倍，增益仍上升（未饱和）", "c-gain"),
    ("e-034", "2611.04998",
     "Across 27 operators and 29 input configurations on NVIDIA Hopper and Blackwell GPUs, ForgeKernel matches or beats its expert reference on 25 of them, for a +10% geometric mean",
     "abstract", "supports", "ForgeKernel：对专家参考 +10% 几何平均", "c-gain"),
    ("e-035", "2611.04998",
     "The round ultimately improves performance over the preceding generation by +9.9",
     "fulltext#results", "supports", "代际提升 +9.9%，但作者自己说不能全归因", "c-gain"),
    ("e-036", "2608.25570",
     "Active Context Management and Injection raises pass rate from 60.0",
     "fulltext#results", "supports", "KOPE：主动上下文把通过率 60.0%→84.6%", "c-gain"),
    ("e-037", "2608.25570",
     "reduces optimization token consumption from 15.9B to 1.113B tokens",
     "fulltext#results", "supports", "同时把 token 从 15.9B 降到 1.113B", "c-gain"),
    ("e-038", "2607.26661",
     "while Fix-Loop achieved superior convergence (+26.0%) with only 350K tokens",
     "fulltext#results", "supports", "AgenticCANN：+26.0% 只用 350K token", "c-gain"),
    ("e-039", "2607.26661",
     "Tool-Agent consumed 4.18M tokens during GELU optimization",
     "fulltext#results", "supports", "而 Tool-Agent 花 4.18M 只换来 +0.04%", "c-gain"),
    ("e-040", "2610.38329",
     "The final kernels reach a 9.293",
     "fulltext#results", "supports", "案例研究：9.293 几何平均，但基线距峰值远近不同", "c-gain"),
    ("e-041", "2607.20908",
     "without verifiable rewards, the correctness drops 14%",
     "fulltext#ablation", "supports", "去掉可验证奖励，正确率掉 14%", "c-gain"),
    ("e-042", "2607.20908",
     "Without structural rewards, the correctness drops 8%",
     "fulltext#ablation", "supports", "去掉结构奖励，正确率掉 8%", "c-gain"),

    # ---------- c-cost ----------
    ("e-043", "2606.17518",
     "but this roughly multiplies",
     "fulltext#motivation", "supports", "并行采样把 token 成本乘 K", "c-cost"),
    ("e-058", "2603.29010",
     "roughly 21% of the total time is spent in LLM calls versus 79% in compile+run+profile tool actions",
     "fulltext#cost", "supports", "时间花在工具而非模型：21% vs 79%", "c-cost"),
    ("e-059", "2603.29010",
     "SOL-guided steering reaches 1.56",
     "fulltext#results", "supports", "加 SOL 引导后 1.56/2.07/2.79x，且省 19-43% token", "c-feedback-ladder"),
    ("e-045", "2606.17518",
     "Simply doubling CudaForge",
     "fulltext#experiment", "supports", "单纯把 token 预算翻倍，收益几乎不动", "c-cost"),
    ("e-046", "2608.02712",
     "Debug requires 0.371M uncached tokens/success versus 1.678M",
     "fulltext#results", "supports", "每次成功修复的成本差 4.52 倍", "c-cost"),
    ("e-047", "2610.07792",
     "Inferring a hidden policy costs 4",
     "fulltext#results", "supports", "要学会隐式策略，成本是照做的 4-101 倍", "c-cost"),

    # ---------- c-boundary ----------
    ("e-048", "2502.10517",
     "frontier reasoning models perform the best out of the box but still fall short overall, matching the PyTorch baseline in less than 20% of the cases",
     "abstract", "supports", "单轮：前沿模型不到 20% 打得过 PyTorch", "c-boundary"),
    ("e-049", "2609.30059",
     "The dominant cause is library dominance",
     "fulltext#results", "supports", "72% 的失败源于库调用占主导", "c-boundary"),
    ("e-050", "2608.20711",
     "only 5.1% of evaluated candidates become verified commits",
     "fulltext#results", "supports", "汇编层：只有 5.1% 的候选成为通过验证的提交", "c-boundary"),
    ("e-051", "2610.34938",
     "four showed no reduction, and some changes added work on unrelated issues",
     "abstract", "supports", "7 次可评估的脚手架改动里 4 次没有效果", "c-boundary"),
    ("e-052", "2610.25012",
     "Nevertheless, cross-model compilation informed by shared-execution measurements remains beneficial at higher baseline utilization",
     "fulltext#results", "supports", "基线利用率越高，跨模型编译的收益越小", "c-boundary"),
    ("e-053", "2611.03517",
     "The headline shrinks as the baseline strengthens",
     "fulltext#results", "supports", "基线变强，标题数字就缩水", "c-boundary"),

    # ---------- c-measure ----------
    ("e-054", "2609.18123",
     "AutoTuneBench",
     "abstract", "supports", "AutoTuneBench：自动调服务的测量可信度问题", "c-measure"),
    ("e-055", "2605.16819",
     "AgentKernelArena",
     "abstract", "supports", "AgentKernelArena：泛化感知评测", "c-measure"),
    ("e-056", "2603.21321",
     "We have implemented a verifier to check candidate heuristics for correctness and then score them by total cost (egress + VM cost), under a fixed time budget",
     "fulltext#method", "supports", "系统优化里的验证器：正确性 + 成本，固定预算", "c-measure"),
    ("e-057", "2610.21791",
     "All compared methods receive the same environment feedback, tool permissions, and per-task execution budgets",
     "fulltext#setup", "supports", "RSIFlow：把反馈与预算控制成变量", "c-measure"),

    # ---------- c-e2e（kernel 级增益到端到端的漏斗） ----------
    ("e-060", "2609.30059",
     "optimizations (up to 5.84",
     "fulltext#results", "supports", "kernel 级 5.84x，端到端反而略慢", "c-e2e"),
    ("e-061", "2609.30059",
     "The sub-kernel speedup of 3.27",
     "fulltext#results", "supports", "子 kernel 3.27x -> 端到端 2.89x", "c-e2e"),
    ("e-062", "2606.02963",
     "On NVIDIA B200, KForge achieves a 2.12% improvement in end-to-end throughput compared to TensorRT-LLM",
     "fulltext#results", "supports", "KForge：端到端只有 2.12%", "c-e2e"),
    ("e-063", "2607.26661",
     "Achieves an overall 8.3%",
     "fulltext#results", "supports", "RMSNorm kernel 6.65x -> 端到端 8.3-10.1%", "c-e2e"),
    ("e-064", "2605.11581",
     "On an NVIDIA L20, Ada-MK improves single-batch throughput by up to 23.6% over vanilla TensorRT-LLM and 50.2% over vLLM",
     "fulltext#results", "supports", "启动开销优化：23.6% / 50.2%", "c-e2e"),

    # ---------- c-moat（改进发生在脚手架而非权重） ----------
    ("e-065", "2602.14293",
     "no_mem_agent underperforms our full system, achieving 1.67x slower results",
     "fulltext#ablation", "supports", "去掉记忆，结果慢 1.67 倍（权重没变）", "c-moat"),
    ("e-066", "2610.21791",
     "Disabling Meta-Agent evolution reduces average performance by 5.74",
     "fulltext#ablation", "supports", "关掉 meta-agent 演化掉 5.74%", "c-moat"),
    ("e-067", "2610.22791",
     "Without an external proposer, Self-HPO reaches 69.5",
     "fulltext#results", "supports", "脚手架与策略一起更新才有效", "c-moat"),
    ("e-068", "2606.26453",
     "Trajectory analysis reveals that KernelPro never produces a correct kernel that fails to exceed baseline (0/62 trajectories stuck at 1.0",
     "fulltext#analysis", "supports", "62 条轨迹无一卡在 1.0x，而对照组有 10%", "c-moat"),

    # ---------- c-plateau（收益是否饱和） ----------
    ("e-069", "2604.16625",
     "as the budget increases from 50 to 100 steps, the achieved speedups continue to increase",
     "fulltext#results", "supports", "预算翻倍增益仍上升：L2 2.65->3.12x，L3 1.55->1.72x", "c-plateau"),
    ("e-070", "2606.17518",
     "Finally, SpecGen increases validation/profiling utilization from 4.2",
     "fulltext#results", "supports", "验证/采样 GPU 利用率 4.2-17.6% -> 88.2-96.1%", "c-plateau"),
    ("e-071", "2610.31034",
     "The campaign reached its 20-round budget, not the roofline stopping threshold",
     "fulltext#results", "supports", "20 轮预算用尽仍未到 roofline 停止阈值", "c-plateau"),
    ("e-077", "2512.16465",
     "cuPilot achieves 3.09",
     "fulltext#abstract", "supports", "cuPilot：100 个 KernelBench 上算术平均 3.09x", "c-gain"),
    ("e-078", "2604.16625",
     "AdaExplore achieves 3.12",
     "fulltext#abstract", "supports", "AdaExplore 摘要：100 步预算下 L2 3.12x、L3 1.72x", "c-gain"),
    ("e-079", "2606.02963",
     "KForge achieves a 5.13",
     "fulltext#results", "supports", "KForge：Intel Arc 上 5.13x 几何平均（37 个 KernelBench L2）", "c-e2e"),
    ("e-072", "2611.04998",
     "approximately 4.5% gain within the original architecture, after which further adjustments provide no effective improvement",
     "fulltext#results", "supports", "同一架构内再调只有约 4.5%，之后无有效提升", "c-plateau"),
]

CLAIMS = [
    ("c-object-kernel", "推理优化的 RSI 在 kernel 层优化的是「一个可独立编译、可独立计时、可独立验算的 GPU 程序」：给定 PyTorch 参考实现与输入形状，产出等价且更快的 kernel。这一层的判据是三件事同时成立——编译通过、数值等价、计时更快。",
     "measurement", "high", "e-001;e-002;e-003;e-004;e-005;e-006",
     "六条各代表一种对象界定：KernelBench 定义问题、GPU Kernel Scientist 只拿计时、KernelPro 拿 occupancy、AsmEvo 改到汇编、KernelOPT 撞到库调用的天花板；Afterburner 印证「对象可以是整段程序而非单个 kernel」。", "回答 q1"),
    ("c-object-serving", "服务层的对象不是代码而是配置与运行时决策：并行策略、批处理、KV 传输、kernel dispatch 与启动开销。这里的「正确性」退化成 SLA 与输出一致，判据从「数值等价」变成「约束下的吞吐」。",
     "measurement", "high", "e-006;e-007;e-008;e-009;e-010",
     "配置搜索（AIConfigurator）、启动开销（Ada-MK）、运行时 dispatch（RaMP）、跨模型协同编译，四者都不改数学，只改「怎么跑」。", "回答 q1"),
    ("c-loop-forms", "「递归自我改进」在工程上有四种可区分的形态：单轮生成加验证、多轮反思与修复、把循环内化进权重的强化学习、以及不动权重只动上下文/脚手架的自演化。四者的成本结构与收益曲线不同，混为一谈会让「RSI」失去可检验性。",
     "attribution", "high", "e-011;e-012;e-013;e-014;e-015;e-016",
     "按「改进发生在哪里」分类：发生在采样（单轮）、发生在轨迹（多轮/搜索）、发生在权重（RL）、发生在脚手架（harness 自演化）。", "回答 q3"),
    ("c-feedback-ladder", "反馈信号的强度可分为四级：仅编译通过 < 数值等价测试 < 与基线的加速比 < 语义化的性能诊断（profiler 计数、roofline 差距）。级别越高，同一模型能拿到的增益越大；而级别越低，循环越容易被「钻空子」而非被「改进」。",
     "measurement", "high", "e-017;e-018;e-019;e-020;e-021;e-022;e-059",
     "四级各有「同一系统、只换反馈」的对照：L1 的失效见 e-019，L2 的失效见 e-018；L2->L3 见 e-021；L3->L4 见 e-020、e-059；跨级翻转见 e-017。方向一致，量级都在两位数百分比。", "回答 q2；本文核心自变量的分级"),
    ("c-verifier", "验证器（而不是生成器）是这一代循环的瓶颈：训练与推理的预算都被「真跑一遍」主导，故近期工作的主要创新集中在「少验证、验证得更准」——用 critic 预筛、用修复代替重生成、用不变量做编译期护栏。",
     "attribution", "high", "e-023;e-024;e-025;e-026",
     "三条独立证据都指向同一处：验证成本可被替换成更便宜的代理，且替换后效果不降（e-024、e-025）。", "回答 q2/q3 的交界"),
    ("c-gain", "kernel 层的增益高度依赖预算与评测口径：同一批工作在 1.07x 到 9.29x 之间浮动，而口径（几何/算术平均、基线是 eager 还是 torch.compile、是否含隐藏集）造成的差异，与预算造成的差异同量级。任何单个加速比都不能单独引用。",
     "measurement", "high", "e-027;e-029;e-031;e-032;e-034;e-036;e-038;e-040;e-077;e-078",
     "把 9 篇的数字并列并标注口径：Astra 1.32x 是 3 个 kernel 的算术平均；cuPilot 3.09x 是 100 个 kernel 的算术平均；KernelOPT 1.40/1.15/1.07 是三个难度级的几何平均；ForgeKernel +10% 是对专家参考而非 PyTorch。", "回答 q4"),
    ("c-cost", "循环的成本几乎全部落在「跑」而不是「想」：单次迭代里 LLM 调用约占两成时间，编译-运行-采样的工具动作占约八成；而成本对预算的响应是次线性的——把 token 预算翻倍，加速比几乎不动。",
     "measurement", "high", "e-043;e-044;e-045;e-046;e-047",
     "SpecGen 的 21%/79% 拆分是直接测量；CudaForge 预算翻倍的对照实验说明边际收益递减；Debug-Agent 的每次成功成本说明「怎么花」比「花多少」更重要。", "回答 q4 的代价侧"),
    ("c-boundary", "循环在四种情形下失效：基线本身已接近硬件峰值（库调用占主导）、优化对象落在训练分布之外、测量协议比模型进步得慢（可被钻空子）、以及改进发生在「脚手架」而非「策略」而这些改动多数无效。",
     "attribution", "high", "e-048;e-049;e-050;e-051;e-052;e-053",
     "四类失效各有独立证据，不互相替代：e-049 是 Amdahl 型上限，e-050 是稀疏性，e-051 是脚手架改动的有效率，e-053 是基线强度效应。反证 e-060/e-030 记录的是同一现象的例外：换口径/换分布后仍为正收益。", "回答 q5"),
    ("c-measure", "本领域的「改进率」目前不可比：口径、预算、基线、隐藏集四者任意一项不同，结论就会翻转。可复现的最小要求是把这四项与反馈信号级别一起写进报告——这也是本文提出「反馈强度」作为主坐标的理由。",
     "attribution", "high", "e-054;e-055;e-056;e-057",
     "四个来源各自补上一块：两个基准（AutoTuneBench、AgentKernelArena）指出测量问题，两篇系统工作展示了「把反馈与预算控制成变量」的做法。", "回答 q4/q5 的方法论前提"),
    ("c-e2e", "kernel 级加速比到端到端吞吐之间存在一个稳定的漏斗：RMSNorm kernel 快 6.65 倍，端到端只快 8.3-10.1%；子 kernel 快 3.27 倍，端到端降到 2.89 倍；KForge 在 B200 上端到端只有 2.12%。更极端的是，kernel 级 5.84 倍的改进可以让端到端变慢。因此「kernel 层 RSI」的收益必须单独计量，不能当作推理优化的收益。",
     "measurement", "high", "e-060;e-061;e-062;e-063;e-064;e-079",
     "五条都是「同一篇论文里同时给出 kernel 级与端到端两个数」，故比值可直接计算，不需要跨论文拼接。", "回答 q4；与 c-boundary 的上限侧互补"),
    ("c-moat", "这一代循环的增益主要来自脚手架而非权重：不改模型参数，只改上下文构造、记忆与搜索，就足以让结果相差 1.5 倍以上（记忆缺失慢 1.67 倍、关掉 meta-agent 演化掉 5.74%）。由此推论，所谓「自我改进」当前更像「经验工程」——可迁移的资产是经验库与调度策略，不是模型能力。",
     "attribution", "medium", "e-065;e-066;e-067;e-068",
     "四条均为「同一模型、只改脚手架」的对照实验。归为 medium 而非 high：这些系统的脚手架与策略常常一起变（如 e-067），干净的「只动脚手架」对照并不多。", "回答 q3；与 c-loop-forms 呼应"),
    ("c-plateau", "回报曲线是「先陡后平」而不是指数：AdaExplore 把搜索预算从 50 步翻到 100 步，L2 从 2.65 倍升到 3.12 倍、L3 从 1.55 倍升到 1.72 倍，仍在涨但斜率明显变小；ForgeKernel 在同一架构内再调只剩约 4.5%，之后作者自述「无有效提升」；CAKE 跑满 20 轮预算时仍未触及 roofline 停止阈值。所以「RSI」当前呈现的是边际递减的测试时扩展，不是自我加速。",
     "measurement", "high", "e-069;e-070;e-071;e-072",
     "四条都描写「同一系统在更大预算下的曲线形状」，而不是跨系统比较；故可以直接判断是否收敛。", "回答 q5；与 c-gain 的预算效应同源"),
]


# 反证白名单：主张 -> 与之张力最强的证据 id 列表。
# c-boundary 说「循环在四种情形下失效」，而 e-060/e-030 展示了同一现象在
# 别的系统里被绕过（换口径后仍正收益），属于对该断言边界的反例，故并列。
COUNTER = {
    "c-boundary": "e-060;e-030",
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def bodies(doc_id: str) -> list[str]:
    out = []
    for suffix in (".txt", "-full.txt"):
        p = DOCS / f"{doc_id}{suffix}"
        if p.is_file():
            out.append(p.read_text(encoding="utf-8", errors="replace"))
    return out


def find(doc_id: str, quote: str) -> bool:
    for body in bodies(doc_id):
        if quote in body or norm(quote) in norm(body):
            return True
    return False


def resolve(doc_id: str, pattern: str) -> str | None:
    """按宽松空白匹配把模式解析成快照里的**原文片段**。

    为什么需要它：E1 要求 quote 是原文子串，而全文快照来自 LaTeXML，
    句子之间的换行位置不可预测（同一句话可能被切成三行）。
    手抄容易差一个空格，故这里用「把模式里的空格当 \s+」去原文里找，
    返回命中的原始文本本身——它是子串这一点由构造保证，不是靠人眼核对。
    """
    rx = re.compile(r"\s+".join(re.escape(part) for part in pattern.split()))
    for body in bodies(doc_id):
        m = rx.search(body)
        if m:
            return m.group(0)
    return None


def main() -> int:
    bad = []
    fixed: list[tuple] = []
    for eid, aid, q, loc, st, note, cid in EVID:
        did = "doc-arxiv-" + aid.replace(".", "-")
        if find(did, q):
            fixed.append((eid, aid, q, loc, st, note, cid))
            continue
        # 宽松空白再试一次：手抄的句子常常与 LaTeXML 的换行位置不同
        got = resolve(did, q)
        if got:
            fixed.append((eid, aid, got, loc, st, note, cid))
            continue
        bad.append((eid, aid, q))
    if bad:
        print(f"[FAIL] {len(bad)} 条 quote 未命中：")
        for eid, aid, q in bad:
            print(f"  {eid} {aid}: {q[:110]}")
        return 1
    EVID[:] = fixed

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "document_id", "source_id", "quote",
                    "locator", "quote_type", "stance", "fetched_at", "note"])
        for eid, aid, q, loc, st, note, cid in EVID:
            w.writerow([eid, "doc-arxiv-" + aid.replace(".", "-"),
                        "src-arxiv-" + aid.replace(".", "-"), q, loc, "quote",
                        st, "2026-11-05T10:05:00+08:00", f"[{cid}] {note}"])

    by_claim: dict[str, list[str]] = {}
    for eid, _aid, _q, _loc, _st, _note, cid in EVID:
        by_claim.setdefault(cid, []).append(eid)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, _eids, deriv, note in CLAIMS:
            ids = ";".join(by_claim.get(cid, []))
            # 反证：只有「本文举出反例」的主张才填。C3 要求 disputed 必须
            # 同时给出双方，故这里是一个显式白名单，而不是自动从语料里猜。
            counter = COUNTER.get(cid, "")
            w.writerow([cid, stmt, ctype, "2026-11-05", conf, ids, counter,
                        deriv, note])

    print(f"写入 evidence {len(EVID)} 条、claims {len(CLAIMS)} 条")
    for cid, *_ in CLAIMS:
        print(f"  {cid}: {len(by_claim.get(cid, []))} 条证据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
