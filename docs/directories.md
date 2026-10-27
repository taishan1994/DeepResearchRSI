# 目录职责与边界

本文规定每个目录**负责什么、不负责什么**，避免模块边界在实现期被侵蚀。首版采用**模块化单体**：目录是逻辑边界，可以同进程运行；出现独立扩展需求后再拆服务。

## 顶层布局

```text
apps/          对外入口（进程边界）
services/      领域能力（逻辑边界，首版同进程）
packages/      跨模块共享的契约与工具
evals/         评测资产与运行结果
research/      真实研究任务的留档（数据，不是代码）
docs/          设计与决策文档
scripts/       本地开发工具
tests/         测试
assets/        图片等静态资源
```

## apps/

| 目录 | 职责 | 不负责 |
|---|---|---|
| `apps/api` | HTTP 入口、鉴权、任务提交与状态查询、报告读取 | 研究逻辑、检索、解析 |
| `apps/web` | 报告浏览、证据展开、轨迹审计视图 | 直接访问数据库 |

**API 契约（首版收敛为 6 个端点）**

```
POST /research-runs              创建任务 → run_id
GET  /research-runs/{id}         状态 / 事件流
GET  /research-runs/{id}/report  报告（Markdown + 结构化 claims）
POST /topics                     创建持续跟踪主题
GET  /topics/{id}/updates        相对上次运行的增量变化
GET  /evidence/{id}              证据片段与来源元数据
```

报告与每个 claim 都必须携带 `evidence_ids`，供 UI 展开来源。

## services/

| 目录 | 职责 | 关键输出 |
|---|---|---|
| `orchestrator` | 状态机、预算、重试、并行度、断点恢复 | `ResearchRun` 状态迁移事件 |
| `providers` | 统一 `SearchProvider` / `DocumentProvider` 适配器 | 检索结果 + 原始文档 |
| `ingestion` | 下载、解析、分段、去重、版本化 | `Document`（含内容哈希与解析器版本） |
| `evidence` | Claim / Evidence 抽取、来源匹配、冲突图 | `Claim`、`Evidence`、`Relation` |
| `research` | 规划、检索 worker、分析、综合、核验 | 报告草稿 + 缺口清单 |
| `evolution` | 轨迹归因、候选策略、离线评测、发布门禁 | 版本化策略 + 评测报告 |

**不允许的跨层调用**

- `providers` 不得直接写 `Claim`（必须先经 `ingestion` 得到 `Document`）。
- `research` 不得直接访问 provider 的 SDK，只能走接口。
- `evolution` 不得在运行时修改生产配置，只能产出**候选版本**交给门禁。

## packages/schemas

单一事实来源（single source of truth）的契约层：

- `json/*.schema.json` — 语言无关的 JSON Schema，供 API 校验与前端类型生成。
- `python/deepresearchrsi/` — Python 数据类与校验函数，服务实现直接引用。

修改契约必须同时更新两侧，并在 `docs/data-model.md` 记一行变更说明。

## evals/

| 目录 | 内容 |
|---|---|
| `evals/cases/` | 回归案例：问题、截止日期、参考来源、关键主张、评分 rubric |
| `evals/adapters/` | 基准适配器（DeepResearch Bench、内部任务集） |
| `evals/reports/` | 一次评测运行的分数、配对比较、失败清单 |

每个真实任务经审核后可沉淀为回归案例。热点追踪任务必须加**时间切片测试**，防止系统使用未来信息。

## research/

**这是数据目录，不是代码目录。** 每次研究一个子目录，结构固定：

```text
research/<slug>/
├── brief.yaml        研究简报（问题、范围、截止时点、交付物、子问题）
├── sources.csv       来源登记表（ID、URL、类型、日期、抓取时间、可信度）
├── claims.csv        主张表（ID、主张、类型、置信度、支持/反驳证据）
├── REPORT.md         最终报告
└── notes/            过程笔记、原始摘录
```

字段定义见 `docs/data-model.md`。`scripts/validate_research.py` 会检查引用闭合性。

## docs/

- `adr/` — 架构决策记录（ADR），一条决策一个文件，写明背景、选项、结论与后果。
- `data-model.md` — 实体、字段、不变量。
- `directories.md` — 本文。
- `roadmap.md` — 分阶段实现路线与验收标准。
