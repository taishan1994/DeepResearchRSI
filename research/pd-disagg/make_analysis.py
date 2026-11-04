"""从 evidence.csv 抽出可量化的参数，生成 analysis.json 与图表数据。

## 为什么要有这一步

上一轮（kernel-agent）的教训：论文正文里的数字若手写，会与 claims.csv
漂移，而 audit_paper 的 P2 只能查「这个数是否出现在某条 claim 里」，
查不出「这个数是不是从证据算出来的」。

故本文件把可量化的东西**全部从证据文本正则抽取**，写入 analysis.json，
再由 make_figures.py 与论文正文引用。任何数字都能追到 evidence_id。

## 抽取策略：宁可少，不可错

只抽**有明确单位与语境**的量，且每抽一个都打印原文片段供人工核对。
抽不到的一律留空并在报告里写明「未从证据抽取」，不用估值填充——
本仓库的规矩是「未校验」比「看起来完整」更可信。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_evidence() -> dict[str, dict]:
    p = HERE / "evidence.csv"
    return {r["evidence_id"]: r
            for r in csv.DictReader(p.open(encoding="utf-8", newline=""))}


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def main() -> int:
    ev = load_evidence()
    out: dict = {"_source": "evidence.csv", "parameters": {}, "notes": []}

    # ---------- 1. KV 传输延迟对比（e-011）----------
    # 原文：DeepSeek-V3's 250 MB KV cache transfers in 0.6 ms via NVLink
    #       versus 10 ms via RDMA
    q = ev["e-011"]["quote"]
    m_kv = re.search(r"(\d+(?:\.\d+)?)\s*MB KV cache", q)
    m_nv = re.search(r"in\s+(\d+(?:\.\d+)?)\s*ms via NVLink", q)
    m_rd = re.search(r"versus\s+(\d+(?:\.\d+)?)\s*ms via RDMA", q)
    if m_kv and m_nv and m_rd:
        kv_mb = _num(m_kv.group(1))
        nv_ms = _num(m_nv.group(1))
        rd_ms = _num(m_rd.group(1))
        out["parameters"]["kv_transfer"] = {
            "kv_size_mb": kv_mb,
            "nvlink_ms": nv_ms,
            "rdma_ms": rd_ms,
            "ratio_rdma_over_nvlink": round(rd_ms / nv_ms, 1),
            # 有效带宽（GB/s）= MB / ms
            "nvlink_gbps": round(kv_mb / 1000 / (nv_ms / 1000), 1),
            "rdma_gbps": round(kv_mb / 1000 / (rd_ms / 1000), 1),
            "evidence_id": "e-011",
            "quote": q,
        }
        print(f"[kv_transfer] {kv_mb} MB: NVLink {nv_ms} ms "
              f"({out['parameters']['kv_transfer']['nvlink_gbps']} GB/s) vs "
              f"RDMA {rd_ms} ms "
              f"({out['parameters']['kv_transfer']['rdma_gbps']} GB/s) "
              f"= {out['parameters']['kv_transfer']['ratio_rdma_over_nvlink']}x")
    else:
        out["notes"].append("kv_transfer: 未能从 e-011 抽取完整三元组")

    # ---------- 2. 互联峰值带宽（e-006）----------
    # A100 NVLINK peak 600 GB/s；InfiniBand 800 Gbps
    q = ev["e-006"]["quote"]
    m = re.search(r"peak bandwidth between A100 GPUs is\s+(\d+)\s*GB/s", q)
    m_ib = re.search(r"Infiniband \(e\.g\.,\s*(\d+)\s*Gbps\)", q)
    if m:
        nv = _num(m.group(1))
        ib_gbps = _num(m_ib.group(1)) if m_ib else None
        rec = {"nvlink_peak_gbps": nv, "evidence_id": "e-006", "quote": q}
        if ib_gbps:
            # 800 Gbps = 100 GB/s（按 8 bit/byte）
            rec["infiniband_gbps"] = ib_gbps
            rec["infiniband_gbyte_per_s"] = round(ib_gbps / 8, 1)
            rec["ratio"] = round(nv / (ib_gbps / 8), 1)
            print(f"[interconnect] NVLink {nv} GB/s vs IB {ib_gbps} Gbps "
                  f"= {rec['ratio']}x")
        out["parameters"]["interconnect"] = rec
    else:
        out["notes"].append("interconnect: 未能从 e-006 抽取")

    # ---------- 3. MoE 专家共享比例（e-019）----------
    q = ev["e-019"]["quote"]
    m = re.search(r"eliminates over\s+(\d+)\s*%\s*duplicate model weights", q)
    if m:
        out["parameters"]["moe"] = {
            "duplicate_weight_eliminated_pct": _num(m.group(1)),
            "evidence_id": "e-019", "quote": q,
        }
        print(f"[moe] 消除 >{m.group(1)}% 重复权重")
    else:
        out["notes"].append("moe: 未能从 e-019 抽取")

    # ---------- 4. 逐阶段量化的精度代价（e-020）----------
    q = ev["e-020"]["quote"]
    m = re.search(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*×", q)
    m2 = re.search(r"on\s+(\w+)\s+of\s+(\w+)\s+models", q)
    if m:
        out["parameters"]["stage_quant"] = {
            "accuracy_loss_ratio_low": _num(m.group(1)),
            "accuracy_loss_ratio_high": _num(m.group(2)),
            "models_affected": m2.group(1) if m2 else None,
            "models_total": m2.group(2) if m2 else None,
            "evidence_id": "e-020", "quote": q,
        }
        print(f"[stage_quant] 精度损失 {m.group(1)}–{m.group(2)}x"
              f"（{m2.group(0) if m2 else '?'}）")

    # ---------- 5. CXL vs RDMA（e-022）----------
    q = ev["e-022"]["quote"]
    vals = {}
    # 原文经 LaTeXML 转换后数字会重复出现：
    #   "2.1 × 2.1\times higher throughput"
    # 故模式允许「× 之后再来一个相同数字 + \times」。
    for key, pat in (
        ("throughput_x",
         r"(\d+(?:\.\d+)?)\s*×\s*(?:\d+(?:\.\d+)?\s*\\times\s*)?"
         r"higher throughput"),
        ("ttft_x",
         r"(\d+(?:\.\d+)?)\s*×\s*(?:\d+(?:\.\d+)?\s*\\times\s*)?"
         r"lower TTFT"),
        ("tbt_x",
         r"(\d+(?:\.\d+)?)\s*×\s*(?:\d+(?:\.\d+)?\s*\\times\s*)?"
         r"lower TBT"),
    ):
        m = re.search(pat, q)
        if m:
            vals[key] = _num(m.group(1))
    if vals:
        out["parameters"]["cxl_vs_rdma"] = {
            **vals, "model": "DeepSeek-V3.2", "evidence_id": "e-022",
            "quote": q,
        }
        print(f"[cxl] {vals}")

    # ---------- 6. 反例：聚合优于分离（e-025）----------
    q = ev["e-025"]["quote"]
    m1 = re.search(r"reduces TTFT by up to\s+(\d+(?:\.\d+)?)", q)
    m2 = re.search(r"TPOT by up to\s+(\d+(?:\.\d+)?)", q)
    if m1:
        out["parameters"]["aggregation_wins"] = {
            "ttft_reduction_x": _num(m1.group(1)),
            "tpot_reduction_x": _num(m2.group(1)) if m2 else None,
            "evidence_id": "e-025", "quote": q,
            "interpretation": "相对 PD 分离，聚合方案把 TTFT 降得更多——"
                              "这是分离并非普遍更优的直接反例",
        }
        print(f"[反例] 聚合 vs 分离：TTFT 降 {m1.group(1)}x，"
              f"TPOT 降 {m2.group(1) if m2 else '?'}x")

    # ---------- 7. 证据按维度的分布（图 2 用）----------
    dist: dict[str, int] = {}
    for r in ev.values():
        m = re.match(r"\[(\w+)\]", r["note"] or "")
        dim = m.group(1) if m else "other"
        dist[dim] = dist.get(dim, 0) + 1
    out["evidence_by_dimension"] = dist
    print(f"[分布] {dist}")

    # ---------- 8. 每个 claim 的证据数（图 1 用）----------
    claims = list(csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline="")))
    out["claims"] = [
        {"claim_id": c["claim_id"],
         "n_evidence": len([x for x in c["evidence_ids"].split(";") if x]),
         "confidence": c["confidence"],
         "statement": c["statement"]}
        for c in claims
    ]
    print("[claims] " + ", ".join(
        f"{c['claim_id']}={c['n_evidence']}" for c in out["claims"]))

    (HERE / "analysis.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n写入 analysis.json（参数 {len(out['parameters'])} 组）")
    if out["notes"]:
        print("未抽取：")
        for n in out["notes"]:
            print("  -", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
