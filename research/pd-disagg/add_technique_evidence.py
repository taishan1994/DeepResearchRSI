"""为「优化技巧」一层补来源、文档、证据。

## 这一层怎么组织

用户指出第 1 轮缺的是**具体优化技巧**（举例 lplb / waterfill / tbo /
dspark），并明确「上述的只是例子」。故不能只补这四个，而要按
**技巧作用的对象**分层，让读者能自己定位新技巧。

按作用对象分四类（这是本文的组织原则，不是论文原有的分类）：

  A. 省传输量      layerwise transfer / chunk-level / KV 压缩 / 量化 /
                  prefix cache / 重算 vs 传输
  B. 让传输不可见   TBO / SBO / DBO / piggyback / 异步流水
  C. 均衡负载      Waterfill / LPLB / EPLB / 请求迁移 / 弹性配比
  D. 省 decode 步  DSpark 自适应验证 / 投机解码

分类的意义在于：**同类技巧互相替代，异类技巧可以叠加**。
这直接回答「该上哪几个」，比逐个罗列有用。

## 每条证据的来源

优先取「有一手实测数字」的材料：
  · Waterfill/LPLB -> NVIDIA+SGLang 博客，逐数据集表格
  · TBO/SBO        -> SGLang EP 官方文档
  · DBO            -> vLLM DBO 设计文档（含调度图与阈值）
  · DSpark         -> vLLM 博客（含并发扫描与限制）
  · layerwise      -> Splitwise 论文原文
  · piggyback      -> Sarathi-Serve 论文原文

## E1 纪律

每条引文都用 find 从快照里切片，不手抄。
手抄会破坏 E1（引文必须是快照原文子串）。
锚点找不到就报错，不静默跳过——静默会产生「以为补了其实没补」。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))

# ---- 新来源 ----
NEW_SOURCES = [
    {
        "source_id": "src-sglang-ep",
        "url": "https://docs.sglang.io/docs/advanced_features/expert_parallelism",
        "source_type": "official",
        "publisher": "SGLang",
        "title": "SGLang: Expert Parallelism（含 TBO / SBO 官方定义）",
        "published_at": "", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜TBO 与 SBO 的一手定义与适用条件",
    },
    {
        "source_id": "src-waterfill-lplb",
        "url": "https://github.com/bojieli/ai-infra-book/blob/"
                "b069b6971faf6c4701b57a8b025462b9f2694b8f/references/"
                "framework-history/2026-09-08/ep-reconfiguration/"
                "sglang-waterfill-lplb-2026.md",
        "source_type": "official",
        "publisher": "NVIDIA / SGLang",
        "title": "Improving DeepEP MoE Load Balance in SGLang with "
                 "Waterfill and LPLB",
        "published_at": "2026-06-26", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜Waterfill 与 LPLB 的机制、LP 形式化、"
                 "逐数据集实测表",
    },
    {
        "source_id": "src-vllm-dbo",
        "url": "https://github.com/vllm-project/vllm/blob/main/docs/design/dbo.md",
        "source_type": "official",
        "publisher": "vLLM",
        "title": "vLLM: Dual Batch Overlap (DBO) 设计文档",
        "published_at": "", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜DBO 的调度图、启动阈值、与 DP+EP 的绑定关系",
    },
    {
        "source_id": "src-vllm-dspark",
        "url": "https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification",
        "source_type": "official",
        "publisher": "vLLM",
        "title": "Adaptive Verification in vLLM: DSpark "
                 "confidence-scheduled verification",
        "published_at": "2026-08-14", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜DSpark 置信度调度验证：动机、成本模型、"
                 "并发扫描与限制",
    },
]

# ---- 新文档 ----
NEW_DOCS = [
    ("doc-sglang-ep", "src-sglang-ep", "sglang-ep.txt"),
    ("doc-waterfill-lplb", "src-waterfill-lplb", "sglang-waterfill-lplb.txt"),
    ("doc-vllm-dbo", "src-vllm-dbo", "vllm-dbo.txt"),
    ("doc-vllm-dspark", "src-vllm-dspark", "vllm-dspark.txt"),
]

# ---- 新证据 ----
# (evidence_id, doc_id, 锚点, 取多长, dimension, note)
# dimension 用技巧层自己的命名，便于后续按类聚合：
#   t-amount（省传输量）/ t-hide（让传输不可见）/ t-balance（均衡）
#   / t-steps（省 decode 步）
SPECS: list[tuple[str, str, str, int, str, str]] = [
    # ===== B. 让传输不可见 =====
    ("e-041", "doc-sglang-ep",
     "TBO splits requests into micro-batches", 430, "t-hide",
     "SGLang TBO：请求拆成 microbatch，attention 与 dispatch/combine 交错"),

    ("e-042", "doc-sglang-ep",
     "Single-Batch Overlap (SBO)", 400, "t-hide",
     "SGLang SBO：不拆 batch，在 batch 内部重叠 shared expert 与通信"),

    ("e-043", "doc-vllm-dbo",
     "The Dual Batch Overlap system works by splitting the batch", 460,
     "t-hide",
     "vLLM DBO：拆两个线程，在 FusedMoEModularKernel 的 yield 点乒乓"),

    ("e-044", "doc-vllm-dbo",
     "dbo-decode-token-threshold", 380, "t-hide",
     "vLLM DBO：低于 token 阈值时不拆，避免线程切换与小 GEMM 反拖慢"),

    ("e-045", "doc-arxiv-2311-18677",
     "At the end of each layer, we trigger an asynchronous transfer", 520,
     "t-hide",
     "Splitwise：逐层异步传输 KV，prompt 计算继续下一层"),

    ("e-046", "doc-arxiv-2311-18677",
     "For small prompt sizes, the KV-cache is small and it is unnecessary",
     420, "t-hide",
     "Splitwise：小 prompt 时逐层同步的固定开销反而不值得——"
     "技巧有适用下限"),

    # ===== A. 省传输量 =====
    ("e-047", "doc-arxiv-2401-11181",
     "Utilizing chunk-level transfer enables us to parallelize", 420,
     "t-amount",
     "chunk-level 传输：chunked prefill 与 KV 传输并行；"
     "request-level 则减少传输次数"),

    # ===== C. 均衡负载 =====
    ("e-048", "doc-waterfill-lplb",
     "**Waterfill**, a lightweight shared-expert load balancing method", 520,
     "t-balance",
     "Waterfill：把 shared expert 派到负载轻的 rank，"
     "吞吐 +1.48% 至 +4.66%"),

    ("e-049", "doc-waterfill-lplb",
     "**LPLB**, a linear-programming-based load balancer", 520, "t-balance",
     "LPLB：对冗余专家副本解 min-max 线性规划，"
     "吞吐 +0.84% 至 +7.34%"),

    ("e-050", "doc-waterfill-lplb",
     "It does not move weights and it does not change the router's logical",
     430, "t-balance",
     "LPLB 只改物理副本分配，不改 router 的逻辑 top-k，故不损精度"),

    ("e-051", "doc-waterfill-lplb",
     "A subtlety of DP-attention is that different EP ranks run different",
     520, "t-balance",
     "PD 下各 rank 跑不同 forward 模式（prefill/decode/idle），"
     "没有单个 rank 看得到全局分布——这是技巧与 PD 的关键交互"),

    ("e-052", "doc-waterfill-lplb",
     "LPLB's benefit tracks how much the live batch deviates", 560,
     "t-balance",
     "LPLB 的收益取决于在线流量偏离标定分布的程度：中规模最强"),

    ("e-053", "doc-waterfill-lplb",
     "there are no redundant replicas to rebalance", 400,
     "t-balance",
     "LPLB 在 red0（无冗余副本）时只有开销、没有收益——"
     "技巧有前置依赖"),

    # ===== D. 省 decode 步 =====
    ("e-054", "doc-vllm-dspark",
     "At batch size 1 that is a good trade", 480, "t-steps",
     "DSpark 动机：batch=1 时投机解码近乎免费，"
     "batch=256 时 draft 与真 token 抢算力"),

    ("e-055", "doc-vllm-dspark",
     "the last drafted token of a 7-token block survives less than 10%",
     460, "t-steps",
     "DSpark：7 token 块的最后一个存活率不足 10%，第一个超过 70%"),

    ("e-056", "doc-vllm-dspark",
     "instead of picking a speculation length per deployment", 420,
     "t-steps",
     "DSpark：按步决定验证多少 draft，而非按部署选固定长度"),

    ("e-057", "doc-vllm-dspark",
     "Adaptive verification stays on the edge of the Pareto curve", 420,
     "t-steps",
     "DSpark：并发 1 到 256 全程停留在 Pareto 前沿"),

    ("e-058", "doc-vllm-dspark",
     "FULL varlen decode graphs require", 420, "t-steps",
     "DSpark 的限制：需 ALWAYS 级 CUDA graph 支持，"
     "不支持 --enforce-eager / LoRA / PP"),
]


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()

    # ---- sources ----
    sp = HERE / "sources.csv"
    srows = list(csv.DictReader(sp.open(encoding="utf-8", newline="")))
    sf = list(srows[0].keys())
    have = {r["source_id"] for r in srows}
    added_s = 0
    for s in NEW_SOURCES:
        if s["source_id"] in have:
            continue
        row = {k: "" for k in sf}
        row.update(s)
        row["fetched_at"] = now
        srows.append(row)
        added_s += 1
        print(f"  + source {s['source_id']}")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=sf, lineterminator="\n")
    w.writeheader()
    w.writerows(srows)
    sp.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"sources.csv: {len(srows) - added_s} -> {len(srows)}")

    # ---- documents ----
    #
    # ⚠️ documents.csv 的字段是
    #     document_id / source_id / content_hash / parser_version /
    #     byte_size / snapshot
    # 第一版按直觉写了 fetched_at 与 bytes，DictWriter 直接抛
    # `dict contains fields not in fieldnames`。
    #
    # content_hash 必须真实计算：不变量 D1 要求
    # 「一个 document_id 对应一个 content_hash」，且 E1 用它定位快照。
    # 不能留空、不能编。
    import hashlib

    dp = HERE / "documents.csv"
    drows = list(csv.DictReader(dp.open(encoding="utf-8", newline="")))
    df = list(drows[0].keys())
    have_d = {r["document_id"] for r in drows}
    added_d = 0
    for did, sid, snap in NEW_DOCS:
        if did in have_d:
            print(f"  {did} 已存在，跳过")
            continue
        p = DOCS / snap
        if not p.is_file():
            print(f"  [!] 快照不存在 {snap}")
            continue
        raw = p.read_bytes()
        row = {k: "" for k in df}
        row.update({
            "document_id": did,
            "source_id": sid,
            "content_hash": hashlib.sha1(raw).hexdigest(),
            "parser_version": "html-doc-v1",
            "byte_size": str(len(raw)),
            "snapshot": f"documents/{snap}",
        })
        drows.append(row)
        added_d += 1
        print(f"  + document {did} ({len(raw):,} 字节)")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=df, lineterminator="\n")
    w.writeheader()
    w.writerows(drows)
    dp.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"documents.csv: {len(drows) - added_d} -> {len(drows)}")

    # ---- evidence ----
    docs = {r["document_id"]: r["snapshot"] for r in drows}
    srcs = {r["source_id"] for r in srows}
    ep = HERE / "evidence.csv"
    erows = list(csv.DictReader(ep.open(encoding="utf-8", newline="")))
    ef = list(erows[0].keys())
    have_e = {r["evidence_id"] for r in erows}
    added_e = 0

    for eid, did, anchor, span, dim, note in SPECS:
        if eid in have_e:
            print(f"  {eid} 已存在，跳过")
            continue
        snap = docs.get(did)
        if not snap:
            print(f"  [!] {eid}: 无 document {did}")
            continue
        p = HERE / snap
        if not p.is_file():
            print(f"  [!] {eid}: 快照不存在 {snap}")
            continue
        text = " ".join(p.read_text(encoding="utf-8",
                                     errors="replace").split())
        i = text.find(" ".join(anchor.split()))
        if i < 0:
            print(f"  [!] {eid}: 锚点未找到 -> {anchor[:44]}")
            continue
        quote = text[i:i + span].strip()

        # 找该 document 对应的 source
        drow = [r for r in drows if r["document_id"] == did][0]
        sid = drow["source_id"]
        if sid not in srcs:
            print(f"  [!] {eid}: source {sid} 不存在")
            continue

        row = {k: "" for k in ef}
        row.update({
            "evidence_id": eid,
            "document_id": did,
            "source_id": sid,
            "quote": quote,
            "locator": f"doc#{dim}",
            "quote_type": "quote",
            "stance": "supports",
            "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        erows.append(row)
        added_e += 1
        print(f"  + {eid} [{dim}] {len(quote)} 字符  {note[:40]}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ef, lineterminator="\n")
    w.writeheader()
    w.writerows(erows)
    ep.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"\nevidence.csv: {len(erows) - added_e} -> {len(erows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
