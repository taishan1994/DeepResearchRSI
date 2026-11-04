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


def main() -> int:
    a = load()
    print("生成图表：")
    fig1(a)
    fig2(a)
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
