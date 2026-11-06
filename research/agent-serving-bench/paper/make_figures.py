# -*- coding: utf-8 -*-
"""生成四张图。数值全部来自 data/*.csv，不在这里写任何字面量。"""
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
    r = rows("fig1_funnel.csv")
    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    xs = list(range(len(r)))
    vals = [float(x["count"]) for x in r]
    ax.barh(xs, vals, color=[C["mut"], C["main"], C["ok"]], height=0.52)
    for x, v in zip(xs, vals):
        ax.text(v + 0.4, x, "%g" % v, va="center", fontsize=9)
    ax.set_yticks(xs)
    ax.set_yticklabels([x["item"] for x in r], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, max(vals) * 1.18)
    ax.set_xlabel("次数")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig1_funnel.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig2():
    r = rows("fig2_cross.csv")
    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    xs = list(range(len(r)))
    vals = [float(x["value"]) for x in r]
    colors = [C["main"], C["alt"], C["mut"]]
    ax.bar(xs, vals, color=colors, width=0.5)
    ax.axhline(1.0, color="black", lw=0.9, ls="--")
    ax.text(len(r) - 0.45, 1.02, "参考线 1.0", fontsize=8, ha="right")
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.05, "%g" % v, ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["item"] for x in r], fontsize=8)
    ax.set_ylabel("dollars per dollar")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig2_cross.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig3():
    r = rows("fig3_verify.csv")
    labels = [x["item"] for x in r]
    vals = [float(x["count"]) for x in r]
    pairs = [(vals[0], vals[1]), (vals[2], vals[3])]
    titles = ["自然停止检查的覆盖", "未通过里提交前已有症状"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4))
    for ax, (a, b), title, lab in zip(axes, pairs, titles,
                                     [(labels[0], labels[1]), (labels[2], labels[3])]):
        ax.bar([0, 1], [a, b], color=[C["alt"], C["mut"]], width=0.5)
        for i, v in enumerate([a, b]):
            ax.text(i, v + max(a, b) * 0.04, "%g" % v, ha="center", fontsize=9)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["命中", "总数"], fontsize=9)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0, max(a, b) * 1.25)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig3_verify.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig4():
    r = rows("fig4_honest.csv")
    fig, ax = plt.subplots(figsize=(5.2, 2.5))
    xs = list(range(len(r)))
    vals = [float(x["speedup"]) for x in r]
    ax.bar(xs, vals, color=[C["alt"], C["ok"]], width=0.42)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.25, "%g×" % v, ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["item"] for x in r], fontsize=9)
    ax.set_ylabel("报告的加速比")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig4_honest.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def main():
    for f in (fig1, fig2, fig3, fig4):
        print("  ", f().name)


if __name__ == "__main__":
    main()
