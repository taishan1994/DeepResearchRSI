# -*- coding: utf-8 -*-
"""生成四张图。数值全部来自 data/*.csv，不在这里写任何字面量。

## 分组原则

四张图刻意分成不同量纲，组内可比、组间不可比：

  图 1  标称 —— 反馈三属性在 12 个代表工作上的取值（y/p/n）
  图 2  倍数 —— 同族的加速比，**每个柱子带对象与基线**
  图 3  比例 —— 同一工作内的消融（KOPE 的三种上下文策略）
  图 4  比例 —— 天花板与余量（任务已解比例、入选率等）

**不放**的：把吞吐倍数、MFU 百分比、pass rate、token 数放进同一张图。
它们不是一把尺子。图 2 里的 3.0 / 3.27 / 2.75 也不可相减——
对象分别是生产服务、单 H100 单请求、训练集群。
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C = {"main": "#2f6fb3", "alt": "#c0504d", "mut": "#7f7f7f", "ok": "#4f9d69",
     "warn": "#e0a13c"}


def rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fig1():
    """反馈三属性矩阵：行是工作，列是 local / cheap / verifiable。"""
    r = rows("fig1_feedback.csv")
    marks = {"y": 2, "p": 1, "n": 0}
    grid = [[marks[x[k]] for k in ("local", "cheap", "verifiable")] for x in r]

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            color = [C["mut"], C["warn"], C["main"]][v]
            ax.add_patch(plt.Rectangle((j, len(grid) - 1 - i), 0.94, 0.86,
                                       facecolor=color, edgecolor="white", lw=2))
            ax.text(j + 0.47, len(grid) - 1 - i + 0.43,
                    ["未涉及", "部分", "显式实现"][v],
                    ha="center", va="center", color="white", fontsize=8)

    ax.set_xlim(-0.05, 3)
    ax.set_ylim(-0.1, len(grid))
    ax.set_xticks([0.47, 1.47, 2.47])
    ax.set_xticklabels(["足够局部", "便宜及时", "可客观验证"], fontsize=9)
    ax.set_yticks([len(grid) - 1 - i + 0.43 for i in range(len(grid))])
    ax.set_yticklabels([x["model"] for x in r], fontsize=8)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("反馈三属性在各代表工作上的实现程度", fontsize=11, pad=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_feedback.png", dpi=200)
    plt.close(fig)


def fig2():
    """同族加速比：每个柱子带对象标签，禁止裸比。"""
    r = rows("fig2_speedup.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]
    scopes = [x["scope"] for x in r]

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ys = list(range(len(r)))[::-1]
    colors = [C["alt"] if v < 1 else C["main"] for v in vals]
    ax.barh(ys, vals, color=colors, height=0.62)
    ax.axvline(1.0, color=C["mut"], ls="--", lw=1)
    ax.text(1.02, len(r) - 0.35, "基线 = 1×", color=C["mut"], fontsize=8)

    for y, v, s in zip(ys, vals, scopes):
        ax.text(v + 0.04, y, f"{v:.2f}×", va="center", fontsize=8.5)
        ax.text(0.02, y - 0.28, s, va="center", fontsize=6.6, color="#555555")

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("相对各自基线的加速比（倍）", fontsize=9)
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_title("同族的加速比：口径不同，不可相减", fontsize=11, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_speedup.png", dpi=200)
    plt.close(fig)


def fig3():
    """KOPE 消融：三种上下文策略的 pass rate。"""
    r = rows("fig3_ablation.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]

    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    xs = list(range(len(r)))
    bars = ax.bar(xs, vals, color=[C["mut"], C["warn"], C["ok"]], width=0.58)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.4, f"{v:.1f}%",
                ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("通过率（%）", fontsize=9)
    ax.set_title("同一工作内的消融：记忆结构决定通过率", fontsize=10.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_ablation.png", dpi=200)
    plt.close(fig)


def fig4():
    """天花板与余量。"""
    r = rows("fig4_ceiling.csv")
    labels = [x["model"] for x in r]
    vals = [float(x["value"]) for x in r]

    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ys = list(range(len(r)))[::-1]
    colors = [C["ok"] if v >= 50 else C["main"] for v in vals]
    ax.barh(ys, vals, color=colors, height=0.6)
    ax.axvline(0, color=C["mut"], lw=0.8)
    for y, v in zip(ys, vals):
        off = 1.2 if v >= 0 else -1.2
        ax.text(v + off, y, f"{v:+.2f}" if abs(v) < 10 else f"{v:.2f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_xlabel("百分比（%）", fontsize=9)
    ax.set_title("天花板与余量：任务剩余空间决定元级收益", fontsize=10.5, pad=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(min(vals) - 6, max(vals) * 1.15)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_ceiling.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    print("figures ->", OUT)
