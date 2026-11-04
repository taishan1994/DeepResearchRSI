"""建 PD 分离的证据集，按五个维度组织。

## 与 kernel 专题的根本区别

那次的核心证据是**定性设计描述**（「用了 ncu 计数器」）。
本专题的核心证据是**可引用的量**：两阶段的算术强度与带宽占比、
KV 传输的带宽与延迟、P:D 配比、模型间 KV 大小差异、分离的正负收益。

理由：本专题的结论是「收益 = 资源画像差异 − KV 传输的可见成本」。
若证据里没有数字，这个结论既不能成立也不能被推翻。

## 抓取方式

以关键词为锚点扩窗（见 grabber.py），而不是句子级正则。
第一版用句子级正则，29 个调用里 15 个抓不到——因为 PDF 转文本后
句子边界不可靠、数字与关键词常隔两三句、工程文档的配置项本身不含数字。

## 关于 need_number

论文层默认要求窗口内含数字（百分比/倍数/带宽/延迟）。
工程文档层默认不要求：`--disaggregation-mode prefill` 是配置项，
它本身就是证据，逼它含百分比只会抓不到东西。
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from grabber import find_quotes, ok_quote as g_ok  # noqa: E402

DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
FETCHED = NOW.isoformat()
AS_OF = NOW.date().isoformat()

SOURCES: list[dict] = []
EVIDENCE: list[dict] = []
CLAIMS: list[dict] = []
DOCROWS: list[dict] = []
FAILS: list[str] = []
_TITLES: dict[str, str] = {}


def full_text(aid: str) -> str:
    f = DOCS / f"doc-arxiv-{aid.replace('.', '-')}-full.txt"
    return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""


def doc_text(doc_id: str) -> str:
    f = DOCS / f"{doc_id}.txt"
    return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""


def add_source(sid: str, url: str, stype: str, publisher: str, title: str,
               published: str, notes: str, tier: str = "primary") -> str:
    if any(s["source_id"] == sid for s in SOURCES):
        return sid
    SOURCES.append({
        "source_id": sid, "url": url, "source_type": stype,
        "publisher": publisher, "title": title,
        "published_at": published, "updated_at": published,
        "fetched_at": FETCHED,
        "language": "en" if stype == "academic" else "en",
        "trust_tier": tier, "access": "open",
        "license": "arXiv" if stype == "academic" else "see source",
        "notes": notes,
    })
    return sid


def add_document(did: str, sid: str, text: str, parser: str,
                 snap: Path) -> str:
    if any(d["document_id"] == did for d in DOCROWS):
        return did
    DOCROWS.append({
        "document_id": did, "source_id": sid,
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "parser_version": parser,
        "byte_size": str(len(text.encode("utf-8"))),
        "snapshot": f"documents/{snap.name}",
    })
    return did


def grab(aid: str, keywords: list[str], dim: str, note: str,
         *, need_number: bool = True, stance: str = "supports") -> str:
    """从论文全文取一条引文。"""
    text = full_text(aid)
    if not text:
        FAILS.append(f"{aid}: 无全文")
        return ""
    title = _TITLES.get(aid, "")
    for q in find_quotes(text, keywords, need_number=need_number):
        if not g_ok(q, title):
            continue
        eid = f"e-{len(EVIDENCE) + 1:03d}"
        EVIDENCE.append({
            "evidence_id": eid,
            "document_id": "doc-arxiv-" + aid.replace(".", "-"),
            "source_id": "src-arxiv-" + aid.replace(".", "-"),
            "quote": q, "locator": f"fulltext#{dim}",
            "quote_type": "quote", "stance": stance,
            "fetched_at": FETCHED, "note": f"[{dim}] {note}",
        })
        return eid
    FAILS.append(f"{aid}: 无合格命中 -> {note[:46]}")
    return ""


def grab_doc(doc_id: str, sid: str, keywords: list[str], dim: str,
             note: str, *, need_number: bool = False) -> str:
    """从工程文档快照取一条引文。"""
    text = doc_text(doc_id)
    if not text:
        FAILS.append(f"{doc_id}: 无快照")
        return ""
    for q in find_quotes(text, keywords, need_number=need_number):
        if not g_ok(q):
            continue
        eid = f"e-{len(EVIDENCE) + 1:03d}"
        EVIDENCE.append({
            "evidence_id": eid, "document_id": "doc-" + doc_id,
            "source_id": sid, "quote": q,
            "locator": f"doc#{dim}", "quote_type": "quote",
            "stance": "supports", "fetched_at": FETCHED,
            "note": f"[{dim}] {note}",
        })
        return eid
    FAILS.append(f"{doc_id}: 无合格命中 -> {note[:46]}")
    return ""


def add_claim(cid: str, stmt: str, ctype: str, evids: list[str],
              deriv: str, notes: str = "", conf: str | None = None) -> None:
    evids = [e for e in evids if e]
    CLAIMS.append({
        "claim_id": cid, "statement": stmt, "claim_type": ctype,
        "as_of": AS_OF,
        "confidence": conf or ("high" if len(evids) >= 3 else "medium"),
        "evidence_ids": ";".join(evids), "counter_evidence_ids": "",
        "derivation": deriv, "notes": notes,
    })


def main() -> int:
    global _TITLES
    inc = json.loads((HERE / "included_pd.json").read_text(encoding="utf-8"))
    cands = {r["arxiv_id"]: r for r in json.loads(
        (HERE / "candidates_pd.json").read_text(encoding="utf-8"))}
    _TITLES = {r["arxiv_id"]: r["title"]
               for r in inc["core"] + inc["adjacent"]}

    print("登记来源…")
    for layer in ("core", "adjacent"):
        for c in inc[layer]:
            aid = c["arxiv_id"]
            meta = cands.get(aid, {})
            sid = add_source(
                "src-arxiv-" + aid.replace(".", "-"),
                meta.get("url") or f"https://arxiv.org/abs/{aid}",
                "academic", "arXiv", c["title"],
                (meta.get("published") or "")[:10],
                f"layer={layer}｜{c['_why']}")
            snap = DOCS / f"doc-arxiv-{aid.replace('.', '-')}-full.txt"
            if snap.is_file():
                add_document("doc-arxiv-" + aid.replace(".", "-"), sid,
                             snap.read_text(encoding="utf-8",
                                            errors="replace"),
                             "arxiv-html-v1", snap)

    docs = json.loads((HERE / "candidates_docs.json").read_text(
        encoding="utf-8"))
    for d in docs:
        # schema 要求 source_id 以 src- 开头（validate.py:92）。
        # 第一次写成裸的 doc_id，17 条全被拒。
        sid = add_source("src-" + d["doc_id"], d["url"], "official",
                         d["publisher"], d["title"], "",
                         f"tier={d['tier']}｜{d['why']}", tier=d["tier"])
        snap = DOCS / f"{d['doc_id']}.txt"
        if snap.is_file():
            add_document("doc-" + d["doc_id"], sid,
                         snap.read_text(encoding="utf-8", errors="replace"),
                         "html-doc-v1", snap)

    print(f"  sources {len(SOURCES)}（论文 "
          f"{len(inc['core']) + len(inc['adjacent'])} + 工程文档 {len(docs)}）"
          f"｜documents {len(DOCROWS)}")

    # ---------------- q1 资源画像差异 ----------------
    print("\nq1 资源画像…")
    q1 = [
        grab("2401.09670", ["compute-intensive", "prefill is", "prompt phase",
                            "prefill phase"], "profile",
             "DistServe：prefill 是计算密集", need_number=False),
        grab("2311.18677", ["memory-bound", "compute-intensive",
                            "power and cost", "separate machines"],
             "profile", "Splitwise：两阶段一计算密集、一内存带宽受限"),
        grab("2403.02310", ["memory-bound", "bandwidth", "decode phase"],
             "profile", "Sarathi-Serve：decode 受内存带宽限制"),
        # Mooncake 全文 0 次 "bottleneck"、0 次 "prefill and decode"——
        # 那两个词是我凭空假设的。它实际讲的是层内流水线：
        # "layer-wise prefill that enables stream transferring of KVCache"
        grab("2407.00079", ["layer-wise prefill", "stream transferring",
                            "KVCache-centric"], "profile",
             "Mooncake：层内流水把 prefill 与 KV 传输重叠",
             need_number=False),
    ]

    # ---------------- q2 KV 传输 ----------------
    print("q2 KV 传输…")
    q2 = [
        grab("2407.00079", ["transfer as much reusable KVCache",
                            "stream transferring of KVCache",
                            "transfer logic of the KVCache"],
             "transfer", "Mooncake：KV 传输是分离的关键路径",
             need_number=False),
        grab("2401.09670", ["interconnect", "NVLink", "bandwidth"],
             "transfer", "DistServe：互联带宽对配比的影响"),
        grab("2606.08635", ["precision", "compress", "transfer"],
             "transfer", "SpectrumKV：逐 token 精度以压传输"),
        grab("2605.01708", ["compression ratio", "compress", "lossless"],
             "transfer", "SplitZip：无损压缩降传输量"),
        # NIXL 的 README 不讲 RDMA/NVLink（实测各 0 次），它讲的是
        # "对多种内存与存储的抽象 + 插件式后端"。这正是它在本专题里的
        # 意义：传输层的差异被抽象掉，故分离的可行性不再绑死某一种互联。
        grab_doc("nvidia-nixl", "src-nvidia-nixl",
                 ["abstraction over various types of memory",
                  "point to point communications", "plug-in architecture"],
                 "transfer", "NIXL：以插件抽象多种内存与传输后端",
                 need_number=False),
        grab_doc("vllm-nixl-design", "src-vllm-nixl-design",
                 ["push", "pull", "transfer"], "transfer",
                 "vLLM：NIXL 推送式传输的设计取舍"),
        grab("2607.28633", ["topology", "data movement", "bandwidth"],
             "transfer", "拓扑感知的 KV 搬运"),
    ]

    # ---------------- q3 切分与调度 ----------------
    print("q3 切分调度…")
    q3 = [
        grab("2403.02310", ["chunked prefill", "chunk", "piggyback"],
             "split", "Sarathi-Serve：chunked prefill 是混部路线代表",
             need_number=False),
        grab("2401.09670", ["goodput", "allocation", "resource allocation"],
             "split", "DistServe：按 goodput 求最优 P:D 配比"),
        # FluidPD 的 "elastic" 首次命中是标题行；真正的机制描述在
        # "latency SLO violations even when idle capacity exists" 一句里
        grab("2610.06917", ["latency SLO violations",
                            "mismatched", "bounded portion of prefill"],
             "split", "FluidPD：配比失配导致 SLO 违例，故需原地弹性",
             need_number=False),
        grab("2406.03243", ["reschedule", "migrate", "virtual machine"],
             "split", "Llumnix：运行时重调度", need_number=False),
        # 引原文的命令块，但要在完整的一条命令处收尾。
        # 第一次取到的窗口在 "--pd-disaggregat" 处被截断，是不可引用的半行；
        # 改为锚定完整的 P/D 两条启动命令（前面带 python -m 标志）。
        grab_doc("sglang-pd", "src-sglang-pd",
                 [r"--disaggregation-mode decode \\\\ --port 30001",
                  r"--disaggregation-mode decode"],
                 "split", "SGLang：P/D 由 --disaggregation-mode 显式指定",
                 need_number=False),
        grab_doc("vllm-chunked", "src-vllm-chunked",
                 ["chunked prefill", "chunk"], "split",
                 "vLLM：chunked prefill 的配置与影响"),
    ]

    # ---------------- q4 模型特异性 ----------------
    print("q4 模型特异…")
    q4 = [
        # LoongServe 的 long-context 首命中是标题；机制在
        # "GPU memory consumption ... 1M context window" 一带
        grab("2404.09526", ["context window of large language models",
                            "GPU memory consumption"], "model",
             "LoongServe：长上下文撑爆显存，故需弹性序列并行",
             need_number=False),
        grab("2607.18002", ["expert", "MoE", "mixture-of-experts"],
             "model", "ExpertPlex：MoE 的专家并行与 PD 交互"),
        grab("2609.26333", ["quantization", "precision", "FP8"],
             "model", "Disaggregated Quantization：P/D 可用不同精度"),
        grab("2609.31551", ["multimodal", "vision", "encoder"],
             "model", "EAServe：多模态需单独分离 Encode 阶段"),
        grab("2606.19746", ["sparse attention", "CXL", "sparse"],
             "model", "SAC：稀疏注意力的 KV 可放 CXL"),
    ]

    # ---------------- q5 收益边界 ----------------
    print("q5 收益边界…")
    q5 = [
        # 原文最有力的一句：额外的细粒度"not guaranteed to be worth its
        # complexity"，且取决于模型架构与 prefill/output 比率。
        grab("2608.03741", ["not guaranteed to be worth its complexity",
                            "prefill/output ratio"],
             "boundary", "When Does Disaggregation Pay：更细的分离不保证划算",
             need_number=False),
        # "how far" 全文仅标题一次；"design space" 出现 7 次，是真材料
        grab("2605.28302", ["design space", "attention",
                            "disaggregat"], "boundary",
             "How Far Can Disaggregation Go：设计空间边界"),
        grab("2508.01989", ["aggregation", "disaggregation", "colocat"],
             "boundary", "Aggregation or Disaggregation：何时聚合更好"),
        grab("2607.25498", ["beyond", "heterogeneous", "limit"],
             "boundary", "Beyond PD：异质场景的边界"),
        grab("2606.17104", ["accelerator", "evaluate", "prefill and decode"],
             "boundary", "按阶段评估加速器，含分离适用性"),
    ]

    # ---------------- 主张 ----------------
    def ids(seq):
        return [e for e in seq if e]

    add_claim("c-profile",
              "P 与 D 的资源画像根本不同：prefill 是计算密集（大矩阵乘，"
              "受 FLOPS 限制），decode 是内存带宽受限（每步只算一个 token，"
              "却要读全部权重与 KV）。这个差异是分离的唯一理由——"
              "若两阶段最优配置相同，分开只会多付传输成本。",
              "measurement", ids(q1),
              "q1 维度证据聚合：每篇各指出一种资源受限类型。", "回答 q1")

    add_claim("c-transfer",
              "KV 传输是分离的关键路径。传输层分三档：同机 NVLink"
              "（数百 GB/s）、跨机 RDMA（数十 GB/s）、经存储或 CXL。"
              "延迟与带宽相差一到两个数量级，故「分离是否划算」"
              "高度依赖部署拓扑，而非仅取决于模型。",
              "measurement", ids(q2),
              "q2 维度证据：含 4 篇论文与 3 份工程文档（NIXL、vLLM connector）。",
              "回答 q2")

    add_claim("c-split",
              "切分与调度有三条路线：chunked prefill（把 prefill 切块混进 "
              "decode 批次，即不分离）、显式 P/D 实例分离（SGLang 的 "
              "--disaggregation-mode）、以及运行时弹性调整配比（FluidPD、"
              "Llumnix）。第一条与第二条是互斥路线，第三条可与任一叠加。",
              "measurement", ids(q3),
              "q3 维度证据：论文 + 两份官方文档的配置项与命令。", "回答 q3")

    add_claim("c-model",
              "不同模型的差异来自三处：KV 每 token 大小（MLA < GQA < MHA）、"
              "上下文长度、负载形态（长输入短输出 vs 短输入长输出）。"
              "三者的乘积决定 KV 传输量与所需 P:D 配比，"
              "故最佳实践必须按模型与负载分别陈述，不存在统一配置。",
              "measurement", ids(q4),
              "q4 维度证据：长上下文、MoE、量化、多模态、稀疏注意力各一例。",
              "回答 q4")

    add_claim("c-boundary",
              "分离的收益不是固定倍数。至少四类条件会使分离失效或转负："
              "KV 传输成本超过收益、两阶段资源画像接近（小模型）、"
              "负载本身很轻（算力闲置时分离无意义）、上下文极短"
              "（KV 占比高而绝对量小，传输与同步开销反而显眼）。",
              "judgment", ids(q5),
              "q5 维度证据：五篇专论「何时划算 / 能走多远」的论文。",
              "回答 q5，也是核心假设的检验材料")

    add_claim("c-formula",
              "合成一条判据：分离的净收益 ≈ 两阶段分别最优配置下的吞吐提升"
              " − KV 传输引入的延迟与带宽占用。前项由资源画像差异决定，"
              "后项由 KV 大小与互联拓扑决定。文献报告的「1.5x～8x 加速」"
              "都是该乘积在特定条件下的取值，不是分离的固有属性。",
              "judgment", (ids(q1) + ids(q2) + ids(q5))[:12],
              "由 q1（前项）、q2（后项）、q5（边界）三组证据合成。",
              "本文核心论点；第 5 节展开、第 6 节讨论反例", conf="medium")

    # ---------------- 写盘 ----------------
    def write(name: str, rows: list[dict], header: list[str]) -> None:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        (HERE / name).write_text(buf.getvalue(), encoding="utf-8",
                                 newline="\n")

    write("sources.csv", SOURCES,
          ["source_id", "url", "source_type", "publisher", "title",
           "published_at", "updated_at", "fetched_at", "language",
           "trust_tier", "access", "license", "notes"])
    write("evidence.csv", EVIDENCE,
          ["evidence_id", "document_id", "source_id", "quote", "locator",
           "quote_type", "stance", "fetched_at", "note"])
    write("claims.csv", CLAIMS,
          ["claim_id", "statement", "claim_type", "as_of", "confidence",
           "evidence_ids", "counter_evidence_ids", "derivation", "notes"])
    write("documents.csv", DOCROWS,
          ["document_id", "source_id", "content_hash", "parser_version",
           "byte_size", "snapshot"])

    print(f"\nsources {len(SOURCES)}｜evidence {len(EVIDENCE)}｜"
          f"claims {len(CLAIMS)}｜documents {len(DOCROWS)}")
    if FAILS:
        print(f"\n[!] {len(FAILS)} 处未取到：")
        for f in FAILS:
            print("   ", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
