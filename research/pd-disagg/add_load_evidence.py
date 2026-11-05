"""补第 6 轮：负载形态。

## 这一层与前四层的区别

前四层（成本链 / 实现平面 / SLO 方向）都是**决策维度**。
负载形态不是决策维度，它是**输入**——它决定前四层的结论是否适用。

它之所以必须单列，是因为有两个数字把整个结论翻转了：

  1. **94.2% 缓存命中率**。前缀命中率一旦到这个量级，
     「省传输量」和「隐藏传输」这两类技巧的意义急剧下降——
     命中意味着根本不需要搬。
  2. **131:1 的输入输出比**。分离的前提是两阶段资源画像不同；
     但当输入是输出的 131 倍时，decode 流占比极小，
     P/D 的资源配比会极端倾斜，而「均衡」这件事几乎无从谈起。

## 数据来源纪律

三个来源，性质不同，必须分开表述：

  · Codex/SWE-bench Pro 的 610 条 trace（实测统计）
      中位 33 轮/trace，94.2% 命中率，131:1，每轮 +2242 token，
      12K->80K，轮间隔中位 5.2s / P99 81.4s
  · CXL 可行性研究（小规模实测，作者自述非性能评估）
      外部命中率 95.4-99.5%，TTFT 降 5.5x-36.6x，sharing gap 1-4%
  · Mooncake 集成（工程实测）
      3.8x 吞吐 / 46x 降 TTFT / 8.6x 降端到端，扩到 60 张 GB200

第三组的数字幅度大得多，必须注明它的对比基线是「本地 KV offload」
而非「无缓存」，否则会被误读成分离本身的收益。

## 两个必须写进去的实现细节

  · offload 粒度 256 token：非整数倍的前缀会重算尾部
  · hash 链按进程播种：PYTHONHASHSEED 未固定时跨实例查找
    会**静默全部未命中，且呈现一个看起来合理的零命中率**

第二条是「命中率不可信」的一手证据，属于测量陷阱。
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
        "source_id": "src-vllm-mooncake",
        "url": "https://vllm.ai/blog/2026-05-06-mooncake-store",
        "source_type": "official", "publisher": "vLLM / Mooncake",
        "title": "Serving Agentic Workloads at Scale with vLLM x Mooncake",
        "published_at": "2026-05-06", "updated_at": "",
        "language": "en", "trust_tier": "primary", "access": "open",
        "license": "see source",
        "notes": "tier=primary｜610 条 Codex/SWE-bench Pro trace 的"
                 "负载形态统计：94.2% 命中率、131:1 输入输出比",
    },
]

NEW_DOCS = [
    ("doc-vllm-mooncake", "src-vllm-mooncake", "vllm-mooncake.txt"),
]

# (eid, doc, anchor, span, dim, note)
SPECS = [
    ("e-086", "doc-vllm-mooncake",
     "94.2% cache hit rate", 480, "t-load",
     "agentic 负载形态：610 条 trace、中位 33 轮、94.2% 命中率、"
     "131:1 输入输出比、每轮 +2242 token、12K->80K"),

    ("e-087", "doc-vllm-mooncake",
     "3.8x higher throughput", 400, "t-load",
     "接入分布式 KV 池后：3.8x 吞吐、46x 降 TTFT、8.6x 降端到端，"
     "扩到 60 张 GB200"),

    ("e-088", "doc-vllm-mooncake",
     "A 100K-token context can occupy GBs of storage", 560, "t-load",
     "本地 offload 的两个失效条件：容量被长会话撑满并驱逐；"
     "路由为均衡迁移会话导致跨实例未命中"),

    ("e-089", "doc-arxiv-2609-10790",
     "cross-node prefix reuse reduces TTFT by 5.5", 520, "t-load",
     "CXL 可行性研究：外部命中率 95.4-99.5% 时 TTFT 降 5.5x-36.6x，"
     "sharing gap 1-4%（作者自述非性能评估）"),

    ("e-090", "doc-arxiv-2609-10790",
     "offloading has a granularity (256 tokens in our configuration)",
     420, "t-load",
     "offload 粒度 256 token：前缀非整数倍时尾部要重算"),

    ("e-091", "doc-arxiv-2609-10790",
     "every cross-instance lookup misses silently", 420, "t-load",
     "测量陷阱：hash 链按进程播种，PYTHONHASHSEED 未固定时"
     "跨实例查找静默全部未命中，且呈现一个看起来合理的零命中率"),

    ("e-092", "doc-arxiv-2609-10790",
     "the study demonstrates memory disaggregation rather than", 420,
     "t-load",
     "作者的自我限定：两副本都跑完整引擎，展示的是内存分离"
     "而非 P/D 分离，作为可行性研究而非性能评估"),
]


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()

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

    ep = HERE / "evidence.csv"
    erows = list(csv.DictReader(ep.open(encoding="utf-8", newline="")))
    ef = list(erows[0].keys())
    have_e = {r["evidence_id"] for r in erows}
    meta = {r["document_id"]: (r["snapshot"], r["source_id"]) for r in drows}
    added = 0
    for eid, did, anchor, span, dim, note in SPECS:
        if eid in have_e:
            print(f"  {eid} 已存在")
            continue
        snap, sid = meta[did]
        text = " ".join((HERE / snap).read_text(
            encoding="utf-8", errors="replace").split())
        i = text.find(" ".join(anchor.split()))
        if i < 0:
            print(f"  [!] {eid} 锚点未找到: {anchor[:44]}")
            continue
        row = {k: "" for k in ef}
        row.update({
            "evidence_id": eid, "document_id": did, "source_id": sid,
            "quote": text[i:i + span].strip(),
            "locator": f"doc#{dim}", "quote_type": "quote",
            "stance": "supports", "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        erows.append(row)
        added += 1
        print(f"  + {eid} [{dim}] {note[:50]}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ef, lineterminator="\n")
    w.writeheader()
    w.writerows(erows)
    ep.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"\nevidence.csv: {len(erows)}（新增 {added}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
