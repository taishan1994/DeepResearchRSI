"""给 PAPER.md 插入行内主张引用。

为什么要脚本而不是手改：
    42 条主张要在十几个地方挂上，手改必然漏几个，而「漏了」的表现是
    audit 报引用闭合率不足——那时已经很难定位是哪一段少了。
    这里用**精确字面锚点**替换，每个锚点必须出现且只出现一次，
    否则脚本报错退出（不静默跳过，也不猜一个位置）。

    这跟 build_evidence.py 用的是同一条纪律：不在「差不多对」的地方动手。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"

# (锚点, 追加的引用)
EDITS: list[tuple[str, str]] = [
    # ---- 摘要 ----
    ("第四组是 2×Max-Q 的量化旁路。故本文把结论分成两层——",
     "[c-gap-no-se-measurement] "),
    ("**在这台机器上，上下文长度几乎不花显存，能不能装下权重才是唯一门槛。**",
     " [c-kv-implication]"),
    ("把 188.83 GiB 的 Engram 表下放主机内存后降到 4 张；再往下只能靠 3-bit 量化。",
     " [c-minimum-viable]"),
    ("SGLang 官方硬件矩阵不含 SM120 且该模型未进 release。",
     " [c-upstream-vllm-blocked] [c-sglang-no-sm120]"),
    ("同类假象在作者自己的两组数据里都出现过。",
     " [c-cache-artifact]"),
    ("差两个数量级，故自建的理由是数据主权与可定制，不是省钱。",
     " [c-selfhost-breakeven] [c-selfhost-for-control]"),

    # ---- §1 ----
    ("全部主张见附录 B。其中 37 条为 `high` 置信、5 条为 `medium`（均为二手转述或跨硬件推算）；",
     "[c-v41-is-552b-moe] "),

    # ---- §2 ----
    ("**这是本主题最容易犯的第一个错误**：厂商标称「16B 激活」时，读者的直觉是「16B 的模型，一张 24 GB 卡就够」。",
     " [c-active-not-total]"),
    ("按 FP8 稠密 + FP4 专家的混合精度，第三方测算权重约 **511 GB**（48 个 safetensors 分片），",
     "[c-no-1m-on-2x96] "),
    ("| 纯 KV 尺寸 | 890 B/token | 官方口径，FP4 主 KV + CSA2 跨层共享 |",
     " [c-kv-890-bytes]"),
    ("技术报告还给出一个更硬的恒等式：上下文从 4K 拉到 1M（256 倍），单 token 解码 FLOPs 只涨 1/4。",
     " [c-decode-flops-flat]"),
    ("把它当 KV 会得出「KV 有 200 GB」的错误结论。",
     " [c-engram-dominates]"),
    ("另外，API 侧只有 `deepseek-flash` 支持视觉，\n`deepseek-v4-pro` 不支持。",
     " [c-vision-native]"),
    ("这是很多「部署完发现对话格式不对」的根因。",
     " [c-no-chat-template]"),

    # ---- §3 ----
    ("但 **vLLM/SGLang 要求 TP 为 2 的幂**（2/4/8/16），奇数卡只能走流水并行。故：",
     " [c-tp-power-of-2]"),
    ("| 8×96 GB | 768 GB | 装得下 | 是 | vLLM TP8 |",
     " [c-tp8-on-8x96]"),
    ("4 × 96 = 384 GB 恰好落在这个区间之上——**余量约 34–69 GB，够 KV、激活与通信缓冲**。",
     " [c-min-4x96]"),
    ("「Engram 表占主导：两张约 100 GB 的分片，整个 TP 组合计 189 GiB」。",
     " [c-tp8-on-8x96]"),

    # ---- §4 ----
    ("| 带宽 | **1597 GB/s** | **1792 GB/s** | SE 低约 11% |",
     " [c-se-spec] [c-se-vs-ws-bandwidth]"),
    ("这是本文唯一一条关于「SE 比别的变体慢多少」的量化说法，且它**不是实测**。",
     " [c-se-vs-ws-bandwidth]"),
    ("故那组数字**双重不可迁移**：既是 MQ，又超了频。",
     " [c-r6k-not-se]"),
    ("600 W → 300 W 单用户仅损失约 4%；",
     " [c-power-scaling]"),
    ("- 现场实测：8 卡跑 128K 预填时 GPU 利用率约 87%，但只吃到 **220 W / 600 W**。",
     " [c-prefill-sgl-8x]"),

    # ---- §5 ----
    ("4. 原文结论：「纯上游 vLLM 今天在 SM120 上无法服务 DeepSeek-V4-Flash（带不带 DSpark 都一样）」。",
     " [c-upstream-vllm-blocked]"),
    ("真正的瓶颈是「软件分叉」——主流实验室的 kernel 开发优先服务 SM100 生产环境。",
     " [c-sglang-no-sm120]"),
    ("官方还明说该模型**尚未进入任何 SGLang release**，stock `pip install sglang` 无法服务它。",
     " [c-sglang-no-sm120]"),
    ("加速器清一色是数据中心卡（Vera Rubin NVL72 等），**无一例 RTX PRO 6000**。",
     " [c-aa-no-sm120]"),
    ("不是「SGLang 0.x.y」。这对生产选型是实质风险。",
     " [c-need-forked-image]"),

    # ---- §6 ----
    ("**故：本文所有吞吐数字都是 MQ 或未标变体的，SE 上一个都没有。**",
     " [c-gap-no-se-measurement]"),
    ("| `chunked_prefill_size=2048`（生产） | **6,853** |",
     " [c-prefill-sgl-8x]"),
    ("**唯一的大倍率来自前缀缓存**：112K token 前缀命中时 0.34 s ≈ **325K tok/s（约 39 倍）**。",
     " [c-prefill-ceiling]"),
    ("生产用 `block_size=6` 时结构化提示约 **237–252 tok/s**。",
     " [c-decode-dspark]"),
    ("作者明说 N=2，**不是误差棒**，应读作首轮而非定表。",
     " [c-decode-tp4-conc]"),
    ("32K 预填 **17,982 tok/s**、4,727,748 逻辑 KV token。",
     " [c-stable-tp4-profile]"),
    ("**结论：一次完整的 1M 冷预填约 5 分钟。**",
     " [c-1m-cold-5min]"),
    ("真实冷数字是 79.5 s（5,065 tok/s）。",
     " [c-cache-artifact]"),
    ("**「能跑」与「跑得快」是两件事**：4,584 对 SGLang 的 6,853（上下文长度不同，不可直接比）。",
     " [c-vllm-1m-verified]"),
    ("**这个端点擅长服务一个重请求，而不是多个**。",
     " [c-long-ctx-collapse]"),
    ("**两条独立路线撞到同一面墙。** 96 GB 是硬边界，且余量只有约 1 GB——",
     " [c-vram-ceiling] "),

    # ---- §7 ----
    ("| **`--enable-dp-attention` 单独用** | 静默 | 单独启用 | `dp_size` 仍是 1。会让人把**旧配置当成新配置**记录，整轮数据作废 |",
     " [c-sgl-rejects-dp]"),
    ("| **FP8 KV 的 scale 布局** | 静默 | 短提示全过，≥100K 暴露 |",
     " [c-fp8-kv-layout-pitfall]"),
    ("| **前缀缓存假象** | 静默 | 共享前缀的提示 |",
     " [c-cache-artifact]"),
    ("| DeepGEMM autotune 挂死 | 首次长上下文批（128K+）deadlock，bring-up 需跳过或 eager |",
     " [c-deepgemm-hang]"),
    ("| SGLang 拒绝 DP 拓扑 | DP2×TP4 抛「V4.1 vision currently supports TP/EP without DP, CP, PP or MoE A2A」，两副本约 70 s 内死亡 |",
     " [c-sgl-rejects-dp]"),
    ("这不是可以「修好」的配置问题，是内核覆盖缺口。",
     " [c-marlin-fallback]"),

    # ---- §8 ----
    ("| 并发上限 | **2,500** |",
     " [c-api-price]"),
    ("| 8 并发合计（8 卡，社区调优） | 805.5 tok/s | 1/18 |",
     " [c-selfhost-breakeven]"),
    ("MIT 许可让这些成为可能（可商用、可微调、可再分发）。",
     " [c-selfhost-for-control]"),
    ("必须 W8A8 权重 + INT8 Engram，且必须显式 `VLLM_USE_V2_MODEL_RUNNER=0`。",
     " [c-ascend-alt]"),

    # ---- §9 ----
    ("| C | 2×96 GB | EXL3 3-bit | 量化旁路 | agentic 224.1 tok/s；KL 0.0522 |",
     " [c-quant-quality-cost]"),
    ("- 前提：接受 KL 高于噪声底 6 倍；主机 RAM 约 260 GiB、磁盘约 340 GB。",
     " [c-quant-quality-cost]"),

    # ---- §10 ----
    ("真正的限制是 PCIe（无 NVLink 时预填约 7K tok/s 封顶）与 SM120 的内核覆盖缺口。",
     " [c-prefill-ceiling] [c-upstream-vllm-blocked]"),
    ("13,962 tok/s 与 3,242 tok/s 差 4.3 倍，而两者跑的是同一个模型、同一台机器、同一个镜像。",
     " [c-cache-artifact]"),
    ("按带宽比推算 SE 的解码应低约 11%，预填差别应更小——但这是**推算**。",
     " [c-se-vs-ws-bandwidth]"),
]


def main() -> int:
    text = PAPER.read_text(encoding="utf-8")
    bad: list[str] = []
    for anchor, cite in EDITS:
        n = text.count(anchor)
        if n != 1:
            bad.append(f"出现 {n} 次：{anchor[:60]}")
            continue
        text = text.replace(anchor, anchor + " " + cite.strip())
    if bad:
        print("锚点不唯一或不存在：")
        for b in bad:
            print("  - " + b)
        return 1
    PAPER.write_text(text, encoding="utf-8")
    print(f"已插入 {len(EDITS)} 处引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
