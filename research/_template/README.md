# research/_template

新研究任务的骨架模板。**不要直接在此目录下工作**，用脚本生成副本：

```bash
python scripts/new_research.py --slug my-topic --question "要回答的核心问题"
```

## 生成的目录结构

```text
research/<slug>/
├── brief.yaml      研究简报（问题、范围、截止时点、子问题）
├── sources.csv     来源登记表
├── evidence.csv    证据片段表
├── claims.csv      主张表
├── REPORT.md       最终报告
└── notes/          过程笔记
```

## 字段定义

见 [docs/data-model.md](../../docs/data-model.md)。核心不变量：

- `Source.fetched_at` 必填且带时区
- `Evidence.quote` 必须是原文子串
- `Claim` 必须至少有一条证据
- `prediction` 类主张必须填 `derivation`

## 校验

```bash
python scripts/validate_research.py research/<slug>
```

CI 会对 `research/` 下所有目录跑这一步。校验不通过不得合入。

## 写作约定

- 报告中用 `[c-<id>]` 引用主张，用 `[e-<id>]` 引用证据，用 `[src-<id>]` 引用来源。
- 冲突主张并列呈现，标注 `disputed`，不强裁决（ADR-0003）。
- 系统推断必须标注，不能伪装成来源事实。
- 明确写出信息截止时间与已知证据缺口。
