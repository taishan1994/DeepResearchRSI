# -*- coding: utf-8 -*-
"""生成四张图。数值全部来自 data/*.csv，不在这里写任何字面量。

## 分组原则（本主题特有）

四张图刻意分成三组量纲，组内可比、组间不可比：

  图 1  计数 —— 题库构成
  图 2  倍数 —— 两条连续赛道的几何平均加速比（同基准、同 agent）
  图 3  计数 —— day-0 逐题的通过 agent 数
  图 4  比例 —— day-0 的 pass@1 与 f2p 通过率（同一批评测的两个切面）

图号即正文出现次序。**不放**：把 pass@1 与 speed-up 画进同一张图——
前者分母是尝试次数、后者分母是基线实测吞吐，不是一把尺子；
跨基准的增益倍数（MLE-bench 16.9% / RE-Bench 4× / PostTrainBench 23.2%）
也一张图都不进，只进表并逐行标注口径。
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

C = {"main": "#2f6fb3", "alt": "#c0504d", "mut": "#7f7f7f", "ok": "#4f9d69"}


def rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fig1():
    """题库构成：三段赛道 + 两种引擎 + 两种加速器。"""
    r = rows("fig1_compose.csv")
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    ys = list(range(len(r)))[::-1]
    vals = [float(x["count"]) for x in r]
    # 三个切面用三种颜色，避免被读成一列同质的排序
    colors = []
    for x in r:
        if x["facet"].startswith("赛道"):
            colors.append(C["main"])
        elif x["facet"].startswith("引擎"):
            colors.append(C["ok"])
        else:
            colors.append(C["mut"])
    ax.barh(ys, vals, color=colors, height=0.62)
    ax.set_yticks(ys)
    ax.set_yticklabels([x["facet"] for x in r], fontsize=8)
    for y, v in zip(ys, vals):
        ax.text(v + 0.25, y, f"{v:g}", va="center", fontsize=8)
    ax.set_xlabel("题数")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig1_compose.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig2():
    """两条连续赛道：同一 agent 的吞吐 vs 回归（倍数，同量纲）。"""
    r = rows("fig2_split.csv")
    agents = []
    for x in r:
        if x["agent"] not in agents:
            agents.append(x["agent"])
    fig, ax = plt.subplots(figsize=(6.8, 2.85))
    w = 0.34
    xs = list(range(len(agents)))
    for k, track in enumerate(["吞吐赛道", "回归赛道"]):
        vals = [float(next(x["speedup"] for x in r
                           if x["agent"] == a and x["track"] == track))
                for a in agents]
        offs = [x + (k - 0.5) * w for x in xs]
        ax.bar(offs, vals, width=w, color=C["main"] if k == 0 else C["alt"],
               label=track)
        for o, v in zip(offs, vals):
            ax.text(o, v + 0.03, f"{v:g}x", ha="center", fontsize=8)
    ax.axhline(1.0, color=C["mut"], lw=0.9, ls=":")
    ax.text(xs[-1] + 0.5, 1.03, "1.00x = 无加速", fontsize=7.5, color=C["mut"],
            ha="right")
    ax.set_xticks(xs)
    ax.set_xticklabels(agents, fontsize=8.5)
    ax.set_ylabel("几何平均加速比（倍数）")
    ax.set_ylim(0, 2.5)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig2_split.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig3():
    """day-0 逐题：每题有多少 agent 曾全通过一次。"""
    r = rows("fig3_pertask.csv")
    # 按通过数排序，让「一半有、一半 0」的形状自己显出来
    r = sorted(r, key=lambda x: -float(x["agents_passed"]))
    fig, ax = plt.subplots(figsize=(8.4, 3.1))
    xs = list(range(len(r)))
    vals = [float(x["agents_passed"]) for x in r]
    colors = [C["ok"] if v > 0 else C["alt"] for v in vals]
    ax.bar(xs, vals, color=colors, width=0.62)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.12, f"{v:g}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["task"] for x in r], rotation=32, ha="right", fontsize=7.5)
    ax.set_ylabel("曾全通过的 agent 数")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.grid(axis="y", alpha=0.25)
    # 一条分隔线：左边有人过，右边全场 0
    n_pos = sum(1 for v in vals if v > 0)
    ax.axvline(n_pos - 0.5, color=C["mut"], ls="--", lw=0.9)
    ax.text(n_pos - 0.55, max(vals) * 1.12, "← 有人通过", ha="right", fontsize=7.5,
            color=C["mut"])
    ax.text(n_pos - 0.45, max(vals) * 1.12, "全场 0 通过 →", ha="left", fontsize=7.5,
            color=C["mut"])
    fig.tight_layout()
    p = OUT / "fig3_pertask.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig4():
    """day-0 的两个切面：pass@1（全通过）与 f2p（检查项通过率）。"""
    r = rows("fig4_ceiling.csv")
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    xs = list(range(len(r)))
    vals = [float(x["value"]) for x in r]
    colors = [C["main"] if x["metric"] == "pass@1" else C["alt"] for x in r]
    ax.bar(xs, vals, color=colors, width=0.56)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.018, f"{v:g}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f'{x["agent"]}\n{x["metric"]}' for x in r], fontsize=7.5)
    ax.set_ylabel("比例")
    ax.set_ylim(0, 1.06)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig4_ceiling.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def main() -> int:
    for fn in (fig1, fig2, fig3, fig4):
        p = fn()
        print(f"  {p.name}: {p.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
