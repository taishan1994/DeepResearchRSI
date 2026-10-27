# packages/schemas

跨模块共享的数据契约。**单一事实来源**，服务实现只能引用它，不能各自定义。

## 两侧必须同步

| 位置 | 用途 |
|---|---|
| `json/*.schema.json` | 语言无关；API 校验、前端类型生成 |
| `python/deepresearchrsi/` | Python 数据类与校验函数，服务直接 import |

改一侧必须同时改另一侧，并在 `docs/data-model.md` 记录变更。

## JSON Schema 清单

| 文件 | 对应实体 | 关键约束 |
|---|---|---|
| `brief.schema.json` | `ResearchBrief` | `as_of` 必填；`subquestions` 至少 1 条 |
| `claim.schema.json` | `Claim` | 至少 1 条 `evidence_ids`；`prediction` 必须有 `derivation` |
| `source.schema.json` | `Source` | `fetched_at` 必填且带时区 |

## Python 侧

```python
from deepresearchrsi import Brief, Claim, Evidence, Source, validate_research_dir
```

数据类在 `__post_init__` 里强制不变量：
- `Source.fetched_at` 必须 timezone-aware（S1）
- `Evidence.quote` 非空（E1）
- `Claim` 至少一条证据（C1）
- `Claim.claim_type == "prediction"` 必须有 `derivation`（C2）

## 校验入口

```bash
python scripts/validate_research.py research/rtx-pro-6000
```

## 依赖约束

本包**不得**依赖任何 `services/*` 模块。依赖方向是单向的：services → schemas。

## run.schema.json

`ResearchRun` 的契约，落地为每个研究目录下的 `run.json`。回答「这次研究是**怎么跑出来的**」：

- `stop_reason`（**R1**）：`answered` / `budget_exhausted` / `gap_remaining` / `error`；
  后两者必须同时给 `stop_note` 说明未解决部分。
- `trace`：结构化事件序列，`seq` 唯一递增（**R3**），`kind` 枚举见 schema。
  事件可携带 `source_ids` / `evidence_ids` / `claim_ids`，**必须指向真实存在的记录**。
- `budget`：`limits` 与 `used` 分离，便于事后审计是否超支。
- `eval`：本次运行的评测结果；`citation_support_rate` 需人工抽样，未抽样时留空而非填 1.0。
