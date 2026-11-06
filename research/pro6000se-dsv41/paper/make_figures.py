"""生成论文的三张图。

设计原则：**每张图只回答一个判断**，且图上的每个数字都必须能在证据里找到。
不做「把所有数据画在一起」的图——那种图看起来信息量大，实际不支撑任何结论。

图 1　容量阶梯：回答「要几张卡」
图 2　预填速率随上下文衰减 + 缓存假象：回答「1M 有多慢，以及为什么会测错」
图 3　解码：投机开关是分水岭：回答「可用 vs 不可用」
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

# 中文字体：SimHei 覆盖常用汉字，且是**单色**字体（彩色字体会渲染成空白）。
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 200
plt.rcParams["savefig.dpi"] = 200

INK = "#1a1a1a"
MUTED = "#8a8a8a"
BLUE = "#2f5d8a"
RED = "#a8322d"
GREEN = "#3d6b47"
AMBER = "#b8860b"


def fig1_capacity() -> None:
    """容量阶梯：511 GB 权重 vs 96 GB×N 的显存总量。"""
    fig, ax = plt.subplots(figsize=(6.4, 3.5))

    cards = [1, 2, 4, 6, 8]
    total = [96 * n for n in cards]

    # 三档需求线
    ax.axhline(511, color=RED, lw=1.6, ls="-", zorder=3)
    ax.text(8.35, 511, " 全精度权重 511 GB", va="center", ha="left",
            fontsize=7.6, color=RED)
    ax.axhspan(315, 350, color=AMBER, alpha=0.22, zorder=1)
    ax.text(8.35, 332, " Engram 下放后\n 315–350 GB", va="center", ha="left",
            fontsize=7.2, color="#7a5c07")

    colors, labels = [], []
    for n, t in zip(cards, total):
        # 6 卡：算术够（576 > 511），但 TP 必须 2 的幂 → 不可用
        if n == 6:
            colors.append("#c9c9c9")
            labels.append("拓扑不可行")
        elif t < 315:
            colors.append("#d9d9d9")
            labels.append("装不下")
        elif t < 511:
            colors.append(GREEN)
            labels.append("可行")
        else:
            colors.append(BLUE)
            labels.append("可行")

    bars = ax.bar([str(n) for n in cards], total, color=colors,
                  edgecolor=INK, linewidth=0.7, width=0.62, zorder=2)

    # 在柱顶标出「装不装得下」
    for b, n, lab in zip(bars, cards, labels):
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 12, lab,
                ha="center", va="bottom", fontsize=6.8,
                color=INK if lab != "拓扑不可行" else "#5a5a5a",
                rotation=0)

    # 6 卡的特殊注解：这是本文最容易被忽略的一条算术
    ax.annotate("576 GB 算术够，\n但 TP 须为 2 的幂",
                xy=(3, 576), xytext=(3.35, 660),
                fontsize=6.6, color="#5a5a5a", ha="left",
                arrowprops=dict(arrowstyle="->", color="#5a5a5a", lw=0.7))

    ax.set_ylim(0, 830)
    ax.set_xlim(-0.6, 4.6)
    ax.set_ylabel("显存总量（GB）", fontsize=8)
    ax.set_xlabel("RTX PRO 6000 卡数（每卡 96 GB）", fontsize=8)
    ax.tick_params(labelsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e8e8e8", lw=0.6, zorder=0)

    legend = [Patch(facecolor=BLUE, edgecolor=INK, lw=0.7, label="全精度可行"),
              Patch(facecolor=GREEN, edgecolor=INK, lw=0.7, label="需 Engram 下放"),
              Patch(facecolor="#d9d9d9", edgecolor=INK, lw=0.7, label="装不下（仅量化旁路）"),
              Patch(facecolor="#c9c9c9", edgecolor=INK, lw=0.7, label="TP 拓扑不允许")]
    ax.legend(handles=legend, fontsize=6.4, frameon=False,
              loc="upper left", ncol=2, handlelength=1.2, columnspacing=0.9)

    fig.tight_layout()
    fig.savefig(FIG / "fig-1.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  图 1  容量阶梯")


def fig2_prefill() -> None:
    """预填速率随上下文衰减，并把「缓存命中」这个假象画出量级差。"""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))

    # 冷预填阶梯（SGLang 4 卡，每行提示带唯一标记）
    ctx = [402625, 704582, 905885, 1006538]
    rate = [5065, 4022, 3478, 3242]
    ax.plot(ctx, rate, "o-", color=BLUE, lw=1.8, ms=5.5,
            label="冷预填（唯一提示，真实值）", zorder=4)

    for x, y in zip(ctx, rate):
        ax.annotate(f"{y:,}", (x, y), textcoords="offset points",
                    xytext=(0, -12), ha="center", fontsize=6.8, color=BLUE)

    # 重复一次的第二个点
    ax.plot([1006538], [3126], "o", color=BLUE, ms=5.5, mfc="white",
            mew=1.4, zorder=4)
    ax.annotate("重复 3,126", (1006538, 3126), textcoords="offset points",
                xytext=(-4, -14), ha="right", fontsize=6.6, color=BLUE)

    # 假象：13,962 tok/s（前缀缓存命中，只预填了约 140K）
    ax.plot([1040000], [13962], "*", color=RED, ms=13, zorder=5)
    ax.annotate("13,962 tok/s\n（前缀缓存命中，只真预填 ~140K）",
                xy=(1040000, 13962), xytext=(560000, 12200),
                fontsize=6.8, color=RED, ha="left",
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.8,
                                connectionstyle="arc3,rad=-0.15"))

    # 假象：6,528（作者自己的旧数）
    ax.plot([409000], [6528], "x", color=RED, ms=7, mew=1.8, zorder=5)
    ax.annotate("6,528（同一假象的旧版本，\n真实为 5,065）",
                xy=(409000, 6528), xytext=(330000, 8600),
                fontsize=6.6, color=RED, ha="left",
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.7,
                                connectionstyle="arc3,rad=0.2"))

    ax.set_xlim(280000, 1120000)
    ax.set_ylim(0, 15800)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K"))
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v/1000:.1f}K" if v >= 1000 else f"{v:.0f}"))
    ax.set_xlabel("提示长度（token）", fontsize=8)
    ax.set_ylabel("预填速率（tok/s）", fontsize=8)
    ax.tick_params(labelsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color="#ececec", lw=0.6, zorder=0)

    ax.legend(fontsize=6.8, frameon=False, loc="lower left")
    ax.text(0.99, 0.03, "1M 冷预填 310.5 s ≈ 5 分钟",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.8, color=MUTED, style="italic")

    fig.tight_layout()
    fig.savefig(FIG / "fig-2.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  图 2  预填衰减与缓存假象")


def fig3_decode() -> None:
    """双面板：左=投机开关的落差，右=并发扩展。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 3.3),
                                   gridspec_kw={"width_ratios": [1.05, 1]})

    # ---- 左：DSpark 开/关 ----
    cats = ["散文", "结构化"]
    on = [78.9, 120.5]
    off = [36.5, 36.5]
    x = range(len(cats))
    w = 0.34
    b1 = ax1.bar([i - w / 2 for i in x], on, w, color=GREEN,
                 edgecolor=INK, lw=0.7, label="DSpark 开")
    b2 = ax1.bar([i + w / 2 for i in x], off, w, color="#d9d9d9",
                 edgecolor=INK, lw=0.7, label="DSpark 关")
    for bars in (b1, b2):
        for b in bars:
            ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + 2.5,
                     f"{b.get_height():.1f}", ha="center", fontsize=7)

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(cats, fontsize=7.5)
    ax1.set_ylabel("单流解码（tok/s）", fontsize=8)
    ax1.set_ylim(0, 145)
    ax1.set_title("投机是「可用 vs 不可用」的分界", fontsize=8, pad=6)
    ax1.legend(fontsize=6.6, frameon=False, loc="upper left")
    ax1.tick_params(labelsize=7.2)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.grid(axis="y", color="#ececec", lw=0.6)
    ax1.axhline(36.5, color=RED, lw=0.8, ls=":", zorder=1)

    # ---- 右：并发扩展 ----
    conc = [1, 2, 4, 8]
    agg = [115.2, 220.6, 322.2, 468.2]
    per = [121.9, 125.8, 108.5, 66.2]

    ax2.plot(conc, agg, "o-", color=BLUE, lw=1.7, ms=5,
             label="合计吞吐（tok/s）")
    ax2.plot(conc, per, "s--", color=AMBER, lw=1.3, ms=4,
             label="每流吞吐（tok/s）")
    ax2.plot(conc, [115.2 * c for c in conc], ":", color=MUTED, lw=1.0,
             label="线性理想（1.00×）")

    for c, a in zip(conc, agg):
        ax2.annotate(f"{a:.0f}", (c, a), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=6.8, color=BLUE)

    ax2.set_xscale("log", base=2)
    ax2.set_xticks(conc)
    ax2.set_xticklabels([str(c) for c in conc], fontsize=7.5)
    ax2.set_xlabel("并发请求数", fontsize=8)
    ax2.set_ylabel("tok/s", fontsize=8)
    ax2.set_ylim(0, 1080)
    ax2.set_title("4 卡 TP4/EP4：8 并发是硬上限（4.06×）", fontsize=8, pad=6)
    ax2.legend(fontsize=6.4, frameon=False, loc="upper left")
    ax2.tick_params(labelsize=7.2)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.grid(color="#ececec", lw=0.6)

    fig.tight_layout()
    fig.savefig(FIG / "fig-3.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  图 3  解码的两个维度")


def main() -> int:
    print("生成图：")
    fig1_capacity()
    fig2_prefill()
    fig3_decode()
    for p in sorted(FIG.glob("*.png")):
        print(f"  {p.name}  {p.stat().st_size:,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
