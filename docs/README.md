# docs/

设计与决策文档。

## 文档清单

| 文件 | 内容 |
|---|---|
| [directories.md](./directories.md) | 目录职责与边界，API 端点草案 |
| [data-model.md](./data-model.md) | 实体字段、不变量、评测指标映射 |
| [SOURCES.md](./SOURCES.md) | **来源清单**：全项目搜过的地址，按性质 / 站点 / 年份分组（脚本生成） |
| [roadmap.md](./roadmap.md) | 四阶段实现路线与验收门槛 |
| [EVOLUTION.md](./EVOLUTION.md) | **自我进化记录**：五个阶段、七条判据、三次失败 |
| [LESSONS.md](./LESSONS.md) | **经验手册**：可复用的做法与它们的出处 |
| [adr/](./adr/) | 架构决策记录 |

### 关于 SOURCES.md

它回答一个跨归档的问题：**这个项目目前一共搜过哪些地方**。
每个 `research/<slug>/sources.csv` 只回答「这一篇用了哪些来源」；
14 个归档拼起来才看得出检索面实际长什么样。

由 `scripts/source_inventory.py` 从 `sources.csv` 现算生成，**不要手改**。
`--check` 比对文档与数据是否一致，可挂进 CI 防漂移：

```
python scripts/source_inventory.py          # 重新生成
python scripts/source_inventory.py --check  # 只比对，不一致则退出码 1
```

两个口径值得先知道：

- **按 URL 去重，不按 `source_id`。** 后者是归档内的局部命名，
  同一篇论文在四个归档里就是四个同名 id、四条记录——按它数会虚高。
- **但按 URL 数也会低估。** `rsi-inference-bench` 把同一个仓库的 14 份文件
  登记成 14 个独立来源（各有自己的快照与 `trust_tier`），URL 却只有一个。
  两个数都得看，SOURCES.md 第 6 节把这两类重复分开列了。

### 关于 EVOLUTION 与 LESSONS 的区别

这两份容易混，分工如下：

- **EVOLUTION.md** 回答「这个系统实际怎么变的」——按阶段记录触发了什么、
  加了什么机制、代价是什么，并附可复现的统计（`scripts/evolution_stats.py`）。
  它是**历史**，只写发生过的。
- **LESSONS.md** 回答「这些经验能不能迁移」——上篇是做项目的通用做法，
  下篇是自我改进的做法。每条都注明出处，没有出处的建议不收。

两份都有「三次没起作用」的章节。只记成功会失真。

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
