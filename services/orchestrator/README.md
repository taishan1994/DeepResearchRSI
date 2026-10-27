# services/orchestrator

研究任务的状态机与资源管理。

## 职责

- `ResearchRun` 状态迁移：`queued → planning → retrieving → analyzing → synthesizing → verifying → done/failed`
- 全局预算控制：工具调用数、token、墙钟时间
- 重试与退避（针对限速与临时故障）
- 并行度控制（worker 数量）
- 断点恢复：进程崩溃后能从最后一个检查点继续

## 不负责

- 具体检索逻辑（`services/providers`）
- 报告写作（`services/research`）

## 关键不变量

- **R1**：`stop_reason` 必填。预算耗尽时必须返回"已完成 + 未解决"，不得静默截断。
- **R2**：每个子问题必须有状态。状态从 `unanswered` 单向推进到 `answered` 或 `partial`，不得回退。

## 事件模型

每次状态迁移、查询、来源抓取、预算消耗都写入结构化事件流。这是"为何选择此来源/为何结束研究"审计视图的数据源。

## 当前状态

规范已定，实现待补（阶段 1）。
