"""修正 candidates_docs.json 的 URL：用真实抓到的路径替换猜的路径。

## 为什么会有这个文件

第一版 15 个 URL 里 3 个是死链——都是我按「看起来合理的路径」猜的：

    /features/nixl_connector.html      -> 404
    docs.sglang.ai/backend/mooncake.html -> 域名已迁到 docs.sglang.io，且 404
    docs.sglang.ai/advanced_features/router.html -> 404

`check_docs_urls.py` 把它们抓出来了。这件事本身值得记：
**猜 URL 的失败率在我这里是 3/15 = 20%**，而猜出来的链接长得和真的一样。
若没有这一步校验，论文里就会有三个点不开的引用，而读者只会觉得
「作者不严谨」——比缺引用更损害可信度。

## 真实路径怎么来的

不猜，从**已确认可用的页面上抽链接**：
  · SGLang 的 Mooncake / Router 是 PD 页内的**锚点**，不是独立页面。
    故另收两个真实存在的独立页：EPD Disaggregation、KV Cache Sharing。
  · vLLM 的 NIXL 有独立**设计文档**（design/nixl_kv_push_connector/），
    比原计划的 features 页更权威；另收 mooncake_connector_usage。

## 适用条件

这些路径是在 2026-11-04 抓到的。文档站改版后仍可能失效，
故 `check_docs_urls.py` 要能重复跑。
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 保留原 12 条可用 + 修正/替换 3 条 + 新增 3 条
FINAL = [
    # ---- vLLM ----
    ("vllm-disagg", "vLLM: Disaggregated Prefilling",
     "https://docs.vllm.ai/en/latest/features/disagg_prefill/",
     "vLLM", "primary", "官方分离式预填充文档，含 KV 连接器与示例"),
    ("vllm-kvconn", "vLLM: KV Transfer Config",
     "https://docs.vllm.ai/en/latest/api/vllm/config/kv_transfer/",
     "vLLM", "primary", "KV 传输配置项的权威定义"),
    ("vllm-nixl-design", "vLLM: NIXL KV Push Connector 设计",
     "https://docs.vllm.ai/en/latest/design/nixl_kv_push_connector/",
     "vLLM", "primary", "NIXL 推送式 KV 连接器的设计说明（修正：原猜路径 404）"),
    ("vllm-nixl-lease", "vLLM: NIXL KV Cache Lease 设计",
     "https://docs.vllm.ai/en/latest/design/nixl_kv_cache_lease/",
     "vLLM", "primary", "KV cache 租约机制，解决生命周期与并发写冲突"),
    ("vllm-mooncake", "vLLM: Mooncake Connector 使用",
     "https://docs.vllm.ai/en/latest/features/mooncake_connector_usage/",
     "vLLM", "primary", "经 Mooncake 传输引擎的 connector 用法"),
    ("vllm-chunked", "vLLM: Optimization and Tuning",
     "https://docs.vllm.ai/en/latest/configuration/optimization/",
     "vLLM", "primary", "chunked prefill 的开关与影响"),
    # ---- SGLang（域名 docs.sglang.ai -> docs.sglang.io）----
    ("sglang-pd", "SGLang: PD Disaggregation",
     "https://docs.sglang.io/docs/advanced_features/pd_disaggregation",
     "SGLang", "primary", "官方 PD 分离文档；Mooncake 与 Router 在此页内为锚点"),
    ("sglang-epd", "SGLang: EPD Disaggregation",
     "https://docs.sglang.io/docs/advanced_features/epd_disaggregation",
     "SGLang", "primary", "Encode-Prefill-Decode 三段分离，多模态场景"),
    ("sglang-kvshare", "SGLang: KV Cache Sharing",
     "https://docs.sglang.io/docs/advanced_features/kv_cache_sharing",
     "SGLang", "primary", "KV 复用机制，与分离配套"),
    # ---- NVIDIA ----
    ("trtllm-disagg", "TensorRT-LLM: Disaggregated Serving",
     "https://nvidia.github.io/TensorRT-LLM/features/disagg-serving.html",
     "NVIDIA", "primary", "TRT-LLM 的分离式服务实现"),
    ("nvidia-nixl", "NVIDIA: NIXL (Inference Xfer Library)",
     "https://github.com/ai-dynamo/nixl",
     "NVIDIA", "primary", "KV 传输库源码与说明"),
    ("nvidia-dynamo", "NVIDIA Dynamo Documentation",
     "https://docs.nvidia.com/dynamo/",
     "NVIDIA", "primary", "Dynamo 的分离与 KV-aware 路由设计"),
    # ---- DeepSeek ----
    ("deepseek-3fs", "DeepSeek: 3FS",
     "https://github.com/deepseek-ai/3FS",
     "DeepSeek", "primary", "推理栈的存储层，与 PD 分离配套"),
    ("deepseek-profile", "DeepSeek: open-infra-index",
     "https://github.com/deepseek-ai/open-infra-index",
     "DeepSeek", "primary", "官方推理系统说明，含 P/D 分离与配比"),
    # ---- Mooncake / 其他 ----
    ("mooncake-repo", "Mooncake: KVCache-centric Disaggregated Architecture",
     "https://github.com/kvcache-ai/Mooncake",
     "Moonshot AI", "primary", "KVCache 为中心的分离架构实现"),
    ("lmcache", "LMCache",
     "https://github.com/LMCache/LMCache",
     "LMCache", "primary", "KV cache 复用与传输层"),
    ("deepinfra-pd", "DeepInfra Blog",
     "https://deepinfra.com/blog",
     "DeepInfra", "secondary", "第三方部署方的实测经验（可能含负面结果）"),
]


def main() -> int:
    rows = [{"doc_id": d[0], "title": d[1], "url": d[2],
             "publisher": d[3], "tier": d[4], "why": d[5]} for d in FINAL]
    out = HERE / "candidates_docs.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"已写入 {len(rows)} 条（原 15 条 -> 修正 3 条死链、新增 3 条真实页）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
