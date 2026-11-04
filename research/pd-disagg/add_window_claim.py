"""第 2 轮：新增 c-window 主张，并把新数字写进已有 claim。

## 为什么新开一条 claim

第 1 轮 6 条 claim 的 `c-boundary` 只说了「分离的收益不是固定倍数，
存在使分离失效的条件」——这是定性的。本轮找到了定量测量：
收益随输入输出比是**有上下界的窗口**，且翻转集中在一个数量级内。

「存在窗口且非单调」是一条独立、可证伪的断言，不该塞进
「边界条件」那条里。故新开 `c-window`。

## 为什么必须把数字写进 statement

`audit_paper.py` 的判据 C 要求 `paper/data/*.csv` 里的每个 value
都能在对应 claim 的 statement 里逐字找到。第 1 轮踩过这个坑：
claim 写得没有数字，判据 C 只能报「提示」（数字只在 evidence 里），
等于主张无法被直接复核。

故新增的 11 个数值全部先写进 statement，再进 data/*.csv。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

NEW_CLAIM = {
    "claim_id": "c-window",
    "statement": (
        "分离的收益是输入输出比的有界窗口，不是单调函数。跨 8 个模型的"
        "模拟测量显示：I/O 为 0.01 与 1 时，不分离对每一个被测模型都最强，"
        "PD、AF、PDAF 全线低于 1.00 倍，PD 最高仅 0.89 倍；"
        "I/O=100 时 PDAF 对全部 8 个模型超过不分离，区间 1.05 至 1.92 倍，"
        "PD 对 8 个中的 7 个超过，唯一例外 DeepSeek-V4-Pro 为 0.95 倍。"
        "翻转集中在一个数量级之内：I/O=1 时 0.48 倍，I/O=10 时 2.10 倍。"
        "此后非单调：平台期 1.5 至 1.8 倍延续到 I/O=500，"
        "I/O=1000 时回落到 1.27 倍，因为 prefill 大到成为系统瓶颈后，"
        "为 decode 单独配置的硬件开始闲置。"
    ),
    "claim_type": "measurement",
    "as_of": "2026-11-04",
    "confidence": "high",
    "evidence_ids": "e-028;e-029;e-030;e-038",
    "counter_evidence_ids": "",
    "derivation": "跨 8 个模型的 NPU 设计空间模拟，扫 9 个输入输出比；"
                  "直接取原报告的三段结论与离散测点。",
    "notes": "第 2 轮新增。把「收益取决于负载」从定性升级为有形状的函数，"
             "并首次给出上界（太重也不划算）。",
}

# 补充到已有 claim 的数字
PATCH = {
    "c-model": (
        "不同模型的差异来自两个正交的轴，而不是一个「模型类别」："
        "KV 占用随注意力变体（MHA > GQA > MLA）变化，但该轴与 MoE 稀疏性"
        "正交——稀疏性完全落在 FFN 里。第一个轴决定传输字节数，"
        "第二个轴决定并行与专家放置。实测差异跨一个数量级以上："
        "Qwen3-32B 在 8K 上下文下 KV 达 GB 级，经 100 Gbps RDMA 传输需"
        "数百毫秒，与 prefill 本身相当；Llama2-7B 上 GPU 达成低 39 倍的"
        "延迟与高 41 倍的吞吐；Llama 3.3 70B 在 16 块 H100 上满足 TTFT/TPOT "
        "SLO 的同时把 prefill 能耗降 39%、decode 能耗降 48%；"
        "DeepSeek-V2-Lite 上 P95 TTFT 降 81%、SLO 达成率升 79%；"
        "SAC 在 DeepSeek-V3.2 上用 CXL 相对 RDMA 取得 2.1 倍吞吐、"
        "9.7 倍更低的 TTFT、1.8 倍更低的 TBT；MoE 场景下专家共享消除"
        "超过 95% 的重复权重；逐阶段量化的代价不对称——只量化 prefill 的"
        "精度损失是只量化 decode 的 1.1 至 4.1 倍（8 个模型中 7 个如此）。"
        "跨模型最一致的做法是四路 PDAF：在 8 个模型中的 6 个上是最佳模式，"
        "对 Llama-4 Maverick 与 Scout 分别达 1.81 倍与 1.77 倍；"
        "只拆注意力与 FFN 的 AF 在所有比例上最弱，从未超过不分离。"
    ),
    "c-boundary": (
        "分离的收益不是固定倍数，存在使分离失效或转负的条件。"
        "最直接的反例：有方案相对 PD 分离把 TTFT 降低 13.2 倍、"
        "相对 PD 聚合把 TPOT 降低 1.69 倍——分离本身不是这个维度上的"
        "最优解。另有五类条件使分离失效：KV 传输成本超过收益、"
        "两阶段资源画像接近、负载落在窗口之外（太轻或太重）、"
        "上下文极短导致固定开销主导、以及调度干扰未被消除——"
        "DeepSeek-V3.2 在 DP=16 时单条 prefill 可拖住全部 decode，"
        "空转率达 36.21% 至 59.98%。"
    ),
    "c-transfer": (
        "KV 传输是分离的关键路径，且成本可量化：DeepSeek-V3 的 250 MB "
        "KV cache 经 NVLink 传输需 0.6 ms、经 RDMA 传输需 10 ms，"
        "两者相差 16.7 倍；A100 节点内 NVLink 峰值带宽 600 GB/s，"
        "集群 InfiniBand 规格 800 Gbps（约合 100 GB/s），相差 6 倍。"
        "但这个数字不能跨模型外推：Qwen3-32B 在 8K 上下文下 KV 达 GB 级，"
        "经 100 Gbps RDMA 传输需数百毫秒，与 prefill 本身相当。"
        "故「分离是否划算」高度依赖部署拓扑与模型/上下文组合，"
        "而非仅取决于模型。"
    ),
}


def main() -> int:
    p = HERE / "claims.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    have = {r["claim_id"] for r in rows}

    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    if NEW_CLAIM["claim_id"] not in have:
        # 只填本表实际存在的字段：多一个键 DictWriter 会抛
        # ValueError: dict contains fields not in fieldnames
        row = {k: "" for k in fields}
        for k, v in NEW_CLAIM.items():
            if k in fields:
                row[k] = v
        rows.append(row)
        print(f"  + 新增 {NEW_CLAIM['claim_id']}")

    for r in rows:
        if r["claim_id"] in PATCH:
            if r["statement"] != PATCH[r["claim_id"]]:
                r["statement"] = PATCH[r["claim_id"]]
                print(f"  ~ 改写 {r['claim_id']}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"claims.csv: {len(rows)} 条")
    for r in rows:
        print(f"    {r['claim_id']:<12} {r['confidence']:<6} "
              f"{len(r['statement'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
