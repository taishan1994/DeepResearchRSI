"""把 analysis.json 的参数落成 paper/data/*.csv，供审计做数值回溯。

## 为什么需要

audit_paper.py 的判据 C 是：论文正文里标注了 cite 的数值，
必须能在对应 claim 的 statement 里找到同一个数字。

它的输入是 `paper/data/*.csv`，每行一个 `value` + 一个 `cite`，
`cite` 必须是 **claim_id**（不是 evidence_id——这是上一轮踩过的坑：
写错会静默统计成 0，看起来像「没有数值需要回溯」）。

## 为什么这些数能通过判据 C

判据 C 要求「value 出现在 claim 的 statement 里」。故每一行都必须
对应一条**把该数字写进了 statement** 的 claim。

本归档的 6 条 claim 里，实际写了数字的是：
  c-transfer  含 250 MB / 0.6 ms / 10 ms / 16.7 倍 / 600 GB/s / 800 Gbps
  c-boundary  含 13.2× / 1.69×
  c-model     含 2.1× / 9.7× / 1.8× / 95% / 1.1–4.1 倍

⚠️ 因此不能把 analysis.json 里所有数都塞进来——像「416.7 GB/s」
是我从 250/0.6 反算的派生值，claim 的 statement 里没有它，
硬塞会被判据 C 挡住。这类数标注为 derived，不进 data/*.csv，
在论文里以表 tab1 的形式呈现，并在 caption 说明由实测反算。

这正是判据 C 的价值：它逼我区分「文献报的数」与「我算的数」。
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"


def write(name: str, header: list[str], rows: list[list[str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    (DATA / name).write_text(buf.getvalue(), encoding="utf-8",
                             newline="\n")
    print(f"  {name}  {len(rows)} 行")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    kv = a["parameters"]["kv_transfer"]
    agg = a["parameters"]["aggregation_wins"]
    cxl = a["parameters"]["cxl_vs_rdma"]
    moe = a["parameters"]["moe"]
    sq = a["parameters"]["stage_quant"]

    print("生成 data/*.csv（每行的 cite 必须是 claim_id）：")

    # ---- 传输：文献直接报告的值 ----
    write("transfer.csv",
          ["metric", "value", "unit", "cite", "note"],
          [
              ["kv_size", f"{kv['kv_size_mb']:g}", "MB", "c-transfer",
               "DeepSeek-V3 的 KV cache 规模（e-011）"],
              ["nvlink_ms", f"{kv['nvlink_ms']:g}", "ms", "c-transfer",
               "经 NVLink 传输耗时（e-011）"],
              ["rdma_ms", f"{kv['rdma_ms']:g}", "ms", "c-transfer",
               "经 RDMA 传输耗时（e-011）"],
              ["ratio", f"{kv['ratio_rdma_over_nvlink']:g}", "x", "c-transfer",
               "RDMA 相对 NVLink 的倍数（由前两项相除）"],
              ["nvlink_peak", "600", "GB/s", "c-transfer",
               "A100 节点内 NVLink 峰值（e-006）"],
              ["ib_gbps", "800", "Gbps", "c-transfer",
               "集群 InfiniBand 规格（e-006）"],
          ])

    # ---- 边界：反例 ----
    write("boundary.csv",
          ["metric", "value", "unit", "cite", "note"],
          [
              ["ttft_reduction", f"{agg['ttft_reduction_x']:g}", "x",
               "c-boundary",
               "相对 PD 分离，聚合方案的 TTFT 降幅（e-025）"],
              ["tpot_reduction", f"{agg['tpot_reduction_x']:g}", "x",
               "c-boundary",
               "相对 PD 聚合的 TPOT 降幅（e-025）"],
          ])

    # ---- 模型：按类型 ----
    rows = [
        ["sparse_throughput", f"{cxl['throughput_x']:g}", "x", "c-model",
         "SAC 在 DeepSeek-V3.2 上相对 RDMA 的吞吐（e-022）"],
        ["sparse_ttft", f"{cxl['ttft_x']:g}", "x", "c-model",
         "SAC 的 TTFT 降幅（e-022）"],
        ["sparse_tbt", f"{cxl['tbt_x']:g}", "x", "c-model",
         "SAC 的 TBT 降幅（e-022）"],
        ["moe_dedup", f"{moe['duplicate_weight_eliminated_pct']:g}", "%",
         "c-model", "专家共享消除的重复权重比例（e-019）"],
        ["quant_loss_low", f"{sq['accuracy_loss_ratio_low']:g}", "x",
         "c-model",
         "prefill-only 量化的精度损失倍数下界（e-020）"],
        ["quant_loss_high", f"{sq['accuracy_loss_ratio_high']:g}", "x",
         "c-model",
         "prefill-only 量化的精度损失倍数上界（e-020）"],
    ]
    write("model.csv", ["metric", "value", "unit", "cite", "note"], rows)

    # ---- 收益窗口：跨 8 个模型的 I/O 扫描（e-028 至 e-030）----
    # cite 用 c-window——这一组数字的 statement 在 c-window 里，
    # 不在 c-boundary。判据 C 要求 value 出现在**对应** claim 里。
    write("window.csv",
          ["metric", "value", "unit", "cite", "note"],
          [
              ["io_high_pdaf_low", "1.05", "x", "c-window",
               "I/O=100 时 PDAF 相对 ND 的下界（e-029）"],
              ["io_high_pdaf_high", "1.92", "x", "c-window",
               "I/O=100 时 PDAF 相对 ND 的上界（e-029）"],
              ["pd_best_low_io", "0.89", "x", "c-window",
               "I/O=1 时 PD 最好的表现，仍未过平价（e-028）"],
              ["crossover_low", "0.48", "x", "c-window",
               "I/O=1 时 PDAF 相对 ND（e-030）"],
              ["crossover_high", "2.10", "x", "c-window",
               "I/O=10 时 PDAF 相对 ND（e-030）"],
              ["plateau_low", "1.5", "x", "c-window",
               "平台期下界，延续到 I/O=500（e-030）"],
              ["plateau_high", "1.8", "x", "c-window",
               "平台期上界（e-030）"],
              ["falloff", "1.27", "x", "c-window",
               "I/O=1000 时回落到 1.27x（e-030）"],
              ["models_beaten_by_pdaf", "8", "个", "c-window",
               "I/O=100 时 PDAF 超过 ND 的模型数，共 8 个（e-029）"],
              # 「6 个」这句话在 c-model（跨模型最一致的做法），
              # 不在 c-window。判据 C 要求 value 在**对应** claim 里。
              ["models_best_is_pdaf", "6", "个", "c-model",
               "PDAF 为最佳模式的模型数，共 8 个（e-038）"],
              ["idle_ratio_low", "36.21", "%", "c-boundary",
               "DeepSeek-V3.2 DP=16 时空转率下界（e-039）"],
              ["idle_ratio_high", "59.98", "%", "c-boundary",
               "空转率上界（e-039）"],
              ["qwen32b_kv_scale", "8", "K", "c-model",
               "Qwen3-32B 在该上下文长度下 KV 达 GB 级（e-032）"],
              ["llama2_latency", "39", "x", "c-model",
               "Llama2-7B 上 GPU 延迟更低倍数（e-033）"],
              ["llama2_throughput", "41", "x", "c-model",
               "Llama2-7B 上 GPU 吞吐更高倍数（e-033）"],
              ["llama33_prefill_energy", "39", "%", "c-model",
               "Llama 3.3 70B 分离后 prefill 能耗降幅（e-034）"],
              ["llama33_decode_energy", "48", "%", "c-model",
               "decode 能耗降幅（e-034）"],
              ["dsv2lite_ttft", "81", "%", "c-model",
               "DeepSeek-V2-Lite 的 P95 TTFT 降幅（e-035）"],
              ["dsv2lite_slo", "79", "%", "c-model",
               "SLO 达成率提升（e-035）"],
              ["pdaf_llama4_mav", "1.81", "x", "c-model",
               "PDAF 对 Llama-4 Maverick（e-037）"],
              ["pdaf_llama4_scout", "1.77", "x", "c-model",
               "PDAF 对 Llama-4 Scout（e-037）"],
          ])

    # ---- 明确不入库的派生值（记录下来，避免以后有人以为漏了）----
    derived = HERE / "paper" / "data" / "DERIVED.md"
    derived.write_text(
        "# 派生值说明\n\n"
        "以下数值由实测值**反算**得出，未写入 `data/*.csv`。\n\n"
        "原因：`audit_paper.py` 的判据 C 要求每个 value 能在对应 claim 的\n"
        "statement 里逐字找到。派生值不在 statement 里，硬塞会被拦下——\n"
        "这个拦截是对的，它逼人区分「文献报的数」与「我算的数」。\n\n"
        "| 派生值 | 算法 | 来源 |\n|---|---|---|\n"
        f"| {kv['nvlink_gbps']:g} GB/s | 250 MB ÷ 0.6 ms | e-011 两项相除 |\n"
        f"| {kv['rdma_gbps']:g} GB/s | 250 MB ÷ 10 ms | e-011 两项相除 |\n"
        "| 100 GB/s | 800 Gbps ÷ 8 | 单位换算 |\n"
        "| 6× | 600 GB/s ÷ 100 GB/s | e-006 两项相除 |\n"
        "| 约 0.1× | RDMA 的 1/10 | **推算，非实测** |\n\n"
        "这些值出现在论文表 tab1 与图 fig2 中，并在 caption/正文标注\n"
        "「由实测反算」或「推算」。\n",
        encoding="utf-8", newline="\n")
    print("  DERIVED.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
