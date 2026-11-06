# -*- coding: utf-8 -*-
"""生成论文图。每个图回答一个问题，数值全部来自 data/*.csv。

## 设计原则（与 pd-disagg 一致）

- 一张图只回答一个问题，标题即问题。
- 任何出现在图上的数字都必须能追到 cite 列指向的主张。
- 派生/估算点必须显式标注，不得与实测混在一起。
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

for _f in ("Microsoft YaHei", "SimHei", "DejaVu Sans"):
    if _f in {x.name for x in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 170
C = {"main": "#2f5d8a", "warm": "#c4622d", "grey": "#7a7a7a", "light": "#9fc0dd"}


def rows(name):
    with (HERE / "data" / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fig1():
    r = rows("fig1_gain.csv")
    labels = [x["label"] for x in r]
    vals = [float(x["value"]) for x in r]
    fig, ax = plt.subplots(figsize=(8.6, 3.15))
    colors = [C["warm"] if v < 1.5 else C["main"] for v in vals]
    bars = ax.barh(labels, vals, color=colors, height=0.62)
    ax.axvline(1.0, color=C["grey"], lw=1.0, ls="--")
    ax.set_xlabel("报告值（倍数；ForgeKernel 为对专家参考的 % 增益，标为 10）")
    for b, v in zip(bars, vals):
        ax.text(v + 0.08, b.get_y() + b.get_height() / 2, f"{v:g}",
                va="center", fontsize=8)
    ax.set_xlim(0, max(vals) * 1.16)
    ax.invert_yaxis()
    fig.tight_layout()
    p = OUT / "fig1_gain.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig3():
    r = rows("fig3_budget.csv")
    fig, ax = plt.subplots(figsize=(6.6, 2.85))
    for name, color in (("AdaExplore L2", C["main"]), ("AdaExplore L3", C["warm"])):
        pts = [(float(x["budget"]), float(x["value"])) for x in r if x["system"] == name]
        pts.sort()
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", label=name,
                color=color, lw=2, ms=7)
    ax.set_xlabel("搜索预算（迭代步数）")
    ax.set_ylabel("几何平均加速比")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig3_budget.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig4():
    r = rows("fig4_funnel.csv")
    fig, ax = plt.subplots(figsize=(7.4, 2.85))
    xs = range(len(r))
    k = [float(x["kernel_level"]) for x in r]
    e = [float(x["e2e"]) for x in r]
    ax.bar([i - 0.19 for i in xs], k, width=0.36, color=C["light"], label="kernel 级")
    ax.bar([i + 0.19 for i in xs], e, width=0.36, color=C["main"], label="端到端")
    ax.axhline(1.0, color=C["grey"], ls="--", lw=1)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([x["object"] for x in r], fontsize=7.5)
    ax.set_ylabel("相对基线的倍数")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    p = OUT / "fig4_funnel.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig5():
    r = rows("fig5_cost.csv")
    fig, ax = plt.subplots(figsize=(7.8, 2.85))
    labels = [f'{x["system"]}\n{x["metric"]}' for x in r]
    vals = [float(x["value"]) for x in r]
    ax.bar(labels, vals, color=[C["warm"] if v > 100 else C["main"] for v in vals])
    ax.set_yscale("log")
    ax.set_ylabel("数值（对数轴）")
    for i, v in enumerate(vals):
        ax.text(i, v * 1.15, f"{v:g}", ha="center", fontsize=7.5)
    plt.setp(ax.get_xticklabels(), fontsize=7)
    fig.tight_layout()
    p = OUT / "fig5_cost.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def main():
    with matplotlib.rc_context({"font.family": plt.rcParams["font.family"]}):
        for f in (fig1, fig3, fig4, fig5):
            print("  ", f().name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())