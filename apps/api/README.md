# apps/api

研究任务的 HTTP 入口。**只做协议转换与鉴权，不放研究逻辑。**

## 职责

- 接收 `ResearchBrief`，校验后创建 `ResearchRun`
- 查询运行状态与结构化事件
- 返回报告（Markdown + 结构化 claims）
- 主题订阅的创建与增量查询
- 证据片段读取（供 UI 展开来源）

## 端点（首版 6 个）

```
POST /research-runs              创建任务 → run_id
GET  /research-runs/{id}         状态 / 事件流
GET  /research-runs/{id}/report  报告 + claims + evidence_ids
POST /topics                     创建持续跟踪主题
GET  /topics/{id}/updates        相对上次运行的增量变化
GET  /evidence/{id}              证据片段与来源元数据
```

## 不负责

- 检索、解析、抽取、综合（在 `services/`）
- 直接访问数据库中的研究数据（通过 service 接口）

## 契约

请求/响应体必须符合 `packages/schemas/json/*.schema.json`。任何新增字段先改 schema，再改实现。

## 当前状态

规范已定，实现待补（阶段 1）。
