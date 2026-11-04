"""生成论文图表。数字只读 analysis.json，不手写。

## 两张图

fig1_dims     五个环节被多少篇工作覆盖（论文数）
fig2_evidence 五个环节各有多少条证据

两者一起看才有信息：某环节「论文多但证据少」说明每篇只提一句；
「论文少但证据多」说明少数工作在深挖。

## 约束

图内标题**不写编号**（编号由 LaTeX caption 生成），避免出现「图 1：图 1」。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

INK = "#2b2b2b"
ACCENT = "#b5352e"
MUTED = "#8a8a8a"
LIGHT = "#c9d6df"

LABELS = {
    "observe": "观测\nobserve",
    "act": "动作\nact",
    "budget": "预算\nbudget",
    "recover": "恢复\nrecover",
    "eval": "评测\neval",
}


def pick_cjk_font() -> str:
    for name in ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC"):
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return name
        except Exception:  # noqa: BLE001
            continue
    return "DejaVu Sans"


FONT = pick_cjk_font()
plt.rcParams["font.family"] = [FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 200
plt.rcParams["savefig.bbox"] = "tight"


def save(fig, name: str) -> None:
    p = FIG / name
    fig.savefig(p, facecolor="white")
    plt.close(fig)
    print(f"  {name}  {p.stat().st_size // 1024} KB")


def main() -> int:
    d = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    dims = d["dims"]
    order = dims["order"]

    xs = [LABELS[k] for k in order]
    src_n = [dims["source_count"][k] for k in order]
    ev_n = [dims["evidence_count"][k] for k in order]

    # ---- fig1：覆盖的工作数 ----
    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    colors = [ACCENT if k == "recover" else INK for k in order]
    bars = ax.bar(xs, src_n, color=colors, width=0.58)
    ax.set_ylabel("工作数", fontsize=9)
    ax.set_title("各环节被多少篇工作覆盖", fontsize=10, color=INK, pad=8)
    for b, v in zip(bars, src_n):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, str(v),
                ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_ylim(0, max(src_n) + 1.4)
    ax.tick_params(axis="x", labelsize=8)
    # 标出最薄的一环
    i = order.index("recover")
    ax.annotate("归因最薄", xy=(i, src_n[i]), xytext=(i, src_n[i] + 1.9),
                ha="center", fontsize=8, color=ACCENT,
                arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.0))
    save(fig, "fig1_dims.png")

    # ---- fig2：证据条数 ----
    fig, ax = plt.subplots(figsize=(4.6, 2.7))
    x = range(len(order))
    ax.bar([i - 0.19 for i in x], src_n, width=0.36, color=LIGHT,
           label="工作数")
    ax.bar([i + 0.19 for i in x], ev_n, width=0.36, color=ACCENT,
           label="证据条数")
    ax.set_xticks(list(x))
    ax.set_xticklabels(xs, fontsize=8)
    ax.set_ylabel("数量", fontsize=9)
    ax.set_title("工作数与证据条数的对比", fontsize=10, color=INK, pad=8)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_ylim(0, max(max(src_n), max(ev_n)) + 1.6)
    save(fig, "fig2_evidence.png")

    print(f"\n工作数 {src_n}｜证据数 {ev_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
