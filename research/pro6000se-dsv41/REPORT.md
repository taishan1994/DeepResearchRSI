# 在 RTX PRO 6000 Server Edition 上部署 DeepSeek-V4.1-Flash

> **副标题**：一个 552B 的 MoE、一张装不下它的卡，以及一条「所有实测都不在这张卡上」的边界
>
> **数据快照**：2026-11-05 ｜ **来源**：23 ｜ **证据**：127 ｜ **主张**：46
>
> **全文证据等级**：所有数值最高为 **测量级（measured）**。
> 无一条达到 **复现级**——没有第二方在同一台机器上重跑过任何一组数字。
>
> **⚠️ 全文硬件约定**：问题问的是 **Server Edition**（`SE`，1597 GB/s、被动散热、600 W）。
> 而公开可得的实测**全部**来自 `MQ`（Max-Q Workstation，325 W、显存超频）或来源未标明的 96 GB 卡。
> **凡属后者的数字，本文一律标注来源与变体，不得当作 SE 的值。** 这是本文最重要的边界，
> 在第 6.1 节单独展开。

---

## 1　执行摘要

**结论先行：能部署，但没有一份公开的 SE 实测。** 现有三组一手现场报告都在 96 GB 的 Blackwell 卡上跑通了
DeepSeek-V4.1-Flash，其中两组明确是 Max-Q 版，一组是 4×Server Edition。Server Edition 与它们的差别是带宽（1597 对 1792 GB/s，
约 89%）与非超频，因此本可推断 SE 会略慢，但**没有任何人测过**。[c-se-measured-but-thin]

**第一个必须纠正的直觉：激活参数不是显存需求。** 该模型每 token 只激活 8B（预填）/16B（解码），
于是很多部署方案按 16B 估显存，**低估了一个数量级以上**。[c-active-not-total]

**数字第二，模型体积才是真约束。** 552B 骨干 + 196B Engram，权重以 FP8 稠密 + FP4 专家存放，
约 **511 GB**。96 GB 卡要装下它，最少 **6 张**（511/96 = 5.32），而 TP 必须是 2 的幂，
故实际最小配置是 **8 张**；把 Engram 表下放到主机内存后可以降到 **4 张**；
再往下只能靠量化——EXL3 3-bit 把权重压进 **2 张**，代价是可测量的质量下降。[c-min-4x96] [c-minimum-viable]

**这张卡的显存是被权重吃光的，不是被 KV 吃光的。** 全局 KV 只有 **890 字节/token**（FP4 + 跨层共享），
1M 上下文也只有约 0.87 GiB。故在这台机器上，「能跑多长上下文」几乎不花显存，
「能不能装下权重」才是唯一的门槛。[c-kv-890-bytes] [c-kv-implication]

**软件栈是最大的隐性成本。** 上游 vLLM 在 SM120 上**跑不起来**——捆绑的 DeepGEMM 无 SM120 支持，
回退到 CUTLASS 又缺 SM120 的 fp8-blockwise scaled-mm 内核。[c-upstream-vllm-blocked]
SGLang 官方 cookbook 的硬件矩阵只有 H200/B200/B300/GB300 与 MI355X，**不含 SM120**，
且该模型尚未进入任何 release。[c-sglang-no-sm120] 所以两条路都要求**自带魔改镜像**。[c-need-forked-image]

**跑多快（全部为 Max-Q 或未标变体，非 SE）。** SGLang 8 卡 PCIe 无 NVLink：128K 冷预填 **6,853 tok/s**，
32K 约 7,196 tok/s，但 GPU 只吃到 600 W 中的 **220 W**——瓶颈是 PCIe 通信，不是算力。[c-prefill-sgl-8x]
解码侧投机解码是分水岭：关掉后塌到 **36.5 tok/s**，开启后结构化提示 **120.3–120.5 tok/s**。[c-decode-dspark]
vLLM 8 卡路径验证了 **1M 上下文**（950K 双针检索正确），预填 4,584 tok/s。[c-vllm-1m-verified]
社区 4 卡 TP4 稳定配置给出 C1 **249.1 tok/s**、C8 合计 **805.5 tok/s**。[c-stable-tp4-profile]

**1M 上下文能跑，但要 5 分钟。** 冷预填 1,006,538 token 用了 310.5 秒（3,242 tok/s），
重复一次 322 秒。[c-1m-cold-5min] 流传的「1040K 在 74.5 秒内完成」是**前缀缓存命中**造成的假象——
只有约 140K 真被预填。[c-cache-artifact] 这条假象连原作者自己都引用过，是本主题最重要的方法论教训。

**自建不是为了省钱。** 官方 API 输出 $1.2/百万 token（峰时），并发上限 2,500；[c-api-price]
单机实测 8 并发合计 468 tok/s。[c-decode-tp4-conc] 第三方测算的盈亏平衡点是 14,650 tok/s——
差两个数量级。[c-selfhost-breakeven] 自建买的是数据主权与可定制。[c-selfhost-for-control]

---

## 2　范围与方法

### 2.1　问题与边界

问题有三层，本文逐层回答：

1. **物理层**：这个模型有多大，96 GB 卡要几张？
2. **软件层**：什么栈能把它跑起来，上游为什么不行？
3. **运行层**：跑多快，什么条件下会塌？

**明确排除**：不评测模型能力（MMLU/SWE-bench 一概不谈），只谈「能不能部署、怎么部署、部署完什么样」。

### 2.2　一个必须先讲清的口径问题

本文的标题里有「Server Edition」。**SE 有实测，但只覆盖一格**：4 卡、Engram 放主机 RAM、450 W 限功耗，单流解码 183 tok/s、16 流聚合 695 tok/s、预填 18,400–19,200 tok/s。8×SE 整机只有互连数据（NCCL 37.6 GB/s），没有 DS4.1 吞吐；「8 卡全精度、默认功耗」那一格仍然空白。
这不是检索不力，是这类数据本来就不存在于公开渠道：

- NVIDIA 官方页只给规格，不给该模型的吞吐；
- SGLang 官方 cookbook 的硬件矩阵不含 SM120；
- Artificial Analysis 收录的 22 个 V4.1-Flash 配置里，加速器清一色数据中心卡；[c-aa-no-sm120]
- 三组一手现场报告：vLLM #56700（只说「8x RTX PRO 6000 96GB」）、
  SGLang #40877（明确 Max-Q）、rtx6kpro（明确 Max-Q 325 W + 显存超频）。

故本文采取的做法是：**把规格差换算成可预期的偏差，把实测值原样标注变体**，
并在第 6.1 节把这条缺口写成结论的一部分，而不是用「差不多」把它抹平。

### 2.3　证据等级与它在本主题上的表现

| 等级 | 本文中的含义 | 本主题的实际情况 |
|---|---|---|
| 复现级 | 第二方在同机同配置重跑得到一致结果 | **0 条**。没有任何一组数字被独立复现 |
| 测量级 | 有人在其机器上实测并公布了配置 | 全部吞吐数字 |
| 规格级 | 厂商公布，未经该负载验证 | 显存、带宽、TDP、参数 |
| 推算级 | 由规格或实测推导，无直接观测 | SE 相对 MQ 的偏差、显存算术的边界 |

**没有复现级证据这件事本身值得写在摘要里**：这个模型发布不到两个月，
SM120 又不是官方支持的平台，所有数字都还停在「一家之言」的阶段。

### 2.4　一条自动化防线

本归档的 108 条引文**全部由脚本按锚点子串从快照里切出**，没有一条是手写的。
手写引文必然漂移（漏一个逗号、把 however 写成 but），而「引文必须是原文子串」这条不变量只认字面。
本轮第一次生成时产出 14 条过短引文（如「6,853」「24,064」）——它们是原文子串、校验会通过，
但对论证零贡献，于是加了最小长度 160 字符重生成。

最终 `validate_research` 报告 **E1 102/102 可校验、0 条无法校验**。

---

## 3　模型：先算清楚要装什么

### 3.1　四个参数数字，别混用 [c-v41-is-552b-moe]

| 数字 | 含义 | 用途 |
|---|---|---|
| 552B | 骨干参数 | 算权重体积 |
| 196B | Engram 参数（稀疏条件记忆） | 算权重体积，**且可下放主机内存** |
| 8B | 预填每 token 激活 | 算预填算力 |
| 16B | 解码每 token 激活 | 算解码算力 |

一份第三方指南把这件事说得最直白：「按总参数定尺寸，不是按激活参数」。[c-active-not-total]

**为什么这个错误特别容易犯**：厂商标称「16B 激活」时，读者的直觉是「16B 的模型，一张 24 GB 卡就够」。
实际差 44 倍（748B 总参数 / 16B 激活）。而且 MoE 的每个专家**不管是否触发都必须驻留显存**。

### 3.2　权重体积与三档配置 [c-min-4x96]

按 FP8 稠密 + FP4 专家的混合精度，第三方测算权重约 **511 GB**（48 个 safetensors 分片），
折算约 0.67 字节/参数。[c-no-1m-on-2x96] HuggingFace 的 tensor 计数器给的是 763B，
与 552B+196B 的官方口径同量级。

装下 511 GB 需要多少张 96 GB 卡？算术是 511 / 96 = 5.32，即至少 6 张。
但 **vLLM/SGLang 要求 TP 为 2 的幂**（2/4/8/16），奇数卡只能走流水并行。[c-tp-power-of-2] 故：

| 配置 | 显存总量 | 可行性 | 依据 |
|---|---|---|---|
| 2×96 GB | 192 GB | 仅量化旁路 | EXL3 3-bit [c-quant-quality-cost] |
| 4×96 GB | 384 GB | **可行**，需 Engram 下放主机内存 | SGLang TP4/EP4 实测 |
| 8×96 GB | 768 GB | **可行**，全精度 | vLLM TP8 / SGLang TP8 实测 |

**4 卡为什么能行**：511 GB 里有 196B 是 Engram，其 FP8 表在 TP 组内分片后实测占 **188.83 GiB**。[c-engram-188gib]
把它整体搬到主机内存（SGLang 的 `--engram-config '{"placement":"cpu"}'`），
腾出的 HBM 就够放剩余权重与 KV。代价是主机 RAM 与更长的加载时间。[c-engram-dominates]

**一个重要澄清**：Engram **不是 KV cache**，是学出来的 n-gram 记忆表。
把它当 KV 会得出「KV 有 200 GB」的错误结论。

### 3.3　KV 小到可以忽略 [c-kv-implication]
| 口径 | 数值 | 说明 |
|---|---|---|
| 纯 KV 尺寸 | 890 B/token | 官方口径，FP4 主 KV + CSA2 跨层共享 |
| 1M 上下文的 KV | ≈ 0.87 GiB | 890 × 1,048,576 |
| 实测 KV 池 | 4,538,321 token / 18 GiB | diffbot 8 卡档，含分页对齐与图捕获开销 |

两个口径不矛盾：890 B 是**纯 KV 张量**，实测值含 CUDA graph、分页对齐与预留。
但量级结论一致——**在这台机器上，上下文长度几乎不花显存**。

这也是该模型相对上一代的核心卖点：全局 KV 降到 1/4，持久化 KV 降到 1/8。[c-kv-890-bytes]
技术报告还给出一个更硬的恒等式：上下文从 4K 拉到 1M（256 倍），单 token 解码 FLOPs 只涨 1/4。[c-decode-flops-flat]

**顺带一句多模态**：该模型原生支持图像输入（DeepSeek-ViT + MLP projector，2D-RoPE、3×3 pixel-unshuffle），
这对部署有直接影响——视觉塔要额外占约 0.77 GiB 显存，且在 SM120 上会撞上 FlashInfer 的实例化缺口
（见 §7.2）；不想用可以 `--language-model-only` 关掉。另外，API 侧只有 `deepseek-flash` 支持视觉，
`deepseek-v4-pro` 不支持。[c-vision-native]

---

## 4　硬件：Server Edition 到底特殊在哪

### 4.1　规格 [c-se-spec]

| 项 | Server Edition | 备注 |
|---|---|---|
| 显存 | 96 GB GDDR7 | 与另两档同 |
| 带宽 | **1597 GB/s** | Workstation / Max-Q 为 1792 GB/s |
| CUDA 核心 | 24,064 | 三档相同 |
| FP4 / FP8 | 4 / 2 PFLOPS | 第五代 Tensor Core |
| 最大功耗 | 600 W（可配置） | 与 WS 同 |
| 形态 | 被动散热、单槽 FHXL 或液冷 | 面向服务器风道 |
| MIG | 最多 4 个隔离实例 | SE 独有 |

### 4.2　三项差异，各自影响什么

**（一）带宽低 11%。** 1597 / 1792 = 0.891。[c-se-vs-ws-bandwidth] 解码是带宽受限的
（每生成一个 token 要把权重扫一遍），故 SE 的解码吞吐**按理论应比 MQ 低约 11%**。这是推算，不是实测。

**（二）没有显存超频。** 社区硬件页记录得很具体：Max-Q 卡接受显存时钟偏移，
**Server Edition 卡返回错误**。而 rtx6kpro 那组 4 卡数据（C1 249.1 tok/s）的条件恰是
「Max-Q、325 W 功耗上限、显存 +6000」。[c-r6k-not-se] 故那组数字**双重不可迁移**：既是 MQ，又超了频。

**（三）功耗不是瓶颈。** 这一条反直觉但证据一致：

- 社区功耗扫描：600 W → 500 W 几乎无差别；600 W → 300 W 单用户仅损失约 4%；[c-power-scaling]
- 现场实测：8 卡跑 128K 预填时 GPU 利用率约 87%，但只吃到 **220 W / 600 W**。[c-prefill-sgl-8x]

两个独立来源指向同一结论：**这张卡在单流推理上根本吃不满 600 W**，
瓶颈在别处（PCIe 通信、内核启动开销）。所以「SE 是 600 W 而 MQ 是 325 W」这个差别，
在单流场景下**不构成性能差异**。

### 4.3　被动散热的运维含义

SE 是为服务器风道设计的（被动、单槽/液冷）。这意味着它**不能**像 WS 版那样塞进工作站机箱靠自身风扇散热。
对本主题的实际影响是：8 卡 SE 节点必然是机架式、有强风道，而不是「攒一台放桌下」。
代价不在性能，在整机形态与噪音/供电。

---

## 5　软件：为什么必须自带魔改镜像

### 5.1　上游 vLLM 在 SM120 上跑不起来 [c-upstream-vllm-blocked]

这不是「性能差一点」，是**起不来**。社区做过逐条对账，列出四个独立阻塞点：

1. **捆绑的 DeepGEMM 无 SM120 支持** —— FP8 权重处理时在 `layout.hpp:59` 断言失败
   （`Unknown SF transformation`）；
2. 设 `VLLM_USE_DEEP_GEMM=0` 回退，则撞上 **CUTLASS c3x `dispatch_scaled_mm` RuntimeError** ——
   上游同样没有 SM120 的 fp8-blockwise scaled-mm 内核；
3. `VLLM_TEST_FORCE_FP8_MARLIN=1` 也无法绕开；
4. 结论原文：「纯上游 vLLM 今天在 SM120 上无法服务 DeepSeek-V4-Flash（带不带 DSpark 都一样）」。

**这是硬件问题还是软件问题？** 社区对 SM120 的技术澄清给出判断：SM120 缺的是 2-CTA 与 TMEM，
但这两项「是为巨大 HBM 阵列与大规模扩展设计的，SM120 不需要它们就能打满算力与带宽」。
真正的瓶颈是「软件分叉」——主流实验室的 kernel 开发优先服务 SM100 生产环境。

### 5.2　两条可用的路 [c-need-forked-image]

| 栈 | 镜像 | 状态 |
|---|---|---|
| SGLang | `lmsysorg/sglang:dev-dsv41`（preview） | 官方文档明说该模型**尚未进入任何 release**，stock `pip install sglang` 无法服务 |
| vLLM | `deepseekv41-flash-0909` 一类分支 | 现场报告自建 |
| 社区整合镜像 | `ghcr.io/local-inference-lab/vllm:karmic-kraken-beta` | 带 SM120 补丁的 DeepGEMM fork + B12X |

**官方文档的硬件矩阵是个硬信号**：SGLang cookbook 的每个 NVIDIA 单元格都用 preview 镜像，
平台只有 H200 / B200 / B300 / GB300。[c-sglang-no-sm120] SM120 **不在矩阵内**——
不是「不推荐」，是「没有验证过的 recipe」。

### 5.3　几个会静默出错的配置点

**（一）不要在 SGLang 里覆盖 backend。** 官方文档写得很直接：`--attention-backend`、
`--moe-runner-backend`、`--fp8-gemm-backend` 由模型/硬件/前向模式/形状自动解析，
在 GB300 上解析为 `dsv4` / `flashinfer_mxfp4` / `flashinfer_cutedsl`。
覆盖它们是「最常导致失望测量结果的原因」——会把 32 宽的 ue8m0 块打到 Triton `_w8a8_block_fp8_matmul`
回退上，吃掉大部分 bs=1 吞吐。

**（二）DSpark 是两个栈里唯一的投机路径。** 官方明确：**没有 EAGLE，也没有 MTP**，
`--speculative-num-steps` 这个旋钮不存在（草稿 token 数从 checkpoint 解析）。
SGLang 开关是 `--speculative-algorithm DSPARK --speculative-dspark-block-size 5`。

**（三）高吞吐配方会关掉投机。** 官方解释：DSpark 一步的成本显著高于普通解码步，
故 bs=1 的收益约等于「接受长度 ÷ 该固定步成本」；大批量时固定成本收不回来。
这条和现场实测完全一致（见 §6.3）。

**（四）PD 分离在非 SM100 上要显式改 backend。** 两个角色默认都跑 MegaAttention
（`--dsv4-attn-backend flashmla_mega`），但那只在 SM100/SM103 上；解码端若在别的 GPU 上，
预填端也必须设 `--dsv4-attn-backend flashmla`，否则首个请求就以 `KV layout mismatch` 失败。

**（五）该 release 不含 Jinja chat template。** 需用官方 encoding 目录下的脚本做提示编码。[c-no-chat-template]
这是很多「部署完发现对话格式不对」的根因。

---

## 6　实测：全部来自 Max-Q 或未标变体

### 6.1　先把边界钉死 [c-se-measured-but-thin]

| 来源 | 硬件原话 | 变体 |
|---|---|---|
| vLLM #56700 | 「8x RTX PRO 6000 96GB」 | **未标明** |
| SGLang #40877 | 「8× RTX PRO 6000 Blackwell Max-Q」 | Max-Q |
| rtx6kpro | 「Max-Q、325 W、显存 +6000」 | Max-Q（超频） |
| diffbot EXL3 | 「two RTX PRO 6000 Blackwell Max-Q」 | Max-Q |

**故：本文所有吞吐数字都是 MQ 或未标变体的，SE 上一个都没有。**

可迁移的部分：显存算术（96 GB 三档相同）、TP 约束、软件栈、坑的清单、
「功耗不是瓶颈」的结论（SE 更是 600 W，只会更不吃紧）。

不可迁移的部分：任何绝对吞吐数字。按带宽比推算，SE 的**解码**吞吐约低 11%；
预填受算力而非带宽限制，且实测吃不满功耗，故预填的差别应小于 11%——但这是推算。

### 6.2　预填：约 7K tok/s 是无 NVLink 的天花板 [c-prefill-sgl-8x]

SGLang，8 卡 PCIe（**无 NVLink**），128K 冷预填：

| 配置 | tok/s |
|---|---|
| `chunked_prefill_size=2048`（生产） | **6,853** |
| 同配置重跑 | 6,765（−1.3%） |
| `flashmla` 预填后端 | 6,845 |
| fused-MoE all-reduce | 6,828 |
| `chunked_prefill_size=4096` | 6,301 |
| `chunked_prefill_size=1024` | 6,012 |

**怎么读这张表**：作者自己后来更正——`flashmla`（6,845）与 fused-MoE（6,828）
都落在生产重跑（6,853 vs 6,765）的 ±1.3% 内，正确读法是「**无可检测差异**」，
不是「这两个变体更慢」。单次重跑不是噪声估计。

真正的信号是资源占用：32K 提示约 7,196 tok/s，**GPU 利用率约 87% 但只吃到 220 W / 600 W**。
作者据此判断「瓶颈是 PCIe 通信，不是算力」，并给出「这块板子无 NVLink 时约 7K tok/s 是天花板」。[c-prefill-ceiling]

**这是本文最可迁移的一条**：4 卡档实测 4,714 token 冷提示 0.788 s ≈ 5,982 tok/s——[c-decode-tp4-conc]
卡数减半，预填只降 13%，进一步证明不是算力受限。

**唯一的大倍率来自前缀缓存**：112K token 前缀命中时 0.34 s ≈ **325K tok/s（约 39 倍）**。[c-prefill-ceiling]

### 6.3　解码：投机解码是「可用 vs 不可用」 [c-decode-dspark]

SGLang，8 卡，单流：

| 提示类型 | DSpark 开 | DSpark 关 |
|---|---|---|
| 散文 | 76.5–78.9 tok/s | 36.4–36.5 tok/s |
| 结构化 / JSON | 120.3–120.5 tok/s | 36.5 tok/s |
| 接受长度 | 3.0 token/步 | 1.0 |

**关掉投机后，模型无论提示类型都塌到约 36.5 tok/s。** 作者的判断是：
「投机是这个硬件上『可用』与『不可用』延迟的分界」。生产用 `block_size=6` 时结构化提示约 **237–252 tok/s**。

这与官方文档的说明互相印证：DSpark 的接受率**强依赖负载**（数学/代码最高，开放聊天较低，
agentic trace 更低），且一步的成本不随接受长度或草稿块大小变化——
所以调 `block_size` 不会买来吞吐，只会改变「在哪个负载上更划算」。

**4 卡 TP4/EP4 的并发曲线**（同机改用 4 卡后）：[c-decode-tp4-conc]

| 并发 | 合计 tok/s | 相对 1 | 每流 tok/s | TTFT | TPOT |
|---|---|---|---|---|---|
| 1 | 115.2 | 1.00× | 121.9 | 0.121 s | 8.2 ms |
| 2 | 220.6 | 1.91× | 125.8 | 0.147 s | 8.0 ms |
| 4 | 322.2 | 2.80× | 108.5 | 0.643 s | 9.3 ms |
| 8 | 468.2 | 4.06× | 66.2 | 0.157 s | 15.2 ms |

**并发 2 是免费的**（每流速率不变），8 是硬上限（`max_running_requests=8` 且 decode 图只捕到 bs=8）。
作者明说 N=2，**不是误差棒**，应读作首轮而非定表。

社区 4 卡（MQ 325 W，超频）的另一组稳定配置：C1 **249.1 tok/s**、C8 合计 **805.5 tok/s**、
32K 预填 **17,982 tok/s**、4,727,748 逻辑 KV token。[c-stable-tp4-profile]
比上面那组高得多，差别在 adaptive DSpark K7 与更激进的调优。**两组不可直接比较**——硬件条件与镜像都不同。

### 6.4　1M 上下文：能跑，但要 5 分钟 [c-1m-cold-5min]

SGLang，4 卡，冷预填阶梯（每行提示带唯一标记，保证不是缓存命中）：

| 提示 token | 耗时 | 预填速率 |
|---|---|---|
| 402,625 | 79.5 s | 5,065 tok/s |
| 704,582 | 175.2 s | 4,022 tok/s |
| 905,885 | 260.5 s | 3,478 tok/s |
| 1,006,538 | 310.5 s | **3,242 tok/s** |
| 1,006,538（重复） | 322.0 s | 3,126 tok/s |

**结论：一次完整的 1M 冷预填约 5 分钟。**

**而流传的「1040K 在 74.5 秒内完成（13,962 tok/s）」是假象**：那 900K 前缀已在 radix cache 里，
实际只预填了约 140K。[c-cache-artifact] 作者不仅更正了这个数，还更正了自己更早的「409K = 62.7 s（6,528 tok/s）」——
真实冷数字是 79.5 s（5,065 tok/s）。

vLLM 路线独立验证了「1M 能跑」这件事：950K token 双针检索正确，
预填 4,584 tok/s（纯 torch logits 路径、eager 模式）。[c-vllm-1m-verified] **「能跑」与「跑得快」是两件事**：
4,584 对 SGLang 的 6,853（虽然上下文长度不同，不可直接比）。

### 6.5　长上下文的并发会塌 [c-long-ctx-collapse]

同一 4 卡机，906K 上下文：

- 单请求重复 5 次：解码 100 tok/s、TPOT 10 ms、TTFT 2.38 s（对比冷预填 260 s，前缀缓存值 **109 倍**）；
- **4 个并发**（各 906K 上下文、各 256 输出 token）：合计 8.6 s，**仅 29.7 tok/s**（每流约 7.4）。

作者的判断很直接：「`max_running_requests=8` 在这个上下文规模下是名义值；
这个端点擅长服务一个重请求，而不是多个。」

### 6.6　显存天花板：98.9% [c-vram-ceiling]

| 路线 | 实测峰值 | 余量 |
|---|---|---|
| SGLang 4 卡 1M 配置 | 96.8 / 97.9 GB（98.9%） | ~1 GB |
| EXL3 2 卡 1.04M 提示 | 96,655–97,029 / 97,887 MiB | ~0.8–1.2 GB |

**两条独立路线撞到同一面墙。** 96 GB 是硬边界，且余量只有约 1 GB——
「跑两个长请求」之前必须先算这笔账。

---

## 7　坑：哪些报错，哪些静默

这一节按「失败是否可见」排序，因为**静默的比报错的危险得多**。

### 7.1　静默失败（最危险）

| 坑 | 症状 | 为什么危险 |
|---|---|---|
| **FP8 KV 的 scale 布局** | 短提示冒烟全过，只在 ≥100K 检索时出错 | 块布局是 `[64tok×128B fp8 \| 64tok×4B fp32 scale]`（块尾追加），不是逐 token 交错。理解错就是**数值损坏**，不报错 [c-fp8-kv-layout-pitfall] |
| **前缀缓存假象** | 测出 13,962 tok/s 这类虚高值 | radix cache 会保留已完成请求的页，共享前缀的「级别」几乎不做预填。作者自己的两组数都中招 [c-cache-artifact] |
| **`--enable-dp-attention` 单独用** | 看起来正常，`dp_size` 仍是 1 | 「静默不生效」会让人把**旧配置当成新配置**记录，整轮数据作废 [c-sgl-rejects-dp] |
| **容器没传 `-e TP_SIZE`** | 服务照常起，跑的是默认 TP8 | 作者记录「整轮假数据」就是这么来的，后来加了配置门 |
| **镜像未标 commit** | 数字无法归因到任何 release | 40877 的镜像 `ai.sglang.build.commit=unknown`、`pip show sglang` 为 `0.0.0.dev0` |

**应对这三条的方法，来源里给了现成的**：
用 `--enable-cache-report`，每行断言 `usage.prompt_tokens_details.cached_tokens ≈ 0`；
用 `/get_server_info` 核对生效配置再计时；用户报告的更细一条是——
SGLang 只在 `cached_tokens > 0` 时才发 `prompt_tokens_details`，
故冷行该字段**缺失而非 0**，harness 要按 `or {}` 默认为 0，否则最想要的冷行会被丢掉。

### 7.2　会报错或挂死的

| 坑 | 表现 |
|---|---|
| DeepGEMM autotune 挂死 | 首次长上下文批（128K+）deadlock，bring-up 需跳过或 eager [c-deepgemm-hang] |
| FlashInfer sparse-MLA SM120 实例化缺口 | 部分 `(num_heads, topk)` 组合（如 `(16, 512)`）不在分发表里，视觉路径同样中招 |
| CUDA graph 捕获崩溃 | flashinfer 算子在图里、>4K token 时崩；作者用纯 torch 替换后正常 |
| SGLang 拒绝 DP 拓扑 | DP2×TP4 抛「V4.1 vision currently supports TP/EP without DP, CP, PP or MoE A2A」，两副本约 70 s 内死亡 [c-sgl-rejects-dp] |
| 预填 CUDA graph 捕获崩 | 即使关掉投机也崩，与投机无关 |
| 整个 TP 组被 SIGKILL（Exited 137） | 未复现的最可疑原因：冷启动后首个超大请求触发 Triton 形状 JIT，卡过 300 s 看门狗 |

**一条运维规矩值得抄下来**：冷启动后先发一个几百 K token 的预热请求并等它完成，再信任服务。
另外，`docker rm -f` 可能杀不掉 defunct 容器，而孤儿引擎进程仍占端口并应答健康检查——
于是下一次实验会被静默标错。要循环 `docker rm -f` 直到端口真的没人监听。

### 7.3　性能回退

**MXFP4 专家路径在 SM120 上回退到 Marlin 内核**（上游已知 issue #30135）。[c-marlin-fallback]
能跑，性能损失被作者评为「可接受」。这不是可以「修好」的配置问题，是内核覆盖缺口。

---

## 8　自建还是 API

### 8.1　官方价目 [c-api-price]

| 项 | deepseek-flash（V4.1-Flash-1017） |
|---|---|
| 输出 / 1M token（峰时） | **$1.2** |
| 输出 / 1M token（谷时） | $0.6 |
| 输入 / 1M token（缓存命中，峰时） | **$0.006** |
| 上下文 | 1M |
| 并发上限 | **2,500** |

谷时是峰时的 50%，峰时为 UTC 周一至周五 01:00–04:00 与 06:00–10:00。

### 8.2　量级对比（不是同条件对照） [c-selfhost-breakeven]

第三方给出的盈亏平衡点是：8×H200 节点（AWS 约 $63/小时）要持续产出约 **14,650 输出 token/s**
才能追平 $1.2/百万 token。

本主题的实测：

| 场景 | 实测 | 与 14,650 的比 |
|---|---|---|
| 单流解码（4 卡，DSpark） | 115.2 tok/s | 1/127 |
| 8 并发合计（4 卡） | 468.2 tok/s | 1/31 |
| 8 并发合计（8 卡，社区调优） | 805.5 tok/s | 1/18 |

**必须写明的限制**：14,650 那个数来自 **8×H200**，本文的实测来自 **4–8×RTX PRO 6000**。
两者不是同一台机器、不是同一价格、不是同一负载。故这个比值**只能作量级参照**，
不能读成「自建贵 31 倍」。

即便如此，量级差是清楚的：**自建的理由是数据主权、可微调、提示不出 VPC，不是省钱。**[c-selfhost-for-control]
MIT 许可让这些成为可能（可商用、可微调、可再分发）。

### 8.3　另一条硬件路线的代价 [c-ascend-alt]

vLLM-Ascend 给出了在 8×128 GB NPU 上部署的完整配方，但代价具体：
必须 W8A8 权重 + INT8 Engram，且必须显式 `VLLM_USE_V2_MODEL_RUNNER=0`。
列在这里是为了说明「换平台不是换个 kernel，是换一套精度方案」。

---

## 9　如果非要一个部署方案

按「最小可行」到「生产可用」排序：

### 9.1　方案 A：8×96 GB，全精度（推荐）

- 栈：SGLang `dev-dsv41` 镜像，TP8/EP8，`--mem-fraction-static 0.72`，fp8_e4m3 KV；[c-tp8-on-8x96]
- 或 vLLM 分支，TP=8，`--kv-cache-dtype fp8 --block-size 128 --gpu-memory-utilization 0.85`；
- 实测：预填约 6.8K tok/s（128K 冷）、1M 上下文可跑、单流约 115–249 tok/s（视调优）；[c-prefill-sgl-8x]
- 前提：接受魔改镜像；Engram 放主机内存或分片显存。

### 9.2　方案 B：4×96 GB，全精度（更省卡，更挑栈）

- 栈：SGLang TP4/EP4，`--engram-config '{"placement":"cpu"}'`；[c-stable-tp4-profile]
- 实测：C1 115.2 tok/s、8 并发 468.2 tok/s、1M 冷预填约 5 分钟、峰值 VRAM 98.9%；[c-decode-tp4-conc] [c-1m-cold-5min]
- 前提：主机 RAM 要够放 188.83 GiB 的 Engram 表；镜像必须自带 SM120 补丁。[c-engram-188gib]

### 9.3　方案 C：2×96 GB，EXL3 3-bit（能省一半卡，但付质量） [c-quant-quality-cost]

- 实测：**agentic 单会话解码 224.1 tok/s**（同轮墙钟 228.7 s）；固定提示下 2K 单流 156.9、
  **46K 单流中位 172.8**、46K 四流聚合 362.9；**40K 冷预填 11,157 / 11,467 tok/s**。[c-exl3-throughput]
- 质量：原模型自身重跑的 KL 噪声底 **0.0082**（中性文本），该包实测
  **0.0522 / 0.0306 / 0.0111 / 0.0338**，中性文本上是噪声底的 **6.4 倍**；
  GSM8K-200 98.5%→99.0%、HumanEval 95.7%→97.6%（这部分在噪声内）。[c-quant-quality-cost]
- 故代价是三条：KL 偏离可测（6.4×）、非上游量化内核与打包格式、Engram int4 111 GB 常驻主机 RAM。
  主机 RAM 约 260 GiB、磁盘约 340 GB。

### 9.4　不推荐的做法

- **按 16B 估显存**：会得出「一张卡够」的错误结论，差 44 倍；[c-active-not-total]
- **直接用上游 vLLM/SGLang**：SM120 上起不来；[c-upstream-vllm-blocked]
- **在 SGLang 里手动指定 backend**：会把 ue8m0 块打到 Triton 回退，吃掉大部分 bs=1 吞吐；
- **关掉投机解码**：解码塌到 36.5 tok/s；[c-decode-dspark]
- **用共享前缀的提示做吞吐基准**：会测出 39 倍虚高。[c-cache-artifact]

---

## 10　结论：三条可带走的判断

**第一，能装，但要 4 张起。** 552B+196B、约 511 GB 权重，96 GB 卡的下限是 4 张（Engram 下放主机内存），
2 张只能靠 3-bit 量化。TP 必须是 2 的幂，故 6 张这种「算术够、拓扑不行」的配置不存在。[c-minimum-viable]

**第二，瓶颈不在显存带宽，也不在功耗，在软件与互连。** 三条独立证据：
GPU 只吃 220 W / 600 W；600 W→300 W 单用户仅损 4%；4 卡预填只比 8 卡低 13%。[c-power-scaling]
真正的限制是 PCIe（无 NVLink 时预填约 7K tok/s 封顶）与 SM120 的内核覆盖缺口。[c-prefill-ceiling]

**第三，关于 Server Edition 的问题，公开证据已覆盖两格。** 4×SE / Engram-on-RAM / 450 W 有完整吞吐
（183 / 695 / 18,400–19,200）；8×SE 全精度也有——同一节点跑 TP4+EP4 单副本，
codeconc C=128 聚合 4,404 tok/s、单流 code 403.5。[c-se-8x-measured]
按带宽比推算 SE 的解码应比 WE 低约 11%，预填差别应更小——但这是**推算**。[c-se-vs-ws-bandwidth]
唯一仍空白的是「8 张卡做**单个 TP8 副本**」：现有数据都是把 8 卡切成两个 4 卡副本。
在那之前，本文的价值是：把可迁移的部分（显存算术、拓扑约束、软件栈、坑）
与不可迁移的部分（绝对吞吐）分开写清楚，而不是给一个看起来精确的平均数。

---

## 附录 A　复现路径

```bash
cd research/pro6000se-dsv41
python fetch.py && python fetch2.py && python fetch3.py \
  && python fetch4.py && python fetch5.py && python fetch6.py   # 抓快照
python build_evidence.py    # 锚点扩窗生成 102 条引文（非手写）
python build_tables.py      # sources.csv + claims.csv，含引用闭合校验
python build_run.py         # run.json（轨迹 + 预算 + 缺口）
cd ../.. && python scripts/validate_research.py research/pro6000se-dsv41
python scripts/audit_paper.py research/pro6000se-dsv41/paper
python scripts/check_paper.py research/pro6000se-dsv41/paper
```

## 附录 B　失败抓取登记

按「失败也要留档」的原则记录，避免后来者重复踩：

| URL | 结果 |
|---|---|
| `docs.vllm.ai/.../deepseek_v41flash` | 404（三处候选路径皆无） |
| `api.github.com/repos/deepseek-ai/DeepGEMM/issues/236/comments` | 403 限流 |
| `cloud.tencent.cn/developer/article/2740943` | 只抓到骨架（正文需 JS），登记为 tertiary，**不用于支撑任何主张** |
| `cdw.com` / `enzu.com` 价格页 | 连接被拒 / 403；SE 零售价因此缺失 |

## 附录 C　参考文献

**官方（一手）**

1. DeepSeek-AI. *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression*（模型卡）. 2026-09-10. <https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash>
2. DeepSeek-AI. *DeepSeek-V4.1-Flash Technical Report*. 2026-09-10. <https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf>
3. DeepSeek. *DeepSeek-V4.1-Flash: Smarter, Faster, More Efficient*. 2026-09-10. <https://api-docs.deepseek.com/news/news260910.md>
4. DeepSeek. *Models & Pricing*. 2026-09-10（更新 2026-10-17）. <https://api-docs.deepseek.com/quick_start/pricing>
5. NVIDIA. *RTX PRO 6000 Blackwell Server Edition*. <https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/>
6. SGLang / LMSYS. *DeepSeek-V4.1 — SGLang cookbook*. <https://docs.sglang.io/cookbook/autoregressive/DeepSeek/DeepSeek-V4_1>
7. vLLM-Ascend. *DeepSeek-V4.1-Flash on Ascend NPU*. <https://github.com/vllm-project/vllm-ascend/blob/main/docs/source/tutorials/models/DeepSeek-V4.1-Flash.md>

**一手现场报告与测量**

8. Lei-010. *[SM120] Field report: running DeepSeek-V4.1-Flash end-to-end on 8x RTX PRO 6000*. vLLM #56700, 2026-09-13. <https://github.com/vllm-project/vllm/issues/56700>
9. Lei-010. *[SM120] Field report: DeepSeek-V4.1-Flash in production on 8x RTX PRO 6000 (PCIe, no NVLink)*. SGLang #40877, 2026-09-23（更新至 2026-10-11）. <https://github.com/sgl-project/sglang/issues/40877>
10. local-inference-lab. *DeepSeek-V4.1-Flash serving profile on RTX PRO 6000*. <https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md>
11. local-inference-lab. *GPU Configurations & Rig Builds*. <https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/gpu-configs.md>
12. local-inference-lab. *SM120 vs. SM100 Architecture*. <https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/sm120-vs-sm100-architecture.md>
13. local-inference-lab. *DSpark: ours vs upstream vLLM — consolidation study*. 2026-07-03. <https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/dspark-upstream-consolidation.md>
14. diffbot. *DeepSeek-V4.1-Flash-1017 EXL3 3-bit for 2× RTX PRO 6000 Blackwell*. <https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000>

**第三方汇总（多为转述，已标 secondary/tertiary）**

15. Qovery. *Self-Hosting DeepSeek V4.1-Flash: The Exact GPU Setup You Need*. 2026-10-30. <https://www.qovery.com/blog/self-host-deepseek-v4-1-flash-gpu-setup-own-cloud>
16. Artificial Analysis. *Inference Serving Configurations*. <https://artificialanalysis.ai/hardware-inference-stack/configs>
17. 腾讯云开发者社区. *DeepSeek V4.1 Flash 部署完整指南*（抓取失败，仅登记）. 2026-09-10. <https://cloud.tencent.cn/developer/article/2740943>

---

## 校验结果

`sources=26, evidence=138, claims=48, claims_high=43, claims_disputed=0, trace_events=26, c3_violations=0, subquestions=7, r2_violations=0, c1_violations=0`

由 `python scripts/validate_research.py research/pro6000se-dsv41` 现算；E1 可校验 138 条、无法校验 0 条。
