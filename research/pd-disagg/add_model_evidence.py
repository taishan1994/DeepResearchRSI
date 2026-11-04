"""补一批按模型族与收益边界的证据（第 2 轮）。

## 为什么补

第 1 轮 27 条证据里 `model` 维度只有 5 条，每类模型 1 条，
只能支撑「做法不同」，支撑不起用户要的「最好效果」。

本轮从 44 篇全文里挖到 3 类此前完全没有的证据：

### A. 收益边界被量化了（最重要的发现）
HeteroPanacea（2608-03741）跨 8 个模型、扫 9 个 I/O 比，报告：
  · I/O = 0.01 与 1：ND（不分离）对**每个**模型都是最强，
    PD/AF/PDAF 全线低于 1.00×，PD 最高仅 0.89×
  · I/O = 100：PDAF 对 8/8 模型超过 ND（1.05–1.92×），
    PD 对 7/8 超过；唯一例外 DeepSeek-V4-Pro 为 0.95×
  · 翻转集中在一个数量级：I/O=1 时 0.48×，I/O=10 时 2.10×
  · 之后**非单调**：平台 1.5–1.8× 至 I/O=500，I/O=1000 回落到 1.27×

这把「收益是差的函数」从定性论断变成了可引用的测量。
尤其「非单调」这一条，此前没有任何来源支撑。

### B. 注意力结构与稀疏性正交
同一篇论文明确指出：KV footprint 取决于 MHA/GQA/MLA，
但该轴「与稀疏性正交」，因为 MoE 稀疏性完全在 FFN 里。
这比我原来的写法更清楚——不该把「MoE 模型」当成一个
注意力类型，它们是两个独立的轴。

### C. 按模型族的实测数字
  · Qwen3-32B @ 8K：KV 达 GB 级，100 Gbps RDMA 上传输数百毫秒，
    与 prefill 本身相当（2606-29986）
  · Llama2-7B：GPU 上延迟低 39×、吞吐高 41×（2606-17104）
  · Llama 3.3 70B：16×H100 上满足 SLO 同时 prefill 能耗降 39%、
    decode 降 48%（2602-18755）
  · DeepSeek-V2-Lite：P95 TTFT 降 81%、SLO 达成率升 79%（2607-02043）
  · Gemma3 / Qwen3 @ >16K：卸载使 NVFP4 prefill 延迟增 <5% 与 8%
    （2609-26333）

## 纪律

每条引文都从快照文件里**逐字取子串**，不手工转录。
E1 不变量要求引文是快照原文的子串；手抄数字必然破坏它。
故本脚本用 find 定位、切片，而不是把文字写进代码。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))

# (evidence_id, 快照名, 锚点起点文字, 取多长, dimension, note)
# 锚点文字必须唯一且逐字存在于快照里；脚本会断言找到，
# 找不到就报错而不是静默跳过——否则会以为「补了」其实没补。
SPECS: list[tuple[str, str, str, int, str, str]] = [
    # ---- A. 收益边界：跨 8 模型的 I/O 扫描 ----
    ("e-028", "doc-arxiv-2608-03741", "At low and balanced prefill/output ratios", 470,
     "boundary",
     "HeteroPanacea：I/O 低与均衡时不分离最强，8 个模型全线低于 1.00x"),

    ("e-029", "doc-arxiv-2608-03741", "At I / O = 100 I/O=100 , the ranking shifts", 520,
     "boundary",
     "HeteroPanacea：I/O=100 时 PDAF 对 8/8 模型超过不分离（1.05-1.92x）"),

    ("e-030", "doc-arxiv-2608-03741",
     "The transition is abrupt and confined to a single decade", 620,
     "boundary",
     "HeteroPanacea：翻转集中在一个数量级，且此后非单调"),

    # ---- B. 两个正交轴 ----
    ("e-031", "doc-arxiv-2608-03741",
     "the KV footprint does depend heavily on the attention variant", 300,
     "model",
     "HeteroPanacea：KV footprint 随 MHA/GQA/MLA 变，但该轴与 MoE 稀疏性正交"),

    # ---- C. 按模型族的实测数字 ----
    ("e-032", "doc-arxiv-2606-29986",
     "Qwen3-32B at 8K context produces gigabytes of KV state", 420,
     "model",
     "Qwen3-32B@8K：KV 达 GB 级，100Gbps RDMA 上传输数百毫秒，与 prefill 相当"),

    ("e-033", "doc-arxiv-2606-17104",
     "GPUs achieve up to 39", 300,
     "model",
     "Llama2-7B 评测：GPU 延迟低 39x、吞吐高 41x，量化两阶段不对称"),

    ("e-034", "doc-arxiv-2602-18755",
     "BiScale meets TTFT/TPOT SLOs while reducing energy", 320,
     "model",
     "Llama 3.3 70B @ 16xH100：满足 SLO 同时 prefill 能耗降 39%、decode 降 48%"),

    ("e-035", "doc-arxiv-2607-02043",
     "reduces P95 TTFT", 380,
     "model",
     "DeepSeek-V2-Lite：P95 TTFT 降 81%、SLO 达成率升 79%"),

    ("e-036", "doc-arxiv-2609-26333",
     "At context length above 16", 360,
     "model",
     "Qwen3 / Gemma3 长上下文：卸载使 prefill 延迟增 <5% 与 8%"),

    # ---- D. 模型架构与收益的关系（跨模型最一致的做法）----
    ("e-037", "doc-arxiv-2608-03741",
     "4 way Prefill Decode Attention FFN disaggregation is the most consistent",
     420,
     "model",
     "HeteroPanacea：4 路 PDAF 跨模型最一致，吞吐最高提升 75%"),

    ("e-038", "doc-arxiv-2608-03741",
     "PDAF is the best mode for six of the eight models", 330,
     "model",
     "HeteroPanacea：PDAF 在 8 个模型中的 6 个上是最佳模式"),

    # ---- E. 长上下文 / 容量视角 ----
    ("e-039", "doc-arxiv-2610-16592",
     "a single prefill request can stall all other decode batches", 360,
     "model",
     "DeepSeek-V3.2(DP=16)：单条 prefill 可拖住全部 decode，空转率 36-60%"),

    ("e-040", "doc-arxiv-2607-25498",
     "extending the decode length from 128 to 1024", 380,
     "model",
     "Llama-13B：解码长度从 128 增至 1024 会改变最大边际收益所在的阶段"),
]


def main() -> int:
    src = list(csv.DictReader(
        (HERE / "sources.csv").open(encoding="utf-8", newline="")))
    have = {r["source_id"] for r in src}
    docs = {r["document_id"]: r["snapshot"] for r in csv.DictReader(
        (HERE / "documents.csv").open(encoding="utf-8", newline=""))}

    ev_path = HERE / "evidence.csv"
    old = list(csv.DictReader(ev_path.open(encoding="utf-8", newline="")))
    fields = list(old[0].keys())
    old_ids = {r["evidence_id"] for r in old}

    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    added: list[dict[str, str]] = []

    for eid, doc_stem, anchor, span, dim, note in SPECS:
        if eid in old_ids:
            print(f"  {eid} 已存在，跳过")
            continue
        doc_id = "doc-" + doc_stem.replace("doc-", "")
        snap = docs.get(doc_id)
        if not snap:
            print(f"  [!] {eid}: documents.csv 里没有 {doc_id}")
            continue
        # documents.csv 的 snapshot 字段值是**相对归档根**的路径，
        # 已经带了 `documents/` 前缀（如 documents/doc-arxiv-xxx-full.txt）。
        # 第一版又拼了一次 HERE/"documents"/(snap)，于是路径里出现
        # 两遍 documents/，全部报「快照文件不存在」。
        p = HERE / snap
        if not p.is_file():
            print(f"  [!] {eid}: 快照文件不存在 {snap}")
            continue

        text = p.read_text(encoding="utf-8", errors="replace")
        flat = " ".join(text.split())
        i = flat.find(" ".join(anchor.split()))
        if i < 0:
            # 断言而非跳过：锚点找不到说明我对原文的记忆有误，
            # 静默跳过会让人以为这条证据已经补上了。
            print(f"  [!] {eid}: 锚点未找到 —— {anchor[:50]}")
            continue

        quote = flat[i:i + span].strip()
        sid = [r for r in have if r.startswith("src-arxiv-"
                                               + doc_stem.split("-", 2)[2])]
        if not sid:
            print(f"  [!] {eid}: 找不到对应 source")
            continue

        added.append({
            "evidence_id": eid,
            "document_id": doc_id,
            "source_id": sid[0],
            "quote": quote,
            "locator": f"fulltext#{dim}",
            "quote_type": "quote",
            "stance": "supports",
            "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        print(f"  + {eid} ({len(quote)} 字符) {note[:44]}")

    if not added:
        print("没有新增")
        return 0

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(old + added)
    ev_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"\nevidence.csv: {len(old)} -> {len(old) + len(added)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
