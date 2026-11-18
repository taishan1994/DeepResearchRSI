# -*- coding: utf-8 -*-
"""生成 4 张实验图 + 4 张框架结构图。数值全部来自 data/*.csv。

## 分组原则

  图 1  谱系双轴（中间表示 × 验证信号强度）—— 标称/序数
  图 2  「画面像」vs「内容对」的落差 —— 百分比，同量纲
  图 3  记忆/规则类机制的对照 —— 计数，同一工作内
  图 4  build 循环成本 —— 五种量纲混排，故逐项标注单位，不共享坐标轴

## 框架图为什么自绘

本模型无法读图，无法核对嵌入的原图是否与原文一致；且投稿复用他人原图有版权问题。
故框架图按 method 章节自绘示意图，拓扑可逐句溯源（出处写在函数 docstring）。
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C = {"main": "#2f6fb3", "alt": "#c0504d", "mut": "#7f7f7f", "ok": "#4f9d69",
     "warn": "#e0a13c", "human": "#e8e3d3", "agent": "#cfe0f0", "env": "#d8ead8",
     "mem": "#f2d9d0", "edge": "#4a4a4a"}


def rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def box(ax, x, y, w, h, text, fc, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.012,rounding_size=0.02",
                                facecolor=fc, edgecolor=C["edge"], lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.5)


def arrow(ax, p, q, text="", rad=0.0, fs=7.4, color=None):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11,
                                 lw=1.15, color=color or C["edge"],
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        ax.text(mx, my + 0.018, text, ha="center", va="bottom", fontsize=fs,
                color=color or "#333333")


def blank(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


# ============================================================ 图 1 谱系
def fig1():
    r = rows("fig1_lineage.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    irs = ["Manim", "Blender", "SVG", "Web", "通用", "程序真值"]
    cmap = {k: c for k, c in zip(irs, [C["main"], C["ok"], C["warn"],
                                       "#8e7cc3", C["mut"], C["alt"]])}
    for x in r:
        xi = irs.index(x["ir"]) if x["ir"] in irs else 4
        yi = int(x["signal_rank"])
        ax.scatter(xi, yi, s=110, color=cmap.get(x["ir"], C["mut"]),
                   edgecolor="white", lw=1.2, zorder=3)
        ax.annotate(x["model"], (xi, yi), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=7.2)
    ax.set_xticks(range(len(irs)))
    ax.set_xticklabels(irs, fontsize=9)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["只编译", "编译+渲染", "渲染+VLM 评", "渲染+程序真值", "人评"],
                       fontsize=8.5)
    ax.set_xlabel("中间表示类型", fontsize=9)
    ax.set_ylabel("验证信号的来源", fontsize=9)
    ax.set_xlim(-0.6, len(irs) - 0.4)
    ax.set_ylim(0.4, 5.6)
    ax.grid(alpha=0.22, ls="--", lw=0.7)
    ax.set_axisbelow(True)
    ax.set_title("谱系：中间表示 × 验证信号强度", fontsize=11, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_lineage.png", dpi=200)
    plt.close(fig)


# ============================================================ 图 2 落差
def fig2():
    r = rows("fig2_gap.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ys = list(range(len(r)))[::-1]
    colors = [C["alt"] if "BVB" in l else C["main"] for l in labels]
    ax.barh(ys, vals, color=colors, height=0.6)
    for y, v in zip(ys, vals):
        ax.text(v + 1.2, y, f"{v:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_xlim(0, 108)
    ax.set_xlabel("百分比（%）", fontsize=9)
    ax.set_title("同一工作内并置：画面像 ≠ 内容对", fontsize=10.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_gap.png", dpi=200)
    plt.close(fig)


# ============================================================ 图 3 记忆
def fig3():
    r = rows("fig3_memory.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    ys = list(range(len(r)))[::-1]
    colors = [C["alt"] if v > 0 else C["ok"] for v in vals]
    ax.barh(ys, vals, color=colors, height=0.58)
    for y, v in zip(ys, vals):
        ax.text(v + 0.35, y, f"{v:g}", va="center", fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xlabel("计数（次 / 个）", fontsize=9)
    ax.set_title("记忆与规则的作用依模型强弱而反转", fontsize=10.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_memory.png", dpi=200)
    plt.close(fig)


# ============================================================ 图 4 成本
def fig4():
    r = rows("fig4_cost.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    ys = list(range(len(r)))[::-1]
    ax.barh(ys, vals, color=C["main"], height=0.58)
    for y, v in zip(ys, vals):
        ax.text(v + max(vals) * 0.012, y, f"{v:g}", va="center", fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_xlim(0, max(vals) * 1.16)
    ax.set_xlabel("数值（单位见各标签，不可相互比较）", fontsize=9)
    ax.set_title("build 循环的成本结构（五种量纲混排，故不共享语义）",
                 fontsize=10.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_cost.png", dpi=200)
    plt.close(fig)


# ============================================================ 框架图
def fw1():
    """构建-检查-修订闭环（MaLiang-Harness 的 PEG/TGP/REV）。

    出处：persistent executable generation state；traceable generation process
    把编辑与渲染证据连起来；revision-aware editing and verification 在完成前
    检查当前修订。
    """
    fig, ax = blank((8.0, 4.2))
    box(ax, 0.03, 0.56, 0.20, 0.18, "需求\n(composition/motion)", C["human"], fs=8)
    box(ax, 0.30, 0.56, 0.20, 0.18, "规划\n先出结构再写码", C["agent"], fs=8)
    box(ax, 0.57, 0.56, 0.20, 0.18, "写程序\nManim/Blender/SVG", C["agent"], fs=8)
    box(ax, 0.57, 0.22, 0.20, 0.18, "执行\n编译 + 渲染", C["env"], fs=8)
    box(ax, 0.30, 0.22, 0.20, 0.18, "检查\n静态 + 渲染后", C["env"], fs=8)
    box(ax, 0.03, 0.22, 0.20, 0.18, "修订\n定位到代码片段", C["agent"], fs=8)
    box(ax, 0.30, 0.03, 0.47, 0.13,
        "持久状态：程序 + 构建历史 + 验证证据（共享同一修订基准）", C["mem"], fs=8)

    arrow(ax, (0.23, 0.65), (0.30, 0.65))
    arrow(ax, (0.50, 0.65), (0.57, 0.65))
    arrow(ax, (0.67, 0.56), (0.67, 0.40), "run")
    arrow(ax, (0.57, 0.31), (0.50, 0.31))
    arrow(ax, (0.30, 0.31), (0.23, 0.31), "差异")
    arrow(ax, (0.13, 0.40), (0.35, 0.56), "patch", rad=0.22, color=C["hi"]
          if "hi" in C else C["main"])
    arrow(ax, (0.40, 0.22), (0.40, 0.16), "落库")
    arrow(ax, (0.66, 0.16), (0.66, 0.56), "取证据", rad=-0.25, color=C["main"])
    ax.text(0.5, 0.95, "通用闭环：构建 → 检查 → 修订", ha="center", fontsize=11)
    ax.text(0.5, 0.895, "P2V gap 决定了检查必须发生在渲染之后",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig5_framework_loop.png", dpi=200)
    plt.close(fig)


def fw2():
    """Manim 线的记忆形态：双通道情节记忆 + 规则入库（ManimAgent / Reels-RSI）。"""
    fig, ax = blank((8.0, 4.0))
    box(ax, 0.04, 0.58, 0.18, 0.16, "任务\n论文小节→动画", C["human"], fs=8)
    box(ax, 0.29, 0.58, 0.18, 0.16, "写 Manim 代码", C["agent"], fs=8)
    box(ax, 0.54, 0.58, 0.18, 0.16, "渲染关键帧", C["env"], fs=8)
    box(ax, 0.79, 0.58, 0.17, 0.16, "VLM 打分", C["env"], fs=8)

    box(ax, 0.06, 0.24, 0.40, 0.20,
        "正例通道 M+\n成功理由（软参考样例）", C["ok"], fs=8)
    box(ax, 0.52, 0.24, 0.40, 0.20,
        "负例通道 M−\n已证实的坑（硬性禁忌）", C["alt"], fs=8)
    box(ax, 0.20, 0.04, 0.60, 0.14,
        "检索：按任务相似度取预算内条目 → 注入下一次尝试", C["mem"], fs=8)

    arrow(ax, (0.22, 0.66), (0.29, 0.66))
    arrow(ax, (0.47, 0.66), (0.54, 0.66))
    arrow(ax, (0.72, 0.66), (0.79, 0.66))
    arrow(ax, (0.87, 0.58), (0.75, 0.44), "成功")
    arrow(ax, (0.87, 0.58), (0.30, 0.44), "失败", rad=0.15)
    arrow(ax, (0.26, 0.24), (0.40, 0.18))
    arrow(ax, (0.72, 0.24), (0.60, 0.18))
    arrow(ax, (0.30, 0.11), (0.29, 0.58), "先验", rad=0.3, color=C["main"])
    ax.text(0.5, 0.95, "Manim 线：记忆把单次反思变成跨任务资产",
            ha="center", fontsize=11)
    ax.text(0.5, 0.895, "无需更新权重；记忆本身可被单元测试",
            ha="center", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig6_framework_memory.png", dpi=200)
    plt.close(fig)


def fw3():
    """程序即真值：为什么本族能自动验证（PROWBench / BVB 的镜像结构）。"""
    fig, ax = blank((8.0, 3.8))
    box(ax, 0.04, 0.60, 0.26, 0.18, "程序 / 引擎状态\n(实体、事件、时间戳)",
        C["human"], fs=8.2, bold=True)
    box(ax, 0.40, 0.72, 0.26, 0.14, "渲染出参考画面", C["env"], fs=8)
    box(ax, 0.40, 0.46, 0.26, 0.14, "模型生成的视频", C["alt"], fs=8)
    box(ax, 0.74, 0.59, 0.22, 0.18, "逐帧/逐事件\n比对", C["ok"], fs=8)

    arrow(ax, (0.30, 0.72), (0.40, 0.79), "确定性渲染")
    arrow(ax, (0.30, 0.64), (0.40, 0.53), "同一意图")
    arrow(ax, (0.66, 0.79), (0.74, 0.72))
    arrow(ax, (0.66, 0.53), (0.74, 0.64))
    box(ax, 0.04, 0.18, 0.92, 0.18,
        "关键：程序给出的是**可回放的真值**（实体状态、事件时刻），\n"
        "故验证不需要人来判「像不像」，而可以问「事件是否在正确时刻发生」",
        C["mem"], fs=8.2)
    ax.text(0.5, 0.95, "程序即真值：本族可自动验证的根源", ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig7_framework_truth.png", dpi=200)
    plt.close(fig)


def fw4():
    """两种失败路径：语法端 vs 视觉端（对应 SFT/GRPO 的分工）。"""
    fig, ax = blank((8.0, 3.9))
    box(ax, 0.30, 0.80, 0.40, 0.13, "意图（自然语言 / 规格）", C["human"],
        fs=9, bold=True)
    box(ax, 0.04, 0.44, 0.26, 0.16, "代码\n(Manim / Blender)", C["agent"], fs=8.4)
    box(ax, 0.37, 0.44, 0.26, 0.16, "渲染结果\n(帧序列)", C["env"], fs=8.4)
    box(ax, 0.70, 0.44, 0.26, 0.16, "观众看到的内容", C["ok"], fs=8.4)

    arrow(ax, (0.40, 0.80), (0.17, 0.60))
    arrow(ax, (0.50, 0.80), (0.50, 0.60))
    arrow(ax, (0.60, 0.80), (0.83, 0.60))

    box(ax, 0.04, 0.16, 0.26, 0.18,
        "失败 A：语法/API 幻觉\n可用版本约束与检索修", C["alt"], fs=7.8)
    box(ax, 0.37, 0.16, 0.26, 0.18,
        "失败 B：视觉-逻辑漂移\n只能渲染后判定", C["alt"], fs=7.8)
    box(ax, 0.70, 0.16, 0.26, 0.18,
        "失败 C：画面像但内容错\n需真值比对", C["alt"], fs=7.8)

    arrow(ax, (0.17, 0.44), (0.17, 0.34))
    arrow(ax, (0.50, 0.44), (0.50, 0.34))
    arrow(ax, (0.83, 0.44), (0.83, 0.34))
    ax.text(0.5, 0.95, "P2V gap 的两端：三种失败各需不同信号",
            ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig8_framework_failure.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------ 逐工作框架图（9–14）
def _panel(ax, x0, y0, w, h, title, boxes, arrows, fs=7.2):
    """在给定矩形内画一张小框架图。

    boxes: [(dx, dy, dw, dh, text, color)]
    arrows: [((x1,y1),(x2,y2))]
    坐标全部相对该 panel，便于并排两张而不互相干扰。
    """
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                facecolor="none", edgecolor="#bbbbbb",
                                lw=0.9, ls="--"))
    ax.text(x0 + w / 2, y0 + h - 0.035, title, ha="center", va="center",
            fontsize=8.4, fontweight="bold")
    for dx, dy, dw, dh, text, col in boxes:
        box(ax, x0 + dx * w, y0 + dy * h, dw * w, dh * h, text, col, fs=fs)
    for (a, b) in arrows:
        p = (x0 + a[0] * w, y0 + a[1] * h)
        q = (x0 + b[0] * w, y0 + b[1] * h)
        arrow(ax, p, q)


def fw_pair(name, title, sub, left, right, figsize=(8.6, 3.5)):
    """左右并排两个工作的框架图，用于同支线对照。"""
    fig, ax = blank(figsize)
    _panel(ax, 0.02, 0.06, 0.46, 0.78, left[0], left[1], left[2])
    _panel(ax, 0.52, 0.06, 0.46, 0.78, right[0], right[1], right[2])
    ax.text(0.5, 0.955, title, ha="center", fontsize=11)
    ax.text(0.5, 0.905, sub, ha="center", fontsize=7.8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def fw9():
    """Manim 线的训练/推理策略对照。

    出处：ManimTrainer —— SFT 提代码质量、GRPO 提视觉质量；
    推理侧 RITL-DOC 注入 API 文档。最强配置 94% RSR + 85.7% VS。
    """
    left = ("ManimTrainer（训练侧）", [
        (0.06, 0.70, 0.40, 0.16, "Manim 语料\n+ 执行结果", C["human"]),
        (0.54, 0.70, 0.40, 0.16, "SFT\n提代码质量", C["agent"]),
        (0.54, 0.42, 0.40, 0.16, "GRPO\n提视觉质量", C["agent"]),
        (0.06, 0.42, 0.40, 0.16, "渲染帧\n视觉相似度", C["env"]),
        (0.06, 0.10, 0.88, 0.18, "94% RSR + 85.7% VS\n（Qwen3 Coder 30B）", C["ok"]),
    ], [((0.46, 0.78), (0.54, 0.78)),
        ((0.74, 0.70), (0.74, 0.58)),
        ((0.54, 0.50), (0.46, 0.50)),
        ((0.46, 0.50), (0.54, 0.50)),
        ((0.74, 0.42), (0.50, 0.28))])
    right = ("ManimAgent（推理侧）", [
        (0.06, 0.70, 0.40, 0.16, "任务\n论文小节", C["human"]),
        (0.54, 0.70, 0.40, 0.16, "写码 → 渲染", C["agent"]),
        (0.54, 0.42, 0.40, 0.16, "VLM 评关键帧\n结构化奖励", C["env"]),
        (0.06, 0.10, 0.88, 0.18, "双通道 EMB\n正例理由 / 负例坑", C["mem"]),
    ], [((0.46, 0.78), (0.54, 0.78)),
        ((0.74, 0.70), (0.74, 0.58)),
        ((0.74, 0.42), (0.50, 0.19)),
        ((0.50, 0.19), (0.06, 0.78))])
    fw_pair("fig9_framework_manim.png",
            "Manim 线的两条正交路线：改权重 vs 改记忆",
            "左：把能力压进参数；右：不动参数只累积经验。二者可叠加",
            left, right)


def fw10():
    """OmniManim 的三段式：先布局、再写码、后诊断。

    出处：render-feedback-aware constrained code generation；
    先预测关键帧布局以缓解下游插值造成的中间帧失败。
    """
    fig, ax = blank((8.0, 3.4))
    box(ax, 0.03, 0.52, 0.20, 0.20, "问题描述\n+ 空间约束", C["human"], fs=8)
    box(ax, 0.28, 0.52, 0.20, 0.20, "关键帧布局\n预测（先看）", C["agent"], fs=8)
    box(ax, 0.53, 0.52, 0.20, 0.20, "写 Manim 代码\n（后写）", C["agent"], fs=8)
    box(ax, 0.78, 0.52, 0.19, 0.20, "渲染\n全帧序列", C["env"], fs=8)
    box(ax, 0.28, 0.18, 0.45, 0.18, "诊断：哪些帧失败？\n是布局错还是插值错？", C["ok"], fs=8)
    box(ax, 0.78, 0.18, 0.19, 0.18, "定点修\n布局或代码", C["alt"], fs=8)

    arrow(ax, (0.23, 0.62), (0.28, 0.62))
    arrow(ax, (0.48, 0.62), (0.53, 0.62))
    arrow(ax, (0.73, 0.62), (0.78, 0.62))
    arrow(ax, (0.87, 0.52), (0.70, 0.36))
    arrow(ax, (0.73, 0.27), (0.78, 0.27))
    arrow(ax, (0.87, 0.36), (0.87, 0.52), "回灌", rad=-0.3, color=C["main"])
    ax.text(0.5, 0.93, "先看后写：把 P2V gap 的检查点前移", ha="center", fontsize=11)
    ax.text(0.5, 0.875, "难点在于「约束只有渲染后才可判」，故布局预测本身也可能错",
            ha="center", fontsize=7.8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig10_framework_omni.png", dpi=200)
    plt.close(fig)


def fw11():
    """ManimCode：把反馈轨迹变成可训练资产。

    出处：24,034 条渲染验证、质量过滤的轨迹，保存中间程序、执行错误、
    视觉批评与修正；角色条件 SFT 训 4B，再用 RL 训 Reviser。
    """
    fig, ax = blank((8.2, 3.6))
    box(ax, 0.03, 0.58, 0.17, 0.20, "初始程序\n（会失败）", C["human"], fs=7.8)
    box(ax, 0.24, 0.58, 0.17, 0.20, "执行\n拿 traceback", C["env"], fs=7.8)
    box(ax, 0.45, 0.58, 0.17, 0.20, "渲染帧\nVLM 批评", C["env"], fs=7.8)
    box(ax, 0.66, 0.58, 0.17, 0.20, "修正\n产生新版本", C["agent"], fs=7.8)
    box(ax, 0.66, 0.20, 0.31, 0.20,
        "轨迹：程序 + 错误 +\n批评 + 修正动作", C["mem"], fs=7.8)
    box(ax, 0.24, 0.20, 0.38, 0.20,
        "角色条件 SFT（写/审/改）→ 4B\n再用 RL 训 Reviser", C["ok"], fs=7.8)

    for a, b in [((0.20, 0.68), (0.24, 0.68)), ((0.41, 0.68), (0.45, 0.68)),
                 ((0.62, 0.68), (0.66, 0.68)), ((0.74, 0.58), (0.78, 0.40)),
                 ((0.74, 0.40), (0.62, 0.40)), ((0.66, 0.30), (0.45, 0.10)),
                 ]:
        arrow(ax, a, b)
    arrow(ax, (0.83, 0.20), (0.83, 0.58), "回灌下一轮", rad=-0.28, color=C["main"])
    ax.text(0.5, 0.93, "把「修正能力」本身变成可训练对象", ha="center", fontsize=11)
    ax.text(0.5, 0.878, "24,034 条轨迹的价值不在规模，而在保存了中间态",
            ha="center", fontsize=7.8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig11_framework_trace.png", dpi=200)
    plt.close(fig)


def fw12():
    """LASEV：三 agent + 中央编排 + 质量闸门。

    出处：Orchestrating Agent 监督 Solution Agent（严格解题）、
    Illustration Agent（生成可执行可视化代码）、Narration Agent（学习者导向旁白）；
    所有输出经语义批评、规则约束、工具级编译检查。
    """
    fig, ax = blank((8.2, 3.8))
    box(ax, 0.34, 0.76, 0.32, 0.14, "Orchestrating Agent\n中央编排 + 共享生产状态",
        C["mem"], fs=7.9, bold=True)
    box(ax, 0.04, 0.46, 0.27, 0.17, "Solution Agent\n严格解题", C["agent"], fs=7.9)
    box(ax, 0.37, 0.46, 0.27, 0.17, "Illustration Agent\n可执行可视化代码", C["agent"], fs=7.9)
    box(ax, 0.70, 0.46, 0.27, 0.17, "Narration Agent\n学习者导向旁白", C["agent"], fs=7.9)
    box(ax, 0.04, 0.18, 0.93, 0.16,
        "三道闸门：语义批评 · 规则约束 · 工具级编译检查", C["ok"], fs=8.2)
    box(ax, 0.04, 0.02, 0.93, 0.12, "音画对齐 → 成品", C["env"], fs=8)

    for x in (0.175, 0.505, 0.835):
        arrow(ax, (0.50, 0.76), (x, 0.63), "", rad=0.0)
        arrow(ax, (x, 0.46), (x, 0.34))
    arrow(ax, (0.50, 0.18), (0.50, 0.14))
    arrow(ax, (0.175, 0.63), (0.50, 0.76), "回报", rad=-0.25, color=C["mut"])
    ax.text(0.5, 0.955, "LASEV：为什么要代码——逻辑严谨性优先于画面",
            ha="center", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig12_framework_lasev.png", dpi=200)
    plt.close(fig)


def fw13():
    """SceneCraft 与 LogoMotion：两条与主流相反的设计。

    出处：SceneCraft 场景图 → 数值约束 → Blender Python，library learning；
    LogoMotion 代码与 GUI 控件打通，非程序员做局部修改。
    """
    left = ("SceneCraft（先结构后代码）", [
        (0.06, 0.72, 0.88, 0.14, "文本描述", C["human"]),
        (0.06, 0.50, 0.88, 0.16, "场景图蓝图\n（含空间关系）", C["agent"]),
        (0.06, 0.28, 0.88, 0.16, "数值约束 → Blender Python", C["agent"]),
        (0.06, 0.08, 0.42, 0.14, "VLM 看渲染\n迭代", C["env"]),
        (0.52, 0.08, 0.42, 0.14, "library\nlearning", C["mem"]),
    ], [((0.50, 0.72), (0.50, 0.66)), ((0.50, 0.50), (0.50, 0.44)),
        ((0.27, 0.28), (0.27, 0.22)), ((0.27, 0.15), (0.06, 0.58)),
        ((0.73, 0.22), (0.73, 0.30))])
    right = ("LogoMotion（可编辑优先）", [
        (0.06, 0.72, 0.88, 0.14, "自然语言意图", C["human"]),
        (0.06, 0.50, 0.88, 0.16, "SVG / JS 动画代码", C["agent"]),
        (0.06, 0.28, 0.42, 0.16, "编译器\n渲染", C["env"]),
        (0.52, 0.28, 0.42, 0.16, "GUI 控件\n（代码连通）", C["ok"]),
        (0.06, 0.08, 0.88, 0.14, "局部修改：动效/分组/时序", C["mem"]),
    ], [((0.50, 0.72), (0.50, 0.66)), ((0.27, 0.50), (0.27, 0.44)),
        ((0.73, 0.50), (0.73, 0.44)), ((0.50, 0.28), (0.50, 0.22)),
        ((0.27, 0.36), (0.06, 0.58))])
    fw_pair("fig13_framework_plan_edit.png",
            "两条与主流相反的设计：先结构，或先可改",
            "左：把规划显式化；右：把交付之后的修改成本当一等公民",
            left, right)


def fw14():
    """基准的三种结构：写码、验像素、重建。

    出处：VibeVideoBench 沙箱禁用生成模型只许写码；
    PROWBench 用程序化 episode 提供真值检验像素模型；
    BVB 要求 agent 用 Blender 程序重建视频。
    """
    left = ("写码：VibeVideoBench", [
        (0.06, 0.66, 0.88, 0.16, "239 任务 / 12 类 / 中英", C["human"]),
        (0.06, 0.40, 0.88, 0.18, "agent 在沙箱写码\n（禁用生成模型）", C["agent"]),
        (0.06, 0.12, 0.88, 0.20, "程序检查 + 13k 评分项\n+ VLM 评审", C["ok"]),
    ], [((0.50, 0.66), (0.50, 0.58)), ((0.50, 0.40), (0.50, 0.32))])
    right = ("验像素 / 重建：PROWBench · BVB", [
        (0.06, 0.66, 0.88, 0.16, "程序 / 引擎状态（真值）", C["human"]),
        (0.06, 0.38, 0.42, 0.20, "渲染参考", C["env"]),
        (0.52, 0.38, 0.42, 0.20, "被测对象：\n像素模型 / agent", C["alt"]),
        (0.06, 0.12, 0.88, 0.18, "逐事件比对：是否在正确时刻", C["ok"]),
    ], [((0.27, 0.66), (0.27, 0.58)), ((0.73, 0.66), (0.73, 0.58)),
        ((0.27, 0.38), (0.27, 0.30)), ((0.73, 0.38), (0.73, 0.30))])
    fw_pair("fig14_framework_bench.png",
            "基准的两种结构：考 agent，或考像素模型",
            "关键差别：真值来自程序（右），还是来自任务规格（左）",
            left, right)


def fw15():
    """CodeReel 的执行层：精确帧复用 + 阻塞感知调度。

    出处：37.5% 的帧在更早版本已画过；一半的 build 停在检查处，
    但哪些会停只有查完才知道。故检查先行、渲染并行（空闲优先级），
    按绘制命令给帧做键以跨版本精确复用。
    """
    left = ("不做的事：重排执行顺序", [
        (0.06, 0.72, 0.88, 0.14, "agent 发出命令", C["human"]),
        (0.06, 0.50, 0.88, 0.16, "逐条 build\n（一步等一步）", C["alt"]),
        (0.06, 0.26, 0.88, 0.16, "一半的 build 停在检查", C["env"]),
        (0.06, 0.06, 0.88, 0.14, "等待时间：基线", C["mut"]),
    ], [((0.50, 0.72), (0.50, 0.66)), ((0.50, 0.50), (0.50, 0.42)),
        ((0.50, 0.26), (0.50, 0.20))])
    right = ("做的事：检查先行 + 渲染并行 + 帧复用", [
        (0.06, 0.72, 0.88, 0.14, "命令 → 检查先行", C["human"]),
        (0.06, 0.50, 0.42, 0.18, "渲染并行\n（空闲优先级）", C["agent"]),
        (0.52, 0.50, 0.42, 0.18, "按绘制命令\n给帧做键", C["mem"]),
        (0.06, 0.28, 0.88, 0.16, "键重复即复用\n（跨版本、跨时间位移）", C["ok"]),
        (0.06, 0.06, 0.88, 0.14, "等待 −36.3% / −57.9%", C["ok"]),
    ], [((0.50, 0.72), (0.27, 0.68)), ((0.50, 0.72), (0.73, 0.68)),
        ((0.27, 0.50), (0.50, 0.44)), ((0.73, 0.50), (0.50, 0.44)),
        ((0.50, 0.28), (0.50, 0.20))])
    fw_pair("fig15_framework_codereel.png",
            "CodeReel：不动生成内容，只动执行层",
            "两个可省之处：37.5% 的帧画过、一半的 build 只为拿一个判决",
            left, right)


def fw16():
    """VibePrevisBench 的失败观测：看得到，改不对。

    出处：11 个前沿 coding agent 的轨迹分析，Observation 3 ——
    agents inspect their own renders but fail to correct their errors。
    同族对照：LLM2Manim 用专家复核绕开这一步；SimuScene 用视觉奖励
    把这一步变成训练信号；AnimWeb-Bench 证明显式看帧确实有帮助。
    """
    fig, ax = blank((8.4, 3.8))
    box(ax, 0.03, 0.62, 0.20, 0.18, "任务 + 灰模\n（4D 场景）", C["human"], fs=7.8)
    box(ax, 0.28, 0.62, 0.20, 0.18, "agent 写\nBlender 代码", C["agent"], fs=7.8)
    box(ax, 0.53, 0.62, 0.20, 0.18, "渲染 →\nagent 自己看", C["env"], fs=7.8)
    box(ax, 0.78, 0.62, 0.19, 0.18, "仍不改正\n（观测 3）", C["alt"], fs=7.8)
    box(ax, 0.03, 0.30, 0.29, 0.19,
        "绕开：专家复核\n（LLM2Manim）", C["mut"], fs=7.6)
    box(ax, 0.355, 0.30, 0.29, 0.19,
        "变信号：视觉奖励\n（SimuScene）", C["ok"], fs=7.6)
    box(ax, 0.68, 0.30, 0.29, 0.19,
        "加强：显式看帧\n（AnimWeb-Bench）", C["ok"], fs=7.6)
    box(ax, 0.03, 0.05, 0.94, 0.16,
        "缺口：从「看出差异」到「改对代码」的映射，尚无工作报告专门训练它",
        C["mem"], fs=8.2)

    for a, b in [((0.23, 0.71), (0.28, 0.71)), ((0.48, 0.71), (0.53, 0.71)),
                 ((0.73, 0.71), (0.78, 0.71)),
                 ((0.875, 0.62), (0.175, 0.49)),
                 ((0.875, 0.62), (0.50, 0.49)),
                 ((0.875, 0.62), (0.825, 0.49))]:
        arrow(ax, a, b)
    ax.text(0.5, 0.95, "本族最尖锐的负结果：看得到，改不对",
            ha="center", fontsize=11)
    ax.text(0.5, 0.895, "三种应对都在「绕开或加强」这一步，没有一种直接训练该映射",
            ha="center", fontsize=7.8, color="#666666")
    fig.tight_layout()
    fig.savefig(OUT / "fig16_framework_gapmap.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fw1()
    fw2()
    fw3()
    fw4()
    fw9()
    fw10()
    fw11()
    fw12()
    fw13()
    fw14()
    fw15()
    fw16()
    print("figures ->", OUT)
