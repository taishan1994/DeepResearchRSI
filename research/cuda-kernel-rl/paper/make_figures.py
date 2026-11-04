"""生成论文图表。所有数字从 `analysis.json` 取，不在此处硬编码。

## 为什么强调这一点

上一份综述（`cuda-kernel-gen`）的图注里出现过 `1.19x`——一个在
papers.json、evidence.csv、表格里都不存在的数。审计脚本查出来才知道。

故本文件只做**画图**，数字全部来自 `analysis.json`（由 analyze.py 生成，
而 analyze.py 只读 sources/evidence/claims/papers）。
任何图注里的数字也必须能在 analysis.json 里找到对应的键。

## 中文与负号

matplotlib 默认字体不带中文，需显式挑一个系统里有的中文字体；
`axes.unicode_minus=False` 否则负号显示成方块。
这两条在 cuda-kernel-gen 里踩过，照抄其字体探测逻辑。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE / "analysis.json"
FIGS = HERE / "figures"
FIGS.mkdir(exist_ok=True)


def pick_cjk_font() -> str:
    """挑一个可用的中文字体；找不到就明确报错，不静默用默认字体。"""
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                 "Source Han Sans SC", "PingFang SC", "WenQuanYi Zen Hei"):
        try:
            fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
            return name
        except Exception:  # noqa: BLE001
            continue
    raise SystemExit(
        "找不到中文字体。装 Microsoft YaHei / Noto Sans CJK SC 后重试——"
        "不要退回默认字体，那样图里的中文会是方块。")


FONT = pick_cjk_font()
plt.rcParams["font.sans-serif"] = [FONT]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 160
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.linestyle"] = ":"

d = json.loads(ANALYSIS.read_text(encoding="utf-8"))
counts = d["counts"]
core_n = counts["sources_core"]

INK = "#1f2d3d"
ACCENT = "#c0392b"
MUTED = "#7f8c8d"


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGS / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {name}")


# ---------------------------------------------------------------- 图 1
def fig_timeline() -> None:
    """按季度的核心论文数。"""
    tl = d["timeline"]
    labels = [t["quarter"] for t in tl]
    vals = [t["count"] for t in tl]

    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    bars = ax.bar(range(len(vals)), vals, color=INK, width=0.62)
    # 最后一根用强调色：它对应 2026-Q4，只有 1 篇，是因为检索截止
    bars[-1].set_color(MUTED)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("核心论文数", fontsize=9)
    ax.set_title("按季度的核心 RL 方法论文数", fontsize=10, color=INK, pad=8)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.06, str(v), ha="center", va="bottom", fontsize=8,
                color=INK)
    ax.set_ylim(0, max(vals) + 0.9)
    # 灰柱需要说明，否则读者会以为领域在萎缩
    ax.annotate("检索截止，非趋势",
                xy=(len(vals) - 1, vals[-1]),
                xytext=(len(vals) - 2.1, max(vals) + 0.45),
                fontsize=7, color=MUTED,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.7))
    save(fig, "fig1_timeline.png")


# ---------------------------------------------------------------- 图 2
def fig_reward_forms() -> None:
    """奖励形态的分布——本文的核心论据。"""
    rs = d["reward_shift"]
    # 中文标签；顺序按数量降序，便于看出主次
    label_map = {
        "outcome": "结果型（正确+加速）",
        "multi_turn": "多轮交互",
        "profiling": "profiling 驱动",
        "anti_hack": "反作弊机制",
        "synthetic": "合成数据/课程",
        "structural": "结构化代码奖励",
        "contrastive": "对比式",
        "curriculum": "课程学习",
    }
    items = [(label_map.get(k, k), v) for k, v in
             sorted(rs.items(), key=lambda kv: -kv[1])]
    names = [i[0] for i in items]
    vals = [i[1] for i in items]

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    colors = [ACCENT if n.startswith("反作弊") else INK for n in names]
    ax.barh(range(len(vals))[::-1], vals, color=colors, height=0.62)
    ax.set_yticks(range(len(vals))[::-1])
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel(f"论文数（共 {core_n} 篇核心工作，一篇可含多种形态）",
                  fontsize=8.5)
    ax.set_title("奖励形态分布", fontsize=10, color=INK, pad=8)
    for i, v in enumerate(vals):
        ax.text(v + 0.12, len(vals) - 1 - i, str(v), va="center", fontsize=8,
                color=INK)
    ax.set_xlim(0, max(vals) + 1.3)
    save(fig, "fig2_reward_forms.png")


# ---------------------------------------------------------------- 图 3
def fig_algorithm() -> None:
    """算法分布：单调得几乎无信息——这正是论点。"""
    # 数字来自 analyze 的算法统计（在 analyze.py 中计算并写入 algo_mix）
    am = d.get("algo_mix") or {}
    if not am:
        print("  [跳过] analysis.json 没有 algo_mix，先重跑 analyze.py")
        return
    order = ["GRPO", "对比式", "PPO", "未点名"]
    vals = [am.get(k, 0) for k in order]

    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    bars = ax.bar(order, vals, color=[INK, INK, ACCENT, MUTED], width=0.55)
    ax.set_ylabel("论文数", fontsize=9)
    ax.set_title("核心工作使用的算法", fontsize=10, color=INK, pad=8)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, str(v),
                ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_ylim(0, max(vals) + 1.0)
    ax.tick_params(axis="x", labelsize=9)
    save(fig, "fig3_algorithm.png")


def fig_alpha_ablation() -> None:
    """TritonRL 表 3 的 α 消融：已发表工作里最干净的一处「奖励组件开关」证据。

    ⚠️ 数字不是从 analysis.json 算出来的，而是从论文表 3 读出的**外部事实**。
       这与图 1-3 不同（那三张是对语料的统计，可由脚本重算）。
       故这里从 data/fig4_alpha_ablation.csv 读，并在图上注明来源，
       防止读者误以为本文重新测量过。
    """
    import csv as _csv
    from pathlib import Path as _P

    src = _P(__file__).parent / "data" / "fig4_alpha_ablation.csv"
    if not src.is_file():
        print("  [跳过] 缺 fig4_alpha_ablation.csv")
        return
    with src.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    if not rows:
        return

    alphas = [r["alpha"] for r in rows]
    correct = [float(r["correct"]) for r in rows]
    valid = [float(r["valid"]) for r in rows]

    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    x = range(len(alphas))
    ax.plot(list(x), correct, "o-", color=ACCENT, lw=1.8, ms=5,
            label="correct（编译并正确）")
    ax.plot(list(x), valid, "s--", color=MUTED, lw=1.3, ms=4,
            label="valid（语法有效）")

    # 标出 α=0 与 α=0.1 之间的落差：这是「删掉 plan 奖励」的代价
    i0 = alphas.index("0.0") if "0.0" in alphas else 0
    i1 = alphas.index("0.1") if "0.1" in alphas else 1
    ax.annotate("", xy=(i1, correct[i1]), xytext=(i0, correct[i0]),
                arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.2))
    ax.text((i0 + i1) / 2, (correct[i0] + correct[i1]) / 2 - 9,
            f"+{correct[i1] - correct[i0]:.0f} 点", ha="center",
            fontsize=8.5, color=ACCENT, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"α={a}" for a in alphas], fontsize=8.5)
    ax.set_ylabel("百分比（%）", fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_title("删掉 plan 奖励的代价（TritonRL 表 3）",
                 fontsize=10, color=INK, pad=8)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.text(0.0, -0.30, "数据源：TritonRL 表 3，KernelBench Level 1，pass@10",
            transform=ax.transAxes, fontsize=7, color=MUTED)
    save(fig, "fig4_alpha_ablation.png")


if __name__ == "__main__":
    print(f"字体：{FONT}")
    print("生成图表：")
    fig_timeline()
    fig_reward_forms()
    fig_algorithm()
    fig_alpha_ablation()
    print("完成")
