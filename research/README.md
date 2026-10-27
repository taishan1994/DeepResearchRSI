# research/

真实研究任务的留档。**这是数据目录，不是代码目录。**

## 结构约定

每个任务一个子目录，目录名用 kebab-case slug：

```text
research/<slug>/
├── brief.yaml      研究简报
├── sources.csv     来源登记表
├── evidence.csv    证据片段表
├── claims.csv      主张表
├── REPORT.md       最终报告
└── notes/          过程笔记（可选）
```

## 已有任务

| slug | 主题 | 规模 |
|---|---|---|
| [rtx-pro-6000](./rtx-pro-6000/REPORT.md) | NVIDIA RTX PRO 6000 Blackwell 全系性能分析 | **225 来源 / 1783 证据 / 1266 主张（971 高置信）/ 5 争议** |

## 新建任务

```bash
python scripts/new_research.py --slug my-topic --question "要回答的核心问题"
```

## 校验（必须通过）

```bash
python scripts/validate_research.py             # 校验全部
python scripts/validate_research.py research/rtx-pro-6000
```

校验项：

- `source_id` / `evidence_id` / `claim_id` 前缀正确且唯一
- `evidence` 引用的 `source_id` 存在
- `claim` 引用的 `evidence_ids` 与 `counter_evidence_ids` 都存在（引用闭合）
- `fetched_at`、`as_of` 非空且可解析
- `prediction` 类主张必须有 `derivation`
- `REPORT.md` 中的 `[c-*]` / `[e-*]` / `[src-*]` 引用均能解析

## 写作纪律

1. **每个事实性结论都要能点回原文片段。** 做不到的句子不写。
2. **区分四类陈述**：来源事实 / 作者主张 / 系统推断 / 未知。系统推断必须标 `derivation`。
3. **冲突并列呈现，不强裁决**（见 [ADR-0003](../docs/adr/0003-conflict-presentation.md)）。
4. **写明信息截止时间**与已知证据缺口。不写"实时"这类无信息量的词。
5. **不引用无法定位原文的二手转述数字**，除非明确标注为 `tertiary` 且仅用于价格/时间点。
