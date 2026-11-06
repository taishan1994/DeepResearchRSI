"""从快照里按「锚点子串」定位证据，并生成 evidence.csv。

设计要点：**引文由脚本从快照里切出来，不由人手写**。
手写引文必然漂移（漏一个逗号、把 however 写成 but），而 E1 只认字面子串——
漂移的后果是校验失败；更糟的是有人为了让它过而把校验放宽。

故这里的流程是：给一个**一定存在于原文**的短锚点，脚本向两侧扩窗到句子边界，
再把切出来的整段写进 evidence.csv。锚点找不到就直接报错退出，不静默跳过
（LESSONS 2.3：不要用「看起来合理的默认值」兜异常）。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (evidence_id, document_id, source_id, anchor, locator, stance)
SPEC: list[tuple[str, str, str, str, str, str]] = [
    # ---------------- 模型本身 ----------------
    ("e-552b-backbone", "doc-hf-dsv41", "src-hf-dsv41",
     "a multimodal Mixture-of-Experts (MoE) model with 552B backbone parameters",
     "README / Introduction §1", "supports"),
    ("e-8b-16b-active", "doc-hf-dsv41", "src-hf-dsv41",
     "activate only **8B parameters per token during prefill** and **16B during decode**",
     "README / Introduction §1 · CED", "supports"),
    ("e-kv-890", "doc-hf-dsv41", "src-hf-dsv41",
     "reduce the global KV cache footprint to **890 bytes per token**",
     "README / Introduction §1 · CSA2", "supports"),
    ("e-swa-eighth", "doc-hf-dsv41", "src-hf-dsv41",
     "reducing the persistent KV cache footprint to roughly **1/8**",
     "README / Introduction §1 · SWA Bounded Replay", "supports"),
    ("e-engram-196b", "doc-hf-dsv41", "src-hf-dsv41",
     "Engram conditional memory (196B parameters, sparsely accessed via token-based lookup)",
     "README / Introduction §1 · additional components", "supports"),
    ("e-vision-native", "doc-hf-dsv41", "src-hf-dsv41",
     "A vision encoder (DeepSeek-ViT, trained from scratch with 2D-RoPE",
     "README / Multimodal architecture", "supports"),
    ("e-1m-context", "doc-hf-dsv41", "src-hf-dsv41",
     "support for contexts of up to one million tokens",
     "README / Introduction", "supports"),
    ("e-40-layers", "doc-hf-dsv41", "src-hf-dsv41",
     "a 40-layer Transformer organized as a 20-layer causal encoder followed by a 20-layer decoder",
     "README / Architecture", "supports"),
    ("e-384-experts", "doc-hf-dsv41", "src-hf-dsv41",
     "The model uses 1 shared expert and 384 routed experts per MoE layer, activating 6 routed experts per token",
     "README / additional components", "supports"),
    ("e-no-jinja", "doc-hf-dsv41", "src-hf-dsv41",
     "This release does not include a Jinja-format chat template",
     "README / Prompt Encoding", "supports"),
    ("e-report-552b-196b", "doc-deepseek-v41-report", "src-deepseek-v41-report",
     "has 552B backbone parameters and 196B Engram parameters, activating 8B parameters per",
     "Tech Report §2.1", "supports"),
    ("e-report-890", "doc-deepseek-v41-report", "src-deepseek-v41-report",
     "reduce its global KV cache footprint (always in HBM) to 890 bytes",
     "Tech Report / Abstract", "supports"),
    ("e-report-flops-flat", "doc-deepseek-v41-report", "src-deepseek-v41-report",
     "increases its Decode FLOPs by only 1/4",
     "Tech Report §2.1 · efficiency", "supports"),
    ("e-report-45t", "doc-deepseek-v41-report", "src-deepseek-v41-report",
     "comprising 45T tokens",
     "Tech Report §2.1 · pre-training", "supports"),

    # ---------------- 硬件 ----------------
    ("e-se-96gb", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "Equipped with 96 GB of ultra-fast GDDR7 memory",
     "NVIDIA 产品页 / Overview", "supports"),
    ("e-se-1597", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "Memory Bandwidth",
     "NVIDIA 产品页 / Specifications · Memory Bandwidth", "supports"),
    ("e-se-fp4", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "4 PFLOPS",
     "NVIDIA 产品页 / Specifications · FP4 Tensor Core", "supports"),
    ("e-se-fp8", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "2 PFLOPS",
     "NVIDIA 产品页 / Specifications · FP8 Tensor Core", "supports"),
    ("e-se-24064", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "24,064",
     "NVIDIA 产品页 / Specifications · CUDA cores", "supports"),
    ("e-se-600w", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "Up to 600W (configurable)",
     "NVIDIA 产品页 / Quick Specs · Max Power", "supports"),
    ("e-se-mig", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "enabling the creation of up to four fully isolated instances",
     "NVIDIA 产品页 / Features · MIG", "supports"),
    ("e-se-passive", "doc-nvidia-pro6000se", "src-nvidia-pro6000se",
     "Liquid: Single-Slot, FHXL",
     "NVIDIA 产品页 / Quick Specs · Form Factor", "supports"),
    ("e-ws-1792", "doc-nvidia-pro6000ws", "src-nvidia-pro6000ws",
     "1792 GB/sec",
     "NVIDIA 工作站版产品页 / Specifications · Memory Bandwidth", "context"),
    ("e-variant-table", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "| **Server Edition** | 600W | Passive cooling |",
     "GPU Variants 表", "supports"),
    ("e-msrp-nvml", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "MaxQ cards accept memory clock offset. Server Edition cards return an error.",
     "Memory Overclocking (MaxQ Only)", "supports"),
    ("e-power-scaling", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "Power-limit 600W cards to 500W: nearly identical performance",
     "Power Optimization", "supports"),
    ("e-600w-to-300w", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "Power-limit to 300W: only ~4% single-user loss",
     "Power Optimization", "supports"),
    ("e-tp-constraint", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "TP must be power-of-2 for vLLM/SGLang: 2, 4, 8, 16",
     "Tensor Parallel Constraints", "supports"),
    ("e-sm120-statement", "doc-r6k-sm120", "src-r6k-sm120",
     "The actual bottleneck is the software fork.",
     "SM120 vs SM100 / 结论段", "supports"),
    ("e-sm120-tcgen05", "doc-r6k-sm120", "src-r6k-sm120",
     "tcgen05 is not necessary for SM120.",
     "SM120 vs SM100 / 第 2 条", "supports"),

    # ---------------- 显存算术与部署形状 ----------------
    ("e-q-511gb", "doc-qovery-selfhost", "src-qovery-selfhost",
     "ships roughly 511 GB of weights",
     "Key Points", "supports"),
    ("e-q-total-vs-active", "doc-qovery-selfhost", "src-qovery-selfhost",
     "Size for total parameters, not active ones.",
     "Key Points", "supports"),
    ("e-q-eneed-614", "doc-qovery-selfhost", "src-qovery-selfhost",
     "you need about 614 GB of GPU memory with everything resident",
     "VRAM section", "supports"),
    ("e-q-engram-ram", "doc-qovery-selfhost", "src-qovery-selfhost",
     "With the Engram tables moved to host RAM, vLLM runs one replica on 4x H200",
     "Key Points", "supports"),
    ("e-q-h100-not-listed", "doc-qovery-selfhost", "src-qovery-selfhost",
     "neither the vLLM recipe nor the SGLang cookbook lists H100",
     "Which cloud GPU instances", "supports"),
    ("e-q-b200-tp2", "doc-qovery-selfhost", "src-qovery-selfhost",
     "Blackwell B200 and B300 run it at TP2 in the vLLM recipe",
     "Which cloud GPU instances", "supports"),
    ("e-q-single-4090-no", "doc-qovery-selfhost", "src-qovery-selfhost",
     "Can I run DeepSeek V4.1-Flash on a single H100, or on a consumer GPU like an RTX 4090?",
     "FAQ", "supports"),
    ("e-q-315-350", "doc-qovery-selfhost", "src-qovery-selfhost",
     "roughly 315-350 GB of weights must stay in GPU memory",
     "FAQ", "supports"),

    ("e-56700-tp8", "doc-vllm-56700", "src-vllm-56700",
     "TP=8",
     "Issue body / What works", "supports"),
    ("e-56700-91gb", "doc-vllm-56700", "src-vllm-56700",
     "~91GB/96GB per GPU",
     "Issue body / What works", "supports"),
    ("e-56700-engram-189", "doc-vllm-56700", "src-vllm-56700",
     "Engram tables dominate",
     "Issue body / What works", "supports"),
    ("e-56700-1m", "doc-vllm-56700", "src-vllm-56700",
     "950K-token double-needle retrieval",
     "Issue body / What works", "supports"),
    ("e-56700-prefill", "doc-vllm-56700", "src-vllm-56700",
     "4584 tok/s prefill throughput",
     "Issue body / What works", "supports"),
    ("e-56700-fp8-layout", "doc-vllm-56700", "src-vllm-56700",
     "the killer",
     "Issue body / Pitfall map 第 3 条", "supports"),
    ("e-56700-silent", "doc-vllm-56700", "src-vllm-56700",
     "only fails at",
     "Issue body / Pitfall map 第 3 条", "supports"),
    ("e-56700-marlin", "doc-vllm-56700", "src-vllm-56700",
     "MXFP4 expert path falls back to Marlin",
     "Issue body / Pitfall map 第 5 条", "supports"),
    ("e-56700-deepgemm-hang", "doc-vllm-56700", "src-vllm-56700",
     "DeepGEMM autotune hang on first long-context batch",
     "Issue body / Pitfall map 第 1 条", "supports"),

    # ---------------- 现场报告：SGLang ----------------
    ("e-40877-maxq", "doc-sglang-40877", "src-sglang-40877",
     "8× RTX PRO 6000 Blackwell Max-Q",
     "Issue body / Summary", "supports"),
    ("e-40877-nonvlink", "doc-sglang-40877", "src-sglang-40877",
     "PCIe-only — no NVLink",
     "Issue body / Summary", "supports"),
    ("e-40877-tp8only", "doc-sglang-40877", "src-sglang-40877",
     "it is the only layout that starts",
     "Issue body / TP8/EP8 说明", "supports"),
    ("e-40877-128k", "doc-sglang-40877", "src-sglang-40877",
     "6,853",
     "Issue body / 128K cold prefill 表", "supports"),
    ("e-40877-commbound", "doc-sglang-40877", "src-sglang-40877",
     "communication-bound on PCIe",
     "Issue body / 32K prompt 段", "supports"),
    ("e-40877-220w", "doc-sglang-40877", "src-sglang-40877",
     "at 220 W of 600 W",
     "Issue body / 32K prompt 段", "supports"),
    ("e-40877-radix", "doc-sglang-40877", "src-sglang-40877",
     "Radix/prefix cache is the only large multiplier",
     "Issue body / 前缀缓存段", "supports"),
    ("e-40877-decode", "doc-sglang-40877", "src-sglang-40877",
     "prose 93.9 tok/s",
     "Issue body / Decode", "supports"),
    ("e-40877-dspark-ab", "doc-sglang-40877", "src-sglang-40877",
     "speculation is the difference between usable and unusable latency",
     "Issue body / DSPARK A/B", "supports"),
    ("e-40877-36-5", "doc-sglang-40877", "src-sglang-40877",
     "flattens to ~36.5 tok/s",
     "Issue body / DSPARK A/B", "supports"),
    ("e-40877-tp4", "doc-sglang-40877", "src-sglang-40877",
     "--tp 4 --ep-size 4",
     "Update 2026-09-27 / What runs now", "supports"),
    ("e-40877-1m-ladder", "doc-sglang-40877", "src-sglang-40877",
     "3,242 tok/s",
     "Update 2026-09-28 / 1M 冷预填表", "supports"),
    ("e-40877-cold-1m", "doc-sglang-40877", "src-sglang-40877",
     "~5 minutes",
     "Update 2026-09-28 / 1M 结论", "supports"),
    ("e-40877-artifact", "doc-sglang-40877", "src-sglang-40877",
     "is a prefix-cache hit",
     "Update 2026-09-28 / 方法论修正", "supports"),
    ("e-40877-longconc", "doc-sglang-40877", "src-sglang-40877",
     "Long-context concurrency collapses",
     "Update 2026-09-28 / 长上下文并发", "supports"),
    ("e-40877-vram-98", "doc-sglang-40877", "src-sglang-40877",
     "GPU steady at 96.8 GB of 97.9 GB",
     "Update 2026-09-28 / Stability", "supports"),
    ("e-40877-dp-reject", "doc-sglang-40877", "src-sglang-40877",
     "DP2 × TP4",
     "Issue body / Topologies SGLang rejects", "supports"),
    ("e-40877-vision-tp", "doc-sglang-40877", "src-sglang-40877",
     "V4.1 vision currently supports TP/EP without DP, CP, PP or MoE A2A",
     "Issue body / Topologies SGLang rejects", "supports"),

    # ---------------- 工程栈：rtx6kpro ----------------
    ("e-r6k-tp4", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "This starts TP4/DCP1 with adaptive DSpark K7 and disk-backed Engram tables",
     "Start the server", "supports"),
    ("e-r6k-hardware-profile", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "HARDWARE_PROFILE=rtx-pro-6000-pcie",
     "docker run 示例", "supports"),
    ("e-r6k-ram-engram-gib", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "188.83 GiB for tables",
     "RAM versus SSD ngrams 表", "supports"),
    ("e-r6k-c1", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "| C1 output | 230.6 tok/s | 249.1 tok/s | +8.01% |",
     "Measured performance 表", "supports"),
    ("e-r6k-c8", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "| C8 aggregate output | 748.3 tok/s | 805.5 tok/s | +7.65% |",
     "Measured performance 表", "supports"),
    ("e-r6k-32k", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "| 32K prefill | 17,503 tok/s | 17,982 tok/s | +2.74% |",
     "Measured performance 表", "supports"),
    ("e-r6k-kvtokens", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "4,727,748 logical KV tokens",
     "Measured performance 段", "supports"),
    ("e-r6k-maxq-clocks", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "Four RTX PRO 6000 **Max-Q**",
     "Measured performance / 条件", "supports"),
    ("e-r6k-engram-not-kv", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "Engram contains learned n-gram model tables. It is **not** KV cache",
     "RAM versus SSD ngrams 段", "supports"),
    ("e-r6k-hetero-cache", "doc-r6k-dsv41-model", "src-r6k-dsv41-model",
     "The native cache is heterogeneous despite the CLI's `fp8` label",
     "Common settings", "supports"),
    ("e-r6k-1994", "doc-r6k-dspark", "src-r6k-dspark",
     "Conclusion: pure upstream vLLM cannot serve DeepSeek-V4-Flash",
     "结论段", "supports"),
    ("e-r6k-four-walls", "doc-r6k-dspark", "src-r6k-dspark",
     "four independent SM120 blockers",
     "Why upstream shows", "supports"),
    ("e-r6k-deepgemm-sm120", "doc-r6k-dspark", "src-r6k-dspark",
     "Bundled DeepGEMM has no SM120 support",
     "blocker 2", "supports"),

    # ---------------- 量化旁路 ----------------
    ("e-exl3-2x", "doc-diffbot-exl3", "src-diffbot-exl3",
     "on two RTX PRO 6000",
     "recipe/README 首段", "supports"),
    ("e-exl3-8x", "doc-diffbot-exl3", "src-diffbot-exl3",
     "PROFILE=8x",
     "The 8× RTX PRO 6000 profile", "supports"),
    ("e-exl3-96gb", "doc-diffbot-exl3", "src-diffbot-exl3",
     "96,655 and 97,029 MiB of 97,887 MiB per card",
     "Memory: what lives where", "supports"),
    ("e-exl3-4454", "doc-diffbot-exl3", "src-diffbot-exl3",
     "| `MAX_MODEL_LEN`, `KV_MEM`, `MAX_NUM_SEQS` | 1048576, 18 GiB, 128 |",
     "The 8× RTX PRO 6000 profile / 表", "supports"),
    ("e-exl3-engram-int4", "doc-diffbot-exl3", "src-diffbot-exl3",
     "Engram tables, int4 (111 GB)",
     "Memory 表", "supports"),

    # ---------------- 官方 API 与价格 ----------------
    ("e-api-flash-price", "doc-deepseek-api-pricing", "src-deepseek-api-pricing",
     "1M OUTPUT TOKENS",
     "Models & Pricing / 1M OUTPUT TOKENS · PEAK", "supports"),
    ("e-api-cache-hit", "doc-deepseek-api-pricing", "src-deepseek-api-pricing",
     "$0.006",
     "Models & Pricing / 1M INPUT TOKENS (CACHE HIT) · PEAK", "supports"),
    ("e-api-1m", "doc-deepseek-api-pricing", "src-deepseek-api-pricing",
     "CONTEXT LENGTH",
     "Models & Pricing / CONTEXT LENGTH", "supports"),
    ("e-api-concurrency", "doc-deepseek-api-pricing", "src-deepseek-api-pricing",
     "Concurrency Limit",
     "Models & Pricing / Concurrency Limit", "supports"),
    ("e-api-vision", "doc-deepseek-api-pricing", "src-deepseek-api-pricing",
     "Vision",
     "Models & Pricing / FEATURES · Vision 行", "supports"),
    ("e-v41-retire", "doc-deepseek-v41-news", "src-deepseek-v41-news",
     "V4-Flash & V4-Flash-Vision-Exp are retired",
     "news260910 / API 段", "supports"),
    ("e-v41-offpeak", "doc-deepseek-v41-news", "src-deepseek-v41-news",
     "Off-peak rates are 50% of peak rates",
     "news260910 / 价格段", "supports"),
    ("e-v41-smaller-kv", "doc-deepseek-v41-news", "src-deepseek-v41-news",
     "1/4 the HBM",
     "news260910 / KV cache 段", "supports"),
    ("e-v41-2000gpu", "doc-deepseek-v41-news", "src-deepseek-v41-news",
     "2,000 GPUs + a storage cluster",
     "news260910 / 开源与部署段", "supports"),

    # ---------------- 官方 serving 栈 ----------------
    ("e-sgl-docker", "doc-sglang-cookbook", "src-sglang-cookbook",
     "not shipped in an SGLang release yet",
     "Deployment / Install", "supports"),
    ("e-sgl-hw", "doc-sglang-cookbook", "src-sglang-cookbook",
     "(H200 / B200 / B300 / GB300)",
     "Deployment / NVIDIA GPUs", "supports"),
    ("e-sgl-engram-cpu", "doc-sglang-cookbook", "src-sglang-cookbook",
     '"placement": "cpu"',
     "1. Model Introduction / Engram", "supports"),
    ("e-sgl-dspark", "doc-sglang-cookbook", "src-sglang-cookbook",
     "DSpark is DeepSeek-V4.1 Flash’s own bundled draft",
     "3.3 Speculative Decoding (DSpark)", "supports"),
    ("e-sgl-sm100", "doc-sglang-cookbook", "src-sglang-cookbook",
     "SM100/SM103",
     "3.4 PD Disaggregation", "supports"),
    ("e-sgl-backend", "doc-sglang-cookbook", "src-sglang-cookbook",
     "Do not override the backends",
     "2. Configuration Tips", "supports"),
    ("e-aa-22of133", "doc-aa-configs", "src-aa-configs",
     "22", "AA 配置页 / 计数", "supports"),
    ("e-aa-rubin", "doc-aa-configs", "src-aa-configs",
     "Vera Rubin NVL72",
     "AA 配置页 / featured 卡片", "supports"),
    ("e-aa-mxfp4", "doc-aa-configs", "src-aa-configs",
     "MXFP4",
     "AA 配置页 / featured 卡片", "supports"),
    ("e-ascend-a3", "doc-vllm-ascend-dsv41", "src-vllm-ascend-dsv41",
     "8 NPUs and 128GB",
     "§3.1 Model Weights and Hardware", "supports"),
]

# 这些锚点在快照里不存在，用于显式声明「没查到」而不是猜一个数字。
# 它们**不进 evidence.csv**，只在缺口清单里出现。
KNOWN_ABSENT = [
    "e-q-apostrophe",
]


def window(text: str, anchor: str, before: int = 260, after: int = 360) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    lo, hi = max(0, i - before), min(len(text), i + len(anchor) + after)
    seg = text[lo:i]
    m = None
    for m in re.finditer(r"(?:[.!?]\s+|\n\n|\n(?=[A-Z（]))", seg):
        pass
    if m:
        lo += m.end()
    seg2 = text[i + len(anchor):hi]
    m2 = re.search(r"[.!?](?:\s|$)|\n\n", seg2)
    if m2:
        hi = i + len(anchor) + m2.end()
    q = " ".join(text[lo:hi].split())
    # ⚠️ 短锚点（表格单元格、数字、单个词）扩窗后可能只有「6,853」这种碎片。
    # 它是原文子串，E1 会通过，但对论证零贡献——这正是 LESSONS 4.2
    # 「18 条证据里 5 条是题名与作者行」的同一类错误。
    # 故设最小长度，不足则按行成对扩张，直到够长或到文档边界。
    return expand(text, lo, hi, i, len(anchor))


MIN_QUOTE = 160


def expand(text: str, lo: int, hi: int, at: int, length: int) -> str:
    """不足 MIN_QUOTE 时按行向外扩张，保证引文自带上下文。"""
    q = " ".join(text[lo:hi].split())
    for _ in range(40):
        if len(q) >= MIN_QUOTE:
            break
        # 先扩下边界，再扩上边界，交替进行——单侧扩张会把平衡拉偏。
        nxt = text.find("\n", hi + 1) if hi < len(text) else -1
        if nxt > 0:
            hi = nxt
        else:
            prev = text.rfind("\n", 0, max(0, lo - 1)) if lo > 0 else -1
            if prev > 0:
                lo = prev + 1
            elif hi >= len(text) and lo <= 0:
                break
        q = " ".join(text[lo:hi].split())
    return q


def main() -> int:
    meta = {}
    with (ROOT / "documents.csv").open(encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            meta[row["document_id"]] = row

    rows: list[dict[str, str]] = []
    missing: list[tuple[str, str]] = []
    for eid, did, sid, anchor, locator, stance in SPEC:
        if eid in KNOWN_ABSENT:
            missing.append((eid, anchor))
            continue
        doc = meta.get(did)
        if not doc:
            raise SystemExit(f"缺文档：{did}（{eid}）")
        text = (ROOT / doc["snapshot"]).read_text(encoding="utf-8")
        try:
            quote = window(text, anchor)
        except LookupError:
            missing.append((eid, anchor))
            continue
        rows.append({
            "evidence_id": eid,
            "document_id": did,
            "source_id": sid,
            "quote": quote,
            "locator": locator,
            "stance": stance,
            "extracted_by": "build_archive.py/1（锚点扩窗，非手写）",
        })

    if missing:
        print("以下锚点在快照里找不到——不是「失败」，是这些句子不在原文里：")
        for eid, anchor in missing:
            print(f"  - {eid}: {anchor!r}")
        print("请改锚点或删条目，不要手写引文。")
        return 1

    out = ROOT / "evidence.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["evidence_id", "document_id", "source_id", "quote",
                        "locator", "stance", "extracted_by"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)
    total = sum(len(r["quote"]) for r in rows)
    print(f"已写 {out.name}：{len(rows)} 条证据，引文合计 {total:,} 字符")

    # ⚠️ 追加层证据：本文件是「全量重写」，故任何在它之外补的证据都会被静默抹掉。
    # 实测过：重跑本脚本后 evidence.csv 从 108 条掉回 102 条，
    # 而 c-quant-quality-cost 恰好依赖那 6 条补录——
    # 于是「修好的结论」会在下一次重跑后悄悄退回错误状态，且没有任何报警。
    # 故把补录做成**幂等的一步**，让重跑本脚本 = 得到完整档案。
    extra = ROOT / "evidence_extra.json"
    if extra.is_file():
        import json
        with extra.open(encoding="utf-8") as fh:
            add = json.load(fh)
        seen = {r["evidence_id"] for r in rows}
        n = 0
        for r in add:
            if r["evidence_id"] in seen:
                continue
            rows.append({k: r[k] for k in
                         ("evidence_id", "document_id", "source_id", "quote",
                          "locator", "stance", "extracted_by")})
            n += 1
        if n:
            with out.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                                   lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            total = sum(len(r["quote"]) for r in rows)
            print(f"已并入 {extra.name} 的 {n} 条补充证据："
                  f"共 {len(rows)} 条，{total:,} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
