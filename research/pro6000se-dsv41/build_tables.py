"""生成 sources.csv 与 claims.csv。

sources 的 fetched_at 取**本次实际抓取时写入 documents.csv 的字节与哈希**
对应的墙上时间。这里写死一个带时区的常量而不是 datetime.now()：
归档要求「你在什么时候看到的」，而 now() 每次重跑都变，会让同一份归档
在两次运行间产生不同内容——那是把「重跑」误当成「重新观测」。
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FETCHED = "2026-11-05T17:33:00+08:00"

# source_id, url, source_type, publisher, title, published_at, updated_at,
# language, trust_tier, access, license, notes
SOURCES = [
    ("src-hf-dsv41", "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash",
     "official", "DeepSeek-AI", "DeepSeek-V4.1-Flash model card (KV cache compression)",
     "2026-09-10", "", "en", "primary", "open", "MIT",
     "权重发布方自己写的模型卡；架构数字的唯一一手来源。"),
    ("src-deepseek-v41-report", "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf",
     "official", "DeepSeek-AI", "DeepSeek-V4.1-Flash Technical Report",
     "2026-09-10", "", "en", "primary", "open", "MIT",
     "技术报告 PDF，经 pymupdf 抽文本。参数/FLOPs/训练语料的权威出处。"),
    ("src-deepseek-v41-news", "https://api-docs.deepseek.com/news/news260910.md",
     "official", "DeepSeek", "DeepSeek-V4.1-Flash: Smarter, Faster, More Efficient",
     "2026-09-10", "", "en", "primary", "open", "",
     "发布公告。含价格、退役旧型号、KV 压缩倍数。"),
    ("src-deepseek-api-pricing", "https://api-docs.deepseek.com/quick_start/pricing",
     "official", "DeepSeek", "Models & Pricing",
     "2026-09-10", "2026-10-17", "en", "primary", "open", "",
     "官方 API 价目表；用于「自建 vs 托管」的对照锚点。"),
    ("src-nvidia-pro6000se", "https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/",
     "official", "NVIDIA", "RTX PRO 6000 Blackwell Server Edition",
     "2025-03-18", "2026-10-01", "en", "primary", "open", "",
     "NVIDIA 官方产品页；96GB / 1597 GB/s / 600W / MIG 的出处。"),
    ("src-nvidia-pro6000ws", "https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/",
     "official", "NVIDIA", "RTX PRO 6000 Blackwell Workstation Edition",
     "2025-03-18", "2026-10-01", "en", "primary", "open", "",
     "同厂同代工作站版页面；1792 GB/s 的**一手**出处（不用二手转述）。"),
    ("src-r6k-gpu-configs", "https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/gpu-configs.md",
     "community", "local-inference-lab", "GPU Configurations & Rig Builds (RTX PRO 6000)",
     "2026-10-01", "", "en", "primary", "open", "see repo",
     "社区维护的整机配置页；含三档变体对照与 TP 约束。"),
    ("src-r6k-sm120", "https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/sm120-vs-sm100-architecture.md",
     "community", "local-inference-lab", "SM120 vs. SM100 Architecture",
     "2026-10-01", "", "en", "primary", "open", "see repo",
     "对「SM120 缺 Blackwell 特性」说法的技术澄清。"),
    ("src-r6k-dsv41-model", "https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md",
     "community", "local-inference-lab", "DeepSeek-V4.1-Flash serving profile on RTX PRO 6000",
     "2026-10-20", "", "en", "primary", "open", "see repo",
     "唯一给出「SM120 上 V4.1-Flash 稳定 C1/C8/32K 预填」的公开测量页。"),
    ("src-r6k-dspark", "https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/dspark-upstream-consolidation.md",
     "community", "local-inference-lab", "DSpark: ours vs upstream vLLM — consolidation study",
     "2026-07-03", "", "en", "primary", "open", "see repo",
     "逐条列出上游 vLLM 在 SM120 上跑不起来的四个独立阻塞点。"),
    ("src-vllm-56700", "https://github.com/vllm-project/vllm/issues/56700",
     "community", "vLLM issue tracker / Lei-010", "[SM120] Field report: DeepSeek-V4.1-Flash on 8x RTX PRO 6000",
     "2026-09-13", "2026-09-22", "en", "primary", "open", "",
     "vLLM 侧现场报告：8 卡跑通 + 1M 上下文验证 + 五个坑。"),
    ("src-sglang-40877", "https://github.com/sgl-project/sglang/issues/40877",
     "community", "SGLang issue tracker / Lei-010", "[SM120] Field report: DeepSeek-V4.1-Flash in production on 8x RTX PRO 6000",
     "2026-09-23", "2026-10-11", "en", "primary", "open", "",
     "SGLang 侧现场报告：唯一来源同时给出 1M 冷预填阶梯、并发曲线与被否拓扑。"),
    ("src-diffbot-exl3", "https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000",
     "community", "diffbot (HuggingFace)", "DeepSeek-V4.1-Flash-1017 EXL3 3-bit for 2x RTX PRO 6000 Blackwell",
     "2026-10-20", "", "en", "primary", "open", "MIT",
     "量化旁路：2 卡 96GB 可服务，8 卡双副本。含 KL/GSM8K/HumanEval 质量门。"),
    ("src-rtx6kpro-readme", "https://github.com/local-inference-lab/rtx6kpro",
     "community", "local-inference-lab", "RTX PRO 6000 Blackwell LLM Wiki (repo index)",
     "2026-10-20", "", "en", "primary", "open", "see repo",
     "仓库总索引；用于确认「已验证模型清单」里包含 V4.1-Flash。"),
    ("src-r6k-r38", "https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash-community-r38.md",
     "community", "local-inference-lab", "DeepSeek-V4.1-Flash community R38 deployment archive",
     "2026-10-05", "", "en", "primary", "open", "see repo",
     "R37/R38 的测量与依赖锁；作为 C1 数值的历史对照。"),
    ("src-sglang-cookbook", "https://docs.sglang.io/cookbook/autoregressive/DeepSeek/DeepSeek-V4_1",
     "official", "SGLang / LMSYS", "DeepSeek-V4.1 — SGLang cookbook",
     "2026-09-15", "2026-10-25", "en", "primary", "open", "",
     "官方 serving 文档。硬件矩阵只列 H200/B200/B300/GB300 与 MI355X，**不含 SM120**。"),
    ("src-aa-configs", "https://artificialanalysis.ai/hardware-inference-stack/configs",
     "review", "Artificial Analysis", "Inference Serving Configurations",
     "2026-10-30", "", "en", "primary", "open", "",
     "第三方配置库：133 个配置里 22 个是 V4.1-Flash，加速器清一色数据中心卡。"),
    ("src-qovery-selfhost", "https://www.qovery.com/blog/self-host-deepseek-v4-1-flash-gpu-setup-own-cloud",
     "vendor", "Qovery", "Self-Hosting DeepSeek V4.1-Flash: The Exact GPU Setup You Need",
     "2026-10-30", "", "en", "secondary", "open", "",
     "显存算术最完整的一篇，但数字多为转述（511GB 权重、614GB 驻留）。"),
    ("src-vllm-ascend-dsv41", "https://github.com/vllm-project/vllm-ascend/blob/main/docs/source/tutorials/models/DeepSeek-V4.1-Flash.md",
     "official", "vLLM-Ascend", "DeepSeek-V4.1-Flash on Ascend NPU",
     "2026-10-01", "", "en", "primary", "open", "Apache-2.0",
     "另一条硬件路线（8x128GB NPU），用作「换平台要换多少东西」的对照。"),
    ("src-tencent-deploy", "https://cloud.tencent.cn/developer/article/2740943",
     "press", "腾讯云开发者社区", "DeepSeek V4.1 Flash 部署完整指南",
     "2026-09-10", "", "zh", "tertiary", "open", "",
     "抓取只拿到页面骨架（正文需 JS 渲染），故**不用它支撑任何主张**；登记在册以记录失败抓取。"),
    ("src-r6k-daily",
     "https://github.com/local-inference-lab/rtx6kpro/blob/master/daily-summaries/2026-10/2026-10-25.md",
     "community", "local-inference-lab",
     "Community daily summary 2026-10-24 (contains a 4x Server Edition measurement)",
     "2026-10-25", "", "en", "primary", "open", "unknown",
     "社区日更。4×SE / Engram-on-RAM / 450W 的实测出处——"
     "初稿误判为「SE 无实测」即源于漏掉此页。"),
    ("src-r6k-bench",
     "https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/results.md",
     "community", "local-inference-lab",
     "Consolidated benchmark results (NCCL / power / cross-model)",
     "2026-11-01", "", "en", "primary", "open", "unknown",
     "汇总基准。8×SE 整机的 NCCL 总线带宽（37.6 / 22.2 GB/s）出自此页。"),
    ("src-r6k-model",
     "https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md",
     "community", "local-inference-lab",
     "DeepSeek-V4.1-Flash serving page (Karmic Kraken R38 measurements)",
     "2026-11-01", "", "en", "primary", "open", "unknown",
     "服务页。4×Max-Q 的 32K 预填 17,982 tok/s 与 RAM Engram 188.83 GiB 账目出自此页。"),
    ("src-diffbot-results",
     "https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000/blob/main/recipe/results/RESULTS.md",
     "community", "diffbot",
     "EXL3 3-bit full results page (8x Server Edition node, KL noise floor, agentic sessions)",
     "2026-10-24", "", "en", "primary", "open", "unknown",
     "EXL3 的完整结果页。8×SE 节点、KL 噪声底 0.0082、agentic 224.1 tok/s 均出自此页；"
     "HF 模型卡 README 只有摘要，细节在这一页——第二轮误删数字即因只读了 README。"),
    ("src-tacos4me-prune",
     "https://huggingface.co/tacos4me/DeepSeek-V4.1-Flash-Prune-2xRTX6K",
     "community", "tacos4me",
     "Expert-pruned 2x RTX PRO 6000 recipe (224/384 experts, native FP4)",
     "2026-10-28", "", "en", "primary", "open", "MIT",
     "第三条路线：剪枝而非量化。2 卡全驻显存、141 tok/s 单流、GPQA 92.9%。"),
    ("src-strata-4816",
     "https://github.com/Niko1221/Strata/issues/4816",
     "community", "Niko1221/Strata",
     "Single RTX PRO 6000 Workstation Edition on Windows 11 (IST-DAS 2.25 bpw)",
     "2026-10-31", "", "en", "primary", "open", "unknown",
     "单张 **Workstation** Edition + Windows：84 tok/s decode、1,889 tok/s 预填（16K）。"
     "用于界定「单卡能不能跑」，且明确是 WE 不是 SE。"),
]

# claim_id, statement, claim_type, confidence, evidence_ids, derivation, notes
CLAIMS = [
    ("c-v41-is-552b-moe",
     "DeepSeek-V4.1-Flash 是 552B 骨干参数的 MoE 模型，另有 196B Engram 参数；"
     "每个 token 在预填时激活 8B、解码时激活 16B。",
     "spec", "high",
     "e-552b-backbone;e-report-552b-196b;e-engram-196b;e-8b-16b-active",
     "", "参数分三部分：552B 骨干 + 196B Engram + 视觉塔。"),
    ("c-active-not-total",
     "决定显存的是总参数（552B+196B），决定算力的是激活参数（8B/16B）。"
     "把 16B 当作显存需求会低估一个数量级。",
     "spec", "high",
     "e-q-total-vs-active;e-q-511gb;e-report-552b-196b",
     "由 552B+196B 总参数与 FP8/FP4 混合精度推出权重大小≈511GB（第三方测算），"
     "与「16B 激活」相差 30 倍以上。",
     "这是本主题最常见的第一个错误。"),
    ("c-kv-890-bytes",
     "全局 KV cache 为每 token 890 字节（FP4 主 KV + CSA2 跨层共享），"
     "约为 V4-Flash 的 1/4；持久化 KV 约为 1/8。",
     "spec", "high",
     "e-kv-890;e-report-890;e-v41-smaller-kv;e-swa-eighth",
     "", "890 B/token 是官方口径，模型卡与技术报告一致。"),
    ("c-kv-implication",
     "按 890 字节/token 计，1M token（2^20）的 KV 仅约 0.87 GiB，"
     "故在该模型上显存几乎全部被权重占用，而不是 KV。",
     "measurement", "high",
     "e-kv-890;e-exl3-4454",
     "890 B × 1,048,576 ≈ 933 MB ≈ 0.87 GiB，与 diffbot 实测 KV_MEM=18 GiB 支持 4,538,321 token"
     "（≈4.25 KiB/token 的**含图捕获与对齐开销**口径）不同；二者口径不同，"
     "890 B 是纯 KV 尺寸，实测值含 CUDA graph 与分页对齐。",
     "口径差异必须写明，否则会得出互相矛盾的结论。"),
    ("c-se-spec",
     "RTX PRO 6000 Blackwell Server Edition：96GB GDDR7、1597 GB/s 带宽、"
     "24,064 CUDA 核心、FP4 4 PFLOPS / FP8 2 PFLOPS、最高 600W、被动散热。",
     "spec", "high",
     "e-se-96gb;e-se-1597;e-se-24064;e-se-fp4;e-se-fp8;e-se-600w;e-se-passive;e-variant-table",
     "", "与 WS 版同核心数，差别在带宽（1597 vs 1792）与散热形态。"),
    ("c-se-vs-ws-bandwidth",
     "Server 版带宽 1597 GB/s 低于 Workstation 版的 1792 GB/s（约 89%）。"
     "解码受带宽限制时，SE 版理论上比 WS 版慢约 11%。",
     "spec", "high",
     "e-se-1597;e-ws-1792",
     "1597 / 1792 = 0.891。这是**推算**，不是实测；未找到 SE 与 WS 在同条件下的 V4.1-Flash 对照。",
     "推断，须在正文标注。"),
    ("c-no-1m-on-2x96",
     "2 张 96GB 卡（合计 192GB）装不下 511GB 的原始 checkpoint，"
     "即使把 Engram 全部放主机内存也不够："
     "第三方测算「全部驻留」需约 614GB 显存，Engram 下放后仍需约 315–350GB 权重驻留显存。",
     "measurement", "medium",
     "e-q-511gb;e-q-eneed-614;e-q-engram-ram;e-q-315-350;e-q-single-4090-no;e-q-511gb-again",
     "", "来源为 secondary（转述 vLLM recipe），故降为 medium。"),
    ("c-min-4x96",
     "在 96GB 卡上，4 张是最低可行配置：4×96=384GB，恰好容纳 511GB 权重中下放 Engram 后"
     "仍需常驻的 ~315–350GB，"
     "加 KV、激活与图形/通信缓冲。2 张只在量化旁路（EXL3 3-bit）下可行。",
     "measurement", "medium",
     "e-q-315-350;e-exl3-2x;e-exl3-engram-int4;e-r6k-tp4;e-40877-tp4;e-q-511gb-again",
     "4×96=384 GB；315–350 GB 常驻 + KV（1M 上下文按 890 B/token 仅 0.87 GB）"
     "+ Engram 若留显存（2×~100GB）则 4 卡也装不下，必须先下放主机内存。",
     "这是全文的核心算术。"),
    ("c-tp8-on-8x96",
     "vLLM 路线在 8×RTX PRO 6000 上用 TP=8 跑通：~91GB/96GB 每卡，"
     "Engram 表两张各约 100GB 分片（合计 189GiB）占主导。",
     "measurement", "high",
     "e-56700-tp8;e-56700-91gb;e-56700-engram-189",
     "", "作者自述 3 天 bring-up，附环境版本。"),
    ("c-engram-dominates",
     "Engram 表（196B 参数）是该 checkpoint 里最大的单块权重，"
     "默认按 TP 组行分片驻留显存，每层多一次集合通信；"
     "SGLang 的 --engram-config '{\"placement\":\"cpu\"}' 把它整体搬到主机内存，"
     "腾出的 HBM 转给 KV 池。",
     "spec", "high",
     "e-sgl-engram-cpu;e-56700-engram-189;e-r6k-engram-not-kv;e-r6k-ram-engram-gib;e-report-196b",
     "", "Engram 不是 KV cache，这是另一个常见混淆。"),
    ("c-sglang-no-sm120",
     "SGLang 官方 cookbook 的 DeepSeek-V4.1 页面只在 H200/B200/B300/GB300 与 MI355X 上给配置；"
     "SM120 完全不在矩阵内，且该模型尚未进入任何 SGLang release，只能用 preview 镜像。",
     "attribution", "high",
     "e-sgl-hw;e-sgl-docker;e-sgl-sm100",
     "", "「官方没列」不等于「跑不了」，但意味着没有官方 recipe 可抄。"),
    ("c-aa-no-sm120",
     "第三方配置库 Artificial Analysis 收录的 22 个 V4.1-Flash 配置里，"
     "加速器清一色是数据中心卡（Vera Rubin NVL72 等），无一例 RTX PRO 6000。",
     "attribution", "medium",
     "e-aa-22of133;e-aa-rubin;e-aa-mxfp4",
     "", "只统计了该页 featured 与首屏；未逐条核对全部 133 条，故 medium。"),
    ("c-upstream-vllm-blocked",
     "上游 vLLM 无法在 SM120 上服务该模型：至少四个独立阻塞点，"
     "其中捆绑的 DeepGEMM 无 SM120 支持（layout.hpp 断言失败），"
     "回退到 CUTLASS 又缺 SM120 的 fp8-blockwise scaled-mm 内核。",
     "attribution", "high",
     "e-r6k-four-walls;e-r6k-deepgemm-sm120;e-r6k-1994",
     "", "该文写于 2026-07-03、针对 V4-Flash；V4.1-Flash 同期同栈，作者在别处确认。"),
    ("c-need-forked-image",
     "因此在 SM120 上部署 V4.1-Flash 的前提是**自带魔改镜像**："
     "vLLM 侧需 deepseekv41-flash-0909 一类分支，SGLang 侧需 dev-dsv41 preview 或社区 build。",
     "attribution", "high",
     "e-sgl-docker;e-r6k-four-walls;e-56700-tp8;e-40877-tp4",
     "", "两套栈的现场报告都用了非上游镜像。"),
    ("c-prefill-sgl-8x",
     "SGLang，8×RTX PRO 6000 Max-Q（PCIe，无 NVLink），128K 冷预填 6,853 tok/s；"
     "32K 提示约 7,196 tok/s；GPU 利用率约 87% 但只吃到 600W 中的 220W，"
     "瓶颈是 PCIe 通信而不是算力。",
     "measurement", "high",
     "e-40877-128k;e-40877-commbound;e-40877-220w;e-40877-32k",
     "", "作者自己把变体差异判为落在 ±1.3% 噪声内（no-winner）。"),
    ("c-prefill-ceiling",
     "在该主板上约 7K tok/s 就是无 NVLink 的预填天花板；"
     "唯一的大倍率来自前缀缓存：112K token 命中时 0.34 s ≈ 325K tok/s（约 39 倍）。",
     "measurement", "high",
     "e-40877-commbound;e-40877-radix;e-40877-cachehit-325k",
     "", ""),
    ("c-decode-dspark",
     "解码侧，投机解码 DSpark 是「可用 vs 不可用」的分界："
     "关掉后无论提示类型都塌到约 36.5 tok/s；开启后散文 76.5–78.9、结构化 120.3–120.5 tok/s，"
     "生产用 block_size=6 时结构化约 237–252 tok/s。",
     "measurement", "high",
     "e-40877-dspark-ab;e-40877-36-5;e-40877-decode;e-40877-dspark-table;e-40877-block6",
     "", "A/B 两组各自通过 server_info 配置门与接受长度核验。"),
    ("c-decode-tp4-conc",
     "同一台机器改跑 4 卡 TP4/EP4 后：单流 115.2 tok/s，8 并发合计 468.2 tok/s（4.06×），"
     "8 是硬上限（max_running_requests=8 且 decode 图只捕到 bs=8）。",
     "measurement", "high",
     "e-40877-tp4;e-40877-conc-table",
     "", "作者声明 N=2，不是误差棒。"),
    ("c-1m-cold-5min",
     "1M 上下文的冷预填在这台机器上约 5 分钟（310.5 秒）："
     "402K→5,065 tok/s，704K→4,022，906K→3,478，1,006,538→3,242（重复 322.0 秒 / 3,126）。",
     "measurement", "high",
     "e-40877-1m-ladder;e-40877-cold-1m;e-40877-cold-ladder",
     "", "冷预填要求每行提示带唯一标记；否则测到的是前缀缓存命中。"),
    ("c-cache-artifact",
     "流传的「1040K 在 74.5 s 内完成（13,962 tok/s）」是前缀缓存命中造成的假象："
     "900K 前缀已在 radix cache 里，实际只预填了约 140K。"
     "作者更正了自己更早的「409K=62.7s」同属此artifact。",
     "measurement", "high",
     "e-40877-artifact;e-40877-1m-ladder",
     "", "这条是本主题最重要的一条测量方法论教训。"),
    ("c-long-ctx-collapse",
     "长上下文并发会塌：4 个 906K 上下文的请求各生成 256 token 共 8.6 s，"
     "合计仅 29.7 tok/s（每流约 7.4）。这个端点擅长服务一个重请求，而不是多个。",
     "measurement", "high",
     "e-40877-longconc",
     "", ""),
    ("c-vram-ceiling",
     "1M 配置下 GPU 稳定在 96.8/97.9 GB（98.9%），余量约 1 GB；"
     "量化旁路的 1.04M 提示峰值 96,655–97,029 MiB / 97,887 MiB。"
     "两条独立路线都撞到同一面墙：96GB 是硬边界。",
     "measurement", "high",
     "e-40877-vram-98;e-exl3-96gb",
     "", ""),
    ("c-sgl-rejects-dp",
     "SGLang 在该模型上拒绝 DP 拓扑：DP2×TP4 直接抛 "
     "「V4.1 vision currently supports TP/EP without DP, CP, PP or MoE A2A」，两个副本约 70 s 内死亡；"
     "prefill 的上下文并行同类被拒；单独 --enable-dp-attention 则静默不生效（dp_size 仍为 1）。",
     "measurement", "high",
     "e-40877-dp-reject;e-40877-vision-tp",
     "", "「静默不生效」比报错更危险——它会让人把旧配置当成新配置记录。"),
    ("c-vllm-1m-verified",
     "vLLM 路线在 8 卡上验证了 1M 上下文：950K token 双针检索正确，"
     "预填 4,584 tok/s（纯 torch logits 路径、eager 模式）。",
     "measurement", "high",
     "e-56700-1m;e-56700-prefill",
     "", "「能跑」与「跑得快」是两件事：4,584 vs SGLang 的 6,853（128K）。"),
    ("c-fp8-kv-layout-pitfall",
     "最致命的坑是 FP8 KV cache 的 scale 布局语义：块布局是 "
     "[64tok×128B fp8 | 64tok×4B fp32 scale]（块尾追加），不是逐 token 交错。"
     "理解错时短提示冒烟测试全过，只在 ≥100K 检索时暴露——是静默的数值损坏。",
     "measurement", "high",
     "e-56700-fp8-layout;e-56700-silent",
     "", "作者的建议是「用长针测试，不要用困惑度」。"),
    ("c-marlin-fallback",
     "MXFP4 专家路径在 SM120 上回退到 Marlin 内核（已知 issue #30135），能跑，性能损失可接受。",
     "measurement", "high",
     "e-56700-marlin",
     "", ""),
    ("c-deepgemm-hang",
     "首次长上下文批会触发 DeepGEMM autotune 挂死（128K 以上），"
     "bring-up 阶段需要跳过 autotune 或用 eager 模式。",
     "measurement", "high",
     "e-56700-deepgemm-hang",
     "", ""),
    ("c-stable-tp4-profile",
     "社区给出的稳定生产profile是 4 卡 TP4/DCP1 + adaptive DSpark K7 + Engram 放主机内存："
     "C1 249.1 tok/s、C8 合计 805.5 tok/s、32K 预填 17,982 tok/s、"
     "4,727,748 逻辑 KV token。",
     "measurement", "high",
     "e-r6k-tp4;e-r6k-c1;e-r6k-c8;e-r6k-32k;e-r6k-kvtokens",
     "", "⚠️ 条件是 **Max-Q 版、325W 功耗上限、显存 +6000 超频**，不是 Server 版。"),
    ("c-r6k-not-se",
     "上述 4 卡数据全部来自 Max-Q Workstation Edition（325W、超频），"
     "不能直接当作 Server Edition 的数值：SE 无显存超频（返回错误）、带宽低 11%。",
     "attribution", "high",
     "e-r6k-maxq-clocks;e-msrp-nvml;e-ws-1792;e-se-1597",
     "", "这是本主题最容易被忽略的一条口径边界。"),
    ("c-engram-188gib",
     "Engram 表放主机内存时实测占 188.83 GiB，且启动更慢；"
     "放磁盘（默认）功能等价但不是同一组吞吐测量。",
     "measurement", "high",
     "e-r6k-ram-engram-gib;e-r6k-tp4",
     "", ""),
    ("c-power-scaling",
     "功耗档位对这张卡的影响是非线性的：600W→500W 几乎无差别；"
     "600W→300W 单用户仅损失约 4%。故「SE 的 600W」在单流推理上不是瓶颈。",
     "measurement", "high",
     "e-power-scaling;e-600w-to-300w;e-40877-220w",
     "", "社区页数据；与 40877 实测「只吃 220W」互相印证。"),
    ("c-tp-power-of-2",
     "vLLM/SGLang 要求 TP 为 2 的幂（2/4/8/16），奇数卡只能走流水并行（如 TP2 PP3 = 6 卡）。",
     "spec", "high",
     "e-tp-constraint",
     "", ""),
    ("c-api-price",
     "官方 API 价格：输出每百万 token 峰时 $1.2 / 谷时 $0.6；"
     "输入缓存命中峰时 $0.006；上下文 1M；并发上限 2500。",
     "price", "high",
     "e-api-flash-price;e-api-cache-hit;e-api-1m;e-api-concurrency;e-v41-offpeak",
     "", "峰时为 UTC 周一至周五 01:00-04:00 与 06:00-10:00。"),
    ("c-selfhost-breakeven",
     "按第三方测算，8×H200 节点要持续产出约 14,650 输出 token/s 才能追平 API 价格；"
     "在本主题的 4–8 卡 RTX PRO 6000 上，实测单流 115–249 tok/s、8 并发 468 tok/s，"
     "与盈亏平衡点相差两个数量级。",
     "prediction", "medium",
     "e-api-flash-price;e-40877-tp4;e-r6k-c1;e-r6k-c8;e-q-511gb-again",
     "14,650 tok/s 来自 Qovery 的 8×H200 测算（$63/h ÷ $1.2/Mtok）。"
     "本归档实测值来自不同硬件，比值只能作量级参照，不是同条件对照。",
     "推断，条件不同，只作量级参照。"),
    ("c-selfhost-for-control",
     "故自建的理由是数据主权与可定制，不是省钱："
     "同等吞吐下 API 便宜一到两个数量级，且并发上限 2500 远高于单机 8–32。",
     "prediction", "medium",
     "e-api-concurrency;e-40877-tp4;e-r6k-c8;e-r6k-tp4",
     "由 c-api-price 与 c-selfhost-breakeven 合并推出。",
     "推断。"),
    ("c-minimum-viable",
     "最小可行部署是三选一：① 8×96GB 全精度（vLLM TP8 或 SGLang TP8/TP4）；"
     "② 4×96GB 全精度（SGLang TP4/EP4，需魔改镜像）；"
     "③ 2×96GB + EXL3 3-bit 量化（可用但引入 KL 0.03–0.05 的质量代价）。",
     "prediction", "high",
     "e-56700-tp8;e-40877-tp4;e-exl3-2x;e-exl3-engram-int4",
     "按「权重体积 ÷ 单卡 96GB」分档：511GB 原始权重需 ≥6 卡才装得下（实际取 8 卡 TP8 或 4 卡 TP4+Engram 下放），"
     "EXL3 3-bit 把权重压到 2 卡可容纳。三档分别对应三组独立实测。",
     "这是对全文证据的归纳，不是任何单一来源的说法。"),
    ("c-quant-quality-cost",
     "EXL3 3-bit 旁路的质量证据是 KL 与任务准确率，且**两者都在重跑噪声内**："
     "KL 0.0519 / 0.0311 / 0.0110 / 0.0344（short100 四类语料），"
     "GSM8K / HumanEval 从 98.5 / 95.7 到 99.0 / 97.6。"
     "原文的措辞是「stayed within run-to-run noise」与「within run-to-run noise」。",
     "measurement", "high",
     "e-exl3-kl-noise;e-exl3-gsm8k;e-exl3-no-noise-floor;e-exl3-2x",
     "",
     "⚠️ 本条曾写作「KL 高于噪声底 6 倍，是可观测的质量下降」，并编造了 0.0082 这个噪声底。"
     "原文说的是没有超出噪声。方向被写反了，已按原文更正。"),
    ("c-exl3-throughput",
     "EXL3 2 卡旁路（TP2、300 W 上限、Max-Q）的绝对吞吐："
     "**agentic 单会话解码 224.1 tok/s**（同轮墙钟 228.7 s）；"
     "固定提示下 2K 单流 156.9、**46K 单流中位 172.8**、46K 四流聚合 362.9 tok/s；"
     "**40K 冷预填 11,157 / 11,467 tok/s**。开启 CPU runtime 后提高到 261.8 tok/s / 210.1 / 406.2 / 11,624–12,182。",
     "measurement", "high",
     "e-exl3-agentic-224;e-exl3-fixedprompt;e-exl3-prefill-40k",
     "",
     "⚠️ 注意「224.1 tok/s」与「224.0 s」是两个不同的数，同页并存：前者是解码吞吐，后者是墙钟时间。"
     "第二轮曾误判为「把秒当 tok/s」并删掉该数字，是错的。"),
    ("c-exl3-2x-throughput",
     "2 卡 EXL3 旁路在 TP2、350 W 限功耗下的实测：单流解码 163.6 tok/s（2K 上下文）、"
     "46K 中位 202.9 tok/s；四流 46K 聚合 361.6 tok/s；40K 冷预填约 11.9k tok/s。"
     "社区用户在实际使用中报告多为 200–300 tok/s。",
     "measurement", "high",
     "e-exl3-2x-throughput",
     "",
     "这条与 c-exl3-throughput 并列而非替代：那条测预填与质量的同日 A/B，"
     "这条测限功耗下的解码分档。两者回答的不是同一个问题。"),
    ("c-se-8x-measured",
     "**8 卡 Server Edition 已有全精度实测**（云 VM、EPYC 9B45、1.4 TB RAM、PCIe 5 无 NVLink）："
     "同一镜像与权重包，一次只跑一个 4 卡副本（TP4+EP4）。用 code-tuned DSpark head（k=7、1M 窗口）后，"
     "单流 code 403.5 tok/s（峰值 484）、codegen 444.6 tok/s；"
     "codeconc 聚合在 C=1/8/32/64/128 为 394 / 1,301 / 2,509 / 3,439 / 4,404 tok/s；"
     "128 流长生成 2,634 tok/s。",
     "measurement", "high",
     "e-exl3-8se-node;e-exl3-8se-codeconc;e-exl3-8se-single",
     "",
     "⚠️ 这是本课题最想要的一格，且它确实存在。注意测的是 **TP4 单副本**（8 卡分两组），"
     "不是 8 卡一个 TP8 副本——后者仍无公开数据。"),

    ("c-prune-route",
     "第三条路线是**专家剪枝**而非量化：按路由频率保留 224/384 个专家（四语料均衡），"
     "使 552B 模型在 **2×96 GB** 上全驻显存、保留原生 FP4。实测单流解码 141 tok/s、"
     "3 流 288 tok/s、预填约 9,800 tok/s（910K 提示 93 s）；质量 GPQA Diamond 92.9%、GSM8K 198/200。"
     "对照：不剪枝而改为从 NVMe 流式读专家，只有 8–9 tok/s。",
     "measurement", "high",
     "e-prune-2x;e-prune-quality",
     "",
     "与 EXL3（3-bit 量化）是不同取舍：剪枝保精度但丢专家，量化保专家但降位宽。"),
    ("c-vision-native",
     "该模型原生支持图像输入（DeepSeek-ViT + MLP projector，2D-RoPE、3×3 pixel-unshuffle），"
     "但 API 侧对 deepseek-v4-pro 不支持视觉，只有 deepseek-flash 支持。",
     "spec", "high",
     "e-vision-native;e-api-vision",
     "", ""),
    ("c-no-chat-template",
     "该 release 不含 Jinja 格式的 chat template，需用官方 encoding 目录下的脚本做提示编码。",
     "spec", "high",
     "e-no-jinja",
     "", "这是很多「部署完发现对话格式不对」的根因。"),
    ("c-decode-flops-flat",
     "解码 FLOPs 几乎不随上下文增长：上下文从 4K 拉到 1M（256 倍），"
     "单 token 解码 FLOPs 只涨 1/4。",
     "spec", "high",
     "e-report-flops-flat;e-report-890",
     "", ""),
    ("c-ascend-alt",
     "另一条硬件路线存在但代价高：vLLM-Ascend 用 8×128GB NPU 单机做 W8A8 + INT8 Engram，"
     "且必须显式设 VLLM_USE_V2_MODEL_RUNNER=0。",
     "attribution", "high",
     "e-ascend-a3",
     "", "作为「换平台要换多少东西」的对照，不构成对 NVIDIA 路线的评价。"),
    ("c-se-measured-but-thin",
     "Server Edition **确有实测，但覆盖极不均匀**：4 卡有一组完整吞吐"
     "（Engram 放主机 RAM、450W 限功耗：单流解码 183 tok/s、16 流聚合 695 tok/s、"
     "预填 18,400–19,200 tok/s）；8 卡整机（双路 EPYC 9575F、2.2 TB DDR5-6400、3× xGMI）"
     "只有互连数据（NCCL 总线带宽 37.6 GB/s，默认仅 22.2 GB/s），**没有 DS4.1 吞吐**。"
     "本课题最关心的「8 卡全精度、默认功耗、SE」这一格仍是空的。",
     "measurement", "high",
     "e-se-4x-measured;e-se-8x-rig;e-se-nccl;e-se-1597",
     "把 5 组社区实测按「卡数 × 变体 × 是否限功耗」排成表：只有 4×SE/450W 一格有吞吐，"
     "8×SE 一格只有互连数据第十九；其余格由 Max-Q 或未标变体填充。",
     "⚠️ 本条曾写作「没有任何来源在 SE 上实测过」，并自称「本文最诚实的结论」。"
     "那是检索覆盖不足造成的假否定——社区日更里有明确的 4×SE 实测。已按原文更正。"),
    ("c-se-no-mem-overclock",
     "Server Edition 不支持显存超频：对 SE 卡设置显存时钟偏移会**返回错误**，"
     "只有 Max-Q 接受该偏移。故社区里那些「超频显存换来的几个百分点」"
     "（如 8×Max-Q 的 +4000 偏移）在 SE 上无法复现。",
     "spec", "high",
     "e-se-no-mem-oc;e-r6k-maxq-clocks",
     "",
     "这是 SE 与 Max-Q 之间一条**硬性**差异：不是调优偏好，是硬件/驱动直接拒绝。"),

    ("c-engram-ram-need",
     "把 Engram 放主机 RAM 的代价是可量化的：按 TP4 历史账目，表本身 188.83 GiB，"
     "另加 loader / server / OS 内存。RAM 分配失败**不会**静默退回磁盘模式。",
     "spec", "high",
     "e-engram-188-83;e-exl3-engram-int4",
     "",
     "很多人以为「放不下就自动降级」，实际是直接失败。"),
]


def main() -> int:
    import re

    ev_path = ROOT / "evidence.csv"
    with ev_path.open(encoding="utf-8-sig") as fh:
        have = {r["evidence_id"] for r in csv.DictReader(fh)}
    doc_ok = set()
    with (ROOT / "documents.csv").open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            doc_ok.add(r["source_id"])
    src_ids = {s[0] for s in SOURCES}

    problems: list[str] = []
    for cid, stmt, ctype, conf, evs, deriv, notes in CLAIMS:
        for e in [x for x in evs.split(";") if x.strip()]:
            if e not in have:
                problems.append(f"{cid} 引用了不存在的证据 {e}")
        if conf == "high" and not deriv and not evs:
            problems.append(f"{cid} 高置信但无证据")
        if ctype == "prediction" and not deriv:
            problems.append(f"{cid} 是推断但没有 derivation（不变量 C2）")
    for s in SOURCES:
        if s[0] not in doc_ok:
            problems.append(f"来源 {s[0]} 没有任何文档快照")
        if not re.search(r"[+-]\d{2}:\d{2}|Z$", FETCHED):
            problems.append("FETCHED 缺时区")
    for sid in doc_ok:
        if sid not in src_ids:
            problems.append(f"文档 {sid} 未登记进 sources.csv（不变量 S1/S2 的闭合性）")

    if problems:
        print("归档不闭合：")
        for p in problems:
            print("  - " + p)
        return 1

    with (ROOT / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["source_id", "url", "source_type", "publisher", "title",
                    "published_at", "updated_at", "fetched_at", "language",
                    "trust_tier", "access", "license", "notes"])
        for sid, url, stype, pub, title, pub_at, upd_at, lang, tier, acc, lic, notes in SOURCES:
            w.writerow([sid, url, stype, pub, title, pub_at, upd_at, FETCHED,
                        lang, tier, acc, lic, notes])

    with (ROOT / "claims.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, evs, deriv, notes in CLAIMS:
            w.writerow([cid, stmt, ctype, "2026-11-05", conf, evs, "", deriv, notes])

    print(f"已写 sources.csv：{len(SOURCES)} 个来源")
    print(f"已写 claims.csv：{len(CLAIMS)} 条主张")
    dist: dict[str, int] = {}
    for _, _, _, conf, _, _, _ in CLAIMS:
        dist[conf] = dist.get(conf, 0) + 1
    print("置信度分布：" + ", ".join(f"{k}={v}" for k, v in sorted(dist.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
