# agent-serving-bench 调研报告（过程记录）

> 这是一个**执行记录**，不是论文。论文在 [`paper/PAPER.md`](./paper/PAPER.md) 与
> [`paper/latex/main.pdf`](./paper/latex/main.pdf)。本文件记录：目标论文讲了什么、
> 谱系是怎么追出来的、哪些判断被推翻、以及还有什么没解决。

## 0　目标论文是什么

**ServerBench: How can your coding agents design specialized LLM serving systems?**
（arXiv [2611.06841](https://arxiv.org/abs/2611.06841)，CMU + USC，2026-11-04）

它问的是：**让 coding agent 从零造出一整套 LLM 推理服务系统，然后由谁来判它造成了？**

### 0.1　它堵的三个缺口

| 缺口 | 原来的做法 | 它的改法 |
|---|---|---|
| 负载简化 | 独立请求，或固定 prefill / decode 场景 | 回放真实 coding-agent 会话（多轮、共享前缀、并行子 agent 分支、轮间延迟） |
| 只比加速比 | 相对基线的加速或吞吐，负载固定 | dollars per dollar：每美元 GPU 成本的合格 token 价值 |
| 只查正确性 | 对参考实现或测试集查输出 | 全新部署 + 留出种子回放 + 事后评审 |

### 0.2　它的结果

11 个 coding-agent 模型 × 3 档部署 = 33 次运行：

- **22 次通过验证，13 次超过最强基线**；
- 最好成绩：Claude Sonnet 5.5 在 Gemma E4B 上 2.97，是 vLLM 参考的 4.87 倍；
- Claude Opus 5.5 在 Qwen3.5 9B 上 4.40（SGLang 参考的 2.71 倍）；
- 同一 agent 跨档位会反号：GPT 6.1 Sol 一档 2.84，另一档 0.98（参考 1.47）。

### 0.3　它自己报的三个发现

1. 高价值设计会把「容量提升」与「负载选择」一起调；
2. agent 会用与负载相关的实验去解读性能反馈；
3. 可靠交付要求验证「优化引入的执行路径」。

## 1　本文做了什么

用户的问题是两件事：**研究这篇论文**，以及**调研是否还有类似的「agent + LLM 推理系统」论文**。

第一件在 §0 已答。第二件的答案是：**有，而且不止一类，一共 13 篇，可以按任务尺度分成四级。**

| 尺度 | 工作 | 与 ServerBench 的关系 |
|---|---|---|
| 整套服务系统 | **VibeServe**（2605.06068） | 最接近的同型：外层规划 + 内层实现的 agent 循环，端到端生成整套服务栈 |
| 整套服务系统 | **SEIS**（2610.04646） | 唯一自称 self-evolving：会话间继承代码与经验，迭代整个 mini-sglang |
| 整套服务系统 | **ServerBench**（2611.06841） | 目标论文：把它做成可比较的基准 |
| 整套服务系统 | FlashRT（2607.18171） | harness 路线：用 chain-of-program 引导 agent 做多卡部署 |
| 整套服务系统 | Simthesizer（2608.24650） | 对象换成模拟器：agent 把自然语言特性请求下沉成仿真实现 |
| 单引擎开放式优化 | **InferenceBench**（2607.20468） | 关键反例：同等预算下简单超参搜索胜过 agent |
| 仓库级功能 | SWE-Serve（2609.26777） | 53 个 SGLang 生产变更任务 |
| 仓库级功能 | InfraDev（2610.36589） | 36 个跨 Megatron-LM / vLLM / verl 的 PR |
| 优化补丁 | ISO-Bench（2602.19594） | 54 个 vLLM / SGLang 已合并 PR |
| 测量可信度 | AutoTuneBench（2609.18123） | 四种失效模式，把「可信」做成架构 |
| 单 kernel | KernelBench（2502.10517） | 这条线的起点 |
| 单 kernel | KernelBench-Verified（2607.16241） | 对起点的审计：TF32 基线 + 四分布隐藏测试 |
| 负载刻画 | TraceLab（2606.30560） | 约 4,300 条 coding-agent 会话的公开轨迹 |
| 负载刻画 | AgentPerfBench（2609.34683） | 把负载换成 agentic 轨迹 |

加粗的四篇是 core。**注意 VibeServe 与 SEIS 都没有被 ServerBench 引用**——它们是同期独立工作，这正是本次调研的价值所在。

## 2　谱系是怎么追出来的

### 2.1　三轮检索

| 轮次 | 方法 | 收获 |
|---|---|---|
| 一 | 按标题精确检索 ServerBench 引用的 10 个基准 | 确认它引用的是哪条线 |
| 二 | 7 组宽关键词（coding agent + serving / benchmark / kernel……） | **捞出它没引用的同型工作**：VibeServe、SEIS、InfraDev、AutoTuneBench、Simthesizer、FlashRT |
| 三 | 5 组补充（self-evolving、serving engine 自动设计……） | 确认没遗漏：self-evolving 方向只命中 SEIS 一篇 |

第二轮是关键。如果只顺着 ServerBench 的 related work 走，会漏掉 VibeServe 和 SEIS——而这两篇恰好是"同型但没被引用"的两篇，也是回答"还有没有类似论文"的核心。

### 2.2　筛选口径

纳入标准是：**让 agent 去造或改推理系统的**，而不是"用 agent 优化某个数"。

按这条排除掉的典型：纯 kernel 生成（KernelBench 系列只留作尺度对照）、纯调度/缓存优化（对象不是 agent）、纯模型侧优化。保留 KernelBench 与 AutoTuneBench 的理由是它们提供判据的另一半。

## 3　哪些判断被推翻了

### 3.1　「agent 造系统一定比人手调更好」——被推翻

InferenceBench 的结论很直接：agent 能超过朴素 PyTorch、常追平默认配置的引擎，但**同等预算下输给简单超参搜索**；作者归因为可靠性与纪律失败，不是能力天花板。

这条推翻了"让 agent 自由探索就会更好"的直觉。

### 3.2　「换更强的模型就行」——被推翻

ISO-Bench 报：同样的底层模型配不同脚手架，表现差别显著，脚手架与模型同等重要；也没有单一 agent 在所有代码库上占优。

ServerBench 自己的跨档位反号（一档 2.84、另一档 0.98）也支持这一点。

### 3.3　「基准的数字可以直接比」——被推翻

这也是我在写论文时改过一次的地方。初稿想画一张"各家增益对比"的柱状图，把 4.87 / 2.3 / 3.27 / 8.08 放在一起。

**后来删了。** 因为这四个数的基线完全不同（vLLM 参考 / 调优后 SGLang / 原始 mini-sglang / 朴素 PyTorch），放在一张图里等于造假。改成表 3，逐行标注基线，并把"可否跨行比较"写成全否。

四张图最后全部是**同一篇论文内部的对照**：交付漏斗、跨档位反号、验证覆盖、诚实基线前后。

### 3.4　一个差点写错的地方

初稿把"agent 能造服务系统"和"agent 造得更好"混为一谈。核到数字后才发现：**22/33 通过验证，只有 13/33 超过基线**——差了 9 次。

这个区分成了论文第 4 章的主线，也是结论"它能造出通过验证的系统，但还不能保证造出更好的系统"的来源。

## 4　校验链

| 检查 | 结果 |
|---|---|
| `validate_research.py` | sources=14, evidence=60, claims=12, claims_high=12, claims_disputed=0, trace_events=14, c3_violations=0, subquestions=6, r2_violations=0, c1_violations=0（e1_checked=60、e1_unverifiable=0） |
| `audit_paper.py` | 4 图 6 表，3 条数值回溯全通过 |
| `check_paper.py` | FAIL 0 / WARN 0（I1–I5） |
| `check_latex.py` | FAIL 0 / WARN 0（X1–X6），7 页 |
| `check_layout.py` | FAIL 0 / WARN 0（L1–L7），7 页 |

## 5　没解决的事

1. **SEIS 的「继承优于独立」只有一句摘要级结论**，没核到具体数值。这是全篇最脆的一条，已在 `run.json` 的 `stop_note` 里标注。
2. **纳入集 6 core + 8 旁证是人工判断**，未被任何校验器覆盖。
3. **没有自跑实验**，全部数字二手。
4. **ServerBench 自身的局限**：负载只来自一个 coding-trace 来源，三档部署、闭循环回放，跨架构与跨加速器的泛化性它自己也声明了限制。
5. **没有回答"这条线多久能到 RSI"**：语料里没人给时间线。

> 📌 **相关归档**：[rsi-inference-bench](../rsi-inference-bench/REPORT.md) 处理的是
> 另一类装置——不是「让 agent 造整套服务系统」，而是「给 agent 一个真实引擎
> 和 1~8 张卡，判它能不能把新模型服务起来 / 优化到多少 / 修掉一个回归」。
> 两篇互补：本篇问「agent 造的系统好不好」，那篇问「谁判它做成了」。
> 那篇的核心发现可以直接接到本篇的第 5 章——它的验证也是**独立 verifier 重建
> 引擎后实测**，与本篇「验证器而非生成器是瓶颈」同构。

## 6　文件

| 文件 | 作用 |
|---|---|
| `brief.yaml` | 问题、六个子问题、核心假设 |
| `build_agent_serving.py` | 候选文本 → `sources.csv` / `documents.csv` / `documents/` |
| `build_claims.py` | 60 条证据 + 12 条主张 → `evidence.csv` / `claims.csv` |
| `paper/make_data.py` | 数据层 → `paper/data/*.csv`、`paper/tables/*.csv` |
| `paper/make_figures.py` | 四张图 |
| `paper/PAPER.md` | 论文正文 |
| `paper/latex/main.pdf` | 排版结果（7 页） |
| `run.json` | 14 条 trace |
