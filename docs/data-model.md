# 数据模型与不变量

核心原则：**保留可回溯的分层数据，而不是只存 embedding**。embedding 可重建，来源快照与片段定位不可重建。

## 实体总览

```text
Source ──1:N──> Document ──1:N──> Evidence ──N:M──> Claim
                                                      │
                                   Entity ──N:M──> Relation
                                                      │
ResearchRun ──> Brief / Plan / Trace / Report ────────┘
```

## Source — 来源

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_id` | str | 稳定 ID，如 `src-nvidia-ws-edition` |
| `url` | str | 原始 URL 或 DOI |
| `source_type` | enum | `official` / `vendor` / `review` / `academic` / `community` / `press` |
| `publisher` | str | 发布方 |
| `published_at` | date? | 发布时间；未知时为 null |
| `updated_at` | date? | 最近更新时间 |
| `fetched_at` | datetime | 抓取时间（必须有时区） |
| `language` | str | BCP-47 |
| `trust_tier` | enum | `primary`（自行产生观测）/ `secondary`（转述他人）/ `tertiary`（聚合，无原始观测） |
| `access` | enum | `open` / `paywalled` / `blocked` / `login_required` |
| `license` | str? | 许可或使用限制 |
| `notes` | str? | 主观备注，不参与事实判定 |

**不变量 S1**：`fetched_at` 必填。任何引用都必须能回答"你在什么时候看到的"。
**不变量 S2**：`access != open` 的来源不得用于支撑关键主张。

## Document — 文档

| 字段 | 类型 | 说明 |
|---|---|---|
| `document_id` | str | |
| `source_id` | str | 外键 |
| `content_hash` | str | 正文 sha256，用于去重与版本检测 |
| `raw_uri` | str | 对象存储路径（HTML / PDF 快照） |
| `parser_version` | str | 解析器版本，保证可重放 |
| `sections` | list | 章节 / 页码结构 |
| `text` | str | 抽取后的纯文本 |

**不变量 D1**：`content_hash` 变化即视为新版本，不覆盖旧记录。
**不变量 D2**：学术元数据与网页正文分开存储，便于纠错与重新解析。

## Evidence — 证据片段

| 字段 | 类型 | 说明 |
|---|---|---|
| `evidence_id` | str | |
| `document_id` | str | 外键 |
| `quote` | str | 精确片段（原文，不改写） |
| `locator` | str | 章节 / 页码 / 段落锚点 |
| `stance` | enum | `supports` / `refutes` / `context` |
| `extracted_by` | str | 抽取器版本或人工标记 |

**不变量 E1**：`quote` 必须是原文子串。允许截断，不允许改写或翻译后回填。

## Claim — 原子主张

| 字段 | 类型 | 说明 |
|---|---|---|
| `claim_id` | str | |
| `statement` | str | 单一事实的陈述句 |
| `claim_type` | enum | `spec` / `measurement` / `price` / `attribution` / `prediction` |
| `as_of` | date | 该主张成立的时点 |
| `confidence` | enum | `high` / `medium` / `low` / `disputed` |
| `evidence_ids` | list[str] | 支持证据 |
| `counter_evidence_ids` | list[str] | 反证 |
| `derivation` | str? | 若为系统推断，写明推导链 |

**不变量 C1**：`confidence=high` 要求至少一条 `trust_tier=primary` 的 `supports` 证据。
校验器强制执行；不满足时报告必须给出具体 `claim_id`，处置只有两种——补一手证据，或降为 `medium`。

> **`trust_tier` 与 `source_type` 正交，别把权威性当来源性质。**
>
> 曾经踩过的坑：把 `independent`（独立评测自跑测量）、`review`（媒体实测）、
> `community`（社区自跑 benchmark）一律标成 `secondary`，理由隐含是"它们不如官方权威"。
> 但 `secondary` 的定义是**转述他人数据**，这些来源恰恰是**自己产生了被引用的观测**，
> 应属 `primary`。错标的直接后果是 451 条高置信主张里有 309 条"违反 C1"——数字看着骇人，
> 实际是标注口径错了，不是证据不足。
>
> 可操作的判据：**这段数据是谁第一次测出来的？**
> - 自己测的（厂商实验室、独立评测、媒体实测、社区 benchmark、学术论文、官方规格页）→ `primary`
> - 引用别人测的（新闻转述、博客综述、厂商 PPT 引用第三方数字）→ `secondary`
> - 只做索引/聚合，无原始观测（榜单站、比价站、导读页）→ `tertiary`
>
> 按此判据重新标注后，违规从 309 降到 39；剩下 39 条是真的只有媒体转述支撑，
> 已如实降为 `medium` 并在 `notes` 记录原因。
**不变量 C2**：系统推断不得写成来源事实；必须填 `derivation` 并在报告中标注。
**不变量 C3**：冲突主张并列呈现，不强裁决；`confidence=disputed` 时报告必须展示双方。

## Paper — 论文

`Paper` 不是一个新的事实容器，而是对已有 `Claim` 的**一次有选择的呈现**。
它不引入新的证据，只决定哪些主张进入正文、以什么顺序、配哪张图。

| 字段 | 说明 |
|---|---|
| `paper_id` | `paper-<slug>` |
| `slug` | 指向 `research/<slug>/` |
| `sections[]` | 章节：编号、标题、正文文件、引用的 claim_id |
| `figures[]` | 图：类型、标题、数据文件、引用的 claim_id |
| `tables[]` | 表：标题、数据文件、引用的 claim_id |

### 为什么 Paper 不是第五种实体

`Source -> Document -> Evidence -> Claim` 是一条**证据链**，每一层都在增加信息。
`Paper` 不增加信息，它只**减少**信息——从 2,238 条主张里选出 23 条。

把它放在证据链之外，是为了防止一种失败模式：**把论文当成新的一层事实来源**。
一旦允许「论文里写了就算数」，引用闭合就断了。

### 不变量

- **P1（引用闭合）**：`Paper` 引用的每个 `claim_id` 必须存在。
- **P2（数值可回溯）**：`paper/data/*.csv` 里每个数值，必须能在对应 claim 的
  `statement`、`derivation` 或其任一 `evidence.quote` 里找到。
- **P3（无凭空图表）**：`paper.json` 声明的每张图/表，其产物文件必须真实存在且非空。

P1–P3 由 `scripts/audit_paper.py` 实现，可放进 CI。


## ResearchRun — 一次研究运行

| 字段 | 说明 |
|---|---|
| `run_id` | |
| `brief` | 研究简报快照 |
| `plan_version` | 计划版本号（动态规划会多次变更） |
| `trace` | 结构化事件：查询、来源、耗时、预算消耗 |
| `budget` | token / 工具调用 / 墙钟时间上限与实际消耗 |
| `report_version` | 输出版本 |
| `eval` | 本次运行的评测结果 |
| `stop_reason` | `answered` / `budget_exhausted` / `gap_remaining` / `error` |
| `stop_note` | `stop_reason` 的自然语言说明；`budget_exhausted` / `gap_remaining` 时为必填 |

**不变量 R1**：`stop_reason` 必填。预算耗尽时必须返回"已完成 + 未解决问题"，不得静默截断。
**落地形式**：每个研究目录下的 `run.json`（schema 见 `packages/schemas/json/run.schema.json`）。
`trace` 每条事件至少含 `seq` / `kind` / `summary`，可选携带 `source_ids` / `evidence_ids` / `claim_ids`
反向链接到留档；`kind` 枚举见 schema。**trace 的引用必须闭合**——指向不存在的来源或证据视为校验失败。

**不变量 R3**：`trace` 的 `seq` 在单次运行内唯一且递增。
**不变量 R2**：每个子问题必须有状态：`answered` / `partial` / `unanswered`。

## Brief — 研究简报

```yaml
question: 核心问题（一句话）
scope: { topic: ..., region: ..., language: ..., time_range: ... }
as_of: 2026-10-27          # 信息截止时点
freshness: realtime | 30d | historical
deliverable: comparison | progress_table | roadmap | tracking_report
constraints:
  source_priority: [official, academic, review, community]
  citation_style: inline_markdown
  depth: deep
  budget: { max_tool_calls: 120, max_minutes: 40 }
exclusions: [...]
subquestions:
  - id: q1
    question: ...
    expected_evidence: ...
    done_when: ...
```

## 评测指标映射

| 层 | 指标 | 数据来源 |
|---|---|---|
| 检索 | Recall@k、来源覆盖、最新版本命中、重复率 | `SearchTrace` vs 参考来源集 |
| 证据 | 片段定位准确率、支持/反驳判断、元数据正确率 | `Evidence` 抽样人工核对 |
| 报告 | 问题覆盖、事实正确、引用准确、时效性、结构完整 | rubric 评分 |
| 系统 | 成功率、延迟、单任务成本、工具错误率 | `ResearchRun.trace` |
| 进化 | 改动前后配对评测、跨主题泛化、回归率 | `evals/reports/` |
