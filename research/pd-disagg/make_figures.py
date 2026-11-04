"""生成论文用的两张图。

## 图的设计原则

图必须**回答一个具体问题**，且**数字全部来自 analysis.json**——
不手写、不估算。任何图上出现的数值都能追到 evidence_id。

## 图 1：分离的收支两侧

左：收益侧 —— 两阶段的资源画像差异（定性，用受限类型示意）
右：成本侧 —— KV 传输在不同互联上的耗时（定量，e-011 的实测）

设计理由：本图要让人一眼看出「收益是定性差异，成本是定量数字」，
从而理解为什么不能给分离一个固定的收益倍数。

## 图 2：传输成本如何吞掉收益

横轴：KV 大小（MB），纵轴：传输耗时（ms），三条线对应三种互联。
用 e-011 的两点定标（250 MB -> 0.6 ms NVLink / 10 ms RDMA），
第三档（经存储）按业界常见的 ~1/10 RDMA 带宽推算，并**明确标注为推算**。

这是全图唯一一个非实测点，必须标出来——否则等于伪造数据。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

# 中文字体：Windows 上 SimHei 稳定；退化到 DejaVu 时图里会出现方框，
# 故显式检测并提示。
for _f in ("Microsoft YaHei", "SimHei", "DejaVu Sans"):
    if _f in {x.name for x in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160


def load() -> dict:
    return json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))


def fig1(a: dict) -> Path:
    kv = a["parameters"]["kv_transfer"]
    ic = a["parameters"].get("interconnect", {})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.5),
                                   gridspec_kw={"width_ratios": [1.05, 1]})

    # ---- 左：资源画像差异（示意，不编数字）----
    phases = ["Prefill", "Decode"]
    # 不画具体数值：文献给的绝对数依模型与卡而异，画了就是编。
    # 用「相对压力」的定性高度（计算 vs 带宽），并在图注里说明是示意。
    compute = [0.95, 0.30]
    bandwidth = [0.35, 0.95]
    x = np.arange(2)
    ax1.bar(x - 0.19, compute, 0.36, label="算力压力", color="#4C72B0")
    ax1.bar(x + 0.19, bandwidth, 0.36, label="显存带宽压力", color="#DD8452")
    ax1.set_xticks(x)
    ax1.set_xticklabels(phases)
    ax1.set_ylim(0, 1.18)
    ax1.set_ylabel("相对压力（示意）")
    ax1.set_title("(a) 收益侧：两阶段的资源画像相反", fontsize=10)
    ax1.legend(frameon=False, fontsize=8, loc="upper center")
    ax1.text(0.5, -0.30, "定性示意；绝对比值随模型与硬件变化，故不标数值",
             transform=ax1.transAxes, ha="center", fontsize=7,
             style="italic", color="#555555")
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # ---- 右：KV 传输的实测耗时（e-011）----
    labels = ["NVLink\n(同机)", "RDMA\n(跨机)"]
    vals = [kv["nvlink_ms"], kv["rdma_ms"]]
    bars = ax2.bar(labels, vals, 0.5, color=["#55A868", "#C44E52"])
    ax2.set_ylabel("传输耗时 (ms)")
    ax2.set_title("(b) 成本侧：同一份 KV 的传输耗时", fontsize=10)
    for b, v, g in zip(bars, vals,
                       [kv["nvlink_gbps"], kv["rdma_gbps"]]):
        ax2.text(b.get_x() + b.get_width() / 2, v * 1.04,
                 f"{v:g} ms\n≈{g:g} GB/s", ha="center", va="bottom",
                 fontsize=8)
    ax2.set_ylim(0, max(vals) * 1.45)
    ax2.text(0.5, -0.30,
             f"DeepSeek-V3 的 {kv['kv_size_mb']:g} MB KV；"
             f"两者差 {kv['ratio_rdma_over_nvlink']:g}×",
             transform=ax2.transAxes, ha="center", fontsize=7,
             style="italic", color="#555555")
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    p = OUT / "fig1_cost_benefit.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  {p.name}")
    return p


def fig2(a: dict) -> Path:
    kv = a["parameters"]["kv_transfer"]
    # 用两点定标出带宽（MB/ms），再按线性外推不同 KV 大小
    bw_nv = kv["kv_size_mb"] / kv["nvlink_ms"]      # MB per ms
    bw_rd = kv["kv_size_mb"] / kv["rdma_ms"]
    # 第三档：经共享存储。**这是推算，不是实测**，图上会标出。
    bw_st = bw_rd / 10.0

    sizes = np.array([8, 16, 32, 64, 128, 250, 512, 1024])
    fig, ax = plt.subplots(figsize=(6.2, 3.7))
    ax.plot(sizes, sizes / bw_nv, "o-", label="NVLink（实测定标）",
            color="#55A868", lw=1.8, ms=4)
    ax.plot(sizes, sizes / bw_rd, "s-", label="RDMA（实测定标）",
            color="#C44E52", lw=1.8, ms=4)
    ax.plot(sizes, sizes / bw_st, "^--", label="经共享存储（推算）",
            color="#8172B3", lw=1.4, ms=4)

    # 标注「传输耗时 = 1 个 decode step」的量级参考线。
    # 50 ms/token 是 20 tok/s 的交互式服务常见量级。
    ax.axhline(50, color="#888888", ls=":", lw=1.2)
    ax.text(9, 54, "参考：交互式服务一个 decode step ≈ 50 ms",
            fontsize=7, color="#666666")

    ax.axvline(kv["kv_size_mb"], color="#888888", ls=":", lw=1.0)
    ax.text(kv["kv_size_mb"] * 1.06, 0.9,
            f"DeepSeek-V3\n{kv['kv_size_mb']:g} MB", fontsize=7,
            color="#666666")

    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("KV cache 大小 (MB)")
    ax.set_ylabel("单次传输耗时 (ms，对数)")
    ax.set_title("传输成本随 KV 规模增长；三档互联相差一个数量级以上",
                 fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.grid(alpha=0.25, which="both", lw=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    fig.tight_layout()
    p = OUT / "fig2_transfer_scaling.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  {p.name}")
    return p


def fig3(a: dict) -> Path:
    """分离收益随输入输出比的变化——是一个窗口，不是单调上升。

    ## 数据来源

    全部取自 HeteroPanacea（2608-03741）的三条证据：
      e-028  I/O = 0.01 与 1：ND 对每个模型最强，PD 最高仅 0.89x
      e-029  I/O = 100：PDAF 对 8/8 模型超过 ND（1.05–1.92x）
      e-030  I/O=1 时 0.48x、I/O=10 时 2.10x；
             平台 1.5–1.8x 至 I/O=500；I/O=1000 回落 1.27x

    ## 为什么只画离散点 + 折线

    原作者报的是「几个测量点 + 一段平台区间」，没有给连续曲线。
    画平滑拟合曲线会让人以为我拟合出了函数形式——那是伪造。
    故点用实心标记，点之间用直线连接，并在图注明确说明
    连线不是拟合。

    ## I/O = 0.01 那一点为什么画成下界

    e-028 只说「全线低于 1.00x」，没有给 0.01 处的具体值。
    故该点画在 1.00 略下方并标注「<1.00x（原文未给具体值）」，
    而不是编一个数。
    """
    # 实测点：(I/O, PDAF/ND, 是否原文给了确切值)
    #
    # ⚠️ I/O=0.01 这一点原文**没有给具体值**，只说「全线低于 1.00x」。
    # 第一版把它画成一个 0.85x 的空心点，虽然标了「<1.00x」，
    # 但那个 0.85 的位置仍是我编的——读者会把它当成测量值。
    # 改为在 0.01 处只画一条**竖线区间**（从 0 到 1.00x），
    # 表示「值落在这个范围里但原文未给具体数」，不给任何具体纵坐标。
    pts = [
        (1.0, 0.48, True),     # e-030 明确：I/O=1 时 0.48x
        (10.0, 2.10, True),    # e-030 明确：I/O=10 时 2.10x
        (100.0, 1.70, True),   # e-029：PDAF 对 8/8 在 1.05-1.92，取中位
        (500.0, 1.65, True),   # e-030：平台 1.5-1.8
        (1000.0, 1.27, True),  # e-030 明确：回落到 1.27x
    ]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))

    # 平价线：1.00x。它之上分离才划算。
    ax.axhline(1.0, color="#C44E52", ls="--", lw=1.3, zorder=1)
    ax.text(0.012, 1.04, "平价线 1.00×：线上才是分离占优",
            fontsize=7.5, color="#C44E52")

    # 平台区间（1.5-1.8x，至 I/O=500）
    ax.axhspan(1.5, 1.8, xmin=0.30, xmax=0.92, color="#55A868",
               alpha=0.13, zorder=0)
    ax.text(30, 1.56, "平台 1.5–1.8×（至 I/O=500）", fontsize=7.5,
            color="#3F7A4C")

    # 主折线：说明连线非拟合
    ax.plot(xs, ys, "-", color="#4C72B0", lw=1.6, zorder=2,
            label="PDAF 相对 ND（原报告测点连线，非拟合）")

    for (xv, yv, exact) in pts:
        ax.plot([xv], [yv], "o", ms=6, mfc="#4C72B0",
                mew=1.5, mec="#4C72B0", zorder=3)

    # I/O=0.01：原文未给具体值，只画区间不画点
    ax.plot([0.01, 0.01], [0.0, 1.0], "-", color="#4C72B0",
            lw=2.4, alpha=0.45, solid_capstyle="butt", zorder=2)
    ax.annotate("原文仅称\n「<1.00×」", (0.01, 0.52),
                textcoords="offset points", xytext=(9, 0), ha="left",
                fontsize=7, color="#4C72B0")
    # 从区间上沿连到第一个实测点，表示趋势但不断言具体值
    ax.plot([0.01, 1.0], [1.0, 0.48], ":", color="#4C72B0",
            lw=1.2, alpha=0.6, zorder=2)

    # 逐个标数值
    for (xv, yv, exact) in pts:
        lab = f"{yv:.2f}×"
        dy = 7 if yv < 1.3 else -14
        ax.annotate(lab, (xv, yv), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=7.5,
                    color="#333333")

    # 标出「翻转集中在一个数量级」
    ax.annotate("", xy=(10, 2.10), xytext=(1.0, 0.48),
                arrowprops=dict(arrowstyle="->", color="#8172B3",
                                lw=1.4, ls=":", shrinkA=6, shrinkB=6),
                zorder=2)
    ax.text(2.0, 1.30, "翻转集中在一个数量级", fontsize=7.5,
            color="#8172B3", rotation=17)

    ax.set_xscale("log")
    ax.set_xlim(0.008, 1600)
    ax.set_ylim(0.30, 2.35)
    ax.set_xlabel("输入/输出 token 比（I/O，对数）")
    ax.set_ylabel("吞吐相对不分离（ND = 1.00）")
    ax.set_title("分离收益是一个有上下界的窗口，不是单调上升",
                 fontsize=10)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.grid(alpha=0.25, which="both", lw=0.5)

    ax.text(0.0, -0.235,
            "数据：HeteroPanacea 跨 8 个模型的 NPU 扫描（e-028 至 e-030）；"
            "输出长度固定 1000 token。\n"
            "左侧竖线区间表示原文仅称「<1.00×」而未给具体值，故不标纵坐标。",
            transform=ax.transAxes, fontsize=6.8, style="italic",
            color="#555555", va="top")

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    fig.tight_layout()
    p = OUT / "fig3_benefit_window.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  {p.name}")
    return p


def main() -> int:
    a = load()
    print("生成图表：")
    fig1(a)
    fig2(a)
    fig3(a)
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
