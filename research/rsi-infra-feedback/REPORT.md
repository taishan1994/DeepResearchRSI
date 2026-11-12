# rsi-infra-feedback

> 状态：已交付
> 信息截止：2026-11-12
> 来源数：29 ｜ 证据数：52 ｜ 主张数：28（全部 high）

<!-- 校验结果（由 scripts/sync_report_counts.py 从 CSV 刷新）：
     sources=29, evidence=52, claims=28, claims_high=28, claims_disputed=0, trace_events=20, c3_violations=0, subquestions=5, r2_violations=0, c1_violations=0 -->

## 1. 执行摘要

本归档研究「RSI 优化推理系统」这一族工作。锚点是智谱 2026-09-17 的工程报告
*Toward Recursive Self-Improvement: How GLM Built Its Own Inference Infrastructure*。

**核心论断**（见 `brief.yaml`）：反馈的价值取决于三条属性——足够局部、便宜及时、
可客观验证——而不取决于反馈体量或模型强弱。

**结论**：论断被 52 条证据支持，且被两组反向证据界定了边界。
严格意义的 RSI 尚未在推理系统这一环出现：现有工作改进的都是**产物**
（代码、配置、经验），而不是**改进者**。

**可证伪性**：论断允许两个方向的反例。若出现「反馈很少但很粗、模型很强、
优化仍成功」的案例，论断被推翻；InferenceBench 的负结果
（agent 在同等预算下打不过超参搜索）属边界证据而非反例，因为它的
搜索空间本就简单、不需要可归因反馈。

## 2. 范围与方法

- **时间范围**：2024-06 ～ 2026-11
- **纳入**：以 agent 闭环改进推理/训练系统或 kernel 的工作；系统级基准；判据类研究
- **排除**：纯人工调优；纯编译器方法；无实验的立场文

检索分三层，详见论文第 9 章：

1. **14 组检索式 × 2 种排序取并集**（relevance 保覆盖、submittedDate 保新鲜）→ 2908 候选
2. **必检自检**：把「应该有哪些」写成清单（10 篇），缺一篇即 `exit 1`
3. **盲测**：剥离 id 兜底，只统计检索式自身召回

## 3. 主体分析

谱系按**反馈构造方式**而非任务类型划分（论文第 3 章）：

| 层 | 被改进的对象 | 判据 | 代表 |
|---|---|---|---|
| L1 单点工具 | 单 kernel | 只有一轮、无跨轮记忆 | GPU Kernel Scientist |
| L2 闭环优化 | 代码 / 配置 | 多轮、反馈驱动、改进者固定 | 锚点、SEIS、KOPE、InfraRSI、ASAP、CANNBot-CAKE |
| L3 元级改进 | 改进策略 / 组织结构 | 慢循环改「怎么改」 | MetaSkill-Evolve、Evolving Agent Teams |
| L4 严格 RSI | 改进者自身源码 | benchmark 选后代、archive 累积 | Darwin Gödel Machine |

## 4. 争议与证据缺口

### 4.1 已记录的冲突

**冲突一：agent vs 搜索。** 锚点主张 agent 能解决端到端指标无法归因的问题；
InferenceBench 报告 agent still fall below a simple hyperparameter search under the
same time budget（最高 11.53×）。二者不矛盾但必须并列：前者面对复杂系统、
后者面对简单搜索空间。按 C3 不变量，本文在 6.3 节并列呈现。

**冲突二：加速比口径。** 同一批模型在标准协议下 1.43×，收紧后 0.88×。
本文一律标注判据，不报裸数字。

### 4.2 引用纪律

- 锚点原文为 `roughly 3×` / `tripling`，**全文无 3.2**。二手报道的 3.2× 不采。
- InfraRSI 四负载几何平均是 **1.83×**；2.75× 仅为单 workload 最佳值，不当作总体。
- SEIS 的 3.27× 与延迟 295→89 ms 均已独立复核。

### 4.3 证据缺口

1. InfraRSI 仓库极新，无第三方复现。
2. 锚点闭源，3× 无法外部复现。
3. KOPE 的经验图跨硬件迁移未验证。
4. 「No Second Run」的反面论证未独立复核，仅作待检验对立面记录。

## 5. 方法自省：三次因方法缺陷整体漏收

这一节必须写，因为**召回缺陷比结论错误更隐蔽**。

### 5.1 第一次：用旧归档的产物做新归档的检索

第一轮候选集是从 `research/*/documents/` 里 grep 出来的。这构成循环：
旧归档定义了「域」，未被旧归档收录的工作自动变成「不存在」。

KOPE（2608.25570）就躺在同级归档的 `documents/` 里，我甚至打印过它的摘要，
却仍然漏收。

**教训**：检索式必须从问题写起，不能从语料写起。

### 5.2 第二次：按日期排序截断了奠基工作

用 `sortBy=submittedDate` + `max_results=60`，导致 DGM（2025-05）、
AlphaEvolve（2025-05）、AutoKernel（2026-03）落在时间窗外。

**修正**：relevance + date 两种排序取并集，每式 200 篇。

### 5.3 第三次：检索式全部建立在同一套词汇上

最初的检索式由「agent / self-evolving / serving」构成，而目标工作用完全不同的
词自我描述：DGM 说 evolutionary program search / archive / open-ended，
AlphaEvolve 说 algorithmic discovery。探测显示 8 种改述里 7 种捞不到 AlphaEvolve，
只有 `all:"algorithmic discovery"` 能命中。

### 5.4 自检机制本身也曾失效

加入 `id_list` 兜底后，必检自检 10/10 全绿，但实际召回是 9/10——
兜底把漏检掩盖了。

**修正**：要求「补入候选数」为 0 才算通过。

### 5.5 仍未解决

修正后已知答案召回从 1/10 到 10/10，但这**只证明能找回我已知道的工作**，
对「未知的未知」零证据。AutoKernel、DGM、AlphaEvolve 各自只依赖一条检索式。

### 5.6 表结构的三次误报（本轮新增）

写证据层时连续踩三个坑，共同点是**表象像内容不足、真因是表结构缺字段**：

1. `evidence.csv` 缺 `source_id` 列 → C1 读到空串，28 条 high 置信**全部**误报
2. `claims.csv` 缺 `evidence_ids` 列 → 同上
3. `document_id` 带 `-full` 后缀与主键不一致 → 关联断裂

第一个最危险：它看起来像「证据确实不足」。若当时选择**降低置信度**而非查根因，
就会把 28 条站得住的主张降级，且永不发现是表结构问题。

**教训**：不变量报错时，先验证「报错所依赖的字段是否真的被填了」，
再判断内容是否不足。

## 6. 产物清单

```
rsi-infra-feedback/
├── brief.yaml              研究问题与可证伪论断
├── fetch_candidates.py     检索（三层防护）
├── candidates.json         2908 候选
├── build_sources.py        来源与快照登记
├── build_claims.py         证据与主张生成（含 E1 校验）
├── sources.csv             29 来源
├── documents.csv           29 文档
├── evidence.csv            52 证据
├── claims.csv              28 主张
├── documents/              29 快照
├── notes/
└── paper/
    ├── PAPER.md            综述正文（可投稿行文）
    ├── paper.json          图/表规格
    ├── make_data.py        数据层（数值列统一 value）
    ├── make_figures.py     4 张实验图
    ├── make_frameworks.py  4 张框架结构图
    ├── data/ tables/ figures/
    └── latex/              main.tex + body.tex + references.tex + main.pdf
```

## 7. 校验状态

| 检查 | 结果 |
|---|---|
| validate_research | 通过（E1 52/52、C1 0 违反、S1/D1 全过） |
| audit_paper | 通过（引用主张 23 个、图 8、表 4、数值回溯 16 条） |
| check_paper | FAIL 0（I1–I5 全过） |
| check_latex | FAIL 0 / WARN 0（11 页，X1–X6） |
| check_layout | FAIL 0 / WARN 1（L7 为参考文献区英文短词，非真分片） |

## 8. 复现

```bash
python research/rsi-infra-feedback/fetch_candidates.py
python research/rsi-infra-feedback/build_sources.py
python research/rsi-infra-feedback/build_claims.py
python research/rsi-infra-feedback/paper/make_data.py
python research/rsi-infra-feedback/paper/make_figures.py
python research/rsi-infra-feedback/paper/make_frameworks.py
python scripts/md_to_tex.py research/rsi-infra-feedback/paper
cd research/rsi-infra-feedback/paper/latex && xelatex main.tex && xelatex main.tex
```

## 9. 参考文献

完整来源列表见 `sources.csv`（29 条，含 URL 与抓取时间）。
论文正文的参考文献见 `paper/PAPER.md` 末节与 `paper/latex/references.tex`。
