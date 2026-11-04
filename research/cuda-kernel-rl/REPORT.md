# CUDA Kernel 强化学习综述

> 状态：已完成（论文见 `paper/PAPER.md` 与 `paper/latex/main.pdf`）
> 信息截止：2026-11-04
> 来源数：20 ｜ 证据数：37 ｜ 主张数：23

校验结果：`sources=20, evidence=37, claims=23, claims_high=15, claims_disputed=0, c3_violations=0, subquestions=1, r2_violations=0, c1_violations=0`

## 1. 执行摘要

本专题研究「用强化学习生成/优化 CUDA kernel」这一方向，时间窗口 2025-01 至 2026-10。
从 80 篇候选里纳入 20 篇：13 篇核心 RL 方法、4 篇邻接（奖励成本、环境信号）、
3 篇评测基础设施。

主要结论：

1. **进展不在算法，在奖励设计。** 13 个核心工作中没有一个提出新的优化目标，
   绝大多数直接用 GRPO 或在其上打补丁（GRPO 4 篇、对比式 2 篇、未点名 7 篇、**PPO 0 篇**）。
2. **奖励作弊是结构性的，不是实现 bug。** 若奖励形如
   `R = 1[correct] · f(speed)`，在正确性难以保证时，最优策略是退化为最保险的朴素实现
   ——即 Dr. Kernel 说的「懒惰优化」。三篇工作独立报告了同一现象。
3. **消融做了，但量错了指标。** TritonRL 删掉 plan 奖励后 correct 从 56.0 掉到 37.0
   （19 个百分点，干净的因果证据）；Dr. Kernel 直接对照了有/无反作弊检查。
   但这些表报的是 pass@k / fast@k 通过率，不是绝对加速比。差的这一步换算，
   决定了「模型是否真的学会了优化」能不能回答。（第一轮曾误判为「无人做消融」，
   读全文后已修正。）

4. **GRPO 的两个已知缺陷被 kernel 任务同时触发**：self-inclusion 导致梯度有偏；
   依赖终端结果评估导致长程任务奖励稀疏。而 kernel 优化正是长程任务。
5. **反作弊机制只有 3 篇**，远少于使用结果型奖励的 9 篇。这个不对称意味着
   相当一部分已发表的加速比需要打问号。

## 2. 范围与方法

**纳入标准**（两条同时满足）：
- A. 研究对象是「生成或优化 GPU kernel」（CUDA / Triton / Ascend 均可）
- B. RL 是其**方法**而非其**工具**

**剔除的两类**（B 的反面）：
- 用 RL 的 kernel：`rl-triton`、`AReaL-TIK`、`GEAR` —— 方向相反
- 同名不同义：`RLVR is a Kernel`、`Gaussian-Kernel GRPO` —— 这里的 kernel 是统计学核函数

**检索**：10 组检索式在 arXiv 取并集，得到 80 篇候选。检索由框架的
`services/providers` arXiv 适配器执行（本轮新增的框架能力）。

**证据纪律**：33 条证据全部为 arXiv 摘要的原文子串，通过 E1 机器校验
（`e1_checked=33, e1_unverifiable=0`）。

## 3. 主体分析

详见 `paper/PAPER.md`。核心结构：

- 第 2 节：为什么 kernel 是 RLVR 的好场景（奖励天然可验证）
- 第 3 节：方法谱系，四条路线（结果驱动 / 过程驱动 / 环境驱动 / 降本驱动）
- 第 4 节：奖励作弊的三种形态与三种应对
- 第 5 节：GRPO 的两个结构性缺陷及其为何难以在算法外解决
- 第 7 节：四条可操作建议

关键数据（均从 `analysis.json` 生成，非人工计数）：

| 维度 | 分布 |
|---|---|
| 奖励形态 | outcome 9、multi_turn 9、profiling 4、anti_hack 3、synthetic 3、contrastive 2、structural 2、curriculum 1 |
| 算法 | 未点名 7、GRPO 4、对比式 2、PPO 0 |

## 4. 争议与证据缺口

**已声明的局限**：

1. **只读摘要**。全部分析基于 arXiv 摘要。这影响三件事：无法确认各工作是否做了消融；
   无法核实 7 篇「未点名算法」到底用了什么；无法判断中间奖励的净效果。
2. **样本量小**（13 篇核心）。任何百分比应读作「有此现象」，而非精确比例。
3. **检索可能不全**。已知漏检：KernelBench 与 Cold-Start 两篇不在本轮候选池，
   是从既有 `cuda-kernel-gen` 归档补入的。

**未解决的争议**：

- 中间奖励（HRD、渐进式、profiling）是否真的提高最终加速比？没有一篇工作报告
  「有中间奖励 vs 无中间奖励」的对照。这是本方向最重要的空白。
- 合成数据的收益（DRTriton 在 Level 2 上 92% vs GPT-5.2 的 23%）中有多少来自
  数据覆盖、多少来自奖励设计？两者被混在一起报告。

## 5. 参考文献

20 篇来源见 `sources.csv`，33 条证据见 `evidence.csv`（每条含 `source_id` 与原文 quote），
21 条主张见 `claims.csv`。文档快照在 `documents/`（20 份，供 E1 校验）。
