# DeepResearchRSI

自动调研的 RSI（受评测约束的系统级自我改进），辅助日常文献检索与信息收集。

整体架构：

![DeepResearchRSI 整体架构图：检索层、证据层、主张层与受控进化环](./assets/image-20261027154416558.png)

## 这个仓库是什么

一个**持续运行的研究工作台**，不是"搜网页 + 写摘要"：

1. **研究一次** — 把开放问题拆成可回答的子问题，检索学术 / Web / 内部资料，产出带引用的报告。
2. **跟踪进展** — 为主题、论文、作者、方法、基准建立实体关系与时间线，新信息出现时给**增量变化**而不是重写综述。
3. **能审计** — 每个结论回到来源片段 + 版本 + 发布时间 + 抓取时间；区分来源事实 / 作者主张 / 系统推断 / 未知。
4. **受控进化** — 从轨迹里找失败模式，改进可回滚的检索策略、记忆规则与工作流；先离线评测，再灰度。

详细设计见 [ARCHITECTURE.md](./ARCHITECTURE.md) · [docs/](./docs/README.md) · [ADR](./docs/adr/)

**这个系统是怎么变的**：[自我进化记录](./docs/EVOLUTION.md)（五个阶段、七条判据、三次没起作用的改进） · [经验手册](./docs/LESSONS.md)（可复用的做法与它们的出处）

**目前搜过哪些来源**：[来源清单](./docs/SOURCES.md)——把 14 个归档的 `sources.csv` 汇成一份，按性质 / 站点 / 年份分组，共 771 个地址（脚本生成，可 `--check` 防漂移）。

## 目录一览

```text
apps/api                  用户 API、任务状态、报告访问
apps/web                  研究结果浏览（证据展开、冲突并列、轨迹审计）
services/orchestrator     状态机、预算、重试、并行度、可恢复执行
services/providers        学术 / Web / 内部文档适配器
services/ingestion        下载、解析、分段、去重、版本管理
services/evidence         Claim / Evidence 抽取、来源匹配、冲突图
services/research         规划、检索 worker、分析、综合、核验
services/evolution        轨迹归因、候选策略、离线评测、发布门禁
packages/schemas          ResearchBrief / Evidence / Claim / Source 契约（JSON + Python）
evals/                    回归案例、基准适配器、评分报告
research/                 每次真实研究任务的留档（数据目录）
docs/                     数据模型、目录职责、路线图、架构决策记录
scripts/                  校验与骨架生成工具
tests/                    契约与不变量测试
```

每个目录都有 README 说明**负责什么、不负责什么**。

## 快速开始

仓库当前处于**规范先行 + 首个研究任务已完成**阶段：Schema、校验器与流程契约可运行，服务实现待补。

```bash
# 校验研究留档的自洽性（引用闭合、字段完整、不变量）
python scripts/validate_research.py

# 生成一份新的研究任务骨架
python scripts/new_research.py --slug my-topic --question "……"

# 跑契约与不变量测试（无需 pytest）
python tests/test_schemas.py
```

## 已完成的研究任务

| 任务 | 主题 | 规模 |
|---|---|---|
| [rtx-pro-6000](./research/rtx-pro-6000/REPORT.md) | NVIDIA RTX PRO 6000 Blackwell 全系性能分析 | **447 来源 / 3002 证据 / 2238 主张（1882 高置信、9 争议）**，70 个子问题 |
| [rsi-model-training](./research/rsi-model-training/REPORT.md) | 模型训练中的递归自我改进（RSI）：外部锚点的迁移与证据边界 | **53 来源 / 63 证据 / 48 主张（25 高置信）/ 0 争议**，61 篇编码 + 10 页 LaTeX 论文 |
| [pro6000se-dsv41](./research/pro6000se-dsv41/REPORT.md) | RTX PRO 6000 Blackwell **Server Edition** 部署 DeepSeek-V4.1-Flash | **26 来源 / 138 证据 / 48 主张（43 高置信）/ 0 争议**，15 页 LaTeX 论文 |
| [rsi-inference-bench](./research/rsi-inference-bench/REPORT.md) | RSI-Inference Bench 与 ML 工程基准这一族：判据的形状决定循环闭不闭 | **22 来源 / 62 证据 / 15 主张（13 高置信）/ 0 争议**，9 章 LaTeX 论文 |
| [rsi-infra-feedback](./research/rsi-infra-feedback/REPORT.md) | RSI 优化推理系统：从「更多反馈」到「可执行反馈」的谱系、判据与证据强度 | **29 来源 / 52 证据 / 28 主张（28 高置信）/ 0 争议**，10 章 11 页 LaTeX 论文（8 图 4 表） |

> 📄 **论文**：`research/rtx-pro-6000/paper/` 下有一份 11 页综述
> [PAPER.pdf](./research/rtx-pro-6000/paper/PAPER.pdf)
> （中文，4 图 2 表，引用 23 条主张），由
> `python scripts/build_paper.py research/rtx-pro-6000/paper` 从同一批 CSV 生成。
> 论文层是 r257 新增的：它不新增事实，只对已有主张做有选择的呈现，
> 并由 `scripts/audit_paper.py` 校验「每个数字都能回到一条主张及其证据」。

**最新一份**：[在 RTX PRO 6000 Server Edition 上部署 DeepSeek-V4.1-Flash](./research/pro6000se-dsv41/paper/latex/main.pdf)
（15 页双栏，3 图 12 表，中文，XeLaTeX 编译）。它回答四件事：要几张卡、什么软件栈、
能跑多快、会踩什么坑——并把「实测 / 推算 / 空白」逐格标注，而不是给一个平均数。
由 `python research/pro6000se-dsv41/build_all.py` 重建。

上一份是[模型训练中的 RSI](./research/rsi-model-training/paper/latex/main.pdf)
（10 页双栏，5 图 4 表），它问的不是「能不能自我改进」，而是
「这些闭环在改什么、证据能不能支撑它们用的词」。


该报告的几个结论值得单独一提：

- **相对 RTX 5090 的领先幅度从 -38% 到 +108%**，取决于负载与 SKU。买它是为了"装得下"（96GB），不是为了"算得快"。
- **三个 SKU 差异来自固件而非硬件**：强制 300W 时 Server 版比 Workstation 版快 38%；但 Blender 上 Server 版可能垫底。
- **渲染没有统一答案**：V-Ray 上 Server 版第一，Blender/Octane 上 Workstation 版第一，同一张卡的 Server 版 Blender 成绩两个来源相差 69%（已标 disputed）。
- **每美元渲染性能排 33 张卡的末位**：RTX 5090 的每美元性能约为它的 3 倍。
- **训练侧存在序列长度交叉点**：<4K 时比 GH200 快 1.8×，>8K 时慢 1.7–1.8×；优化器卸载在 PCIe 上基本不可用。
- **一个未被评测覆盖的运维风险**：多名用户报告在役 SW Power Cap 锁频，性能掉到 1/10–1/20，且不产生任何错误日志。
- **分辨率敏感性相差 20 倍**：同一张卡 4K 相对 FHD 的落差从 +7%（creo）到 +159%（energy），unreal 甚至反向 -10%。高分屏对可视化类负载是真实成本。
- **ISV 认证必须逐应用、逐 SKU 核对**：Dassault 已认证（WS + Max-Q），Ansys 则是 Fluent 仅 Linux、Rocky 仅 Max-Q、Speos 完全不支持。
- **官方认证 ≠ 满血运行**：NVIDIA 认证系统清单里明确写着「GPU power is capped based on system capabilities」。

## 设计红线

- 网页与 PDF 内容是**不可信数据**，不得作为工具指令执行。
- 不抓登录态、不绕过访问控制、尊重站点条款与删除请求。
- 自改代码 / 模型权重属于高风险阶段，必须人工审阅 + 隔离运行 + 独立安全评测。
- 奖励信号不只用 LLM 自评：混合可验证指标、人工抽检与用户反馈。
- **冲突不强裁决**：`confidence=disputed` 的主张必须并列呈现双方（[ADR-0003](./docs/adr/0003-conflict-presentation.md)）。
- **证据必须可回溯**：`Evidence.quote` 是原文子串，`Source.fetched_at` 必填且带时区（[ADR-0002](./docs/adr/0002-evidence-provenance.md)）。