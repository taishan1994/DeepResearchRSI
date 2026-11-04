"""检索 PD 分离相关来源：arXiv 论文 + 关键工程文档。

## 为什么需要两条线

PD 分离与多数研究课题不同：**最佳实践常常先出现在工程实现里**，
后才有论文。例如 chunked prefill 的默认开启、KV 传输库的选型、
P:D 配比的调参经验，都来自 vLLM / SGLang / TensorRT-LLM 的文档与博客。

只检索 arXiv 会得到一个漂亮的分类学，但答不出「该配多少张卡」。

故本脚本分两部分：
  A. arXiv 检索（论文层）
  B. 工程文档登记（实现层）—— URL 手列，因为它们是已知的少数几个

## B 部分的取舍

不穷举，只收**同时满足**两条的：
  1. 该项目的官方文档/博客（一手）
  2. 明确讲 P/D 分离机制或配置

第三方复述（媒体、教程站）只在其包含实测数据时才收，单独标 tier=secondary。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "providers" / "python"))

from deepresearchrsi_providers.arxiv import ArxivProvider  # noqa: E402

HERE = Path(__file__).resolve().parent

# ---- A. arXiv 检索式 ----
# 从「分离」这件事的各个技术面出发，而不是搜 "PD disaggregation" 一词，
# 因为很多论文用 "disaggregated prefill" / "splitwise" / "phase splitting"。
QUERIES = [
    'all:"disaggregated prefill"',
    'all:"prefill-decode disaggregation"',
    'all:"prefill decode disaggregation"',
    'all:"splitwise" AND all:"inference"',
    'all:"phase splitting" AND all:"LLM inference"',
    'all:"KV cache" AND all:"transfer" AND all:"disaggregat"',
    'all:"chunked prefill"',
    'all:"distributed LLM serving" AND all:"prefill"',
    'all:"goodput" AND all:"LLM serving"',
    'all:"LLM serving" AND all:"SLO" AND all:"scheduling"',
    'all:"KV cache" AND all:"RDMA" AND all:"inference"',
    'all:"attention" AND all:"decode" AND all:"memory bandwidth" AND all:"serving"',
]

# ---- B. 工程文档（一手） ----
# 字段：id, title, url, publisher, tier, why
DOCS = [
    # vLLM
    ("vllm-disagg", "vLLM: Disaggregated Prefilling (experimental)",
     "https://docs.vllm.ai/en/latest/features/disagg_prefill.html",
     "vLLM", "primary", "官方分离式预填充文档，含 KV 连接器与示例"),
    ("vllm-kvconn", "vLLM: KV Transfer Config / Connector 接口",
     "https://docs.vllm.ai/en/latest/api/vllm/config/kv_transfer.html",
     "vLLM", "primary", "KV 传输配置项的权威定义"),
    ("vllm-nixl", "vLLM: NIXL KV Connector",
     "https://docs.vllm.ai/en/latest/features/nixl_connector.html",
     "vLLM", "primary", "NIXL 作为生产级 KV 传输后端"),
    ("vllm-chunked", "vLLM: Optimization — Chunked Prefill",
     "https://docs.vllm.ai/en/latest/configuration/optimization.html",
     "vLLM", "primary", "chunked prefill 的开关与影响"),
    # SGLang
    ("sglang-pd", "SGLang: PD Disaggregation",
     "https://docs.sglang.ai/advanced_features/pd_disaggregation.html",
     "SGLang", "primary", "官方 PD 分离文档，含 Mooncake/NIXL 后端与参数"),
    ("sglang-mooncake", "SGLang: Mooncake Transfer Engine",
     "https://docs.sglang.ai/backend/mooncake.html",
     "SGLang", "primary", "Mooncake 传输引擎的接入方式"),
    ("sglang-router", "SGLang: Router / PD 路由",
     "https://docs.sglang.ai/advanced_features/router.html",
     "SGLang", "primary", "P/D 实例间的请求路由"),
    # TensorRT-LLM / NVIDIA
    ("trtllm-disagg", "TensorRT-LLM: Disaggregated Serving",
     "https://nvidia.github.io/TensorRT-LLM/features/disagg-serving.html",
     "NVIDIA", "primary", "TRT-LLM 的分离式服务实现"),
    ("nvidia-nixl", "NVIDIA: NIXL (NVIDIA Inference Xfer Library)",
     "https://github.com/ai-dynamo/nixl",
     "NVIDIA", "primary", "KV 传输库源码与说明"),
    ("nvidia-dynamo", "NVIDIA Dynamo: KV-aware routing / disaggregation",
     "https://docs.nvidia.com/dynamo/",
     "NVIDIA", "primary", "Dynamo 的分离与路由设计"),
    # DeepSeek
    ("deepseek-3fs", "DeepSeek: 3FS / Fire-Flyer 文件系统",
     "https://github.com/deepseek-ai/3FS",
     "DeepSeek", "primary", "DeepSeek 推理栈的存储层，与 PD 分离配套"),
    ("deepseek-profile", "DeepSeek: DeepSeek-V3/R1 推理系统概览",
     "https://github.com/deepseek-ai/open-infra-index",
     "DeepSeek", "primary", "官方推理系统说明，含 P/D 分离与配比"),
    # Mooncake / Moonshot
    ("mooncake-repo", "Mooncake: A KVCache-centric Disaggregated Architecture",
     "https://github.com/kvcache-ai/Mooncake",
     "Moonshot AI", "primary", "KVCache 为中心的分离架构实现"),
    # 其他
    ("lmcache", "LMCache: KV cache layer for LLM serving",
     "https://github.com/LMCache/LMCache",
     "LMCache", "primary", "KV cache 复用与传输层"),
    ("deepinfra-pd", "DeepInfra: PD disaggregation 实测",
     "https://deepinfra.com/blog",
     "DeepInfra", "secondary", "第三方部署方的实测经验（可能含负面结果）"),
]


def main() -> int:
    p = ArxivProvider()
    print(f"A. 检索 arXiv：{len(QUERIES)} 组式子…")
    hits = p.search_many(QUERIES, limit=120)

    rows = []
    for h in hits:
        if not (h.published or "")[:4] in ("2024", "2025", "2026"):
            continue
        rows.append({
            "arxiv_id": h.arxiv_id,
            "title": h.title,
            "published": h.published,
            "summary": h.abstract,
            "url": h.url,
            "query": h.query,
        })
    rows.sort(key=lambda r: r["published"], reverse=True)
    out = HERE / "candidates_pd.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"   命中 {len(hits)}，2024 年后 {len(rows)} 篇 -> {out.name}")

    # ---- B. 工程文档 ----
    docs = [{"doc_id": d[0], "title": d[1], "url": d[2],
             "publisher": d[3], "tier": d[4], "why": d[5]} for d in DOCS]
    (HERE / "candidates_docs.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"B. 工程文档登记 {len(docs)} 条（primary "
          f"{sum(1 for d in docs if d['tier'] == 'primary')}）")

    # 看一眼哪些候选与分离强相关
    kw = ("disaggregat", "splitwise", "prefill", "decode",
          "kv cache", "chunked")
    strong = [r for r in rows
              if sum(1 for k in kw if k in (r["title"] + " " +
                                            r["summary"]).lower()) >= 2]
    print(f"\n强相关候选（≥2 个关键词）：{len(strong)}")
    for r in strong[:15]:
        print(f"  {r['arxiv_id']}  {r['title'][:74]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
