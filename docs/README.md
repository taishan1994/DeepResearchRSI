# docs/

设计与决策文档。

## 文档清单

| 文件 | 内容 |
|---|---|
| [directories.md](./directories.md) | 目录职责与边界，API 端点草案 |
| [data-model.md](./data-model.md) | 实体字段、不变量、评测指标映射 |
| [roadmap.md](./roadmap.md) | 四阶段实现路线与验收门槛 |
| [adr/](./adr/) | 架构决策记录 |

## 架构决策记录（ADR）

一条决策一个文件，写明背景、选项、结论、后果与复查触发条件。

| ADR | 决策 |
|---|---|
| [0001](./adr/0001-modular-monolith.md) | 首版采用模块化单体，而非微服务 |
| [0002](./adr/0002-evidence-provenance.md) | 证据必须留存原文片段与抓取时间 |
| [0003](./adr/0003-conflict-presentation.md) | 冲突不强裁决，并列呈现 |

## 写 ADR 的时机

- 做了会影响多个模块的选择
- 拒绝了一个看起来合理的替代方案（需要解释为什么不选）
- 引入了以后难以撤销的约束

**不要**为显而易见的实现细节写 ADR。
