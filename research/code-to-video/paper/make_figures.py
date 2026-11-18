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


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fw1()
    fw2()
    fw3()
    fw4()
    print("figures ->", OUT)
