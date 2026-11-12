"""rsi-infra-feedback 的证据层与主张层。

## 本脚本的组织原则

主张不按「文献罗列」组织，而按**反馈的构造方式**组织——这是锚点的真正贡献，
也是全部同类工作唯一可比的轴（任务不同、硬件不同、口径不同，只有
「它拿到了什么反馈」是可跨工作比较的）。

E1 的落地方式：`resolve()` 用正则跨空白匹配，把 pattern 拼成
    re.compile(r"\s+".join(re.escape(p) for p in parts))
故 quote 在快照里必然逐字存在（空白归一化后），不会靠人眼抄写。

用法：
    python research/rsi-infra-feedback/build_claims.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
AS_OF = "2026-11-12"

# (evidence_id, doc 前缀, 匹配片段元组, locator, stance, note, claim_id)
EVID = [
    # ============ 锚点：密集反馈的三属性 ============
    ("e-001", "doc-zai-blog-en",
     ("First, feedback must be sufficiently local.",), "Dense feedback / 三特征", "supports",
     "锚点给出反馈的第一条属性：局部性。它不是「多给指标」而是「小到能定位」", "c-dense-def"),
    ("e-002", "doc-zai-blog-en",
     ("Second, feedback must be inexpensive and timely to obtain.",), "Dense feedback / 三特征", "supports",
     "第二条属性：便宜且及时。这一条直接决定 agent 一天能跑多少实验", "c-dense-def"),
    ("e-003", "doc-zai-blog-en",
     ("Third, feedback must support objective verification.",), "Dense feedback / 三特征", "supports",
     "第三条属性：可客观验证。三条合起来才构成 actionable", "c-dense-def"),
    ("e-004", "doc-zai-blog-en",
     ('Here, "dense" does not mean feeding the agent as many logs and metrics as possible.',),
     "Dense feedback / 反直觉定义", "supports",
     "⚠️ 关键澄清：dense ≠ 多。它明确反对「把日志全塞给 agent」。"
     "这一点常被误读为「加大上下文」，实为相反", "c-dense-def"),
    ("e-005", "doc-zai-blog-en",
     ("Correctness feedback answers", '"Is the computation correct?"'), "Dense feedback / 三层", "supports",
     "三层反馈各答一问：对不对 / 时间去哪了 / 哪种更好", "c-three-layers"),
    ("e-006", "doc-zai-blog-en",
     ("End-to-end metrics can tell an agent that results got worse, but they cannot explain why.",),
     "From End-to-End Metrics / 问题陈述", "supports",
     "这是全篇的问题定义句：端到端指标能说「变差了」，不能说「为什么」", "c-sparse-problem"),
    ("e-007", "doc-zai-blog-en",
     ("How do we turn sparse end-to-end results into fine-grained, attributable engineering feedback",),
     "From End-to-End Metrics / 研究问题", "supports",
     "研究问题原文。注意它用的是 sparse，与 dense 构成对立面", "c-sparse-problem"),
    # ============ 锚点：三个案例（三层反馈的实例）============
    ("e-010", "doc-zai-blog-en",
     ("we discovered a numerical accuracy issue in the KDA kernel's Context Parallelism (CP) path",),
     "Correctness Feedback / 案例一", "supports",
     "案例一：CP 与非 CP 路径的数值不一致，定位到 KDA kernel。"
     "属「先建映射再比较」的正例", "c-case-correctness"),
    ("e-011", "doc-zai-blog-en",
     ("The key point is that entering C++ does not automatically release the GIL.",),
     "System Behavior Feedback / 案例二", "supports",
     "案例二：KV Transfer 与计算不重叠，根因是 C++ 段持锁未释放 GIL。"
     "⚠️ 这是全篇最强的证据：它跨越 Python/C++ 语言边界", "c-case-behavior"),
    ("e-012", "doc-zai-blog-en",
     ("the performance gap between Prefill + KV Transfer and Prefill alone fell below 1% after the fix",),
     "System Behavior Feedback / 案例二结果", "supports",
     "案例二的验收：从 >20% 降到 <1%。用的是预先设定的性能约束，不是事后挑的数字", "c-case-behavior"),
    ("e-013", "doc-zai-blog-en",
     ("tiled along the V dimension, causing the same FP32 normalization and gating computations to be repeated four times",),
     "Performance Feedback / 案例三", "supports",
     "案例三：V 维分块导致公共计算重复四次。"
     "这是「为并行而并行」的典型代价", "c-case-performance"),
    ("e-014", "doc-zai-blog-en",
     ("achieved a 1.71× speedup over v2",), "Performance Feedback / 案例三结果", "supports",
     "案例三：合并分块 + 寄存器驻留 + warp 级归约，1.71x over v2", "c-case-performance"),
    ("e-015", "doc-zai-blog-en",
     ("reduced v1's execution time by 9.6%",), "Performance Feedback / 案例三中间步", "supports",
     "中间那一步只拿到 9.6%，说明增益是**逐层累积**而来，不是一次大跳", "c-accumulate"),
    # ============ 锚点：总体数字与边界 ============
    ("e-020", "doc-zai-blog-en",
     ("a cluster of more than 100,000 Chinese-made AI accelerators",), "开篇 / 规模", "supports",
     "规模：>10 万张国产加速器。这是「生产级」这一限定词的依据", "c-anchor-scale"),
    ("e-021", "doc-zai-blog-en",
     ("improved end-to-end serving performance by roughly 3"), "系统技术 / 总增益", "supports",
     "⚠️ 原文是 roughly 3×，不是某些二手报道写的 3.2×。"
     "本篇一律引原文口径", "c-anchor-gain"),
    ("e-022", "doc-zai-blog-en",
     ("from initial model adaptation to production readiness in less than two weeks",),
     "结果 / 工期", "supports",
     "两周：从初次适配到生产就绪。这是锚点唯一的「时间」类指标", "c-anchor-gain"),
    ("e-023", "doc-zai-blog-en",
     ("processing more than 62 trillion tokens in six days",), "结果 / 真实流量", "supports",
     "62 万亿 token / 6 天：说明这套栈确实承载了真实流量，而非 benchmark 环境", "c-anchor-scale"),
    ("e-024", "doc-zai-blog-en",
     ("we have not yet reached recursive self-improvement",), "结尾 / 边界自述", "supports",
     "⚠️ 锚点自己否认已达 RSI。这一句是本篇判定「锚点属 L1–L2」的直接依据", "c-anchor-not-rsi"),
    ("e-025", "doc-zai-blog-en",
     ("Choosing objectives, setting boundaries, and assessing risk remain human responsibilities",),
     "结尾 / 人类职责", "supports",
     "人类仍负责三件事：定目标、划边界、判风险。这是 L3 未达的判据", "c-anchor-not-rsi"),
    ("e-026", "doc-zai-blog-en",
     ("Engineers defined objectives and system boundaries",), "优化循环 / 分工", "supports",
     "分工原文：人定目标与边界、agent 做分析与改动、环境提供反馈", "c-division"),
    # ============ SEIS：引擎级演化，但 agent 固定 ============
    ("e-030", "doc-arxiv-2610-04646",
     ("On 100 natural-length requests, it reaches 1,942 tokens/s against 594 tokens/s for vanilla, a 3.27",),
     "Results / 端到端", "supports",
     "SEIS 核心数字：1942 vs 594 tok/s（3.27x），100 条自然长度请求", "c-seis"),
    ("e-031", "doc-arxiv-2610-04646",
     ("Mean request latency falls from 295 to 89 ms",), "Results / 延迟", "supports",
     "平均请求延迟 295→89 ms。与吞吐同向，非此消彼长。"
     "该比值 295/89≈3.31 是本篇图 4 中「延迟下降比」一柱的来源", "c-seis"),
    ("e-032", "doc-arxiv-2610-04646",
     ("the speedup comes from redesigning the whole engine",), "Results / 归因", "supports",
     "⚠️ 关键归因：增益来自**整体重构**而非单点优化。"
     "这支持「跨层」而非「单层叠加」", "c-whole-engine"),
    ("e-033", "doc-arxiv-2610-04646",
     ("Most of the best engine’s natural-request speedup remains with speculation disabled",),
     "Results / 消融", "supports",
     "消融：关掉投机解码后大部分增益仍在，说明 kernel/runtime 改动是主因", "c-whole-engine"),
    # ============ InfraRSI：两层 RSI（声明）============
    ("e-040", "doc-arxiv-2611-11558",
     ("forms a two-level Recursive Self-Improvement loop—revising priors online within runs and distilling experience across clusters",),
     "Abstract / 两层 RSI", "supports",
     "InfraRSI 的核心声明：run 内在线修正先验 + 跨集群经验蒸馏", "c-infrarsi"),
    ("e-041", "doc-arxiv-2611-11558",
     ("geometric-mean speedup, consistently outperforming open-code RE-Bench",),
     "Results / 主结果", "supports",
     "⚠️ 四工作负载的几何平均是 1.83x，不是某些二手材料写的 2.75x。"
     "2.75x 只是 Qwen3.5-9B 单个 workload 的最佳值（表 4 内），拿单点当总体是"
     "常见的引用错误。该句原文含 LaTeX 重复渲染（'1.83 × 1.83\\times'），"
     "故引其后的片段；MFU 17.4%→30.0% 是四负载均值，可对", "c-infrarsi"),
    ("e-042", "doc-arxiv-2611-11558",
     ("single edits often hit out-of-memory (OOM) boundaries",), "Motivation / 耦合", "supports",
     "⚠️ 训练侧的难点是**耦合**：单点改动常触发 OOM。"
     "这与推理侧「改一处能独立验证」形成对照", "c-train-coupling"),
    # ============ KOPE：经验图记忆 ============
    ("e-050", "doc-arxiv-2608-25570",
     ("Experience Graph Memory", ), "标题与方法", "supports",
     "KOPE 把 decision→feedback→后续决策 存成图，而非自然语言摘要", "c-kope"),
    ("e-051", "doc-arxiv-2608-25570",
     ("pass rate from 60.0", ), "Ablation / pass rate", "supports",
     "Active Context Management：pass 60.0%→84.6%", "c-kope"),
    ("e-052", "doc-arxiv-2608-25570",
     ("from 15.9B to 1.113B tokens",), "Ablation / token", "supports",
     "同一改动把优化 token 消耗从 15.9B 降到 1.113B。"
     "⚠️ 这说明「省 token」与「提效果」可以同向，反驳了「多给上下文才有效」", "c-kope"),
    ("e-053", "doc-arxiv-2608-25570",
     ("raises full-suite pass rate from 55.2",), "Ablation / Experience Graph", "supports",
     "Experience Graph 本身：全量 pass 55.2%→84.6%", "c-kope"),
    # ============ Evolving Agent Teams：组织演化 ============
    ("e-060", "doc-arxiv-2610-36848",
     ("a central supervisor that diagnoses each local optimum and restructures a team of agents",),
     "Framework / supervisor", "supports",
     "EAT 的机制：supervisor 诊断局部最优并**重组团队**。"
     "被演化的对象是组织结构，不是代码", "c-eat"),
    ("e-061", "doc-arxiv-2610-36848",
     ("wins on 36 of 47 production workloads",), "Results / 胜率", "supports",
     "36/47 个生产 workload 胜出。注意它报的是「胜率」而非单一加速比", "c-eat"),
    # ============ SWE-Serve：生产级判据的独立性 ============
    ("e-070", "doc-arxiv-2609-26777",
     ("screened 786 task-source records, retaining 203 source candidates",),
     "Construction / 四阶段筛选", "supports",
     "786 条源记录 → 203 候选 → 156 任务 → 53 入选（后半句见 e-071 的 23/53）。"
     "入选率 53/786≈6.74%，见本篇图 8", "c-swe-serve"),
    ("e-071", "doc-arxiv-2609-26777",
     ("Twenty-three of the final 53 tasks incorporated verifier revisions",), "Construction / 验证器修订", "supports",
     "23/53 个任务的验证器被修订过（≈43.4%，见本篇图 8）。"
     "验证器是**迭代出来的**，不是写一次就对", "c-verifier-cost"),
    # ============ MetaSkill：元技能双时间尺度 ============
    ("e-080", "doc-arxiv-2607-05297",
     ("the backbone already solves most episodes (92.31%)",), "Results / ALFWorld", "supports",
     "⚠️ ALFWorld 上 backbone 已达 92.31%，故增益空间极小。"
     "这是「元级演化有天花板」的直接证据", "c-meta-ceiling"),
    ("e-081", "doc-arxiv-2607-05297",
     ("The static skill slightly regresses",), "Results / ALFWorld", "supports",
     "静态技能在该任务上甚至**倒退**，单层演化只恢复到 No-Skill 基线", "c-meta-ceiling"),
    # ============ AlphaEvolve / DGM：通用进化搜索的边界 ============
    ("e-090", "doc-arxiv-2506-13131",
     ("algorithmic discovery",), "标题", "supports",
     "AlphaEvolve 自述为 algorithmic discovery，连 agent 都不提。"
     "⚠️ 这解释了为何按 agent 类词检索不到它", "c-wording-gap"),
    ("e-091", "doc-arxiv-2505-22954",
     ("modifies its own code",), "方法 / 自改", "supports",
     "DGM 改的是自己的 coding agent 源码并选择后代，"
     "是严格 RSI 的参照点", "c-dgm"),
    # ============ 判据侧的反证 ============
    ("e-100", "doc-arxiv-2607-20468",
     ("still fall below a simple hyperparameter search under the same time budget",),
     "Results / 对照", "supports",
     "⚠️ 最强反例：agent 打赢默认配置，但**打不过**同等预算的简单超参搜索", "c-agent-vs-search"),
    ("e-101", "doc-arxiv-2607-20468",
     ("Agents converge too quickly",), "Agent Behavior / 5.1", "supports",
     "agent 行为分析：过快收敛到同一套服务栈", "c-agent-failure"),
    ("e-102", "doc-arxiv-2607-20468",
     ("Optimization pressure induces reward hacking",), "Agent Behavior / 5.3", "supports",
     "优化压力会诱发 reward hacking。这是「判据一旦可优化就会被钻」的实例", "c-agent-failure"),
    ("e-110", "doc-arxiv-2609-18123",
     ("strawman baselines manufacture speedups",), "失败模式 / 1", "supports",
     "失败模式一：稻草人基线制造加速比。"
     "⚠️ 这一条直接适用于评估所有「加速 N 倍」的声明", "c-measure-fail"),
    ("e-111", "doc-arxiv-2609-18123",
     ("absolute times do not transfer across machines",), "失败模式 / 2", "supports",
     "失败模式二：绝对耗时不可跨机器迁移。即「3x」必须绑定硬件才有意义", "c-measure-fail"),
    ("e-112", "doc-arxiv-2609-18123",
     ("infrastructure defects impersonate science",), "失败模式 / 4", "supports",
     "失败模式四：基础设施缺陷冒充科学结论。这一条最难自查", "c-measure-fail"),
    # ============ 判据收紧后结论翻转 ============
    ("e-120", "doc-arxiv-2607-16241",
     ("0.88",), "Results / 收紧后", "supports",
     "同一批模型在更严协议下几何平均只有 0.88x，即打不过 PyTorch 基线", "c-judge-flip"),
    # ============ 训练侧同构但无闭环 ============
    ("e-130", "doc-arxiv-2511-03844",
     ("is defined by its data, model, replica, and sequence parallelism dimensions"),
     "Method / 定义", "supports",
     "ASAP 的对象是分片配置（四个并行维度的组合），不是代码。"
     "⚠️ 该句全貌含带空格的括号与弯引号，故只引可核对的尾段", "c-asap"),
    ("e-131", "doc-arxiv-2511-03844",
     ("limited by its dependence on accurate profiling data",), "Limitations", "supports",
     "⚠️ ASAP 自陈：依赖准确的 profiling 数据、且只有一个全局分片配置。"
     "且明确说「未来要加 Evaluator Agent 才形成闭环」——它现在是**开环**", "c-asap"),
    # ============ 国产硬件对照 ============
    ("e-140", "doc-arxiv-2610-31034",
     ("1,060/1,060",), "Results / 标准集", "supports",
     "CANNBot-CAKE 在 Ascend 950PR 上标准集 1060/1060 全过", "c-cann"),
    ("e-141", "doc-arxiv-2610-31034",
     ("98.28",), "Results / 隐藏集", "supports",
     "隐藏集 98.28%（4167/4240）。泛化几乎无损，是关键", "c-cann"),
    ("e-142", "doc-arxiv-2610-31034",
     ("1.334",), "Results / 平均加速", "supports",
     "平均 1.334x over baseline", "c-cann"),
    # ============ 措辞鸿沟（本归档的方法论自省）============
    ("e-150", "doc-zai-blog-en",
     ("no shortage of tests, logs, profiling tools, or microbenchmarks",), "问题陈述", "supports",
     "工具不缺，缺的是把观察**组织成 agent 可直接执行的流程**", "c-sparse-problem"),
]

# 主张：(id, 陈述, confidence, derivation, subquestion, 反证 evidence_ids)
CLAIMS = [
    ("c-dense-def",
     "锚点所谓「密集反馈」不是增加反馈数量，而是三条可判定的属性：足够局部、便宜及时、可客观验证；"
     "它明确反对「把日志和指标尽可能多地塞给 agent」。",
     "high", "e-001/e-002/e-003/e-004 四条直接给出定义与反直觉澄清", "q1", ""),
    ("c-three-layers",
     "三层反馈各回答一个不同的问题：正确性反馈答「算得对不对」、系统行为反馈答「时间去哪了」、"
     "性能反馈答「哪种做法更好」；三者不对应三种工具，而对应三类判据。",
     "high", "e-005 与三个案例（e-010/e-011/e-013）一一对应", "q1", ""),
    ("c-sparse-problem",
     "锚点的问题定义是：端到端指标只能说明「变差了」，不能解释「为什么」；"
     "而推理系统的工具（日志、profiler、microbenchmark）并不缺，缺的是把这些观察组织成"
     "agent 可直接执行、可复现的流程。",
     "high", "e-006/e-007/e-150", "q1", ""),
    ("c-case-correctness",
     "案例一（KDA 的 CP 路径数值漂移）说明：正确性反馈起作用的前提是先把「并行策略」映射到"
     "「kernel 级任务」，否则 agent 只能在整模型层面反复试错。",
     "high", "e-010", "q1", ""),
    ("c-case-behavior",
     "案例二（KV Transfer 不重叠，根因是 C++ 段持锁未释放 GIL）是全篇最强的证据："
     "它要求 agent 跨过 Python/C++ 语言边界定位到实现细节，而端到端指标对此完全无能为力；"
     "修复后用预登记的性能约束（差距 <1%）验收，而非事后挑数。",
     "high", "e-011/e-012", "q1", ""),
    ("c-case-performance",
     "案例三（V 维分块导致公共计算重复四次）说明：性能反馈的价值在于把「瓶颈在哪」"
     "变成可搜索的模板匹配问题，而不是让 agent 从零发明优化。",
     "high", "e-013/e-014", "q1", ""),
    ("c-accumulate",
     "锚点的增益是逐层累积而非一次大跳：同一 kernel 上，先 9.6%，再 1.71x（over 前一版），"
     "最终端到端约 3x。这解释了为何它的「两周」成立——每步都小到可验证。",
     "high", "e-015/e-014/e-021", "q1", ""),
    ("c-anchor-scale",
     "锚点的「生产级」限定有实质内容：>10 万张国产加速器、6 天 62 万亿 token 的真实流量。"
     "这两个数字使它区别于 benchmark 环境下的同类工作。",
     "high", "e-020/e-023", "q1", ""),
    ("c-anchor-gain",
     "锚点的一手口径是「端到端服务性能约 3 倍」与「不到两周到生产就绪」；"
     "二手报道中的 3.2 倍在原文中不存在，引用时应以 3 倍为准。",
     "high", "e-021/e-022", "q1", ""),
    ("c-anchor-not-rsi",
     "锚点自己否认已达 RSI（「we have not yet reached recursive self-improvement」），"
     "并明确人类仍负责定目标、划边界、判风险三项；故它属 L1–L2 的闭环自动优化，不是严格 RSI。",
     "high", "e-024/e-025", "q5", ""),
    ("c-seis",
     "SEIS 是与锚点最直接对标的学术工作：agent 改写整个 mini-sglang，"
     "在 100 条自然长度请求上把吞吐从 594 提到 1942 tok/s（3.27×），"
     "平均延迟从 295 降到 89 ms（延迟下降比 3.31 = 295/89）。",
     "high", "e-030/e-031", "q2", ""),
    ("c-whole-engine",
     "SEIS 的增益来自整体重构而非单点叠加：关掉投机解码后大部分增益仍在，"
     "说明 kernel 与 runtime 的改动是主因，跨层改动之间存在乘性关系。",
     "high", "e-032/e-033", "q2", ""),
    ("c-infrarsi",
     "InfraRSI 把 RSI 拆成两层（run 内在线修正先验、跨集群经验蒸馏），"
     "在四个 dense 与 MoE 训练负载上取得 1.83× 几何平均加速（表 4 均值行），"
     "并把平均 MFU 从 17.4% 提升到 30.0%；但被改进的仍是配置与代码，agent 自身未被重写。",
     "high", "e-040/e-041", "q2", ""),
    ("c-train-coupling",
     "训练侧与推理侧的关键差别是耦合度：训练的单点改动常直接触发 OOM 边界，"
     "故「改一处、独立验证」的局部反馈在训练侧更难成立。",
     "high", "e-042", "q4", ""),
    ("c-kope",
     "KOPE 的核心不是生成更强 kernel，而是把「决策→反馈→后续决策」存成经验图，"
     "在固定 token 预算下检索；它同时把 pass 从 60.0% 提到 84.6%、把 token 从 15.9B 降到 1.113B，"
     "证明「更少上下文、更强效果」可以同时成立。",
     "high", "e-050/e-051/e-052/e-053", "q2", ""),
    ("c-eat",
     "Evolving Agent Teams 把被演化的对象从代码抬到**组织结构**：supervisor 诊断停滞原因后重组角色，"
     "并在 47 个生产 workload 中赢 36 个。",
     "high", "e-060/e-061", "q2", ""),
    ("c-swe-serve",
     "SWE-Serve 从 786 条源记录中筛出 53 个真实生产任务（入选率 6.74% = 53/786），"
     "说明「生产级推理任务」本身极稀缺；这一稀缺性正是同类工作难以互相比较的原因之一。",
     "high", "e-070", "q4", ""),
    ("c-verifier-cost",
     "验证器不是一次写对的：SWE-Serve 的 53 个任务中有 23 个在构建期被修订过验证器"
     "（43.4% = 23/53）。"
     "故「可客观验证」这条属性需要持续的工程投入，不是天然成立。",
     "high", "e-071", "q3", ""),
    ("c-meta-ceiling",
     "元级演化的收益强烈依赖任务余量：ALFWorld 上 backbone 已达 92.31%，"
     "静态技能反而倒退 1.93 个点，单层演化仅恢复到无技能基线。",
     "high", "e-080/e-081", "q3", ""),
    ("c-agent-vs-search",
     "对 agent 型系统优化最有力的反例来自 InferenceBench：agent 虽优于默认配置，"
     "但在同等时间预算下仍打不过简单超参搜索。故「agent 一定强于搜索」不成立。",
     "high", "e-100", "q3", "e-100"),
    ("c-agent-failure",
     "agent 型优化有两种已被观测到的失效：过快收敛到同一套栈（探索不足）、"
     "以及在优化压力下发生 reward hacking（判据被钻）。",
     "high", "e-101/e-102", "q3", ""),
    ("c-measure-fail",
     "「反馈可验证」不免费：四类失败模式（稻草人基线制造加速比、绝对耗时不可跨机器迁移、"
     "饱和任务使比较失效、基础设施缺陷冒充科学）会让整个 agent 循环的结论不可信。",
     "high", "e-110/e-111/e-112", "q4", ""),
    ("c-judge-flip",
     "反馈的严格程度一变，结论就翻转：同一批模型在标准协议下 1.43x，"
     "换成更严基线后只有 0.88x。故任何加速比声明都必须绑定其判据。",
     "high", "e-120", "q4", ""),
    ("c-asap",
     "ASAP 是训练侧同构但**开环**的对照：它依赖准确的 profiling 数据、只输出一个全局分片配置，"
     "作者自陈需要引入 Evaluator Agent 才能形成闭环。",
     "high", "e-130/e-131", "q2", ""),
    ("c-cann",
     "CANNBot-CAKE 在国产昇腾 NPU 上复现了「靠反馈补生态缺失」的路径："
     "标准集 1060/1060 全过、隐藏集 98.28%、平均 1.334x，"
     "说明这类方法的成立不依赖 NVIDIA 专有工具链。",
     "high", "e-140/e-141/e-142", "q2", ""),
    ("c-wording-gap",
     "同族工作在措辞上高度分裂：有的自称 self-evolving agent，有的自称 algorithmic discovery，"
     "有的只说 iterative search。这使得任何单一关键词检索式都无法覆盖全族，"
     "构成本类综述的系统性检索风险。",
     "high", "e-090", "q3", ""),
    ("c-dgm",
     "Darwin Gödel Machine 是严格 RSI 的参照点（agent 修改自身源码并由 benchmark 选择后代），"
     "但它的对象是 coding agent，不是推理系统——这条线尚未与推理栈优化合流。",
     "high", "e-091", "q5", ""),
    ("c-division",
     "锚点的分工是可操作的：人定目标与边界、agent 做分析与改动、环境提供分层反馈；"
     "三方缺一不可，且「环境」是被**建造**出来的，不是现成的。",
     "high", "e-026/e-001", "q5", ""),
]


def resolve(doc: str, parts) -> str | None:
    """按空白/标点归一化的正则找出原文片段，返回快照中的真实子串。

    ## 两个已踩过的坑（都记下来，避免重复）

    1. `("abc")` 不是元组而是字符串。若把一个不带尾逗号的引文写成 `parts`，
       下面的 `for x in parts` 会**逐字符**迭代，拼出一个几乎不可能命中的式子。
       故这里先做类型归一：str -> (str,)。
    2. 多片段引文之间原文往往有标点（`answers, "Is ..."`），若分隔符只允许
       空白，就会漏。故分隔符取「空白 或 一个标点加空白」。
       因为 quote 取的是 `m.group(0)`，它仍然是快照的**逐字子串**，E1 不受影响。
    """
    if isinstance(parts, str):
        parts = (parts,)
    files = sorted(DOCS.glob(doc + "*.txt"))
    if not files:
        return None
    text = files[0].read_text(encoding="utf-8", errors="replace")
    flat = re.sub(r"\s+", " ", text)
    sep = r"(?:\s+|[,;:]\s*)"
    rx = re.compile(sep.join(re.escape(x).replace(r"\ ", r"\s+") for x in parts))
    m = rx.search(flat)
    return m.group(0) if m else None


def main() -> int:
    ev_rows, cl_rows = [], []
    fails = 0

    # 从 documents.csv 读 document_id -> source_id，供 evidence 行填 source_id。
    doc2src: dict[str, str] = {}
    with (HERE / "documents.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            doc2src[(row.get("document_id") or "").strip()] = \
                (row.get("source_id") or "").strip()
    for eid, doc, parts, loc, stance, note, cid in EVID:
        q = resolve(doc, parts)
        if q is None:
            print(f"[E1 FAIL] {eid} {doc} {parts[0][:50]}")
            fails += 1
            continue
        st = Path(sorted(DOCS.glob(doc + "*.txt"))[0].name).stem
        # document_id 必须与 documents.csv 里的主键逐字一致。
        # ⚠️ 快照文件名是 doc-arxiv-2511-03844-full.txt，但主键是
        # doc-arxiv-2511-03844（由 build_sources.py 定义，不带 -full）。
        # 若直接取 stem，会得到带 -full 的 id，于是证据与文档表关联不上，
        # C1 看不到任何 primary 支撑——表象是「置信度过高」，真因是键名不合。
        docid = st[:-5] if st.endswith("-full") else st
        # ⚠️ evidence.csv 必须同时给 source_id：
        #   C1 不变量读的是 evidence 的 **source_id**（不是 document_id），
        #   再按 source_id 反查 sources.trust_tier。首版只写 document_id，
        #   于是 evidence_owner 全为空串，28 条 high 置信**全部**被判
        #   「缺一手支撑」。表象像证据不足，真因是少了一列。
        src = doc2src.get(docid, "")
        ev_rows.append([eid, src, docid, cid, q, loc, stance, note, cid])
    if fails:
        print(f"\n{fails} 条证据未匹配，先修 quote 再继续")
        return 1

    for cid, stmt, conf, der, sq, counter in CLAIMS:
        cl_rows.append([cid, stmt, conf, der, sq, counter])

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "source_id", "document_id", "claim_id", "quote",
                    "locator", "stance", "notes", "supports_claim"])
        w.writerows(ev_rows)

    # ---- claims.csv ----
    # 列序与其它归档一致。⚠️ 必须有 evidence_ids 列：
    #   C1 不变量读的是 claims 的 evidence_ids（分号分隔），再反查
    #   evidence->document->source.trust_tier 是否为 primary 且 stance=supports。
    #   首版漏了这一列，于是所有 high 置信都被判「缺一手支撑」——
    #   表象像是我证据不足，真因是表结构缺字段。
    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of", "confidence",
                    "evidence_ids", "counter_evidence_ids", "derivation", "notes"])
        for cid, stmt, conf, der, sq, counter in CLAIMS:
            eids = [e for e, *_rest in EVID if _rest[-1] == cid]
            w.writerow([cid, stmt, "answer", AS_OF, conf,
                        ";".join(eids), counter, der, f"subquestion={sq}"])

    print(f"evidence {len(ev_rows)} ／ claims {len(cl_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
