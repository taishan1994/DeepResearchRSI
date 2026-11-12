"""构造论文的数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每行带 cite 列，指向 claims.csv 的主张；audit_paper.py 会顺着
cite -> evidence_ids -> quote 核对数值。核对不过是硬失败，不许出图。
故这里每个数字都必须先在证据 quote 或主张 statement 里出现过。

## 本主题的三条硬约束

1. **量纲不可混**：吞吐提升（倍数）、MFU（百分比）、pass rate（比例）、
   token 消耗（计数）、延迟（毫秒）是五种量纲。放进同一张图就是造假。
   故图 1 只放「反馈属性的分类」（标称），图 2 只放「同族的加速比且逐行标口径」，
   图 3 只放「同一工作内的消融」，图 4 只放「天花板与余量」。

2. **跨工作加速比不可直接比较**。锚点是生产 serving、SEIS 是单 H100 单请求、
   InfraRSI 是训练、CAKE 是单算子。故图 2 的每一个柱子都必须带
   「对象 / 硬件 / 基线」三列，且在正文明确说这些数字不可相减。

3. **数值列统一命名为 value**。audit_paper 的 C 项回溯按该列名扫，
   若换成 speedup / count / pct 等别名，回溯会静默漏掉行（上一份归档
   就因此让审计「通过」而实际只查了 3 行）。故全表统一 value。
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLES = HERE / "tables"


def w(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
    print(f"  {path.relative_to(HERE)}  {len(rows)} 行")


# ---------------------------------------------------------------- 图 1
# 反馈三属性在 12 个代表工作上的取值（标称量，不是数值）。
# 取值口径：y=工作显式实现了该属性并有实验证明；p=部分/间接；n=未涉及。
FEEDBACK = [
    # name, local, cheap, verifiable, cite, layer
    ("Zhipu Infra Agent", "y", "y", "y", "c-dense-def", "服务系统"),
    ("SEIS", "y", "y", "y", "c-seis", "引擎整体"),
    ("InfraRSI", "p", "y", "y", "c-infrarsi", "训练系统"),
    ("KOPE", "y", "y", "y", "c-kope", "kernel"),
    ("Evolving Agent Teams", "p", "y", "y", "c-eat", "kernel"),
    ("MetaSkill-Evolve", "p", "p", "y", "c-meta-ceiling", "通用 agent"),
    ("Darwin Gödel Machine", "n", "p", "y", "c-dgm", "通用 agent"),
    ("SWE-Serve", "y", "y", "y", "c-swe-serve", "基准"),
    ("InferenceBench", "p", "y", "y", "c-agent-vs-search", "基准"),
    ("AutoTuneBench", "p", "y", "y", "c-measure-fail", "基准"),
    ("ASAP", "p", "n", "p", "c-asap", "训练系统"),
    ("CANNBot-CAKE", "y", "y", "y", "c-cann", "kernel"),
]

# ---------------------------------------------------------------- 图 2
# 同族工作的加速比。**每个都带对象/硬件/基线**，禁止裸比。
SPEED = [
    # label, value, scope, cite
    ("Zhipu（端到端吞吐）", 3.0, "生产服务 / 国产集群 / 初始基线", "c-anchor-gain"),
    ("SEIS（端到端吞吐）", 3.27, "mini-sglang / 单 H100 / vanilla", "c-seis"),
    ("SEIS（延迟下降比）", 3.31, "295ms→89ms / 单 H100 / vanilla", "c-seis"),
    ("InfraRSI（四负载几何平均）", 1.83, "训练 / 8×H100~16×H100 / 初始配置", "c-infrarsi"),
    ("CANNBot-CAKE（算子）", 1.334, "Ascend 950PR / 单算子 / baseline", "c-cann"),
    ("KernelBench-Verified（收紧后）", 0.88, "kernel / 严格协议 / TF32 PyTorch", "c-judge-flip"),
    ("KernelBench（标准协议）", 1.43, "kernel / 标准协议 / torch.compile", "c-judge-flip"),
]

# ---------------------------------------------------------------- 图 3
# 同一工作内的消融：KOPE 的两种上下文策略（同量纲：百分比）。
KOPE = [
    ("无记忆", 55.2, "c-kope"),
    ("轨迹摘要", 60.0, "c-kope"),
    ("经验图（全套）", 84.6, "c-kope"),
]

# ---------------------------------------------------------------- 图 4
# 天花板与余量：任务剩余空间决定元级演化的收益。
CEIL = [
    # label, value(%), cite
    ("ALFWorld 基线已解比例", 92.31, "c-meta-ceiling"),
    ("ALFWorld 静态技能增益", -1.93, "c-meta-ceiling"),
    ("ALFWorld 单层演化恢复", 0.0, "c-meta-ceiling"),
    ("SWE-Serve 任务入选率", 6.74, "c-swe-serve"),
    ("SWE-Serve 验证器被修订比例", 43.4, "c-verifier-cost"),
    ("CANNBot 隐藏集通过率", 98.28, "c-cann"),
]

# ---------------------------------------------------------------- 表
GEN = [
    ["锚点 Infra Agent", "2026-09", "官方博客", "生产证据强、外复现弱", "c-dense-def"],
    ["SEIS", "2026-10", "arXiv", "代码与 session 全公开", "c-seis"],
    ["InfraRSI", "2026-11", "arXiv", "仓库极新，无独立复现", "c-infrarsi"],
    ["KOPE", "2026-08", "arXiv", "经验图需重跑", "c-kope"],
    ["Evolving Agent Teams", "2026-10", "NeurIPS'26", "traces 公开", "c-eat"],
    ["SWE-Serve", "2026-09", "arXiv", "NVIDIA 官方可运行", "c-swe-serve"],
    ["MetaSkill-Evolve", "2026-07", "arXiv", "artifact 不完整", "c-meta-ceiling"],
    ["Darwin Gödel Machine", "2025-05", "arXiv", "代码与日志可运行", "c-dgm"],
]

# 反馈三层的判据对照（锚点三案例）
LAYERS = [
    ["正确性", "算得对不对", "数值一致性 + 映射正确性", "KDA 的 CP 路径", "c-case-correctness"],
    ["系统行为", "时间去哪了", "trace / 事件 / 反事实验证", "KV Transfer 与 GIL", "c-case-behavior"],
    ["性能", "哪种做法更好", "同口径多点计时", "V 维分块重复计算", "c-case-performance"],
]

# 优点 / 缺点 成对表（这是用户要求的「每个都说明优缺点」）
PROSCONS = [
    ["Zhipu Infra Agent", "唯一在生产栈上跑通全链；跨 Python/C++ 边界定位根因",
     "闭源；硬件与模型绑定；3x 无外部复现", "c-anchor-scale", "c-anchor-gain"],
    ["SEIS", "改整个引擎；关掉投机解码后增益仍在",
     "agent 固定、引擎演化；单 H100 单请求", "c-whole-engine", "c-seis"],
    ["InfraRSI", "两层 RSI；把 OOM 当删失观测而非丢弃",
     "仓库极新无独立复现；训练高成本", "c-infrarsi", "c-train-coupling"],
    ["KOPE", "省 token 与提效果同向（15.9B→1.113B 且 pass 升）",
     "经验图构建开销未计；跨硬件迁移未验", "c-kope", "c-kope"],
    ["Evolving Agent Teams", "把可进化对象抬到组织结构层；traces 可审计",
     "supervisor 的重组算法本身固定", "c-eat", "c-eat"],
    ["SWE-Serve", "揭示「局部测试过、端到端失败」",
     "任务是基准不是方法；41 题需 H100", "c-swe-serve", "c-verifier-cost"],
    ["MetaSkill-Evolve", "形式化最干净的双时间尺度",
     "收益强依赖任务余量；ALFWorld 上倒退", "c-meta-ceiling", "c-meta-ceiling"],
    ["Darwin Gödel Machine", "严格 RSI 参照点；archive 可累积",
     "对象是 coding agent，不是推理栈", "c-dgm", "c-dgm"],
    ["ASAP", "profiler+roofline+知识库的分片提案",
     "开环：作者自陈缺 Evaluator Agent", "c-asap", "c-asap"],
    ["CANNBot-CAKE", "国产 NPU 上复现，证明不依赖 NVIDIA 工具链",
     "单算子上限；生态补课件成本高", "c-cann", "c-cann"],
]

# 口径差异（q4）
METRICS = [
    ["基线定义", "torch.compile 默认精度 vs 开 TF32", "结论从 1.43 翻到 0.88", "c-judge-flip"],
    ["任务余量", "已饱和任务使比较失效", "饱和任务上任何改进都不可测", "c-measure-fail"],
    ["硬件绑定", "绝对耗时不可跨机器迁移", "3x 必须绑定该集群才有意义", "c-measure-fail"],
    ["稻草人基线", "人为弱化基线制造加速比", "加速比可被无成本制造", "c-measure-fail"],
]


def main() -> int:
    w(DATA / "fig1_feedback.csv",
      ["model", "local", "cheap", "verifiable", "layer", "cite"],
      [[n, a, b, c, layer, cite] for n, a, b, c, cite, layer in FEEDBACK])
    w(DATA / "fig2_speedup.csv",
      ["model", "value", "scope", "cite"],
      [[l, v, s, c] for l, v, s, c in SPEED])
    w(DATA / "fig3_ablation.csv",
      ["model", "value", "cite"],
      [[l, v, c] for l, v, c in KOPE])
    w(DATA / "fig4_ceiling.csv",
      ["model", "value", "cite"],
      [[l, v, c] for l, v, c in CEIL])

    w(TABLES / "tab1_generations.csv",
      ["工作", "时间", "渠道", "可复现性", "cite"], GEN)
    w(TABLES / "tab2_layers.csv",
      ["层", "它回答什么", "判据", "锚点案例", "cite"], LAYERS)
    w(TABLES / "tab3_proscons.csv",
      ["工作", "优点", "缺点", "cite_pro", "cite_con"], PROSCONS)
    w(TABLES / "tab4_metrics.csv",
      ["口径", "差异", "后果", "cite"], METRICS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
