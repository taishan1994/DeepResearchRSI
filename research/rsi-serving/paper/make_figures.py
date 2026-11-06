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
    r = rows("fig1_gain.csv")
    fig, ax = plt.subplots(figsize=(8.6, 3.15))
    ys = list(range(len(r)))[::-1]
    vals = [float(x["value"]) for x in r]
    # 对 AR 与对 stock 是两把尺子，用颜色区分，避免读成一列可比排序
    colors = [C["alt"] if "AR" in x["system"] else C["main"] for x in r]
    ax.barh(ys, vals, color=colors, height=0.62)
    ax.set_yticks(ys)
    ax.set_yticklabels([x["system"] for x in r], fontsize=8)
    for y, v in zip(ys, vals):
        ax.text(v + 0.15, y, f"{v:g}x", va="center", fontsize=8)
    ax.set_xlabel("报告值（倍数）")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig1_gain.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig2():
    r = rows("fig2_funnel.csv")
    fig, ax = plt.subplots(figsize=(6.6, 2.85))
    xs = list(range(len(r)))
    vals = [float(x["count"]) for x in r]
    ax.bar(xs, vals, color=[C["main"], C["main"], C["main"], C["ok"], C["alt"]], width=0.62)
    for x, v in zip(xs, vals):
        ax.text(x, v + 2, f"{v:g}", ha="center", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["stage"] for x in r], fontsize=8)
    ax.set_ylabel("条数")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig2_funnel.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig3():
    r = rows("fig3_cost.csv")
    fig, ax = plt.subplots(figsize=(7.4, 2.85))
    ys = list(range(len(r)))[::-1]
    vals = [float(x["value"]) for x in r]
    # 跨度 7 到 25000，必须用对数轴，否则小项全部看不见
    ax.barh(ys, vals, color=C["mut"], height=0.6)
    ax.set_xscale("log")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{x['item']}（{x['unit']}）" for x in r], fontsize=8)
    for y, v in zip(ys, vals):
        ax.text(v * 1.08, y, f"{v:g}", va="center", fontsize=8)
    ax.set_xlabel("数值（对数轴）")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig3_cost.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig4():
    r = rows("fig4_reversal.csv")
    fig, ax = plt.subplots(figsize=(7.8, 2.85))
    xs = list(range(len(r)))
    vals = [float(x["gain"]) for x in r]
    ax.bar(xs, vals, color=C["alt"], width=0.55)
    ax.axhline(0, color="black", lw=0.8)
    for x, v in zip(xs, vals):
        ax.text(x, v - 1.2, f"{v:g}%", ha="center", va="top", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{x['mechanism']}\n{x['condition']}" for x in r], fontsize=7.5)
    ax.set_ylabel("相对收益（%）")
    ax.set_ylim(min(vals) * 1.35, 0.5)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig4_reversal.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def main():
    for f in (fig1, fig2, fig3, fig4):
        print("  ", f().name)


if __name__ == "__main__":
    main()
