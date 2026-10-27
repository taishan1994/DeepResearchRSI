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
| `trust_tier` | enum | `primary`（一手）/ `secondary`（二手转述）/ `tertiary`（聚合） |
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
**不变量 C2**：系统推断不得写成来源事实；必须填 `derivation` 并在报告中标注。
**不变量 C3**：冲突主张并列呈现，不强裁决；`confidence=disputed` 时报告必须展示双方。

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

**不变量 R1**：`stop_reason` 必填。预算耗尽时必须返回"已完成 + 未解决问题"，不得静默截断。
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
