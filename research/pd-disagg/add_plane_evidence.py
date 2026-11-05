"""补「四类之外」的证据：三平面与五个新维度。

## 分类怎么处理

原来的 ABCD 不算错，但它的维度是「**作用于 KV 传输成本的哪个环节**」，
只覆盖分离带来的额外成本。真实生产栈按**实现平面**组织，
覆盖面更广。

两者互补：
  · ABCD 回答「分离的那笔账怎么省」
  · 三平面回答「整个服务栈有哪几层可以动」

论文里保留 ABCD，但明确它的边界，并补三平面作为上位的组织框架。
这比推翻重写诚实——ABCD 的分类依据是站得住的，只是不完备。

## 坐标系：三平面 × 五个新维度

  数据面：KV 池分层、session-aware retention、packed layout
  执行面：并行策略选择、kernel/融合、执行模式（CUDA graph/async）
  控制面：调度顺序（长 prefill 上限、prefill 节拍）、路由（粘性 vs 均衡）、
          准入、P/D 配比

## 三个反例必须进证据

它们比正面技巧更有信息量，且直接反驳我论文里的假设：
  1. PP 不适合热轮次（bubble 吃掉收益）
  2. DCP 对 DeepSeek V4 只是打平 DEP（架构决定并行策略）
  3. 负载均衡劣于 session 粘性路由（局部性 > 均衡）
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))

NEW_SOURCES = [
    {
        "source_id": "src-vllm-largescale",
        "url": "https://vllm.ai/blog/2025-12-17-large-scale-serving",
        "source_type": "official", "publisher": "vLLM",
        "title": "vLLM Large Scale Serving: DeepSeek @ 2.2k tok/s/H200 "
                 "with Wide-EP",
        "published_at": "2025-12-17", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜列出九项关键优化，其中六项属 kernel/"
                 "执行模式/physical 层，超出传输成本视角",
    },
    {
        "source_id": "src-vllm-agentx",
        "url": "https://vllm.ai/blog/2026-09-08-vllm-agentx",
        "source_type": "official", "publisher": "vLLM / Inferact",
        "title": "vLLM x AgentX: Optimizing for Real-World Agentic Serving",
        "published_at": "2026-09-08", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜三平面框架，含三条 bitter lessons"
                 "（PP 不适配热轮次、DCP 不迁移、均衡劣于粘性）",
    },
    {
        "source_id": "src-pytorch-dsv4",
        "url": "https://pytorch.org/blog/serving-deepseek-v4-on-gb300-"
               "with-sglang-5x-higher-throughput-at-the-same-"
               "interactivity-since-day-0/",
        "source_type": "official", "publisher": "PyTorch / SGLang",
        "title": "Serving DeepSeek-V4 on GB300 with SGLang",
        "published_at": "2026", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜GB300 上的 kernel 与并行优化实测",
    },
]

NEW_DOCS = [
    ("doc-vllm-largescale", "src-vllm-largescale", "vllm-large-scale.txt"),
    ("doc-vllm-agentx", "src-vllm-agentx", "vllm-agentx.txt"),
    ("doc-pytorch-dsv4", "src-pytorch-dsv4", "pytorch-dsv4-gb300.txt"),
]

# (eid, doc, anchor, span, dim, note)
SPECS = [
    # ---------- 执行面：kernel 与算子融合 ----------
    ("e-063", "doc-vllm-largescale",
     "kernel improvements (silu-mul-quant fusion", 460, "t-kernel",
     "吞吐 1.5k -> 2.2k tok/s/H200 归因于 kernel 改进（SiLU 融合、"
     "Cutlass QKV）+ DBO"),

    ("e-064", "doc-vllm-agentx",
     "GEMM and reduce-scatter fusion", 420, "t-kernel",
     "Kimi K3：GEMM 与 reduce-scatter 融合改善序列并行通信"),

    ("e-065", "doc-vllm-agentx",
     "latent-tail MoE fusion", 340, "t-kernel",
     "Kimi K3：latent-tail MoE 融合把端到端延迟降约 5%"),

    ("e-066", "doc-vllm-agentx",
     "cutting latency by about 13% per layer", 420, "t-kernel",
     "对称内存 + kernel 内融合替代 NCCL all-gather 与 all-to-all，"
     "每层延迟降约 13%"),

    ("e-067", "doc-vllm-agentx",
     "CuteDSL long-context indexer", 380, "t-kernel",
     "MiniMax M3：长上下文 indexer 的 GB300 延迟改善约 3%-31%"),

    # ---------- 执行面：并行策略 ----------
    ("e-068", "doc-vllm-agentx",
     "PCP8 achieves a 2.65", 420, "t-parallel",
     "DeepSeek V4：32K prompt 上 PCP8 相对 TP8 的 prefill 加速 2.65x"),

    ("e-069", "doc-vllm-agentx",
     "DCP offers two benefits for agentic workloads", 460, "t-parallel",
     "Kimi K3：DCP 沿序列切 KV，降 decode 延迟并扩大 KV 容量"),

    ("e-070", "doc-vllm-agentx",
     "Pipeline parallelism (PP) does not fit warm agentic turns", 560,
     "t-parallel",
     "反例：PP 不适合预热轮次——新增 token 太少，流水线 bubble 吃掉收益"),

    ("e-071", "doc-vllm-agentx",
     "DCP only matched DEP rather than surpassing it", 460, "t-parallel",
     "反例：DCP 对 DeepSeek V4 只打平 DEP，架构决定并行策略"),

    # ---------- 数据面：KV 池与分层 ----------
    ("e-072", "doc-vllm-agentx",
     "hierarchical tiers for the distributed KV cache pool", 480,
     "t-kvpool",
     "KV 池分层：用磁盘与纯 CPU 节点扩容量，standalone-store 模式"),

    ("e-073", "doc-vllm-agentx",
     "packed KV cache layout", 460, "t-kvpool",
     "打包 KV 布局替代 92 个碎片化 tensor，减少描述符与 P/D 传输开销"),

    ("e-074", "doc-vllm-agentx",
     "Session-aware prefix-cache retention", 460, "t-kvpool",
     "session 感知的前缀保留：按间隔保留 + 二次观测时保留检查点"),

    # ---------- 控制面：调度顺序 ----------
    ("e-075", "doc-vllm-agentx",
     "long-prefill-token-threshold", 560, "t-sched",
     "长 prefill 每步 token 上限：TPGS 提升最多 93%、P90 交互性约 2.3x"),

    ("e-076", "doc-vllm-agentx",
     "prefill-schedule-interval", 520, "t-sched",
     "prefill 节拍对齐：只每隔 N 步接纳 prefill，其余步纯 decode"),

    # ---------- 控制面：路由（含反例） ----------
    ("e-077", "doc-vllm-agentx",
     "all of these policies underperformed simple session-aware sticky",
     560, "t-route",
     "反例：按队列深度/运行 token/KV 利用率均衡，全部劣于 session 粘性路由"),

    ("e-078", "doc-vllm-agentx",
     "The transfer is asynchronous and overlaps with computation",
     480, "t-route",
     "粘性胜出的机制：迁移要取 KV，预取块占容量，导致「更均衡但并发更少」"),
]


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()

    # sources
    sp = HERE / "sources.csv"
    srows = list(csv.DictReader(sp.open(encoding="utf-8", newline="")))
    sf = list(srows[0].keys())
    have = {r["source_id"] for r in srows}
    for s in NEW_SOURCES:
        if s["source_id"] in have:
            continue
        row = {k: "" for k in sf}
        row.update(s)
        row["fetched_at"] = now
        srows.append(row)
        print(f"  + source {s['source_id']}")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=sf, lineterminator="\n")
    w.writeheader()
    w.writerows(srows)
    sp.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"sources.csv: {len(srows)}")

    # documents
    dp = HERE / "documents.csv"
    drows = list(csv.DictReader(dp.open(encoding="utf-8", newline="")))
    df = list(drows[0].keys())
    have_d = {r["document_id"] for r in drows}
    for did, sid, snap in NEW_DOCS:
        if did in have_d:
            continue
        p = DOCS / snap
        if not p.is_file():
            print(f"  [!] 缺快照 {snap}")
            continue
        raw = p.read_bytes()
        row = {k: "" for k in df}
        row.update({
            "document_id": did, "source_id": sid,
            "content_hash": hashlib.sha1(raw).hexdigest(),
            "parser_version": "html-doc-v1",
            "byte_size": str(len(raw)),
            "snapshot": f"documents/{snap}",
        })
        drows.append(row)
        print(f"  + document {did} ({len(raw):,} 字节)")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=df, lineterminator="\n")
    w.writeheader()
    w.writerows(drows)
    dp.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"documents.csv: {len(drows)}")

    # evidence
    ep = HERE / "evidence.csv"
    erows = list(csv.DictReader(ep.open(encoding="utf-8", newline="")))
    ef = list(erows[0].keys())
    have_e = {r["evidence_id"] for r in erows}
    docs = {r["document_id"]: r["snapshot"] for r in drows}
    sid_of = {r["document_id"]: r["source_id"] for r in drows}
    added = 0
    for eid, did, anchor, span, dim, note in SPECS:
        if eid in have_e:
            print(f"  {eid} 已存在")
            continue
        p = HERE / docs[did]
        text = " ".join(p.read_text(encoding="utf-8",
                                    errors="replace").split())
        i = text.find(" ".join(anchor.split()))
        if i < 0:
            print(f"  [!] {eid} 锚点未找到: {anchor[:44]}")
            continue
        row = {k: "" for k in ef}
        row.update({
            "evidence_id": eid, "document_id": did,
            "source_id": sid_of[did],
            "quote": text[i:i + span].strip(),
            "locator": f"doc#{dim}", "quote_type": "quote",
            "stance": "supports", "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        erows.append(row)
        added += 1
        print(f"  + {eid} [{dim}] {note[:44]}")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ef, lineterminator="\n")
    w.writeheader()
    w.writerows(erows)
    ep.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"\nevidence.csv: {len(erows)}（新增 {added}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
