# -*- coding: utf-8 -*-
"""绘制四张框架结构示意图。

## 画的是「结构」，不是「截图」

每张图的每个框都对应论文 method 章节里的一句原文，不是凭印象画的。
出处写在各函数 docstring 里，便于逐条核对。

为什么不直接嵌论文原图：
  1. 本模型无法读图，无法核对嵌入的图是否与原文一致——
     「看着差不多」不能当证据；
  2. 综述若要投稿，直接复用他人原图有版权问题，需授权。
故这里画**示意图**：拓扑与判据来自原文，图形自绘，可安全引用并逐句溯源。

## 四张图对应四种循环形态

  图 1  锚点：三层反馈闭环（正确性 / 系统行为 / 性能）
  图 2  引擎级：agent 固定，引擎演化（SEIS）
  图 3  经验级：决策→反馈→后续决策 存图（KOPE）
  图 4  元级：快慢双时间尺度（MetaSkill-Evolve / EAT）
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C = {
    "human": "#e8e3d3",
    "agent": "#cfe0f0",
    "env": "#d8ead8",
    "mem": "#f2d9d0",
    "edge": "#4a4a4a",
    "hi": "#2f6fb3",
}


def box(ax, x, y, w, h, text, fc, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.012,rounding_size=0.02",
                                facecolor=fc, edgecolor=C["edge"], lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal",
            linespacing=1.5)


def arrow(ax, p, q, text="", rad=0.0, fs=7.4, color=None):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11,
                                 lw=1.15, color=color or C["edge"],
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        ax.text(mx, my + 0.018, text, ha="center", va="bottom",
                fontsize=fs, color=color or "#333333")


def blank(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


# ------------------------------------------------------------------ 图 1
def fw1():
    """锚点三层反馈闭环。

    出处：blog「Engineers defined objectives and system boundaries. The agent
    handled analysis, hypotheses, and code changes. The experimental environment
    provided ...」；三层为 correctness / system behavior / performance feedback。
    """
    fig, ax = blank((8.0, 4.4))
    box(ax, 0.03, 0.60, 0.20, 0.16, "工程师\n定目标 · 划边界", C["human"], bold=True)
    box(ax, 0.31, 0.60, 0.20, 0.16, "Infra Agent\n分析 · 假设 · 改码", C["agent"], bold=True)

    box(ax, 0.60, 0.76, 0.35, 0.13, "反馈层 1：正确性\n算得对不对", C["env"])
    box(ax, 0.60, 0.59, 0.35, 0.13, "反馈层 2：系统行为\n时间去哪了", C["env"])
    box(ax, 0.60, 0.42, 0.35, 0.13, "反馈层 3：性能\n哪种更好", C["env"])

    box(ax, 0.20, 0.10, 0.60, 0.15,
        "实验环境：编译 · 单元测试 · trace · microbenchmark · 端到端指标\n"
        "三属性 = 足够局部 · 便宜及时 · 可客观验证", C["env"], fs=8.2)

    arrow(ax, (0.23, 0.68), (0.31, 0.68), "约束")
    arrow(ax, (0.51, 0.68), (0.60, 0.82), "")
    arrow(ax, (0.51, 0.66), (0.60, 0.65), "")
    arrow(ax, (0.51, 0.64), (0.60, 0.48), "")
    arrow(ax, (0.78, 0.42), (0.78, 0.25), "归因")
    arrow(ax, (0.50, 0.10), (0.36, 0.60), "下一动作", rad=0.28, color=C["hi"])
    ax.text(0.5, 0.955, "锚点：三层密集反馈闭环（人—agent—环境三分工）",
            ha="center", fontsize=11)
    ax.text(0.5, 0.895, "反馈不是「多给日志」，而是局部、廉价、可验证",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_framework_anchor.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------ 图 2
def fw2():
    """引擎级：agent 固定、引擎演化（SEIS）。

    出处：「agent stays fixed; engine evolves」；多个 session 链，
    后一个继承前一个的代码与报告，并行链之间可交换成果。
    """
    fig, ax = blank((8.0, 3.9))
    box(ax, 0.02, 0.36, 0.17, 0.30, "冻结的\nCoding Agent", C["human"], bold=True)

    for i, x in enumerate((0.24, 0.44, 0.64)):
        box(ax, x, 0.62, 0.17, 0.14, f"Session {i+1}\n改引擎", C["agent"], fs=8)
    box(ax, 0.24, 0.20, 0.57, 0.22,
        "mini-sglang 引擎（被演化的对象）\n"
        "量化 kernel · 算子融合 · runtime 路径 · 投机解码", C["env"], fs=8.2)
    box(ax, 0.84, 0.36, 0.14, 0.30, "评测\n吞吐/延迟\n+ 数值校验", C["env"], fs=8)

    arrow(ax, (0.19, 0.55), (0.24, 0.66), "")
    arrow(ax, (0.41, 0.69), (0.44, 0.69), "继承代码与报告")
    arrow(ax, (0.61, 0.69), (0.64, 0.69), "继承")
    arrow(ax, (0.32, 0.62), (0.32, 0.42), "patch")
    arrow(ax, (0.81, 0.31), (0.84, 0.44), "")
    arrow(ax, (0.84, 0.55), (0.72, 0.62), "选择最优", rad=-0.2, color=C["hi"])
    ax.text(0.5, 0.93, "引擎级：agent 固定，被演化的是整个引擎",
            ha="center", fontsize=11)
    ax.text(0.5, 0.865, "增益来自跨 session 累积，而非单轮更强 —— 故属 L2 而非 L3",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_framework_seis.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------ 图 3
def fw3():
    """经验级：决策→反馈→后续决策 存成图（KOPE）。

    出处：Experience Graph Memory + Active Context Management；
    在固定 context budget 下检索相关经验。
    """
    fig, ax = blank((7.6, 4.0))
    box(ax, 0.04, 0.34, 0.19, 0.26, "Infra Agent\n提出改动", C["agent"], bold=True)
    box(ax, 0.30, 0.34, 0.19, 0.26, "执行\n编译+计时", C["env"])
    box(ax, 0.56, 0.34, 0.19, 0.26, "正确性\n+ 性能反馈", C["env"])

    box(ax, 0.30, 0.05, 0.45, 0.19,
        "经验图记忆：决策 → 反馈 → 后续决策\n（按硬件/任务索引，非自然语言摘要）",
        C["mem"], fs=8.2)
    box(ax, 0.79, 0.05, 0.18, 0.19, "主动上下文\n按预算检索", C["mem"], fs=7.8)

    arrow(ax, (0.23, 0.47), (0.30, 0.47), "patch")
    arrow(ax, (0.49, 0.47), (0.56, 0.47), "读数")
    arrow(ax, (0.65, 0.34), (0.60, 0.24), "落库")
    arrow(ax, (0.75, 0.14), (0.79, 0.14), "")
    arrow(ax, (0.88, 0.24), (0.14, 0.36), "检索历史先验", rad=0.22, color=C["hi"])
    ax.text(0.5, 0.945, "经验级：把一次性调试变成可复用资产",
            ha="center", fontsize=11)
    ax.text(0.5, 0.885, "同一改动同时提升通过率并降低 token（15.9B→1.113B）",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_framework_kope.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------ 图 4
def fw4():
    """元级：快慢双时间尺度。

    出处：MetaSkill-Evolve 的 task-skill 快循环 / meta-skill 慢循环；
    EAT 的 supervisor 诊断停滞并重组团队。
    """
    fig, ax = blank((8.0, 4.3))
    box(ax, 0.05, 0.66, 0.90, 0.16,
        "慢循环（外层）：meta-skill / 团队结构 / harness\n"
        "观察过去 N 个 episode 的停滞原因，改「怎么改」", C["mem"], fs=8.4, bold=True)
    box(ax, 0.05, 0.36, 0.90, 0.16,
        "快循环（内层）：task-skill / 代码 / 配置\n"
        "在单次任务内做假设、改动、验证", C["agent"], fs=8.4, bold=True)
    box(ax, 0.20, 0.07, 0.60, 0.15,
        "判据：held-out 未见任务上的优化效率是否随代数上升", C["env"], fs=8.2)

    arrow(ax, (0.30, 0.66), (0.30, 0.52), "下放策略")
    arrow(ax, (0.72, 0.52), (0.72, 0.66), "上收经验")
    arrow(ax, (0.50, 0.36), (0.50, 0.22), "评测")
    arrow(ax, (0.42, 0.22), (0.42, 0.36), "回灌")
    ax.text(0.5, 0.95, "元级：改进者本身也被改进", ha="center", fontsize=11)
    ax.text(0.5, 0.895, "只有慢循环让「下一代在新任务上更快找到好解」才算递归",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_framework_meta.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fw1()
    fw2()
    fw3()
    fw4()
    print("frameworks ->", OUT)
