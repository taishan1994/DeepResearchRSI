"""生成 paper/data/*.csv 与 tables/*.csv。

这些文件是 audit_paper.py 的 C 项（数值可回溯）的被检对象：
每行一个 (value, cite)，value 必须能在该 claim 的 statement / derivation / notes
或它的任一 evidence.quote 里**逐字**找到。

⚠️ 故这里不放任何「本文自己算出来的、但没写进 claims.derivation 的数」。
   缺失的宁可删行，也不要让 C 项报 FAIL 后再去放宽判据。
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TAB = ROOT / "tables"
DATA.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)

# 字段：metric, value, unit, condition, cite
CAPACITY = [
    ("权重体积", "511", "GB", "FP8 稠密 + FP4 专家，48 分片", "c-min-4x96"),
    ("全部驻留所需显存", "614", "GB", "含 KV 与激活", "c-no-1m-on-2x96"),
    ("Engram 下放后常驻下限", "315", "GB", "区间下界", "c-min-4x96"),
    ("Engram 下放后常驻上限", "350", "GB", "区间上界", "c-min-4x96"),
    ("单卡显存", "96", "GB", "三档 SKU 相同", "c-se-spec"),
    ("全局 KV", "890", "B/token", "FP4 + CSA2", "c-kv-890-bytes"),
    ("Engram 表主机内存占用", "188.83", "GiB", "TP4 分片，ram 模式", "c-engram-188gib"),
]

BANDWIDTH = [
    ("Server Edition 带宽", "1597", "GB/s", "官方规格", "c-se-spec"),
    ("Workstation Edition 带宽", "1792", "GB/s", "官方规格", "c-se-vs-ws-bandwidth"),
]

PREFILL = [
    ("128K 冷预填", "6853", "tok/s", "SGLang 8 卡 Max-Q，chunked=2048", "c-prefill-sgl-8x"),
    ("32K 预填", "7196", "tok/s", "SGLang 8 卡 Max-Q", "c-prefill-sgl-8x"),
    ("GPU 功耗", "220", "W", "600 W 上限，128K 预填中", "c-prefill-sgl-8x"),
    ("4 卡冷预填 402K", "5065", "tok/s", "SGLang 4 卡 TP4/EP4", "c-1m-cold-5min"),
    ("4 卡冷预填 704K", "4022", "tok/s", "同上", "c-1m-cold-5min"),
    ("4 卡冷预填 906K", "3478", "tok/s", "同上", "c-1m-cold-5min"),
    ("4 卡冷预填 1.0M", "3242", "tok/s", "1,006,538 token", "c-1m-cold-5min"),
    ("1M 冷预填耗时", "310.5", "s", "同上", "c-1m-cold-5min"),
    ("前缀缓存命中预填", "325K", "tok/s", "112K 前缀，0.34 s", "c-prefill-ceiling"),
    ("vLLM 8 卡预填", "4584", "tok/s", "950K 双针，eager", "c-vllm-1m-verified"),
    ("社区 4 卡 32K 预填", "17982", "tok/s", "Max-Q 325W 超频", "c-stable-tp4-profile"),
]

DECODE = [
    ("单流散文 DSpark 开", "78.9", "tok/s", "8 卡 Max-Q", "c-decode-dspark"),
    ("单流散文 DSpark 关", "36.5", "tok/s", "同上", "c-decode-dspark"),
    ("单流结构化 DSpark 开", "120.5", "tok/s", "同上", "c-decode-dspark"),
    ("4 卡单流解码", "115.2", "tok/s", "TP4/EP4", "c-decode-tp4-conc"),
    ("4 卡 8 并发合计", "468.2", "tok/s", "4.06×", "c-decode-tp4-conc"),
    ("社区 4 卡 C1", "249.1", "tok/s", "Max-Q 325W 超频", "c-stable-tp4-profile"),
    ("社区 4 卡 C8 合计", "805.5", "tok/s", "同上", "c-stable-tp4-profile"),
    ("长上下文 4 并发合计", "29.7", "tok/s", "各 906K 上下文", "c-long-ctx-collapse"),
]

VRAM = [
    ("SGLang 4 卡 1M 配置峰值", "96.8", "GB", "97.9 GB 上限", "c-vram-ceiling"),
    ("SGLang 4 卡显存占比", "98.9", "%", "同上", "c-vram-ceiling"),
    ("EXL3 2 卡峰值", "96655", "MiB", "97,887 MiB 上限", "c-vram-ceiling"),
]

COST = [
    ("API 输出峰时", "1.2", "USD/Mtok", "deepseek-flash", "c-api-price"),
    ("API 输出谷时", "0.6", "USD/Mtok", "50% 折扣", "c-api-price"),
    ("API 缓存命中输入", "0.006", "USD/Mtok", "峰时", "c-api-price"),
    ("API 并发上限", "2500", "", "官方", "c-api-price"),
    ("盈亏平衡吞吐", "14650", "tok/s", "8×H200，$63/h", "c-selfhost-breakeven"),
]

PITFALL = [
    ("FP8 KV 块布局", "静默", "短提示全过，≥100K 暴露", "c-fp8-kv-layout-pitfall"),
    ("前缀缓存污染", "静默", "虚高 3–4 倍", "c-cache-artifact"),
    ("DP attention 单独用", "静默", "dp_size 仍为 1", "c-sgl-rejects-dp"),
    ("DeepGEMM autotune", "挂死", "首次 128K+ 批", "c-deepgemm-hang"),
    ("MXFP4 专家路径", "回退", "SM120 落到 Marlin", "c-marlin-fallback"),
]

CONFIG = [
    ("方案 A", "8×96 GB", "全精度", "SGLang TP8 或 vLLM TP8", "c-tp8-on-8x96"),
    ("方案 B", "4×96 GB", "全精度", "SGLang TP4/EP4 + Engram 下放", "c-min-4x96"),
    ("方案 C", "2×96 GB", "EXL3 3-bit", "量化旁路，KL 代价", "c-quant-quality-cost"),
]


def write_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.relative_to(ROOT)}  {len(rows)} 行")


def main() -> int:
    print("写 data/：")
    write_csv(DATA / "capacity.csv",
              ["metric", "value", "unit", "condition", "cite"], CAPACITY)
    write_csv(DATA / "bandwidth.csv",
              ["metric", "value", "unit", "condition", "cite"], BANDWIDTH)
    write_csv(DATA / "prefill.csv",
              ["metric", "value", "unit", "condition", "cite"], PREFILL)
    write_csv(DATA / "decode.csv",
              ["metric", "value", "unit", "condition", "cite"], DECODE)
    write_csv(DATA / "vram.csv",
              ["metric", "value", "unit", "condition", "cite"], VRAM)
    write_csv(DATA / "cost.csv",
              ["metric", "value", "unit", "condition", "cite"], COST)

    print("写 tables/：")
    write_csv(TAB / "tab1_capacity.csv",
              ["配置", "显存总量", "权重 511 GB", "可行", "依据"], [
                  ("1×96 GB", "96 GB", "装不下", "否", "—"),
                  ("2×96 GB", "192 GB", "装不下", "仅量化", "c-quant-quality-cost"),
                  ("4×96 GB", "384 GB", "装不下（需下放 Engram）", "是", "c-min-4x96"),
                  ("6×96 GB", "576 GB", "装得下", "否（TP 非 2 的幂）", "c-tp-power-of-2"),
                  ("8×96 GB", "768 GB", "装得下", "是", "c-tp8-on-8x96"),
              ])
    write_csv(TAB / "tab2_pitfall.csv",
              ["坑", "类型", "触发条件", "cite"], PITFALL)
    write_csv(TAB / "tab3_config.csv",
              ["方案", "卡数", "精度", "栈", "cite"], CONFIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
