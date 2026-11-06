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
    r = rows("fig1_gap.csv")
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    xs = list(range(len(r)))
    vals = [float(x["value"]) for x in r]
    # 两组之间是反号：BF16 一次性解多，AWQ 循环解多。用颜色标出这件事。
    colors = [C["main"], C["alt"], C["main"], C["alt"]]
    ax.bar(xs, vals, color=colors, width=0.58)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.5, f"{v:g}", ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["item"] for x in r], fontsize=8)
    ax.set_ylabel("解出的题数")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig1_gap.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig2():
    r = rows("fig2_proxy.csv")
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    xs = list(range(len(r)))
    vals = [float(x["rho"]) for x in r]
    colors = [C["main"]] * 3 + [C["alt"]]
    ax.bar(xs, vals, color=colors, width=0.55)
    ax.axhline(0, color="black", lw=0.8)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.02, f"{v:g}", ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["proxy"] for x in r], fontsize=8)
    ax.set_ylabel("与真实目标的 rank 相关")
    ax.set_ylim(-0.1, 1.0)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig2_proxy.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig3():
    r = rows("fig3_local.csv")
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    xs = list(range(len(r)))
    vals = [float(x["count"]) for x in r]
    colors = [C["mut"], C["alt"], C["mut"], C["ok"]]
    ax.bar(xs, vals, color=colors, width=0.55)
    for x, v in zip(xs, vals):
        ax.text(x, v + 1.2, f"{v:g}", ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["item"] for x in r], fontsize=8)
    ax.set_ylabel("条数")
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig3_local.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig4():
    r = rows("fig4_divergence.csv")
    fig, ax = plt.subplots(figsize=(5.4, 2.7))
    xs = list(range(len(r)))
    vals = [float(x["percent"]) for x in r]
    ax.bar(xs, vals, color=[C["main"], C["alt"]], width=0.42)
    for x, v in zip(xs, vals):
        ax.text(x, v + 1.6, f"{v:g}%", ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels([x["precision"] for x in r], fontsize=9)
    ax.set_ylabel("出现路径分歧的会话占比（%）")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    p = OUT / "fig4_divergence.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def main():
    for f in (fig1, fig2, fig3, fig4):
        print("  ", f().name)


if __name__ == "__main__":
    main()
