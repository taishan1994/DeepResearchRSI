# evals/adapters

把外部基准接入本项目评分体系的适配器。

## 目标基准

| 基准 | 测什么 | 接入方式 |
|---|---|---|
| **DeepResearch Bench** | 报告质量与引用准确率分开评测 | 导出 predictions，跑官方评分脚本 |
| **内部任务集** | 真实业务问题 | 直接复用本项目的 `claims.csv` 契约 |

## 适配器接口

```python
class BenchmarkAdapter(Protocol):
    name: str
    def load_cases(self) -> list[Case]: ...
    def to_submission(self, run: ResearchRun) -> dict: ...
    def score(self, submission: dict) -> dict: ...
```

## 设计原则

- **不修改基准的评分逻辑**。适配器只做格式转换。
- **保留原始分数**，同时记录本项目的辅助指标（引用闭合率、子问题覆盖率）。
- 报告质量与引用准确率**分开报**，不合成单一分数——否则无法定位问题。

## 当前状态

待建。
