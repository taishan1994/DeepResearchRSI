# rsi-serving 调研报告（过程记录）

> 这是一个**执行记录**，不是论文。论文在 [`paper/PAPER.md`](./paper/PAPER.md) 与
> [`paper/latex/main.pdf`](./paper/latex/main.pdf)。本文件记录：为什么这么问、
> 检索与筛选怎么做的、哪些判断被推翻了、以及还有什么没解决。

## 0　这次调研的由来

上一篇 [`rsi-inference`](../rsi-inference/REPORT.md) 做的是 **kernel 层**的 RSI：
被优化对象是一段可独立编译、独立计时、独立验算的 GPU 程序。

本篇换对象：**端到端推理**——serving 栈、投机解码、调度、量化、配置搜索。
触发点是 SpecPilot（arXiv 2611.02501）：它整轮整轮地改投机解码栈，
并且把「改进了没有」写成脚本能算的量。

换对象的代价是判据全变了。kernel 层的判据是一个数（相对基线的稳健计时）；
端到端层的判据是一组统计量 + 一个无损定义 + 一份成本账。**这篇报告的主体就是这三样东西。**

## 1　问题怎么收敛的

### 1.1　初始问题太宽

初始问题是「端到端推理优化里的 RSI 进展如何」。这个问题无法回答，因为：

- 「RSI」在语料里至少指三种东西：改被优化对象、改优化器本身、改脚手架的提议机制。
- 「端到端」的边界模糊：配置搜索算不算？量化算不算？

### 1.2　改成「判据能不能闭合」

于是把问题改成一句可检验的话：

> 端到端层的瓶颈不是「测不到速度」，而是**测到的速度不足以支撑判定**。

若成立，则创新应集中在判据（配对运行、置信下界、无损定义、注入故障验证），
而不是搜索算法。第 7 章的四种失效是它的边界，第 8 章的脚手架实证是它的反证。

### 1.3　六个子问题

| 编号 | 子问题 | 落到哪一章 |
|---|---|---|
| q1 | 端到端被优化的到底是什么？ | §2 |
| q2 | 「改进」用什么判据才闭合？ | §3 §4 §5 |
| q3 | 循环长什么样，权限边界在哪？ | §3.2 §8.1 |
| q4 | 增益与代价各是多少？ | §6 |
| q5 | 判据在哪里失效？ | §7 |
| q6 | 有什么可迁移的判据工程？ | §9 |

## 2　检索与筛选

### 2.1　检索

五组检索式、23 条式子、时间下限 2025-01-01，走 arXiv 官方 API（`fetch_serving.py`）：

| 组 | 关注 | 代表式子 |
|---|---|---|
| A | 投机解码 | speculative decoding draft tree verification |
| B | 服务系统 | LLM serving system agent optimize throughput |
| C | 算法发现 | agent discover inference optimization |
| D | 量化 | quantization agent hardware-aware deployment |
| E | 循环 | self-evolving inference engine recursive improvement |

去重后 **1403 篇**候选（其中 2026 年 1001 篇、2025 年 157 篇）。

### 2.2　筛选

硬标准：core 必须实现「agent 改动端到端推理链路并拿到端到端反馈」的循环，且给出可核对的实验。

- **core 15 篇**：SpecPilot、SEIS、VibeServe、Conjugate Compilation、MetaInfer、
  AIConfigurator、ROCm InferaSim、HAQA、AE-LLM、Ada-MK、RaMP、SpecRSI、
  Verify Less Evolve More、Self-HPO、harness 自演化
- **旁证 8 篇**：InferenceBench、AutoTuneBench、ServeLearnBench、TraceLab、Frontier、
  vLLM/llm-d 控制面、ADOR、ThunderAgent

排除：只改单个 kernel 的（已由 rsi-inference 归档）、纯训练效率、只在摘要给倍数而无判据描述。

### 2.3　抓取结果

| 项 | 数量 |
|---|---|
| 纳入来源 | 23 |
| 全文抓取成功 | 23 / 23（0 失败） |
| 摘要快照 | 23 份 |
| 全文快照 | 23 份 |
| digest 行数 | 1037 |

## 3　主张怎么来的，哪些被删了

### 3.1　两轮收敛

第一轮 6 条（对象 / 晋级 / 无损 / ceiling / 增益 / 成本），第二轮 6 条（边界 / 测量 / 记忆 / 检索混淆 / 脚手架 / 迁移）。

每条主张至少 3 条证据、至少 1 条 primary supports（C1），共 **60 条证据**。

### 3.2　被删掉的东西（重要）

**一张图画不出来，是因为它不成立。**

初版 fig2 是「三轮累计增益」折线：1.16 → 1.55 → 2.13。
校验器 `audit_paper.py` 判它 FAIL，理由是 1.55 在任何证据里都找不到——
它是从论文两张不同的表里拼出来的中间值。

按 P2（数值可回溯）的规矩，正确做法不是补一条证据，而是**删掉这张图**。
最终 fig2 换成了脚手架自改进的漏斗（125 → 24 → 12 → 3），每个数字都有逐条出处。

同一轮里还改了 fig1 的一个值：AIConfigurator 的「+40%」原来被写成倍数 1.40，
与其余六行的「倍数」口径不一致，改为 40.0 并在标签里注明是百分比。

### 3.3　被降级的东西

第 8.1 节的三条 RSI 判据里，第 1 条「改进是否随时间加速」被判为**证据不足**。

理由：语料里没有任何一篇给出「增益随轮次递增」的曲线，只有终点值。
这不是没找到，而是这类证据在这个领域里普遍不报——它本身就是一条发现。

## 4　校验链

| 检查 | 结果 |
|---|---|
| `validate_research.py` | sources=23 evidence=60 claims=12 e1_checked=60 e1_unverifiable=0，C1/C3/R2 全 0 |
| `audit_paper.py` | 4 图 6 表，数值回溯全通过 |
| `check_paper.py` | FAIL 0 / WARN 0（I1–I5） |
| `check_latex.py` | FAIL 0 / WARN 0（X1–X6），8 页 |
| `check_layout.py` | FAIL 0 / WARN 0（L1–L7），8 页 |
| 仓库整体 | 9/9 通过（含本篇） |

### 4.1　为了这篇改的一个工具

`scripts/check_layout.py` 的 L6（行宽填充率）原来按**版心宽度**算，
对双栏排版恒得 ~50%，必然 FAIL。

改成按**栏**算：把行按「左端是否在页面中点右侧」分左右两栏，
每栏的边界取该栏实测最大右端，中位数比边界。

改完后：rsi-serving 8 页 0 FAIL 0 WARN、rsi-inference 9 页 0 FAIL 0 WARN、
pd-disagg 19 页 0 FAIL（3 个 WARN 是图引用次数，与 L6 无关）。

## 5　没解决的事

1. **两篇的关键数字只在摘要**（locator 标 `abstract`），未在全文核对到。
2. **纳入集是人工判断**：15 core + 8 旁证的取舍没有被任何校验器覆盖。
3. **没有自跑实验**：全部数字二手，可逐条点回原文，但本文未复现任何一条。
4. **发布偏差**：反号与失效证据都来自正面论文的消融，真正失败的工作不会被写出来。
5. **「增益加速」无证据**：这是本文对该领域最重的一条批评，也是最可能被后续工作推翻的一条。

## 6　文件

| 文件 | 作用 |
|---|---|
| `brief.yaml` | 问题、子问题、核心假设 |
| `fetch_serving.py` | 五组检索式 → `candidates_serving.json` |
| `build_serving.py` | 筛选 → `sources.csv` / `documents.csv` / `included_serving.json` |
| `fetch_fulltext.py` | 抓 23 篇全文到 `documents/` |
| `make_digest.py` | 全文 → 1037 行 `digest.txt` |
| `build_claims.py` | 60 条证据 + 12 条主张 → `evidence.csv` / `claims.csv` |
| `paper/make_data.py` | 数据层 → `paper/data/*.csv`、`paper/tables/*.csv` |
| `paper/make_figures.py` | 四张图 |
| `paper/PAPER.md` | 论文正文 |
| `paper/latex/main.pdf` | 排版结果（8 页） |
| `run.json` | 14 条 trace |
