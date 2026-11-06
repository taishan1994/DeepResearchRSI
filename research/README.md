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
| [rtx-pro-6000](./rtx-pro-6000/REPORT.md) | NVIDIA RTX PRO 6000 Blackwell 全系性能分析 | **447 来源 / 3002 证据 / 2238 主张（1882 高置信）/ 9 争议** |
| [cuda-kernel-gen](./cuda-kernel-gen/REPORT.md) | CUDA Kernel 自动生成前沿进展（2025-02 ～ 2026-11，98 篇） | **36 来源 / 19 证据 / 19 主张（15 高置信）/ 0 争议** |
| [cuda-kernel-rl](./cuda-kernel-rl/REPORT.md) | CUDA Kernel 强化学习：奖励设计的演进（2025-01 ～ 2026-10，13 篇核心） | **20 来源 / 37 证据 / 23 主张（15 高置信）/ 0 争议** |
| [rsi-model-training](./rsi-model-training/REPORT.md) | 模型训练中的递归自我改进：外部锚点的迁移（2022-03 ～ 2026-11，61 篇编码） | **53 来源 / 63 证据 / 48 主张（25 高置信）/ 0 争议** |
| [pd-disagg](./pd-disagg/REPORT.md) | Prefill–Decode 分离的收益边界（2023-11 ～ 2026-10，46 篇 + 24 份文档） | **70 来源 / 78 证据 / 9 主张（9 高置信）/ 0 争议** |
| [rsi-inference](./rsi-inference/REPORT.md) | 推理优化中的递归自我改进：反馈强度才是主坐标（2024-01 ～ 2026-11，45 篇核心 + 12 旁证） | **57 来源 / 74 证据 / 12 主张（11 高置信）/ 0 争议** |
| [rsi-serving](./rsi-serving/REPORT.md) | 推理优化的递归自我改进：端到端层的判定问题（2025-03 ～ 2026-11，15 篇核心 + 8 旁证） | **23 来源 / 60 证据 / 12 主张（12 高置信）/ 0 争议** |
| [specpilot](./specpilot/REPORT.md) | SpecPilot 论文与源码审计：把「改进了没有」变成脚本能算的量（arXiv 2611.02501 + 仓库 @78c42af） | **3 来源 / 81 证据 / 33 主张（29 高置信）/ 1 争议** |
| [pro6000se-dsv41](./pro6000se-dsv41/REPORT.md) | RTX PRO 6000 Server Edition 部署 DeepSeek-V4.1-Flash：几张卡、什么栈、多快 | **26 来源 / 138 证据 / 48 主张（43 高置信）/ 0 争议** |

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