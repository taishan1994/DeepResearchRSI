# tests

单元与集成测试。测试目标不是覆盖率数字，而是**契约不被破坏**。

## 必测项

| 对象 | 测什么 |
|---|---|
| `packages/schemas` | 数据类的不变量（ID 前缀、时区、quote 非空） |
| `scripts/validate_research.py` | 能检出悬空引用、重复 ID、缺字段 |
| `services/ingestion` | 内容哈希去重、版本化、解析失败降级 |
| `services/evidence` | 片段必须是原文子串（E1） |
| `services/research` | 预算耗尽时返回"已完成+未解决"（R1） |
| `services/evolution` | 候选改动未经门禁不能生效 |

## 契约测试优先

新增字段或改字段名时，先改 `packages/schemas/json/*.schema.json`，再改 Python 侧，最后改测试。测试应能在契约不一致时失败。

## 真实数据回放

`research/rtx-pro-6000` 的 188 条证据可作为解析与抽取的回放样本：给定来源快照，抽取器应能重建这些证据（或给出明确差异）。

## 当前状态

待建（阶段 1）。
