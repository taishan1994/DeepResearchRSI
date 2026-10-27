# NVIDIA RTX PRO 6000 Blackwell 全系性能分析

> **状态**：已完成（存在已声明的证据缺口）
> **信息截止**：2026-10-27
> **覆盖范围**：Workstation Edition / Max-Q Workstation Edition / Server Edition 三个 SKU
> **来源数**：63 ｜ **证据数**：387 ｜ **主张数**：253（高置信 177，争议 1）
> **任务留档**：[brief.yaml](./brief.yaml) · [sources.csv](./sources.csv) · [claims.csv](./claims.csv) · [evidence.csv](./evidence.csv)

---

## 1. 执行摘要

RTX PRO 6000 Blackwell 不是"更快的 RTX 5090"，而是**同一颗 GB202 die 全开 + 三倍显存 + 企业特性**的另一类产品 [c-die][c-mem-96gb]。它的价值曲线在三个维度上分叉：

**① 显存容量是主要卖点，不是算力。**
96GB GDDR7 ECC 让单卡能舒适承载 20B–35B 模型并保留真实上下文与批量，70B 需量化才能装入 [c-96gb-band]。单卡 llama-3.1-8B 峰值输出约 11,500 tok/s [c-single-gpu-8b-peak]，8k 提示词 prefill 约 170k–220k tok/s [c-prefill-throughput]。**单卡免跨卡通信**把 8B 的 TTFT 压到 205ms，而多卡/跨节点方案在 520–1320ms 区间 [c-ttft-advantage]——这是架构性收益，不是芯片算力优势。

**② 相对 RTX 5090 的领先幅度依负载剧烈变化，区间为 -38% 到 +108%。**

| 负载 | 口径 | PRO 6000 vs 5090 |
|---|---|---|
| UL Procyon AI（Llama2） | Workstation，TensorRT | **+21%** [c-vs-5090-procyon-gap] |
| UL Procyon AI（Phi） | Workstation，TensorRT | **+18%** [c-vs-5090-procyon-gap] |
| 综合 AI 指数 | LynxBenchAI 26Q3 | **+20%** [c-vs-5090-lynx] |
| 稠密矩阵乘 FP32 | 同上 | **+108%** [c-vs-5090-fp32] |
| V-Ray 渲染 | **Server Edition** | **+47%** [c-vray-ratios] |
| Blender（Drop & Render） | Workstation | **+8%** [c-blender-dr] |
| OctaneBench 2025 | Workstation | **+1.2%** [c-octane] |
| 稀疏矩阵乘 FP32 | LynxBenchAI | **-12%** [c-vs-5090-fp32] |
| **Blender（Drop & Render）** | **Server Edition** | **-38%** [c-blender-dr] |

**关键判断**：理论算力只领先 20%（FP32 126 vs 104.8 TFLOPS）[c-vs-5090-db]，实际差距靠**显存容量与带宽压力**撑开——模型越大、上下文越长，差距越明显（Llama3 仅 +6.5%，Llama2 +21%）[c-vs-5090-procyon-gap]。买它是为了"装得下"，不是为了"算得快"。

**渲染没有统一答案**：V-Ray 上 Server 版拿第一（+47%），Blender 上 Server 版却比 5090 低 38% [c-render-workload-dependent]。必须按渲染器实测。

**③ 三个 SKU 的差异来自固件，不来自硬件。**
核心规模完全相同（24,064 CUDA / 752 Tensor / 188 RT）[c-cuda-cores-same]，但 V/F 曲线、pstate、显存时钟被固件锁死且用户不可调 [c-vf-skup]。后果反直觉：

- 强制 300W 下，**Server 版比 Workstation 版快 38%** [c-server-low-power-win]
- Server 版在 300W 能效最高（414 Gflop/s/W，比 WS 同功耗高 38%）[c-server-efficiency]
- Workstation 版在 600W 时吞吐最高（165,682 Gflop/s），但比 250–350W 损失约 11% 能效 [c-ws-efficiency-flat]
- **同样的非饱和负载，WS 主动吃满 600W，Server 只取约 390W** [c-ws-uses-watts]
- 渲染性能因 SKU 与渲染器而剧烈分化：V-Ray 上 Server 版第一，Blender/Octane 上 Workstation 版第一 [c-render-workload-dependent]

**④ 最大的采购风险是价格，不是性能。**
发布时渠道价约 $8,435–8,565 [c-price-launch]；2026-08 官方调价至 $16,000 [c-price-now]；**2026-10-27 实际街价已达 $17,999** [c-price-17999]，是同期 RTX 5090（$4,996）的 **3.6 倍** [c-price-ratio]。涨价主因是高端 GDDR7 供应紧张 [c-price-cause]。

按**零售价/渲染性能**计，该卡在其基准库的 33 张有价卡片中**排最后一名** [c-value-worst]——纯渲染用途下 RTX 5090 的每美元性能约为它的 **3 倍** [c-render-value]。但按**持有型 TCO** 计它反而最便宜（$0.68/chip/hr，H200 为 $1.22）[c-tco-rtx-cheaper]。**两个口径不能混用。**

**⑤ 训练侧并非全面劣势，取决于序列长度。**
短序列（<4K）全参 SFT 上，RTX PRO 6000 比 GH200 快最多 1.8 倍；超过约 8K 后 GH200 反超并稳定在 1.7–1.8 倍 [c-ft-crossover]。单卡可完成 GPT-OSS-120B 的 4bit QLoRA 微调 [c-ft-120b-single]，但**优化器卸载在 PCIe 上几乎不可用**（慢 12–25 倍）[c-ft-offload]。

**⑥ 两个跑分看不见、但决定企业采购的维度：MIG 与机密计算。**
MIG 硬件隔离带来可预测 QoS，多 VM 共享提升总吞吐（2 VM +34%，4 VM +52%）[c-vgpu-sharing]。机密计算方面，厂商称开销仅 1–8% [c-cc-vendor-claim]，学术实测在 **RTX PRO 6000** 上为 **13–27%** [c-cc-academic-gap]；但开销最多可回收 92% [c-cc-recover]，根因是 VM-GPU 桥接而非 GPU 算力 [c-cc-cause]。

**⑦ 一个尚未被评测覆盖、但已有多例报告的运维风险：在役性能退化。**
多名用户在 NVIDIA 官方论坛报告，长期高负载运行后出现"假高功耗读数"导致的 SW Power Cap 锁频，FP32 掉到正常值的 1/10–1/20 [c-degradation][c-degradation-scale]。该故障**不产生任何错误日志**，多卡训练时只表现为整体变慢 [c-degradation-silent]。厂商尚未公告，样本有限，但采购高负载长期运行场景应提前建立基线跑分与监控 [c-degradation-procurement]。

**⑧ 本报告最需要警示的是三个与性能无关的风险。**

| 风险 | 后果 | 证据强度 |
|---|---|---|
| **在役退化**（§10.5） | 性能掉到 1/10–1/20，无任何错误日志 | 5+ 用户报告，厂商未公告 |
| **供电接口熔毁**（§10.6） | PSU 侧熔毁，保修可能被拒 | 单一案例 + 3 月先例 |
| **RTX 5090 可能停产**（§12.5） | 3.6 倍比价可能收窄，"5090 更划算"结论失效 | 爆料级，厂商未确认 |

三者都不体现在任何跑分里，但都会改变持有成本。

**⑨ 两个看似矛盾的价格结论，必须按口径分开看。**
按**零售单卡价**（$17,999），每美元渲染性能在 33 张有价卡片中垫底，RTX 5090 是它的 3 倍 [c-value-worst][c-render-value]。按**大规模自持 TCO**（$0.68/chip/hr），它反而比 H100（$1.17）、H200（$1.22）、B200（$1.73）、B300（$2.26）都便宜 [c-tco-rtx-cheaper]。买一张卡和运营一万张卡是两套经济学，**不要混用口径**。

**一句话选型**：需要 96GB 单卡装大模型 / 长上下文 / 4 路 MIG 隔离 / 微调 100B+ 量化模型 → 值得；纯渲染、双精度 HPC、长序列全参训练 → 不值得（FP64 仅约 2 TFLOPS，1:64）[c-not-for-fp64]。

---

## 2. 范围与方法

### 2.1 研究问题拆分

| # | 子问题 | 状态 |
|---|---|---|
| q1 | 三个 SKU 的规格差异究竟是什么？ | ✅ answered |
| q2 | 同为核心数相同的 GB202，性能差异来自哪里？ | ✅ answered |
| q3 | 96GB 显存在实际 AI 负载中能承载什么规模？ | ✅ answered |
| q4 | 相对 RTX 5090 的性能与能效差距有多大？ | ✅ answered |
| q5 | 在专业图形/渲染上的定位如何？ | ✅ answered |
| q6 | 600W 是否值得？最优功耗点在哪？ | ✅ answered |
| q7 | 价格与可获得性如何变化？ | ✅ answered |
| q8 | 软件栈与生态上有哪些限制？ | ✅ answered |
| q9 | 与 H100 / L40S / RTX 6000 Ada 的适用边界？ | ✅ answered |
| q10 | MIG / vGPU 虚拟化下的表现如何？ | ✅ answered |
| q11 | 机密计算（CC）的性能代价有多大？ | ✅ answered |

### 2.2 来源分级

本报告对每条证据标注可信层级，冲突时不强行裁决：

- **primary（一手）**：NVIDIA 官方产品页、新闻稿、博客 — 规格与厂商声明
- **secondary（二手独立）**：StorageReview、HOSTKEY、TechnoLynx、社区实测仓库 — 实测数据
- **tertiary（聚合/转述）**：CG Channel 汇总、中文媒体转述 — 仅用于价格与时间点

**明确的方法论警告**：
- 厂商倍数声明（如"相对 L40S 快 5 倍"）**未公开完整测试条件**，应视为上限而非典型值 [c-vs-l40s]。
- 服务商自测（EcoHash）与托管商自测（HOSTKEY）有商业利益相关性，相关主张置信度已降为 medium [c-single-gpu-8b-peak][c-vs-h100-parity]。
- 不同基准口径不可混用：LynxBenchAI 是稳态吞吐指数，Procyon 是应用级评分，Blender Open Data 是众测渲染分 [e-lynx-method]。

### 2.3 已知证据缺口

以下来源因反爬（Cloudflare 403）或格式限制（PDF）**未能取得正文**，是本报告的明确缺口：

| 目标 | 原因 | 影响 |
|---|---|---|
| Puget Systems 内容创作评测 | 403 Just a moment | 缺少 V-Ray/SPECviewperf 完整数据 |
| Phoronix Linux 性能评测 | 403 | 缺少 Linux 下的横向对比 |
| TechPowerUp 评测与 GPU 数据库 | 404 / 机器人校验 | 缺少部分规格交叉验证 |
| SPECviewperf 15 结果页 | 请求超时 | 缺少专业 CAD 视口分项（NVIDIA 仅给出"Server 版最高"） |
| ~~MLPerf Inference 官方提交~~ | **已补齐** | 改由 Cisco UCS X580p 白皮书取得封闭分区数据 [c-mlperf-closed-available] |
| GigAGPU / WindowsReport | 403 | 缺少 70B 单卡细节（6000D 已由中关村在线补齐） |
| Comino Grando 4U 液冷整机 | 403 | 缺少 8 卡 768GB 一体机实测 |

> 这些缺口不改变主要结论（多个独立来源已相互印证），但**若要用于采购决策，建议补测专业应用分项**。

---

## 3. 规格解剖：三个 SKU 到底是什么关系

### 3.1 完整规格对照

| 项目 | Workstation Edition | Max-Q Workstation | Server Edition |
|---|---|---|---|
| 架构 | Blackwell (GB202) | Blackwell (GB202) | Blackwell (GB202) |
| CUDA 核心 | 24,064 | 24,064 | 24,064 |
| Tensor 核心 | 752 (5th Gen) | 752 (5th Gen) | 752 (5th Gen) |
| RT 核心 | 188 (4th Gen) | 188 (4th Gen) | 188 (4th Gen) |
| 显存 | 96GB GDDR7 ECC | 96GB GDDR7 ECC | 96GB GDDR7 ECC |
| 位宽 | 512-bit | 512-bit | 512-bit |
| **显存带宽** | **1792 GB/s** | **1792 GB/s** | **1597 GB/s** |
| FP32 | 125 TFLOPS | 110 TFLOPS | 120 TFLOPS |
| RT Core | 380 TFLOPS | 333 TFLOPS | 355 TFLOPS |
| FP4 Tensor | 4000 TOPS（稀疏） | 3511 TOPS（稀疏） | 4 PFLOPS |
| FP8 Tensor | — | — | 2 PFLOPS |
| TF32 Tensor | — | — | 234 TFLOPS |
| **TDP** | **600W（可配置）** | **300W** | **600W（可配置）** |
| 形态 | 双槽 5.4×12.0" | 双槽 4.4×10.5" | 单槽 FHXL（液冷）/ 双槽 FHFL（空冷） |
| 散热 | 双流道主动 | 主动 | 被动（依赖机箱风道） |
| 显示输出 | 4× DP 2.1 | 4× DP 2.1 | **无** |
| 多卡 | 2 卡 | **4 卡（384GB）** | **8 卡（800GB / 13TB/s）** |
| MIG | 支持（4 实例） | 支持（4 实例） | 支持（4×24GB） |

来源：[src-nvidia-ws-edition][src-nvidia-maxq][src-nvidia-server][e-press-3skus][c-three-skus][c-mem-96gb][c-bw-ws-1792][c-tdp][c-fp32-tflops][c-ai-tops][c-rt-tflops][c-mig4][c-maxq-4gpu][c-server-8gpu]

**注意**：Server 版标称带宽 1597 GB/s 低于另两者的 1792 GB/s——这不是笔误，与其 P0 pstate 和 12,481 MHz 显存时钟一致 [c-vf-skup]。

### 3.2 与 RTX 5090 的硬件血缘

三者与 RTX 5090 共用 GB202 die（922 亿晶体管 / 750 mm² / L2 128MB）[c-die]，但：

- 核心全开：24,064 vs 21,760 CUDA（+10.6%）[e-cg-lineup]
- 显存三倍：96GB vs 32GB [e-sr-5090-32gb]
- 显存带宽相同：均为 1792 GB/s [e-ws-mem-bandwidth]
- 频率更高：boost 2617 MHz vs 2407 MHz [e-sr-boost-clock]
- FP32 +20%：126 vs 104.8 TFLOPS [e-sr-fp32-126][c-vs-5090-db]
- **FP64 惨烈**：1.968 TFLOPS（1:64）[e-sr-fp64-ratio]

这解释了为什么游戏/图形差距小（同带宽、同 die），而大模型差距大（显存容量与容量压力）。

### 3.3 第四个 SKU：中国特供 RTX 6000D

此前只能看到拆解传闻的 RTX 6000D，现有完整实测数据 [c-6000d-spec]。它是标准 Server 版的规格削减型号：

| 项目 | RTX PRO 6000 | RTX 6000D | 变化 |
|---|---|---|---|
| CUDA 核心 | 24,064 | **19,968** | -17% |
| Tensor 核心 | 752 | 624 | -17% |
| RT 核心 | 188 | 156 | -17% |
| 加速频率 | 2617 MHz | 2430 MHz | -7% |
| 显存 | 96GB / 512-bit | **84GB / 448-bit** | -13% 容量 |
| 带宽 | 1792 GB/s | **1570 GB/s** | -13% |
| FP32 | 126 TFLOPS | **97.04 TFLOPS** | -23% |
| 峰值功耗 | 600W | ~400W | -33% |

**关键细节**：
- PCB 布局与标准版**完全一致**，差异只是显存颗粒从 32 颗减为 28 颗 [e-6000d-pcb]——这是纯粹的规格切割，不是新设计
- 性能降幅（23%）**大于**核心数降幅（17%），因为频率与带宽同时下调 [c-6000d-perf]
- 四个 DisplayPort **不具备视频输出能力**，Windows 下默认加载 TCC 纯计算驱动 [c-6000d-tcc-only]——它不能当工作站显示卡用
- 定位：FP32 略低于 Max-Q，明显高于 RTX PRO 5000 48GB [c-6000d-position]

#### 3.3.1 重要修正：削减不是按比例的，Tensor Core 被砍掉约三分之二

上面那张表会让人以为 6000D 只是"整体弱 17%–23%"。**这是错的。** 一份同软件栈、同矩阵尺寸（16384²）、5 轮 × 30 次迭代的稳态实测给出了完全不同的图景 [c-cn-tensor-cut]：

| 精度 | RTX 6000D | RTX PRO 6000 | 倍数 | **6000D 保留率** |
|---|---:|---:|---:|---:|
| BF16 GEMM | 144.09 TFLOPS | **401.01 TFLOPS** | **2.78×** | **35.9%** |
| FP16 GEMM | 144.02 TFLOPS | **397.67 TFLOPS** | **2.76×** | **36.2%** |
| TF32 GEMM | 72.05 TFLOPS | **194.99 TFLOPS** | **2.71×** | **37.0%** |
| INT8→INT32 | 140.32 TOPS | 238.41 TOPS | 1.70× | 58.9% |
| FP32 GEMM | 66.67 TFLOPS | 75.48 TFLOPS | 1.13× | **88.3%** |
| 显存拷贝带宽 | 1279.44 GB/s | 1460.68 GB/s | 1.14× | **87.6%** |

**结论非常清晰**：FP32 和带宽几乎没动（保留 ~88%），但 **BF16/FP16/TF32 只剩约 36%** [c-cn-tensor-cut]。

**决定性证据是 TF32 的异常** [c-cn-tf32-anomaly]：6000D 的 TF32 只比自己的 FP32 快 **8%**，而 PRO 6000 的 TF32 是 FP32 的 **2.58 倍**。也就是说 **6000D 的 TF32 路径几乎没有获得任何 Tensor Core 增益**——被砍的正是 Tensor Core 本身。

**这排除了"降频导致"的解释** [c-cn-freq-not-cause]：6000D 的 SM 中位频率 2422 MHz（接近满频 2430），PRO 6000 因撞 600W 功耗墙反而只有 2167 MHz——**频率更低的那张卡快 2.78 倍**。

**实践含义** [c-cn-advice]：

| 你的负载 | 6000D 是否合适 |
|---|---|
| 传统 FP32 计算 | ✅ 保留 88%，性价比极高 |
| 带宽受限的单流 decode | ✅ 保留 88%，差距远小于 2.78× [c-cn-bw-close] |
| 量化推理（INT8） | ⚠️ 保留 59%，需评估 |
| **BF16/FP16 训练或高吞吐推理** | ❌ **只有 36%，应选 PRO 6000 或多卡弥补** |

**两条卡相同的参数**：Compute Capability 均为 12.0、最大 SM 时钟均为 2430 MHz、显存时钟均为 12481 MHz、功耗上限均为 600 W、BAR1 均为 128GB [c-cn-same-sku-base][c-cn-bar1]。**正因为纸面几乎一致，才最容易误判**。

**实测参考**：LMStudio 跑 DeepSeek R1 70B（8K 上下文）约 **24.79 tok/s**，比 RTX PRO 5000 快 10%+ [c-6000d-llm]。注意这是 LMStudio 口径，不能与 vLLM 数字直接比。

**市场反应冷淡** [c-6000d-demand-weak]：据行业反馈实际需求有限，未形成稳定采购意向。考虑到它既不能输出视频、Tensor Core 又只剩 36%，这个结果并不意外。

**容量换算**：四卡 336GB、八卡 672GB，可支撑量化后的 671B 模型 [c-6000d-capacity]。

---

## 4. AI 推理性能：96GB 到底买到了什么

### 4.1 单卡容量带

| 卡数 | 可承载模型（NVFP4） | 可承载模型（FP8） |
|---|---|---|
| 1× 96GB | Qwen3.5-27B、MiniMax-M2.5-REAP | — |
| 2× 96GB | MiniMax-M2.5、Qwen3.5-122B | — |
| 4× 96GB | Qwen3.5-397B、GLM-4.7、MiniMax-M2.5 FP8 | MiniMax-M2.5 |
| 6× 96GB | GLM-5（TP2 PP3） | — |
| 8× 96GB | 全部当前模型 | GLM-4.7、Qwen3.5-397B、Kimi K2.5 INT4 |

来源 [e-6k-model-band][e-6k-4x-models][c-not-for-huge-models]

**容量结论**：单卡舒适区是 20B–35B；70B 需量化；235B 级不该考虑单卡 [c-96gb-band]。

### 4.2 单卡实测吞吐

| 模型 | 参数 | TTFT p95 | TPOT | 单流 tok/s | 精度 |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | 35B MoE (3B 激活) | 170 ms | 4 ms | **~213** | FP8 |
| Llama-3.1-8B | 8B | 205 ms | 7 ms | ~143 | FP8 |
| gpt-oss-20b | 20B MoE | 170 ms | 8 ms | ~125 | MXFP4 |
| Qwen3-Coder-30B-A3B | 30B MoE (3B 激活) | 30 ms | 9 ms | ~111 | BF16 |
| Qwen3-VL-8B | 8B | 162 ms | 12 ms | ~78 | BF16 |

来源 [e-eco-qwen35-213][c-35b-tps][c-96gb-band]

**MoE 的 token 速率要按"激活参数"理解**：35B MoE 只有 3B 激活，所以 213 tok/s 高于 8B 稠密模型的 143 tok/s。这不是芯片的线性算力体现。

峰值与预填充：
- llama-3.1-8B 峰值输出约 **11,500 tok/s**；gpt-oss-20b 约 **8,900 tok/s**（单卡）[c-single-gpu-8b-peak]
- 8k 提示词 prefill 约 **170k–220k tok/s** → 长上下文与 RAG 是该卡最具成本优势的场景 [c-prefill-throughput]

### 4.3 多卡扩展与通信约束

RTX PRO 6000 **没有 NVLink**，多卡走 PCIe 5.0 [c-nvlink-absent]。实测：

- 同交换机/NUMA 内 P2P 延迟 **0.36–0.45 μs**
- 关闭 P2P 后延迟跳到 **~14 μs**
- P2P 单向写带宽 ~55–56 GB/s，双向 ~111 GB/s

这对张量并行（TP）的 all-reduce 是硬约束。社区数据：8 卡 NCCL all-reduce 总线带宽 37.6–41.1 GB/s（取决于交换机拓扑与 `NCCL_MIN_NCHANNELS=8`）[e-6k-p2p]。

**实践含义**：能用单卡解决的，不要用多卡；必须多卡时，PCIe switch 拓扑显著优于双路 CPU 直连。

#### 4.3.1 一个会静默损坏输出的 P2P 陷阱（本轮新增，务必先读）

上面讲的是 P2P "慢"。更危险的是 P2P **根本不能用却假装能用**。

**机制** [c-ptp-silent-corruption]：在开启 IOMMU 的裸金属 Linux 上，PCIe peer copy **不是慢，是不被支持**。写入触发 fault，IOMMU 把它当作 Unsupported Request 丢弃——但 `cudaMemcpyPeerAsync` **仍然返回 `cudaSuccess`**，因为它没有"平台吞掉了你的 DMA"这种返回码 [e-ptp-copy]。

**后果**：张量永远没到达，模型输出 `!!!!!`、`/////`、重复的西里尔字母或看似流畅但语义错乱的话——**而且什么都不会记录** [e-ptp-silent]。现场表现和"量化损坏"或"聊天模板写错"一模一样，有用户为此查了一整天。

**为什么 RTX PRO 6000 特别容易踩** [c-ptp-gate-wrong]：多数工具按**产品名**而非**实际 NVLink 拓扑**决定是否开 P2P，而 RTX PRO 6000 被错误列入"数据中心卡"名单——同一名单里还有 RTX 6000 Ada、L40/L40S、L4，**这四个系列全都没有 NVLink 接口** [e-ptp-list]。

**两个反直觉的坑**：

| 坑 | 说明 |
|---|---|
| `GGML_CUDA_P2P=0` 反而**开启** P2P | 该变量是"存在即生效"，不是布尔开关 [c-ptp-zero-trap] |
| 驱动会**撒谎** | `can_device_access_peer()` 和 `nvidia-smi topo -p2p w` 在每次拷贝都失败的机器上仍报 OK [c-ptp-driver-lies] |

llama.cpp 自己的文档就写着：IOMMU 开启时"可能导致崩溃或输出损坏" [e-ptp-doc]。vLLM 也已因此实现了独立的 `can_actually_p2p()` 探针——说明这是行业已知问题，不是孤例。

**可执行的判断与处置** [c-ptp-mitigation]：

```bash
# 唯一可信的判断依据：看拓扑里是不是 NV#
nvidia-smi topo -m
# 出现 SYS / PHB / NODE 而非 NV# → 不要开 P2P
```

| 场景 | 处置 |
|---|---|
| 拓扑显示 `NV#` | 可开 P2P（RTX PRO 6000 不会有这个） |
| 显示 `SYS`/`PHB`/`NODE` | **关闭 P2P**，改用 FP32 累积或每卡独立副本 |
| 必须多卡协同 | 优先返回 CPU 中转（慢但正确），或关闭 IOMMU（有安全与性能代价） |

**这是本报告认为最应该加粗的一条**：无 NVLink 卡的 P2P 失败是**静默的**，它不会报错，只会让你的结果变错。

#### 4.3.2 PCIe 链路可能静默抖动（第二个反直觉陷阱）

即使 P2P 配置正确，链路本身也可能不正常——**而且不报任何错**。

**实测**：在 17 卡 c-payne 系统上，**2 分钟内 35 个设备共发生 1415 次 Gen1/Gen2/Gen5 之间重协商** [c-6kw-link-flap]。而单次 `nvidia-smi` 或 `lspci` 快照只会捕捉到其中一个相位，**看起来完全健康**。

**正确做法**：连续采样，而不是看一次

```bash
watch -n1 'cat /sys/bus/pci/devices/0000:e3:00.0/current_link_speed'
```

**但锁定速率有陷阱** [c-6kw-link-lock]：`Hardware Autonomous Speed Disable`（Link Control 2, bit 5）会**双向**阻止速率变化。如果在卡恰好处于 Gen2 时锁定它，会把卡**永久困在 Gen2**——有生产卡因此以 Gen2 x16 运行了数小时。必须先确认链路已达最大速率再锁。

**另一个高频陷阱** [c-6kw-aspm]：ASPM 与 PCIe 端口电源管理会导致 **Surprise Link Down**（`aer_uncor_status: 0x00000020`）系统锁死。修复：

```bash
GRUB_CMDLINE_LINUX_DEFAULT="pcie_aspm=off pcie_port_pm=off"
```

#### 4.3.3 NCCL 调优能让通信带宽翻倍

默认配置在 PCIe 多卡系统上是**严重次优**的。

**实测** [c-6kw-numachan]：

| 配置 | 8 卡 all-reduce 总线带宽 |
|---|---:|
| 默认 | **22.2 GB/s** |
| `NCCL_MIN_NCHANNELS=8` | **37.6 GB/s** |
| 同上 + 交换机拓扑 | 39.4–41.1 GB/s |

**一条环境变量就带来 +69%**。这在 TP 推理中直接转化为 decode 吞吐。

**小消息还有额外优化** [c-6kw-ncclxml]：在 AMD Turin 平台提供 NCCL 图 XML，32KB 消息延迟从 48.16μs 降到 26.20μs（**1.84×**），64KB 从 48.69μs 降到 25.59μs（**1.90×**）。小消息正是 decode 阶段 all-reduce 的典型形态。

**自定义 all-reduce 有明确交叉点** [c-6kw-custom-ar]：

| 消息大小 | 自定义 | NCCL | 胜者 |
|---:|---:|---:|---|
| 256 B | 7.5 μs | 24.6 μs | 自定义 **3.3×** |
| 32 KB | 16.5 μs | 24.5 μs | 自定义 1.5× |
| 64 KB | 25.9 μs | 24.1 μs | 基本持平 |
| 256 KB | 73.6 μs | 28.0 μs | NCCL **2.6×** |

而且**自定义 all-reduce 只在 PCIe 交换机拓扑下有利**，双路 CPU 无交换机时反而比 NCCL 慢。

**常见死锁的诊断线索** [c-6kw-nccl-deadlock]：GPU 占用 100%、功耗约 140W、显存不增长、进程挂死——这是 `NCCL_P2P_LEVEL` 与拓扑不匹配的典型表现，应从 `4` 改为 `2` 或 `PHB`。

**IOMMU 是多个问题的共同根因** [c-6kw-iommu]：NCCL 死锁与 P2P 锁定的推荐修复都包含 `iommu=off` 以及 `options nvidia_uvm uvm_disable_hmm=1`。这与 §4.3.1 的分析互为印证。

#### 4.3.4 一个电气层面的隐蔽故障

反复掉卡有时不是软件问题 [c-6kw-ground]：一份 16 卡现场报告把问题追到**四个机箱 PSU 的插座未提供保护接地（PE）**。这与 §10.6 的供电熔毁同属供电域——**PCIe 多卡机箱的接地必须由合格电工核验**。

### 4.4 量化格式 × 上下文：最重要的反直觉发现

同一硬件、同一模型（Qwen3.5-397B-A17B）、4× Server Edition TP4 下：

**单流 decode（tok/s），C=1：**

| 量化 + MTP | ctx=0 | 16k | 32k | 64k | 128k | 衰减 |
|---|---|---|---|---|---|---|
| AWQ + MTP ON | **147** | 110 | 88 | 61 | **40** | **-73%** |
| AWQ + MTP OFF | 104 | 104 | 103 | 100 | 96 | -8% |
| NVFP4 + MTP ON | 127 | 127 | 127 | 128 | 122 | **-4%** |
| NVFP4 + MTP OFF | 81 | 80 | 80 | 78 | 77 | -5% |

来源 [e-6k-awq-collapse][e-6k-nvfp4-stable][c-awq-longctx-collapse][c-nvfp4-stable]

**这是本报告最重要的工程结论**：

1. **AWQ + MTP 在长上下文会崩塌**。32k 起 MTP 反而**有害**（88 < 103）；128k 时比不用 MTP 慢 2.4 倍。
2. **NVFP4 + MTP 全程稳定**，128k 仅衰减 4%。
3. **交叉点在 16k–32k**：短上下文 AWQ 快 16%，长上下文 NVFP4 快 3.1 倍 [c-longctx-choice]。
4. 根因尚未完全确定，疑与 vLLM 的 AWQ/MTP KV cache 分配与投机 token 接受率交互有关。

**引擎选择同样关键**：128k 上下文下 vLLM 比 SGLang 快 **4.2 倍**（带 MTP）/ **2.2 倍**（不带）[e-6k-vllm-sglang][c-vllm-longctx]。

**投机解码的整体收益**：短上下文 26–57% 吞吐提升 [c-mtp-benefit]；Qwen3.8-27B 上单 token 延迟 22ms→13ms，同延迟预算内并发 32→64 [e-eco-mtp]。且 GPQA Diamond 上无显著精度损失（+0.76pp，p=0.18）[c-mtp-quality]。

### 4.5 并发扩展

4 卡 TP4、Qwen3.5-397B、短上下文：

| 配置 | C=1 | C=8 | C=16 | C=32 | C=64 | C=128 |
|---|---|---|---|---|---|---|
| AWQ + MTP | 147 | 767 | 1163 | 1679 | 2622 | **3519** |
| NVFP4 + MTP | 127 | 615 | 934 | 1441 | 2283 | 3220 |

来源 [e-6k-concurrency][c-concurrency-scale]

短上下文批处理是 AWQ 的唯一优势区间；长上下文必须切 NVFP4。

#### 4.5.1 跨用户汇总验证：独立 wiki 的 9 组配置

一个专门追踪该卡的实地 wiki（16 卡机箱实战记录）给出了与上面几乎一致的图景 [c-6kw-rig]，可作独立交叉验证：

**Qwen3.5-397B 单流 decode（tok/s）** [c-6kw-397b-matrix]：

| 卡数 | 量化 | 引擎 | MTP | tok/s |
|:--:|---|---|---:|---:|
| 4× | **AWQ-INT4** | SGLang | 5 | **152** |
| 4× | NVFP4 | SGLang | 5 | 132 |
| 4× | NVFP4 | vLLM | 2 | 130 |
| 4× | NVFP4 | vLLM | 无 | 70–86 |
| 8× | NVFP4 | SGLang | 有 | **350** |

**这印证了 §4.4 的核心判断**：AWQ-INT4 + MTP 在短上下文单流上确实最快（152），NVFP4 紧随（132）。

**MTP 的加速幅度稳定在 +51%～+72%** [c-6kw-mtp]：

| 并发 | 无 MTP | MTP=2 | 提升 |
|---:|---:|---:|---:|
| 1 | 85.8 | 130.0 | +51.5% |
| 10 | 334.3 | 573.5 | +71.6% |
| 32 | 605.9 | 922.6 | +52.3% |

接收率 **89.2%**，平均接收长度 2.73–3.69 token。峰值 **1127.1 tok/s** @ 50 用户 1K 上下文。

**长上下文下，模型版本比硬件更重要** [c-6kw-longctx]：

| 上下文 | CARVE (tok/s) | NVIDIA 参考 (tok/s) | 胜者 |
|---:|---:|---:|---|
| 10K | 76.9 | 92.3 | 参考 +20% |
| 100K | 74.8 | 73.6 | 基本持平 |
| 300K | 73.3 | 43.8 | **CARVE +67%** |
| 500K | 67.0 | 42.2 | **CARVE +59%** |

**交叉点在 100K 附近**。这意味着"选哪个量化版本"在长上下文场景下比"选哪张卡"影响更大——与 §4.4 的结论方向一致但更强。

### 4.5.2 DCP：长上下文的一条生死线（此前完全未涉及）

**Decode Context Parallelism（DCP）** 是把 KV cache 沿序列维切分到多卡的技术。它不是可选项：

> Kimi K2.5 在 150K 上下文下，**无 DCP 仅 6–7 tok/s（不可用），DCP=8 可达 28–35 tok/s** [c-6kw-dcp]

这个 4–5 倍的差距，是"能不能用"与"不能用"的分界。本报告此前所有长上下文数据都是在已启用 DCP 的前提下测得的，这个前提必须写明。

### 4.6 MLPerf 官方封闭分区数据（此前缺失的第三方口径）

此前本报告把"MLPerf 封闭分区成绩"列为证据缺口。现由 Cisco UCS X580p 白皮书补齐 [c-mlperf-closed-available]。

**这是唯一一套经过 MLCommons 方法论约束、且由第三方（Cisco）提交的数据**，价值在于口径统一、可跨系统比较。

| 项目 | 内容 |
|---|---|
| 基准版本 | MLPerf Inference **v6.0 Datacenter, Closed Division** |
| 测试配置 | **4× RTX PRO 6000** PCIe（对比 4× H200 NVL、4× RTX PRO 4500） |
| 覆盖模型 | Llama2-70B、Llama3.1-8B、Whisper、Mixtral-7×8B、GPT-OSS-120B [c-mlperf-models] |
| 场景 | Offline（吞吐）+ Server（延迟约束） |

**一个结构性发现**：同一节点上 **H200 NVL 可用两路 NVLink 桥，而 RTX PRO 6000 只能走 PCIe** [c-mlperf-nvlink-asym]。这印证并强化了 §4.3 的结论——该卡的多卡推理劣势是**架构性的、在系统设计层面就被固定的**，不是驱动或软件问题。

**引用注意** [c-mlperf-caveat]：白皮书中部分图表是提交截止后的初步结果，**未经 MLCommons 正式验证**。引用时必须区分"已认证"与"未认证"数据点，不能一概当作官方成绩。

Mixtral-7×8B 与 GPT-OSS-120B 的纳入尤其有价值：前者是 MoE（显存带宽敏感），后者是 120B 级大模型（容量敏感），正是该卡最该被检验的两类负载。

### 4.7 llama.cpp / GGUF：此前完全遗漏的第二条软件路径

前面的推理数据全部来自 vLLM 与 SGLang。但 RTX PRO 6000 还有一条成熟的 **llama.cpp/GGUF** 路径 [c-llamacpp-path]，能在 `sm_120a` 上原生编译运行 [e-btl-sku]。对"本地跑一个模型自己用"的场景，它往往比 vLLM 更容易部署。

**prefill 实测**（`-b 2048 -ub 2048 -fa 1`，全 GPU 卸载，F16 KV）[c-llamacpp-prefill]：

| 模型 | 提示长度 | prefill 吞吐 |
|---|---|---|
| Qwen3.5-35B-A3B-Q8_0 | 2048 | **16,459 tok/s** |
| Qwen3.5-35B-A3B-Q8_0 | 4096 | 16,595 tok/s |
| Qwen3.8-27B-Q8_0 | 2048 | **4,757 tok/s** |
| Qwen3.8-27B-Q8_0 | 4096 | 4,699 tok/s |

**MoE 与稠密的收益差距明显** [c-llamacpp-moe-gap]：同一次 GDN kernel 优化，35B-A3B（MoE）提升 **11–21%**，稠密 27B 只有 **3–6%** [e-lc-moe-gap]。说明 **MoE 在 llama.cpp 上还有较大优化空间**，后续版本可能继续拉开。

**优化不损精度** [c-llamacpp-quality]：困惑度 5.777 → 5.782，top-token 一致率 98.824% [e-lc-ppl]。这个差异小于测量不确定度，可以放心用。

**单流 decode 与 5090 接近持平** [c-llamacpp-decode-parity]：8.4GB 的 Q2 量化模型上，Server 版生成 **43.16 tok/s** [e-btl-gen]。原因很直接——**两者带宽同为 1792 GB/s，decode 是带宽瓶颈** [e-btl-parity]。这再次印证 §5 的核心判断：单流 decode 上 96GB 买不到速度，只能买到容量。

**NVIDIA 官方在 2026-09 宣称** llama.cpp 与 vLLM 的优化可带来最高 **1.9 倍**本地推理提升，并通过 LM Studio / Ollama 直接可用 [c-nvidia-19x]。注意最大收益出现在 RTX 5090 上跑 Qwen3.6-35B，**不代表 PRO 6000 同幅度**。

**双卡部署的坑（重要）** [c-multigpu-split-fails]：在 PCIe 环境下，llama.cpp 的**层切分会损坏文本与工具调用输出**，**行切分不被支持**。唯一可靠方案是**每卡跑一个独立副本** [e-t2-split]——这正是 §4.3.1 那个 P2P 陷阱的另一种表现。

**两种扩展路线的取舍**：

| 路线 | 吞吐 | 适用 |
|---|---|---|
| 双卡独立副本（llama.cpp） | 290.3 tok/s @ 总并发 8 [c-replica-scaling] | 高可用、单卡故障不拖垮全部 |
| 单卡 vLLM 高并发 | **1,336.5 tok/s @ C32** [c-serving-vs-replica] | 吞吐优先的服务化场景 |

**这两行不可直接比较**——批处理形态不同（4 槽/卡 vs 32 并发），原报告也明确声明它不是受控的模型速度 A/B。要比较必须控制并发与序列长度。

**一个有用的交叉验证** [c-500w-tie]：500W 功耗墙下，同一模型在 llama.cpp 与 vLLM 上分别跑到 70.3 与 72.1 tok/s，**基本持平** [e-t2-speed]。这从第二条软件路径独立佐证了 §6.4 的结论：**500W 与 600W 在推理上差异很小**。

**实际可用的上下文能力** [c-longctx-256k]：双卡各 500W 的部署中，每副本 4 槽、池化 1,048,576 token，单槽硬上限 **262,144 token** [e-t2-ctx]。这是 96GB + Q8_0 KV 的真实可用值，不是营销数字。

---

## 5. 与 RTX 5090 的横向对比

### 5.1 三套独立口径

**口径 A — 应用级（UL Procyon AI Text Generation，TensorRT，同平台）：**

| 模型 | PRO 6000 | RTX 5090 | 差距 |
|---|---|---|---|
| Phi | 6,775 | 5,749 | **+17.8%** |
| Mistral | 7,346 | 6,267 | **+17.2%** |
| Llama3 | 6,501 | 6,104 | **+6.5%** |
| Llama2 | 8,008 | 6,591 | **+21.5%** |

来源 [e-sr-procyon-phi][e-sr-procyon-mistral][e-sr-procyon-llama3][e-sr-procyon-llama2][c-vs-5090-procyon]

**注意趋势**：Llama3 只差 6.5%，但 Llama2（更长上下文）差 21.5%。**上下文越长，显存优势越突出** [c-vs-5090-procyon-gap]。

**口径 B — 综合指数（LynxBenchAI 26Q3，固定 PyTorch 模型集，稳态吞吐）：**

| 维度 | 倍数 | PRO 6000 (SE) | RTX 5090 |
|---|---|---|---|
| 综合 | **1.20×** | 718.86 | 597.49 |
| 训练 | 1.14× | 587.80 | 515.26 |
| 推理 | 1.22× | 1201.04 | 985.84 |
| 计算 | 1.31× | 366.56 | 279.64 |

来源 [e-lynx-overall][e-lynx-method][c-vs-5090-lynx]

**分项极值**：稠密 FP32 矩阵乘 2.08×（744.41 vs 357.86）[c-vs-5090-fp32]；但**稀疏 FP32 只有 0.88×**（266.83 vs 301.70）——优势并非全面。

**口径 C — 渲染（Blender Open Data 众测）：**

| GPU | 分数 |
|---|---|
| RTX PRO 6000 Workstation | **18,571** |
| GeForce RTX 5090 | 16,311 |
| RTX PRO 6000 Server | **15,821** |
| GeForce RTX 4090 | 11,663 |

来源 [e-blender-oden][e-blender-5090][e-blender-se][c-vs-5090-blender][c-blender-ratio]

**反直觉点**：Server 版在 Blender 上**低于**消费级 5090 约 3%。原因是显存时钟 12,481 vs 13,365 MHz 与 P0 pstate [c-vf-skup]。**买 Server 版做渲染是错配**。

### 5.2 差距的真正来源

| 因素 | 贡献 |
|---|---|
| 核心数 +10.6%（24,064 vs 21,760） | 线性算力，约 +10% |
| 频率 +8.7%（2617 vs 2407 MHz） | 叠加后 FP32 达 +20% [c-vs-5090-db] |
| 显存容量 3×（96 vs 32GB） | **决定"能否装入"，非"多快"** |
| 显存带宽相同（1792 GB/s） | 短上下文/小模型差距最小的原因 |
| 无 consumer 驱动限制、ECC、MIG | 稳定性与企业特性，不体现为跑分 |

**结论**：如果你的模型本来就能塞进 32GB，PRO 6000 只快 15–20%（实测口径），价格却是 3–8 倍 [c-vs-5090-15-20]。**溢价买的是"装得下"和"跑得稳"，不是"算得快"**。

---

## 6. 功耗与能效：600W 是否值得

### 6.1 三 SKU 的固件差异（核心发现）

同一颗硅片，三套被固件锁死的参数 [c-vf-skup]：

| 变体 | 功耗范围 | TDP | 散热 | pstate | 显存时钟 |
|---|---|---|---|---|---|
| Workstation | 150–600W | 600W | 主动单槽 | **P1** | 13,365 MHz |
| Server | 300–600W | 600W | 被动 | **P0** | 12,481 MHz |
| Max-Q | ~250–325W | 300W | 主动双槽 | P1 | **15,865 MHz** |

**这些参数用户不可调** [e-pl-ws-memclock][e-pl-ws-13365][e-pl-se-12481][e-pl-maxq-15865]。

关键机制：**显存时钟在 SKU 内不随功耗墙变化，功耗墙只限制 SM 频率** [c-memclock-invariant]。因此：
- 计算密集型负载 → 对功耗墙**敏感**
- 显存带宽密集型（decode、attention）→ 对功耗墙**不敏感**

### 6.2 性能-功耗曲线

张量核心吞吐（gpu_burn -tc，Gflop/s）：

| 功耗墙 | WS 均值 | Server 均值 | Server 相对 |
|---|---|---|---|
| 300W | 90,210 | 124,224 | **+38%** |
| 350W | 105,446 | 134,710 | +28% |
| 400W | 118,836 | 143,769 | +21% |
| 450W | 131,127 | 151,414 | +15% |
| 500W | 142,427 | **157,543** | +11% |
| 550W | 153,582 | （受冷却限制） | — |
| **600W** | **163,545** | （受冷却限制） | — |

来源 [e-pl-se-38pct][c-server-low-power-win]

**Server 版在每一个可干净测量的功耗点（≤500W）都更快**，差距从 300W 的 +38% 收窄到 500W 的 +11%。

原因不是硬件，而是**升压哲学**：同一 kernel（BF16 1024² matmul）下，WS 冲到 2805 MHz / 600W，Server 只取 2415 MHz / 390W [e-pl-natural][c-ws-uses-watts]。甚至在功率最接近的 memcopy 上（WS 401W vs Server 365W），**WS 仍高出 17% 频率** [e-pl-memcopy]。

### 6.3 能效最优工作点

| 功耗墙 | WS Gflop/s/W | Server Gflop/s/W |
|---|---|---|
| 300W | 301 | **414** |
| 350W | 305 | 388 |
| 400W | 297 | 359 |
| 500W | 285 | 314 |
| 600W | **274** | — |

来源 [c-server-efficiency][c-ws-efficiency-flat]

**结论**：
- **Server 版 @ 300W 是全系能效最优**（414 Gflop/s/W）[c-server-efficiency]
- **WS 版能效在 200–350W 平坦**（~300–305），600W 相比损失约 11% [c-ws-efficiency-flat]
- 工作站建议跑 300–350W：约 64% 吞吐换一半功耗，温度 47–51°C、噪声低

### 6.4 真实推理负载下的功耗结论

| 对比 | 结果 |
|---|---|
| 500W vs 600W | 性能几乎相同 [c-power-500-600] |
| 300W vs 500W（单用户） | 仅损失 4% |
| 300W vs 500W（64 并发） | 损失可达 **30%** |
| 300W（≤4 并发） | 几乎无损失 |
| Max-Q(300W) vs WS(600W) | prefill 慢约 20%，decode 相近 [c-maxq-ws-diff] |

**运营建议**：低并发/单用户场景可放心把功耗墙降到 300W，省电且几乎不掉性能；高并发服务必须保功耗。

### 6.5 散热陷阱

- Server 版在风冷工作站塔式机箱内，**300W 模式不超 83°C，600W 模式可达 90°C** [c-thermal-hostkey]
- 该卡被动散热，**依赖服务器机箱风道**；塔式机箱超过 500W 会热降频 [c-thermal-chassis-limit]
- 视频生成实测：300W→600W 使生成时间从 ~40 分钟降至 ~30 分钟（+25%），但伴随显著温升 [c-thermal-power-gain]

**这是部署时最容易被忽略的坑**：买 Server 版塞进塔式机箱，性能会被机箱风道卡住，不是卡的问题。

---

## 7. 专业图形与渲染

### 7.1 相对上代的定位

- **vs RTX 6000 Ada**：Procyon 各项领先（Llama2 8008 vs 3957，约 2 倍）[e-sr-procyon-llama2]
- **vs A6000**：Foster + Partners 报告 Cyclops 光追场景达 **5 倍**、渲染速度 5 倍 [c-vs-a6000-foster]（客户引言，未经独立验证）
- **vs L40S**：官方声明渲染超 2 倍、agentic LLM 推理最高 5 倍、基因组近 7 倍、文生视频 3.3 倍 [c-vs-l40s]（厂商口径，条件未公开）

### 7.1.1 SPECviewperf 15 官方分项数据（此前声明的缺口，现已补齐）

此前本报告把"SPECviewperf 15 分项"列为缺口。现由 SPEC 官方结果库直接取得原始数据 [c-vp15-official]。

**口径**：LENOVO ThinkStation P8 / Threadripper PRO 9965WX / 128GB / **Windows 11 Pro** / **4K** / SPECviewperf **15.0.1-rc2**，11 项全部产出分数 [e-vp15-config][e-vp15-version]。

| 工作负载 | 分数 | 说明 |
|---|---:|---|
| **creo-04** | **259.46** | 最强项 |
| **solidworks-08** | **212.31** | 显著强于 CATIA/3ds Max [c-vp15-sw-strong] |
| maya-07 | 189.76 | |
| medical-04 | 170.60 | |
| energy-04 | 159.35 | |
| catia-07 | 125.19 | |
| 3dsmax-08 | 112.81 | |
| blender-01 | 112.88 | |
| unreal_engine-01 | 103.02 | |
| snx-05 | 97.50 | |
| **enscape-01** | **71.96** | 最弱项（实时渲染）[c-vp15-weakest] |

**跨主机一致性检验** [c-vp15-consistency]：三台完全不同的主机（Dell Pro Max T2、Lenovo P3 Tower Gen2、Lenovo P8）给出高度一致的结果——3dsmax 108.2–112.8、blender 110.8–112.9、catia 119.1–125.2 [e-vp15-consistency]。**这是本报告所有渲染数据中最可信的一组**，因为它是官方提交、版本与分辨率都明确、且被多方复现。

**相对上一代 RTX 6000 Ada（同为 4K）** [c-vp15-vs-ada]：

| 工作负载 | Blackwell | Ada | 倍数 |
|---|---:|---:|---:|
| **enscape-01** | 73.00 | 30.44 | **2.40×** |
| **blender-01** | 111.56 | 53.03 | **2.10×** |
| energy-04 | 161.12 | 86.69 | 1.86× |
| 3dsmax-08 | 110.11 | 81.34 | 1.35× |
| catia-07 | 122.40 | 93.66 | 1.31× |
| solidworks-08 | 210.65 | 161.15 | 1.31× |
| medical-04 | 172.50 | 132.82 | 1.30× |
| maya-07 | 178.89 | 143.66 | 1.25× |
| creo-04 | 252.58 | 205.87 | 1.23× |
| **unreal_engine-01** | 95.33 | 85.56 | **1.11×** |
| snx-05 | 104.80 | n/a | 不可比 [c-vp15-ada-snx-missing] |

**几何平均 1.47×，中位数仅 1.31×**。这个差距必须被强调：**代际提升完全取决于你用什么软件**——实时渲染（Enscape/Blender）接近翻倍，而 Unreal 几乎没变（1.11×）。

**相对 AMD Radeon AI PRO R9700（同为 4K）** [c-vp15-vs-amd]：

| 工作负载 | P6000 | R9700 | 倍数 |
|---|---:|---:|---:|
| enscape-01 | 73.0 | 26.1 | **2.80×** |
| energy-04 | 161.1 | 59.0 | 2.73× |
| blender-01 | 111.6 | 52.5 | 2.13× |
| solidworks-08 | 210.6 | 101.8 | 2.07× |
| 3dsmax-08 | 110.1 | 59.6 | 1.85× |
| maya-07 | 178.9 | 102.3 | 1.75× |
| catia-07 | 122.4 | 81.6 | 1.50× |
| creo-04 | 252.6 | 169.0 | 1.49× |
| medical-04 | 172.5 | 131.6 | 1.31× |
| **unreal_engine-01** | 95.3 | 91.0 | **1.05×** |
| snx-05 | 104.8 | n/a | 不可比 |

**几何平均 1.79×** [c-vp15-vs-amd]。NVIDIA 在 ISV 应用上的优势依然明显，但**在 Unreal 上几乎打平**——这修正了"专业卡全面碾压"的简化印象。

**一个被复合分掩盖的事实** [c-vp15-subtest-spread]：单项内部子测试差异可达 **10 倍以上**。3dsmax-08 里 Clay 模型 478.41 FPS，而 Project Soane 线框只有 **31.72 FPS**；blender-01 里 X-ray 413.51 FPS，而带阴影着色只有 **33.27 FPS** [e-vp15-subfps][e-vp15-blender-subfps]。

> **实践含义**：如果你的场景恰好是"大模型 + 线框/阴影"这类低分子项，你感受到的性能会远低于复合分暗示的水平。**复合分是加权平均，不要把它当成你的场景的预测值**。


### 7.2 渲染：三个渲染器给出三种排序（本报告最重要的修正）

**没有一个"哪个 SKU 渲染更强"的统一答案**——渲染器差异远大于 SKU 差异 [c-render-workload-dependent]：

| 渲染器 | Workstation | Server | RTX 5090 | 胜者 |
|---|---|---|---|---|
| **V-Ray** | 11,994 | **14,827** | 10,116 | **Server**（比 WS 高 24%，比 5090 高 47%）[c-vray-se-wins][c-vray-ratios] |
| **Blender**（Drop & Render） | **16,272** | 9,382 | 15,005 | **Workstation**（比 Server 高 73%，比 5090 高 8%）[c-blender-dr] |
| **OctaneBench 2025** | **1,750** | 1,641 | 1,730 | 三者接近，WS 仅比 5090 高 1.2% [c-octane] |

**V-Ray 上 Server 版拿第一（#1 of 210）**，这与"Server 版不适合渲染"的直觉完全相反 [e-dr-se-vray]。原因是 V-Ray 是计算密集的路径追踪，Server 版在高功耗区可充分发挥。

**Blender 上 Server 版掉到 #17**（9,382 分）[e-dr-se-blender]，而 Workstation 版是 #1（16,272）[e-dr-ws-blender]。

### 7.3 一条必须并列呈现的冲突

Blender 的 Server 版成绩，两个来源相差 **69%**：

| 来源 | Server 版 Blender 分 | 说明 |
|---|---|---|
| Blender Open Data（众测） | **15,821** | 社区贡献，样本构成不透明 [e-blender-se] |
| Drop & Render（自建库） | **9,382** | 农场方自测，标注"3 of 4 benchmarks" [e-dr-se-blender] |

**本报告不对该冲突做裁决** [c-blender-conflict]。可能原因：Blender 版本不同、测试场景子集不同、Server 卡在测试机箱内的散热条件不同（被动散热卡对风道极敏感，见 §6.5）。

**采购含义**：若要以 Blender 为主要渲染器，**必须要求供应商在你的场景上实测**，不能引用任一第三方分数。

### 7.4 视频与专业特性

- **4× 第 9 代 NVENC + 4× 第 6 代 NVDEC**，支持 4:2:2 H.264/HEVC 编解码 [c-nvenc]
- 4× DisplayPort 2.1（8K@240Hz / 16K@60Hz）
- ISV 认证驱动（DCC/CAD 应用）

消费级 5090 编码器数量更少、无 ISV 认证 [c-nvenc]。

**4:2:2 不是规格表上的装饰，有同行评议的实测支撑**。一篇 ICIP 2026 Workshops 论文以"四编码器 Blackwell GPU"为测试台，做了 8K 10bit 4:2:2 HEVC 的 V-PCC 编码实验 [c-vpcc-422-milestone]：

| 指标 | 结果 |
|---|---|
| 4 路分帧编码吞吐 | **122 fps**（8K 10bit 4:2:2 HEVC） |
| 是否满足实时 | ✅ 高密度 V-PCC 要求最高 120 fps [c-vpcc-8k-demand] |
| 代价 | BD-Rate 劣化最高 **5%**（切片边界无法利用空间冗余）[c-vpcc-cost] |

**为什么这件事重要**：过去 GPU 编码器不支持 4:2:2，实时 V-PCC 只能靠定制 ASIC。Blackwell 的 10bit 4:2:2 硬件支持让通用 GPU 首次能承担这个负载 [c-vpcc-422-milestone]。

**这是本代在视频领域少有的"质变"而非"量变"**——跑分体现不出来，但对体积视频/点云直播这类场景是能力边界的变化。

### 7.5 整机形态验证

HP Z8 Fury G6i 实际产品印证了 Max-Q 的定位 [c-hpz8-config]：单机可配 **4 张 Max-Q（384GB）** 或 **1 张 600W Workstation 版**，配 2700W 双电源 [e-hpz8-4gpu][e-hpz8-psu]。

这说明 Max-Q 的设计意图不是"单卡最强"，而是**单机显存密度最大化**——4 张 Max-Q 的 384GB 远超任何单卡方案。

### 7.6 CAE / CFD 仿真：一个此前完全未覆盖的场景

本报告此前只覆盖渲染与 CAD。**仿真计算是另一个独立且重要的专业图形场景**，而且有第三方实测 [c-cae-scenario]。

**测试条件**：41.3M 单元排气模型、**双精度**、1:1 CPU 核卡比、Ansys Fluent 2026，对比 RTX PRO 5000、RTX PRO 6000、H200 NVL（有/无 NVLink）[e-fx-method][e-fx-cards]。

**相对 32 核 CPU 的加速比** [c-cae-speedup]：

| 配置 | RTX PRO 5000 | **RTX PRO 6000** | H200 NVL + NVLink | H200 NVL 无 NVLink |
|---|---:|---:|---:|---:|
| 1× | — | — | — | 15.32× |
| 2× | — | **16.67×** | 19.73× | 21.35× |
| 4× | 22.37× | **26.42×** | 23.14× | 25.82× |
| 6× | 26.56× | **29.06×** | 30.44× | 24.06× |
| 8× | 33.67× | **34.23×** | 28.65× | 25.50× |

**第一层结论**：GPU 对 CFD 是**数量级提升**，不是边际改善——单卡就有 15 倍以上。

**第二层结论更反直觉** [c-cae-nvlink-harm]：**NVLink 在中等规模仿真中不但无益，甚至有害**。H200 NVL 在 2 卡与 4 卡时，**无 NVLink 反而更快**（2 卡 390.90s vs 436.13s）。直到 6 卡才反转（331.54s vs 419.58s）。

> **这是对本报告"无 NVLink 是劣势"这一总体判断的重要限定**。对 LLM 推理的 TP，NVLink 必不可少；但对中等规模 CFD，它可能是负资产。**结论不能跨场景套用**。

**第三层结论** [c-cae-vs-5000]：RTX PRO 6000 相对 PRO 5000 的优势**随卡数迅速衰减**——4 卡时快约 15%，6 卡时约 8.5%，8 卡时不到 2%。

**扩展有天花板** [c-cae-scaling-ceiling]：41.3M 单元时 6–8 卡已接近收益下限；报告建议 **60–100M+ 单元**才值得上更多卡 [e-fx-plateau]。**在 CFD 上"堆卡"远不如在 LLM 上有效**。

**精度可以直接换显存和时间** [c-cae-precision]：

| 精度 | 显存占用 | 求解时间 |
|---|---:|---:|
| 单精度 | **64.85 GB** | **253.14s** |
| 混合精度 | 87.69 GB | 265.24s |
| 双精度 | 96.54 GB | 299.80s |

**单精度比双精度省 33% 显存、快 18%**。混合精度是 Ansys 新特性（场变量单精度 + AMG 内迭代双精度），精度优于纯单精度。**显存不够时，先换精度再考虑加卡**。

**厂商侧印证** [c-cae-vendor]：Ansys 官方称 RTX PRO 6000 Blackwell Server 是"中小规模部署的强且更易获得的服务器级选项" [e-ansys-roi]。Synopsys 已在 **6 款 Ansys 产品**上部署 RTX PRO Server，包括 FreeFlow、Lumerical FDTD、Perceive EM、Rocky、Speos [c-syn-portfolio]。

**ISV 覆盖面因此被大幅扩展**——该卡不只是渲染卡或 AI 卡，也是**仿真卡**。

---

## 8. 训练与微调：被误解的一侧

### 8.1 相对 H100 的真实位置

常见说法是"不能训练，只能推理"。实测数据更微妙：**结果取决于负载类型与序列长度**。

**硬件底牌对比**（Max-Q vs H100 SXM5）[c-fp64-vs-h100][c-bf16-vs-h100][c-hbm-bw-gap][c-power-vs-h100]：

| 指标 | Max-Q | H100 SXM5 | 谁强 |
|---|---|---|---|
| FP64 | 1.7 TFLOPS | **33.5 TFLOPS** | H100 约 **20×** |
| FP32 | **109.7 TFLOPS** | 66.9 TFLOPS | Max-Q 约 **1.6×** |
| BF16 张量 | 877.9 TFLOPS | **1978.9 TFLOPS** | H100 约 **2.25×** |
| FP4 | **3511.4 TFLOPS** | 不支持 | Blackwell 独有 |
| 显存带宽 | 1792 GB/s | **3352 GB/s** | H100 约 **1.87×** |
| 显存容量 | **96 GB** | 80 GB | Max-Q |
| 功耗 | **300 W** | 700 W | Max-Q |

**这张表解释了一切**：Blackwell 在 FP32 与 FP4 上强，在 FP64、BF16 张量与显存带宽上弱。

### 8.2 单卡装得下 120B

单张 Max-Q（96GB）可完成 **GPT-OSS-120B 的 4bit QLoRA 微调**——这在 80GB 的 H100 上无法单卡完成 [c-ft-120b-single]。

配套方法收益：Unsloth 相比标准 LoRA 最多快 3 倍、省约 80% 显存 [c-ft-unsloth]。

### 8.3 对 H100 的胜负取决于负载

| 负载 | 结果 |
|---|---|
| 稠密 Qwen3-32B | H100 SXM5 **更快** |
| MoE GPT-OSS-120B | Max-Q **快约 1.3 倍** |

来源 [c-ft-vs-h100-mixed]

**解释**：后者是 CPU-bound 的 MoE 负载，瓶颈不在 GPU 算力，此时 96GB 容量与 PCIe 上的 host 交互反而成了优势。

### 8.4 序列长度交叉点（训练侧最重要的发现）

全参数 SFT（Qwen3.5 0.8B–9B，batch=1，bf16，梯度检查点，8-bit AdamW）在 RTX PRO 6000 与 GH200 上的对比 [c-ft-crossover]：

| 序列长度 | 胜者 | 幅度 |
|---|---|---|
| ≲ 1–4K token | **RTX PRO 6000** | 最多 **1.8×** |
| ≳ 8K token | **GH200** | 稳定在 **1.7–1.8×** |

**交叉点随模型增大而前移**：9B 约 2K token 就转向 GH200，0.8B 要到 8–12K [c-ft-crossover-model]。

**机制**：短序列是 compute/launch-bound，高频率高 FP32 占优；长序列是 memory-bandwidth-bound，HBM3 的 4.0 TB/s 占优 [c-hbm-bw-gap]。

### 8.5 优化器卸载：PCIe 的硬伤

当 96GB 撞墙时，把优化器状态卸载到主机内存是常规手段。两卡的差距在这里最悬殊 [c-ft-offload]：

| GPU | 卸载代价 | 链路 |
|---|---|---|
| GH200 | 短序列损失 20–55%，长序列约 20% | NVLink-C2C **~900 GB/s** |
| RTX PRO 6000 | 短序列慢 **12–25 倍**，从未恢复到 0.5× 以上 | PCIe 5.0 **~64 GB/s** |

**结论**：在 RTX PRO 6000 上，优化器卸载基本不可用 [e-alio-offload]。这是 PCIe（~64GB/s）与 NVLink-C2C（~900GB/s，14 倍）的差距造成的，不是 GPU 本身的问题 [e-alio-c2c]。

### 8.6 最大可训练序列长度

96GB 下两卡的容量上限**基本相同** [c-ft-maxseq]：

| 模型 | RTX | GH200 |
|---|---|---|
| 0.8B | 30,720 | 30,720 |
| 2B | 28,672 | 27,648 |
| 4B | 24,576 | 23,552 |
| 9B | **17,408** | 16,384 |

**这印证了 96GB 是真实可用的训练容量**，不是营销数字。但注意：9B 全参 SFT 在 96GB 上只能到约 17K 序列长度，更长需要卸载（而卸载在 RTX 上不可用）。

### 8.7 训练侧结论

| 场景 | 建议 |
|---|---|
| 短序列（<4K）全参微调 | ✅ RTX PRO 6000（快 1.8×，且 300W 省电） |`n| **8B 级 LoRA 微调** | ⚠️ **优先比价：4× 4500 总耗时反超 2× 6000** [c-lora-time] |
| 单卡微调 100B+ 模型（量化） | ✅ RTX PRO 6000（96GB 装得下） |
| 长序列（>8K）全参 SFT | ❌ 用 H100/GH200 |
| 需要优化器卸载扩展容量 | ❌ 用 GH200（PCIe 卸载不可用） |
| BF16 为主的常规训练 | ❌ 用 H100（张量性能 2.25×） |

### 8.8 LoRA 微调的实测基准：该卡在这里并非最优

上面 §8.1–8.7 主要讲全参与大模型。**LoRA 微调是另一回事**，而独立实测给出了一个需要正视的结论 [c-lora-scenario]。

**测试条件**：Llama-3.1-8B + LoRA（rank 16，q/v_proj，seq 512，batch 2/卡，BF16，DDP）[e-lora-setup]。

| 显卡 | 单卡 tok/s | 单卡能效 | 双卡 tok/s | 双卡效率 |
|---|---:|---:|---:|---:|
| **RTX PRO 6000 SE** | **4,962** | 12.3 tok/s/W | **9,541** | **96.1%** |
| RTX PRO 5000 | 3,721 | 10.4 | 7,216 | 97.8% |
| RTX PRO 4500 WS | 2,777 | 9.6 | 5,429 | 97.8% |

**第一个发现：缺 NVLink 并未损害 DDP** [c-lora-ddp]。双卡扩展效率 96.1%–97.8%——因为 **DDP 每卡持完整副本、只同步梯度**，通信量远小于 TP。这与 §4.3 中 TP 受 PCIe 制约的结论**并不矛盾**，是不同并行策略的差异。

**第二个发现：96GB 在 8B LoRA 上用不上** [c-lora-vs-5000]。RTX PRO 6000 只比 PRO 5000 快 **33%**（4,962 vs 3,721），远小于价格差距。

**第三个发现：四张小的可能比两张大的更快** [c-lora-time]：

| 数据规模 | 1× 4500 | 4× 4500 | 2× 5000 | **2× 6000 SE** |
|---|---|---|---|---|
| 小（5M 参数） | ~30 min | **~8 min** | ~12 min | ~9 min |
| 中（50M） | ~5 hr | **~1.3 hr** | ~1.9 hr | ~1.5 hr |
| 大（500M） | ~50 hr | **~13 hr** | ~19 hr | ~15 hr |
| 研究级（5B） | ~21 天 | **~5.4 天** | ~8 天 | ~6 天 |

**4 张 PRO 4500 在总耗时上反超 2 张 PRO 6000**。对小模型微调，"多而小"确实可能优于"少而大"。

> **这条结论修正了 §8.7 表格里"LoRA 一律选 RTX PRO 6000"的简化表述**。准确的说法是：**该卡的价值在容量与长上下文，不在小模型微调的吞吐**。

**云上成本对照** [c-cloud-rate]：Spheron 上 RTX PRO 6000 按需 $2.35/hr、竞价 $1.11/hr，H100 为 $2.65/$2.20 [e-spheron-price]。

但**单 epoch 成本 $0.18–0.21 是投影值不是实测** [c-cloud-cost-epoch]——它由 H100 实测 $0.30 套用第三方 30–40% 系数得出 [e-spheron-projection]。**证据强度低，引用需谨慎**。

---

## 9. 定位与选型

### 9.1 与 H100 / L40S / 上代的位置

| 对比对象 | 该卡的位置 |
|---|---|
| **RTX 5090** | 综合 1.20×，但渲染/稀疏矩阵乘可能落后 [c-vs-5090-lynx][c-render-workload-dependent] |
| **H100 80GB** | 综合约为 H100 的 **76%**（H100 领先 1.31×）[c-vs-h100-lynx] |
| **H100（小模型推理）** | 整体表现相当，token 速率约 2× [c-vs-h100-parity] |
| **H100（短序列微调）** | RTX 领先最多 1.8× [c-ft-crossover] |
| **H100（长序列训练）** | 落后：BF16 张量 2.25×、带宽 1.87×、FP64 20× 差距 [c-bf16-vs-h100][c-hbm-bw-gap][c-fp64-vs-h100] |
| **H100（优化器卸载）** | 差距最大，PCIe 上卸载慢 12–25 倍 [c-ft-offload] |
| **H100（价格）** | 约为其 **1/4**（托管商口径）/ **1/2.9**（日本市场）[c-vs-h100-price][c-ft-h100-price] |
| **L40S** | 推理最高 5×、渲染 2×+（厂商口径）[c-vs-l40s] |
| **H100（基因组）** | Parabricks 上反而比 H100 快 1.75× [c-parabricks] |
| **GH200** | 短序列训练快 1.8×，长序列慢 1.7–1.8× [c-ft-crossover] |
| **RTX 6000 Ada** | Procyon 约 2× [c-vs-5090-procyon] |
| **A5000** | token 速率约 2.2×，预处理吞吐约 3.8× [c-vs-a5000] |

**口径张力的诚实呈现**：HOSTKEY 说"H100 整体相当"，LynxBenchAI 说"H100 领先 31%"，Fixstars 说"稠密模型 H100 更快"。三者不矛盾——分别测的是**中小模型推理**、**综合指数**、**稠密模型微调**。**不要跨口径引用** [c-vs-h100-parity][c-vs-h100-lynx][c-ft-vs-h100-mixed]。

### 9.2 决策矩阵

| 你的场景 | 推荐 | 理由 |
|---|---|---|
| 单机跑 20–35B 模型，要长上下文 | ✅ **Workstation Edition** | 96GB + 1792 GB/s + 本地显示 [c-96gb-band] |
| 单机跑 70B（量化后） | ✅ Workstation | 需量化，但装得下 [c-96gb-band] |
| 单卡微调 100B+（4bit QLoRA） | ✅ Workstation / Max-Q | 96GB 可跑 GPT-OSS-120B [c-ft-120b-single] |
| 短序列（<4K）全参 SFT | ✅ 任一 | 比 GH200 快最多 1.8× [c-ft-crossover] |
| 4 卡单机、供电/空间受限 | ✅ **Max-Q** | 300W × 4 = 1200W，384GB [c-maxq-4gpu][c-hpz8-config] |
| 数据中心多卡推理服务 | ✅ **Server Edition** | 8 卡 800GB，300W 能效最优 [c-server-8gpu][c-server-efficiency] |
| V-Ray 渲染为主 | ✅ **Server Edition** | V-Ray 排名第一，比 WS 高 24% [c-vray-se-wins] |
| Blender 渲染为主 | ⚠️ 需实测 | 两来源冲突达 69%，不可盲选 [c-blender-conflict] |
| 虚拟工作站 / 多租户隔离 | ✅ 任一（MIG） | 4×24GB 完全隔离实例 [c-mig4] |
| 视频工作站（4:2:2 编解码） | ✅ Workstation | 4× NVENC + ISV 认证 [c-nvenc] |
| **CAE/CFD 仿真** | ✅ **4 卡（6000 或 5000）** | 4 卡是最优性价比点，再多收益骤减 [c-cae-config] |`n| **中等规模仿真（~50M 单元）** | ⚠️ **别上 NVLink** | 无 NVLink 反而更快 [c-cae-nvlink-harm] |`n| **8B 级 LoRA 微调** | ⚠️ **先比价** | 96GB 用不上，4×4500 可能更快更省 [c-lora-scenario] |`n| 纯渲染 / 可视化 | ❌ 用 RTX 5090 | 每美元性能约 3 倍 [c-render-value] |
| 长序列（>8K）全参训练 | ❌ 用 H100/GH200 | GH200 领先 1.7–1.8× [c-ft-crossover] |
| 需要优化器卸载扩容量 | ❌ 用 GH200 | PCIe 卸载慢 12–25 倍 [c-ft-offload] |
| 双精度 HPC / 分子动力学 | ❌ 用 H100/H200 | FP64 仅约 2 TFLOPS，比 H100 低 20× [c-fp64-vs-h100] |
| 235B+ 模型单卡 | ❌ 不可能 | 需 H200 或多卡 [c-not-for-huge-models] |
| **采购前想先验证** | ✅ **用云上 8 卡实例** | CoreWeave / AWS G7e / Akamai 均有 Server 版 [c-driver-cloud-available] |
| **单人多卡、无 NVLink** | ⚠️ **每卡独立副本** | 层切分会静默损坏输出 [c-multigpu-split-fails] |
| **需要 7×24 生产可用** | ⚠️ **必须有冗余** | 整芯片复位无前兆且需断电恢复 [c-fullchip-noprecursor] |

**最实用的一条建议**：不要仅凭本报告或任何第三方跑分下单。该卡的 Server 版**已在公有云提供 8 卡实例**（CoreWeave 分 High/Standard Memory 两档；AWS G7e、Akamai LKE 亦有）[c-driver-cloud-available]。用你的真实模型和真实并发跑一轮，比引用任何评测都可靠 [c-cloud-eval-advice]——尤其考虑到本报告已标注的 Blender 三方冲突与多套互不可比的口径。

### 9.3 SKU 选择的四个反直觉提醒

1. **Server 版不是"更强的 Workstation"**，也不是"更弱的"。它固件更保守：低功耗区更强（+38%），高功耗区受限；V-Ray 上第一，Blender 上垫底 [c-server-low-power-win][c-render-workload-dependent]。**必须按具体负载实测**。
2. **Max-Q 显存时钟最高**（15,865 MHz，高于 WS 的 13,365）[c-vf-skup]。对显存带宽密集的 decode 负载，Max-Q **可能**优于 WS——但**该假设尚未被实测验证**，属待验证推断 [c-maxq-ws-diff]。
3. **Workstation 版会主动吃满功耗**。同样负载下它比 Server 版多用 1.5–2 倍电 [c-ws-uses-watts]，电费敏感场景需主动设功耗墙。
4. **驱动下限只对 Server 版有正式声明**（575.57.08）[c-driver-floor]，而自动化工具会把三个 SKU 折叠成同一个标识 [c-driver-tooling-collapse]——这意味着通用的驱动版本管控可能误判。WS/Max-Q 版需单独核对支持列表（570.195.03 起）[e-driver-ws-list]。

---

## 10. 软件生态与坑

### 10.1 SM120 与 SM100 的分裂

RTX PRO 6000 用 **SM120**（GB202），数据中心 Blackwell 用 **SM100**。差异：

- SM120 **缺少 tcgen05 / TMEM / 2-CTA** 等特性
- 但社区内核级分析认为：**这些特性对 SM120 不是必需的**，硬件本身不受限 [e-sm120-tcgen05][c-sm120-software-gap]
- **真正的瓶颈是软件生态**：主流框架优先为 SM100 优化，SM120 的内核排期靠后 [e-sm120-software][c-sm120-software-gap]

**实际后果**：新模型/新量化格式在 SM120 上往往需要 nightly 构建或补丁（HOSTKEY 测 WAN 2.2 时需 `--pre` 安装 cu129 nightly PyTorch）[c-driver-gap]。

**这不是抽象风险，有精确的实例**（详见 §10.2）：NVIDIA 自己的 TensorRT-LLM 在 sm120 上无法服务 Qwen3-Next，而官方同时把两者都列为"支持" [c-trtllm-misleading]。

### 10.2 案例：TensorRT-LLM 在 sm120 上开箱失败

这是 SM120 生态缺口最清晰的一份证据，值得完整记录。

**现象** [c-trtllm-sm120-gap]：用 `trtllm-serve` 加载 `nvidia/Qwen3-Next-80B-A3B-Instruct-NVFP4`（`Qwen3NextForCausalLM`，混合 Gated-DeltaNet + MoE），服务启动后在 GDN prefill 预热阶段直接崩溃：

```
RuntimeError: delta rule kernel does not support this device major version: 12
```

**根因** [c-trtllm-root-cause]：TensorRT-LLM 1.3.0rc19 捆绑 **flashinfer 0.6.12**，其 `chunk_gated_delta_rule` / `gdn_prefill` kernel **只编译了 Hopper（sm90）**，硬拒绝 compute capability 12.0。错误栈里的路径 `gdn_prefill_sm90/` 直接暴露了范围。

**讽刺之处** [c-trtllm-misleading]：NVIDIA 把 Qwen3-Next 和 Blackwell 都列在支持列表里，组合起来却开箱即失败。**"支持列表"不等于"可部署"**。

**修复已存在但没进发行版** [c-trtllm-fix-available]：flashinfer ≥0.6.13 已加入 sm120 GDN kernel（2026-06-17 合并）。绕过方案（已验证）：

```bash
pip install --upgrade "flashinfer-python>=0.6.13"
export FLASHINFER_CUDA_ARCH_LIST=12.0f
export FLASHINFER_FORCE_SM=120f
```

**这不是孤例** [c-trtllm-not-isolated]：同一 GPU 上 MoE 路径（issue #11932）、以及 #14973/#14780 等多个 issue 呈现同类 sm120 失败。现有 fallback 是设备无关的 Triton 实现，比原生 kernel 慢 [c-trtllm-triton-fallback]。

**实操含义**：在 RTX PRO 6000 上部署新架构模型前，**必须核对捆绑库的 arch 覆盖**，而不是核对模型支持列表。

### 10.3 已知具体坑

| 坑 | 说明 | 来源 |
|---|---|---|
| TensorRT-LLM GDN 仅 sm90 | Qwen3-Next 在 sm120 预热崩溃 | [c-trtllm-sm120-gap] |
| AWQ + MTP 长上下文崩塌 | 128k 时 -73%，32k 起 MTP 有害 | [c-awq-longctx-collapse] |
| SGLang 长上下文劣势 | 128k 下比 vLLM 慢 4.2× | [c-vllm-longctx] |
| Server 版早期无 Windows 驱动 | Linux 需内核 6+ / GCC 12 | [c-driver-gap] |
| 塔式机箱散热不足 | Server 版 >500W 降频 | [c-thermal-chassis-limit] |
| 无 NVLink | 多卡走 PCIe，P2P 关闭时延迟 14μs | [c-nvlink-absent] |


### 10.4 软件栈现状

- **NVFP4 是 SM120 的关键能力**，也是本地推理最重要的优化点 [c-nvfp4-native]
- 投机解码需要 checkpoint 自带 draft head（Qwen3.5/3.6/3.8 系列支持）[c-mtp-benefit]
- 训练侧：`gpu_burn` 类合成负载与真实推理对功耗墙的响应完全不同，**不要用合成负载推断推理性能** [c-memclock-invariant]

### 10.5 在役退化风险：这是本报告最需要警示的运维问题

**评测网站在测新卡，但用户论坛在报旧卡性能退化。** 两者不冲突，只是观察窗口不同。

**症状** [c-degradation]：
- 长期高负载（有报告称 6 个月 80%+ 利用率）后，600W 下最高频率缓慢下降
- 最终触发软件功耗封顶（SW Power Cap），SM 频率锁在 **580–650 MHz**（正常可到 3090 MHz）
- FP32 从 110+ TFLOPS 掉到 **6–11 TFLOPS**，即 **1/10 – 1/20** 性能 [c-degradation-scale]

**判定依据（"假高功耗"指纹）** [c-degradation-false-telemetry]：
- nvidia-smi 报告约 **600W**，但温度仅 **34–36°C** —— 物理上不可能
- 空闲间隙频率能正常冲到 2600 MHz，一进持续计算就塌回 600 MHz
- 说明 GPU **能**跑高频，是功耗遥测误判把它压住了

**排除了什么** [c-degradation-not-software]：驱动（三个分支均复现）、内核、主板 BIOS、功耗上限、线缆 sense 引脚全部排除；且发生在**完全未变更的软件栈**上，运行约 8 个月后出现。

**为什么危险** [c-degradation-silent]：
- **不产生任何错误**：无 Xid、无 ECC 错误、无 PCIe 报错
- 多卡训练时表现为"健康卡等故障卡同步梯度"，整体变慢但很难归因
- 采购验收时跑分正常，几个月后才暴露

**证据强度（诚实标注）**：至少 5 名独立用户在 NVIDIA 官方论坛报告同类指纹，其中一人已退回 2 张卡、另有 2 张异常 [c-degradation-multiuser]。但**未见 NVIDIA 官方公告或召回**，样本量有限，不能推断为全批次缺陷 [c-degradation]。

**另有争议点**：温度阈值显示为负值（Shutdown -5°C）是否算 bug。NVIDIA 论坛人员解释这些是相对 T.Limit 的**差值**而非绝对温度，不是缺陷 [c-temp-threshold-dispute]。本报告采信该解释，但**锁频故障本身仍被多方独立复现**，两者是不同问题。

**运维建议** [c-degradation-procurement]：

| 措施 | 说明 |
|---|---|
| 要求书面 RMA 政策 | 退化是否在保修范围需事先确认 |
| 到货即记录基线 | 存 `nvidia-smi -q` 与标准跑分，作为后续对比锚点 |
| 部署监控告警 | 跟踪 `clocks_event_reasons.sw_power_cap` 与频率/功耗比 |
| 关注空闲功耗 | 有报告空闲 200–300W 偏高 [c-idle-power-high]，可作为早期信号 |
| 多卡训练加看门狗 | 检测单卡吞吐偏离集群中位数 |

### 10.6 供电接口熔毁：另一个与性能无关的硬件风险

600W 全部通过单个 12V-2x6（16-pin）接口输入，这是该卡最脆弱的物理环节。

**已发生的事件** [c-melt-incident]：一台配 ASRock Taichi TC-1650T 电源的 RTX PRO 6000 WS 整机，**接头在电源侧熔毁并熔进插座**，而两端都已完全插到位 [e-melt-event]。显卡本身未损坏，损伤限于电源侧 [c-melt-gpu-survived]。

**根因指向传感器位置** [c-melt-root]：该电源的 NTC 温度传感器被装在**接地线侧而非 12V 侧**，可能因此没能及时捕捉升温 [e-melt-sensor]。

**这不是偶发** [c-melt-recurring]：同一 GPU + PSU 组合在 **2026-03 已发生过一次**类似熔毁。

**保护机制不可依赖** [c-melt-protection-unreliable]：ASRock 的 TempGuard 曾在另一个场景成功拦截 1350W 改装的 5090，但这次没拦住。**"有保护"不等于"保护会生效"**。

**保修风险真实存在** [c-melt-warranty-risk]：已有厂商（PNY）拒绝 16-pin 熔毁的保修索赔，理由是"原生 PSU 线材不在保修范围"。

**采购/部署建议**：

| 措施 | 说明 |
|---|---|
| 优先选原生 12V-2x6 线材 | 避免转接头，减少接触电阻 |
| 确认线材完全插到位 | 该案例中已插到位仍失效，故需更保守 |
| 优先选带 12V 侧温度监测的电源 | 接地线侧传感可能漏检 |
| 确认 PSU 线材的保修条款 | 部分厂商明确不覆盖 |
| 高密度部署考虑 8-pin 多路方案 | 分散单点电流，牺牲便利换安全 |

**诚实标注**：这是基于单一维修技师报告 + 历史先例的分析，**不是统计意义上的故障率**。但它与 RTX 5090 上已大量出现的同类事件同源（同一连接器标准），因此不应被当作孤例忽略。

### 10.7 整芯片复位：比退化更严重的可用性故障

§10.5 的退化是"变慢"，这里是**直接不可用**。本报告在第二轮挖掘中发现了这个此前完全遗漏的故障类别。

**症状** [c-fullchip-fault]：GPU 在持续推理负载下进入不可恢复状态——nvidia-smi 里还能看到，但 Fan / Power / GPU-Util / MIG 全部报 `ERR!`，`GPU Recovery Action: Reset`。**软重启无效，必须彻底断掉 PSU 电源** [e-fc-powercycle]。

**内核日志特征** [c-fullchip-symptoms]：**1 秒内 74,341 次寄存器读错误**，全部返回同一毒值 `0xbadf3200`，随后触发 `NV_ERR_GPU_IN_FULLCHIP_RESET` 断言级联 [e-fc-74k]。

**最棘手的是它没有前兆** [c-fullchip-noprecursor]：故障发生前的内核日志干净，没有任何预警 [e-fc-noprecursor]。这意味着**预测性维护失效**，只能靠冗余。

**时间尺度与退化一致** [c-fullchip-latency]：有用户报告 24/7 稳定运行数月，然后一周内多次复发 [e-fc-months]。采购验收时测不出来。

**已排除项（覆盖相当充分）** [c-fullchip-ruledout]：散热（故障时仅 28°C）、显存 OOM、驱动版本（580.x 与 595.45.04 均复现）、PCIe 链路降级、应用 bug、另一块卡干扰，甚至换 PCIe 插槽也无效——**故障跟随卡而非插槽** [e-fc-slot][e-fc-thermal][e-fc-driver]。

**缓解手段有限且有争议**：

| 手段 | 效果 | 争议 |
|---|---|---|
| 降功耗墙到 450W | 有用户可稳定跑 2 小时 gpu_burn [c-fullchip-powerworkaround] | ⚠️ 另一用户报告 600W/450W 都数分钟崩溃 [c-fullchip-powerworkaround-disputed] |
| 改用 Triton 后端 | 临时可用，非修复 [c-fullchip-workaround-triton] | 说明与特定内核实现相关 |
| RMA 换卡 | 有用户通过 RMA 解决 [e-fc-rma] | 指向个体缺陷 |

**这不是单一故障，而是一个 Xid 家族** [c-xid-family]：Xid 31（MMU fault）、Xid 62/154（GSP PMU halt）、Xid 79（掉卡）、Xid 119（GSP 超时）、Xid 120（GSP kernel panic）。多个错误码指向 **GSP 固件层面的共性问题** [e-mmu-xid31][e-mmu-xid120][e-mmu-xid79]。

**证据强度**：至少 5 名独立用户在 NVIDIA 官方论坛报告，负载覆盖 vLLM、Ollama、llama.cpp 与 UNet 训练 [c-fullchip-multiuser]。Max-Q 版本亦有 MMU 错误报告 [c-mmu-maxq]，但不限于某一 SKU。

> **与 §10.5 的关系**：两者可能是同一硬件问题的不同表现（退化 → 最终复位），也可能是两个独立缺陷。当前证据**不足以判定**，本报告不做合并也不做割裂。

---

## 11. 虚拟化与机密计算：两个被忽视的企业能力

这两个维度是与 RTX 5090 的**结构性分野**，跑分完全不体现，但决定了能否进入企业采购清单。

### 11.1 MIG 多租户：不是"切分显存"，是硬件隔离

MIG 把一张卡在硬件层切成最多 4 个完全隔离的实例（每实例 24GB）[c-mig4]，每个实例有独立的 SM 与存储子系统。

**官方实测收益** [c-vgpu-mig20][c-vgpu-sharing]：

| 配置 | 相对单 VM 的吞吐 |
|---|---|
| 2 个 VM | **+34%** |
| 4 个 VM | **+52%** |
| MIG vs 时间切片（48GB 档） | **+20%** |

**为什么 MIG 更快而非更慢**：时间切片靠调度器轮转，存在上下文切换与 QoS 抖动；MIG 是物理隔离，延迟与吞吐可预测 [c-vgpu-sharing]。

**厂商演示**：4× MIG 实例同时跑 4 个 1080p 全高《赛博朋克 2077》，相比时间切片基线图形扩展性能 **+60%** [c-mig-multitenant]。

**官方选型结论**：RTX PRO 6000 Server Edition 是高性能 vWS 部署的推荐 GPU（SPECviewperf 15 @ 4K 原生性能最高）[c-vgpu-best]。

### 11.2 机密计算：厂商说 98%，学术说 73–87%

RTX PRO 6000 **硬件内置 CC 支持**，与 HGX B200/B300 同属支持 CC 的 Blackwell 产品 [c-cc-supported]。这是消费级 RTX 5090 完全没有的能力。

**两套数字，必须并列**：

| 来源 | 口径 | CC 开销 |
|---|---|---|
| NVIDIA 官方 [c-cc-vendor-claim] | HGX B300 + Qwen3.5-397B FP8，SGLang | **-1% ~ -8%**（保持约 98%） |
| 学术论文 [c-cc-academic-gap] | **RTX PRO 6000** 与 B300 HGX，Intel TDX + GPU-CC | **-13% ~ -27%**，KV 恢复延迟翻倍以上 |

**两者不矛盾，因为测的不是同一件事**：官方基准在 B300 上、且已应用多项优化；学术论文专门研究了**未优化**状态下的桥接开销 [e-arxiv-platforms]。

**根因已定位** [c-cc-cause]：损失来自 **VM-GPU 机密桥接**的串行化，不是 GPU 计算。B300 上 BF16 matmul 仅降到 **0.998×** [e-arxiv-compute]。具体表现为：
- 小块分配-拷贝操作慢约 **44 倍** [c-cc-alloc]
- KV-cache 恢复代价 **+131%**，模型加载慢 **34 倍** [c-cc-kv-load]

**好消息是开销可回收** [c-cc-recover]：调度标志回收 57%，工作线程 drain 在高并发下最多回收 **92%**。工程手段包括 FlashInfer 的 CC-safe 自动调优计时、SGLang 的异步 D2H worker、分片 CUDA graph [c-cc-mitigation]。

**选型提醒**：多卡机密域（NVLink 加密，最多 8 卡）仅 HGX B200/B300 支持；RTX PRO 6000 是**单卡 CC** [c-cc-scope]。需要多卡机密训练/推理的场景，它不是答案。

---

## 12. 价格与采购时机

### 12.1 价格时间线（截至 2026-10-27）

| 时点 | 价格 | 说明 |
|---|---|---|
| 2025-03 发布 | 无官方 MSRP | 通过 PNY / TD SYNNEX 分销 [e-press-availability] |
| 2025-05 上市 | **~$8,435–8,565** | 渠道挂牌价（VideoCardz 转述）[c-price-launch] |
| 2026-08 | **$16,000** | 官方调价，接近翻倍 [c-price-now] |
| **2026-10-27** | **$17,999**（≈¥120,058） | 美国 10 家店的典型最低新价 [c-price-17999] |
| 同期 RTX 5090 | **$4,996**（≈¥33,325） | 美国 17 家店典型最低新价 [c-price-5090-4996] |

**当前价格比 = 3.6 倍** [c-price-ratio]。涨价主因是高端 GDDR7/DRAM 供应紧张，且预期持续多年 [c-price-cause]。

### 12.2 另一种口径：持有型 TCO 下它反而最便宜

上面的 $17,999 是**零售单卡价**。大规模自持部署看的是**每芯片每小时持有成本**（含折旧、电力、机房、运维），两者结论相反。

SemiAnalysis InferenceX 的 2026-07 定价模型 [c-tco-rtx-hourly]：

| 芯片 | TCO（$/chip/hr） |
|---|---|
| **RTX PRO 6000** | **0.68** |
| H100 SXM | 1.17 |
| H200 SXM | 1.22 |
| B200 | 1.73 |
| B300 | 2.26 |

按此口径，RTX PRO 6000 的每小时成本约为 **H200 的 56%、H100 的 58%**，是所列芯片中最低的 [c-tco-rtx-cheaper]。

**为什么两个口径差这么大**：零售价被渠道溢价和 GDDR7 短缺推高，而 TCO 模型按大规模采购折旧摊分，且该卡 600W 的功耗在机房层面不构成主要成本项。**买一张卡和运营一万张卡，是两套经济学。**

**但这个口径不能直接换算成每 token 成本** [c-tco-unmeasured]：SemiAnalysis 在 Qwen3.5-397B 的 65/105/144 tok/s/user 三个档位上**都没有 RTX PRO 6000 的实测吞吐**，只有 H200 的 $0.67/$0.96/$1.19 每百万 token。缺吞吐数据就无法算每 token 成本 [c-tco-not-comparable]。

**诚实结论**：低每小时成本是必要条件，不是充分条件。要判断推理经济性，仍需该卡在目标模型上的实测吞吐——而这一环目前公开数据缺失。

### 12.3 每美元性能：一个残酷的结论（零售口径）

按渲染性能/价格计，RTX PRO 6000 在该基准库 33 张有价卡片中**排最后一名** [c-value-worst]：

| 指标 | RTX PRO 6000 WS | RTX 5090 | 倍数 |
|---|---|---|---|
| V-Ray 每 $100 得分 | **66.6** | **202** | **3.0×** [c-render-value] |

**这意味着：纯渲染用途上，RTX 5090 的每美元性能约为 RTX PRO 6000 的 3 倍** [c-render-value]。

这个结论必须在报告里说清楚：RTX PRO 6000 的价值**不在渲染**，而在"渲染 + 大模型同机共存"。如果不需要 96GB 显存跑模型，纯渲染买它是严重浪费。

### 12.4 同代产品价格锚点

| 产品 | 显存 | 价格 |
|---|---|---|
| RTX PRO 6000 WS | 96GB | **$17,999**（2026-10） |
| RTX PRO 5500 | 84GB | 已发布，21,760 CUDA（=5090 核心数）[c-eol-pro5500] |
| RTX PRO 5000 72GB | 72GB | $9,999 MSRP / £6,899 街价（2025-12）[c-price-5000-72g] |
| RTX 5090 | 32GB | **$4,996**（2026-10），且可能停产 |

### 12.5 一个会改变比价逻辑的变量：RTX 5090 可能停产

**本报告的 3.6 倍比价建立在"5090 现价 $4,996"上。这个分母可能不再稳定。**

有两条独立爆料称，NVIDIA 已停止向 RTX 5090 分配 GB202 晶圆，未来全部 GB202 供给 RTX Pro 系列 [c-eol-5090]。另有爆料称停产日期定在 2027 年 1 月 [c-eol-jan-date]。

**证据等级必须说清楚**：这是**爆料级**信息，NVIDIA 未确认 [c-eol-unconfirmed]。但它有旁证——RTX PRO 5500 已发布，用 5090 的核心数（21,760）配 84GB 显存 [c-eol-pro5500]，正是"GB202 转向 Pro 线"的产物。

**对选型的影响** [c-eol-price-impact]：

| 情形 | 后果 |
|---|---|
| 5090 真停产 | 其价格进一步上涨，**3.6 倍比价收窄** |
| 5090 供给枯竭 | "用 5090 做纯渲染更划算"的建议**时效性变短** |
| 需要长期供货保障 | RTX Pro 系列反而是更稳的选择 |

**这是本报告唯一一个"结论可能因供给变化而反转"的地方**。如果 5090 涨到 $8,000，每美元渲染性能的 3 倍优势就缩到 1.8 倍，选型逻辑会明显松动。

### 12.6 采购建议

**这是本报告最需要强调的时点问题**：所有基于 2025 年 $8,500 价位的"性价比"论证**在 2026 年已失效**。当前 $17,999 下：

| 情形 | 建议 |
|---|---|
| 必须单卡 96GB 跑大模型/长上下文 | 无可替代，接受溢价 |
| 只需 72–84GB 容量 | 考虑 RTX PRO 5000 72GB（约一半价格）或 PRO 5500 84GB |
| 纯渲染/可视化 | ❌ 选 RTX 5090，每美元性能约 3 倍（**但注意停产风险**） |
| 可用多卡替代单卡 | 重新计算总拥有成本（2×5090 的 64GB 仍不及单卡 96GB 的易用性） |
| 数据中心多卡推理 | 对比 H100/H200 的每 token 成本，而非单卡价格 |
| 高负载 7×24 运行 | ⚠️ 先读 §10.5 退化风险与 §10.6 供电风险，要求书面 RMA 政策 |

---

## 13. 争议与证据缺口

### 13.1 明确的口径冲突

| 议题 | 说法 A | 说法 B | 处置 |
|---|---|---|---|
| vs H100 整体性能 | HOSTKEY：整体相当，token 速率约 2× [c-vs-h100-parity] | LynxBenchAI：H100 领先 31% [c-vs-h100-lynx]；Fixstars：稠密模型 H100 更快 [c-ft-vs-h100-mixed] | **并列呈现**：三者分别测小模型推理、综合指数、稠密微调，不可互相否定 |
| **Blender 的 Server 版成绩** | Blender Open Data：15,821 [e-blender-se] | Drop & Render：9,382 [e-dr-se-blender] | **标为 disputed，不做裁决** [c-blender-conflict]，差距 69% |
| vs 5090 差距 | Procyon：+6.5%~21.5% [c-vs-5090-procyon-gap] | Drop & Render Blender：Server 版 -38% [c-blender-dr] | **并列呈现**：前者是 AI 推理，后者是渲染且为不同 SKU |
| Max-Q 是否适合 decode | 推理：显存时钟最高可能更优 | 无实测吞吐数据 | **标为未验证推断** [c-maxq-ws-diff] |
| Server 版是否适合渲染 | V-Ray #1（14,827）[c-vray-se-wins] | Blender #17（9,382）[c-blender-dr] | **按渲染器分别结论** [c-render-workload-dependent] |

### 13.2 证据缺口清单

**本轮已关闭的缺口**（第二轮挖掘的成果）：

| 原缺口 | 状态 | 来源 |
|---|---|---|
| SPECviewperf 15 分项数据 | ✅ **已补齐** | SPEC 官方结果库，11 项分项 + 代际/竞品对比（§7.1.1） |
| 多卡隐蔽故障模式 | ✅ **已补齐** | P2P 静默损坏（§4.3.1）+ 整芯片复位（§10.7） |
| vLLM/SGLang 之外的软件路径 | ✅ **已补齐** | llama.cpp/GGUF 实测（§4.7） |
| 驱动版本与云上可用性 | ✅ **已补齐** | aicr #2446 + CoreWeave/AWS/Akamai（§9.3） |

**仍未取得的资料**：

1. **Puget Systems / Phoronix / TechPowerUp** 完整评测正文（Cloudflare 403 / bot-check）
2. **SPECworkstation** 分项数据（V-Ray 已由 Drop & Render 补上）
3. **Max-Q 的实际推理吞吐**（社区仅提供遥测，无 Gflop/s 或 tok/s）
4. **Comino Grando 4U 液冷整机（8× 768GB）** 的完整评测正文（StorageReview 403）
5. **Blender Server 版冲突的仲裁**（需要同机同版本同场景的三方复测）
6. **MLPerf 具体吞吐数字**（Cisco 白皮书正文以图表呈现，可解析文本未含数值表）
7. **在役退化与整芯片复位的官方定性**（NVIDIA 尚未公开承认或归因）

### 13.3 对结论稳健性的影响

主要结论（规格、SKU 差异来源、显存容量带、功耗-能效关系、价格时间线、训练交叉点）**均有 ≥2 个独立来源交叉印证**，缺口不改变结论方向。但：

- **专业 CAD/AEC 采购**现已可直接引用 §7.1.1 的官方分项数据，无需再自行补测
- **Blender 渲染采购**必须自行实测（现有两个来源冲突 69%）
- **大规模部署**应补测自身负载的 MLPerf 类指标
- **Max-Q 选型**应要求供应商提供实测吞吐
- **7×24 生产部署**必须规划冗余——整芯片复位无前兆且需断电恢复（§10.7）

---

## 14. 下一步观察点

| 观察项 | 为什么重要 | 触发条件 |
|---|---|---|
| GDDR7 供应缓解 | 价格可能回落，性价比结论反转 | DRAM 厂商扩产公告 |
| `RTX 6000D` 国内市场接受度 | 规格已明确（§3.3），但需求疲弱，可能影响后续 SKU 策略 | 出货数据或停产公告 |
| SM120 内核优化进展 | 当前软件劣势可能缩小 | vLLM/SGLang 为 SM120 专门优化 |
| AWQ + MTP 长上下文问题修复 | 可能让 AWQ 重新可用于长上下文 | vLLM issue 关闭 |
| Max-Q 实测吞吐公布 | 决定它是否真是 decode 最优 SKU | 第三方测试 |
| Blackwell 后继架构 | 影响现在是否该等 | NVIDIA 路线图 |

---

## 15. 参考文献

### 一手来源（NVIDIA 官方）

1. [RTX PRO 6000 Blackwell Workstation Edition 产品页](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/) — [src-nvidia-ws-edition]
2. [RTX PRO 6000 Blackwell Max-Q Workstation Edition 产品页](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000-max-q/) — [src-nvidia-maxq]
3. [RTX PRO 6000 Blackwell Server Edition 产品页](https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/) — [src-nvidia-server]
4. [NVIDIA RTX PRO Server 产品页](https://www.nvidia.com/en-us/data-center/products/rtx-pro-server/) — [src-nvidia-rtxpro-server]
5. [GTC 2025 发布新闻稿](https://nvidianews.nvidia.com/news/nvidia-blackwell-rtx-pro-workstations-servers-agentic-ai)（2025-03-18） — [src-nvidia-press-gtc]
6. [NVIDIA Blog：Server Edition 技术说明](https://blogs.nvidia.com/blog/rtx-pro-6000-blackwell-server-edition/)（2025-03-18） — [src-nvidia-blog-server]

### 独立评测与实测

7. [StorageReview：RTX PRO 6000 Workstation GPU Review](https://www.storagereview.com/review/nvidia-rtx-pro-6000-workstation-gpu-review-blackwell-architecture-and-96-gb-for-pro-workflows)（2025-10-07） — [src-storagereview-review]
8. [HOSTKEY：Server Edition Tests & Benchmarks](https://huggingface.co/blog/HOSTKEY/nvidia-rtx-6000-blackwell-server-edition-tests-ben)（2025-08-30） — [src-hostkey-bench]
9. [TechnoLynx LynxBenchAI：Server Edition vs RTX 5090](https://www.technolynx.com/lynxbench-ai/compare/rtx-pro-6000-blackwell-server-edition-vs-rtx-5090/) — [src-technolynx]
10. [EcoHash：What 96 GB on one card actually buys you](https://huggingface.co/blog/ecohash-ai/what-96-gb-on-one-card-actually-buys-you)（2026-09-14） — [src-ecohash-96gb]

### 社区实测档案

11. [local-inference-lab/rtx6kpro：RTX 6000 Pro Wiki](https://github.com/local-inference-lab/rtx6kpro) — [src-rtx6kpro-readme]
12. [Inference Throughput: Qwen3.5-397B Quantizations](https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/inference-throughput/README.md)（2026-03-14） — [src-rtx6kpro-throughput]
13. [Benchmark Results 汇总](https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/results.md) — [src-rtx6kpro-results]
14. [Power-Limit Sweep：Workstation vs Server vs Max-Q](https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/blackwell-power-limit-sweep.md) — [src-rtx6kpro-power]
15. [SM120 vs SM100 Architecture](https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/sm120-vs-sm100-architecture.md) — [src-rtx6kpro-sm120]

### 媒体与价格

16. [CG Channel：NVIDIA launches 72GB RTX PRO 5000 Blackwell GPU](https://www.cgchannel.com/2025/12/nvidia-launches-new-72gb-rtx-pro-5000-blackwell-gpu/)（2025-12-22） — [src-cgchannel-lineup]
17. [什么值得买（转快科技）：RTX PRO 6000 涨价至 16000 美元](https://post.smzdm.com/p/a3morm8k/)（2026-08-13） — [src-smzdm-price]
18. [太平洋科技（转快科技）：RTX PRO 6000 专业卡首测](https://news.pconline.com.cn/1926/19268483.html)（2025-05-16） — [src-pconline]
19. [Blender Artists Community：RTX PRO 6000 Performance](https://blenderartists.org/t/rtx-pro-6000-performance/1648521/2)（2026-07-24） — [src-blenderartists]

### 渲染基准与训练实测

20. [Drop & Render：RTX PRO 6000 Workstation Edition 渲染基准](https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-pro-6000-blackwell-workstation-edition)（更新 2026-10-26） — [src-dropandrender-ws]
21. [Drop & Render：RTX PRO 6000 Server Edition 渲染基准](https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-pro-6000-blackwell-server-edition)（更新 2026-10-26） — [src-dropandrender-se]
22. [Drop & Render：RTX 5090 渲染基准](https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-5090)（更新 2026-10-26） — [src-dropandrender-5090]
23. [Fixstars：RTX 6000 Blackwell Max-Q LLM 微调评估](https://blog.us.fixstars.com/evaluating-llm-fine-tuning-efficiency-on-nvidia-rtx-6000-blackwell-max-q/) — [src-fixstars-ft]
24. [Alio Leuchtmann：RTX PRO 6000 vs GH200 全参 SFT 基准](https://huggingface.co/blog/AlioLeuchtmann/rtx-6000-pro-vs-gh200-sft-benchmark)（2026-06-05） — [src-alio-sft]
25. [StorageReview：HP Z8 Fury G6i 评测（4× Max-Q 整机）](https://www.storagereview.com/review/hp-z8-fury-g6i-review-one-xeon-up-to-four-blackwell-gpus)（2026-06-23） — [src-sr-hpz8]

### 虚拟化与机密计算

26. [NVIDIA：GPU Performance and Sharing Characteristics（RTX vWS 选型指南）](https://docs.nvidia.com/vgpu/sizing/virtual-workstation/latest/right-gpu.html)（更新 2026-08-19） — [src-nvidia-vgpu-sizing]
27. [NVIDIA Developer：Hardware-Rooted AI Security That Won't Slow You Down](https://developer.nvidia.com/blog/hardware-rooted-ai-security-that-wont-slow-you-down/)（2026-07-02） — [src-nvidia-cc-blog]
28. [arXiv:2606.23969：The Serialized Bridge — LLM Serving under Blackwell GPU Confidential Computing](https://arxiv.org/abs/2606.23969)（v2, 2026-07-09） — [src-arxiv-cc]
29. [IT之家（转 WccfTech）：RTX PRO 6000 演示同时跑 4 个《赛博朋克 2077》](https://www.ithome.com/0/878/374.htm)（2025-08-27） — [src-ithome-mig]

### 稳定性与在役退化（社区故障报告）

30. [NVIDIA Developer Forums：Blackwell Pro 6000 MHz degrading](https://forums.developer.nvidia.com/t/blackwell-pro-6000-mhz-degrading/355157)（2026-02～2026-10） — [src-forum-mhzdeg]
31. [NVIDIA Developer Forums：PRO 6000 Blackwell WS — SW Power Cap ~600MHz @ 600W/35°C](https://forums.developer.nvidia.com/t/pro-6000-blackwell-ws-sw-power-cap-600-mhz-600-w-35-c-fix-or-rma/376937)（2026-07-15） — [src-forum-swcap]
32. [NVIDIA Developer Forums：Wrong temperature thresholds causes SW Power Cap, throttled to 510MHz](https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-wrong-temperature-thresholds-causes-sw-power-cap-gpu-throttled-to-510mhz-1-6-performance/362488)（2026-03-05） — [src-forum-thresh]

### 软件生态实证与 TCO

33. [NVIDIA/TensorRT-LLM Issue #15634：Qwen3-Next 在 sm120（RTX PRO 6000）预热失败](https://github.com/NVIDIA/TensorRT-LLM/issues/15634)（2026-06-25） — [src-trtllm-15634]
34. [SemiAnalysis InferenceX：Qwen3.5-397B H200 vs RTX PRO 6000 每美元性能](https://inferencex.semianalysis.com/compare-per-dollar/qwen-3-5-h200-vs-rtx6000pro)（2026-07 定价） — [src-inferencex-tco]
35. [SemiAnalysis InferenceX：AI Chips for LLM Inference（规格与云定价索引）](https://inferencex.semianalysis.com/chips) — [src-inferencex-chips]

### 中国特供型号

36. [中关村在线：RTX 6000D 中国特供版深度拆解 — 性能降约 23%](https://diy.zol.com.cn/1133/11334549.html)（2026-02-12） — [src-zol-6000d]

### MLPerf 与专业媒体实测

37. [Cisco：MLPerf Inference on UCS X580p with H200 NVL and RTX PRO 6000（白皮书）](https://www.cisco.com/c/en/us/products/collateral/servers-unified-computing/ucs-x-series-modular-system/mlperf-inference-ucs-x580p-wp.html)（更新 2026-09-30） — [src-cisco-mlperf]
38. [arXiv:2606.29179：8K 10-bit 4:2:2 硬件编码性能分析（ICIP 2026 Workshops）](https://arxiv.org/abs/2606.29179)（2026-06-28） — [src-arxiv-vpcc]

### 硬件安全与产品生命周期

39. [TechPowerUp：ASRock TempGuard 未能阻止 RTX PRO 6000 的 PSU 侧接口熔毁](https://www.techpowerup.com/352658/asrocks-tempguard-failed-to-stop-a-psu-side-connector-meltdown-on-a-usd-15-000-rtx-pro-6000-rig)（2026-09-14） — [src-tpu-melt]
40. [TechPowerUp：NVIDIA 据称终止 RTX 5090，GB202 晶圆留给工作站卡](https://www.techpowerup.com/353578/nvidia-reportedly-ending-the-rtx-5090-reserves-gb202-silicon-for-workstation-gpus)（2026-10-10） — [src-tpu-eol]

### 驱动与云可用性

41. [NVIDIA/aicr PR #2446：声明 RTX PRO 6000 Server Edition 驱动下限](https://github.com/NVIDIA/aicr/pull/2446)（合并 2026-09-03） — [src-aicr-driver]
42. [CoreWeave：RTX PRO 6000 Blackwell Server Edition（8 卡实例）](https://docs.coreweave.com/platform/instances/gpu/rtxp6000-8x) — [src-coreweave-rtx]

---

## 附录 A：子问题完成度

| # | 问题 | 状态 | 主要依据 |
|---|---|---|---|
| q1 | 三 SKU 规格差异 | ✅ | §3.1 规格表，官方三页交叉验证 |
| q2 | 性能差异来源 | ✅ | §6.1–6.2 功耗扫描，固件 V/F 差异 |
| q3 | 96GB 能装什么 | ✅ | §4.1–4.2 容量表与实测吞吐 |
| q4 | vs RTX 5090 | ✅ | §5 三套独立口径（AI/综合/渲染） |
| q5 | 专业图形定位 | ✅ | §7 三渲染器对比 + 编码器/ISV |
| q6 | 600W 是否值得 | ✅ | §6.3–6.4 能效曲线与推理实测 |
| q7 | 价格变化 | ✅ | §12.1 价格时间线至 2026-10-27 |
| q8 | 软件生态限制 | ✅ | §10 SM120 分裂与具体坑 |
| q9 | vs H100/L40S/Ada 边界 | ✅ | §8 训练交叉点 + §9.1 全象限对比 + §4.6 MLPerf 封闭分区 |
| q10 | MIG / vGPU 虚拟化 | ✅ | §11.1 官方 SPECviewperf 与共享吞吐数据 |
| q11 | 机密计算性能代价 | ✅ | §11.2 厂商 1-8% 与学术 13-27% 并列，含回收手段 |
| q12 | 长期运行是否可靠？ | ✅ | §10.5 社区故障报告与运维建议 |
| q13 | 部署新架构模型的软件风险？ | ✅ | §10.2 TensorRT-LLM sm120 实证案例 |
| q14 | 大规模自持的 TCO 如何？ | ✅ | §12.2 SemiAnalysis 持有型 TCO 口径 |
| q15 | 中国特供 6000D 的规格与定位？ | ✅ | §3.3 完整削减规格与实测 |
| q16 | 视频编码能力有多强？ | ✅ | §7.4 8K 4:2:2 的 122fps 实测 |
| q17 | MLPerf 官方成绩如何？ | ✅ | §4.6 封闭分区数据 |
| q18 | 长期高负载有哪些硬件风险？ | ✅ | §10.5 退化 + §10.6 供电熔毁 |
| q19 | 产品生命周期与停产风险？ | ✅ | §12.5 RTX 5090 停产传闻 |
| q20 | 驱动与云上可用性？ | ✅ | §9.3 驱动下限 + §9.2 云实例建议 |
| q21 | 除 vLLM/SGLang 外的软件路径？ | ✅ | §4.7 llama.cpp/GGUF 与双卡部署约束 |
| q22 | 多卡是否存在隐蔽故障模式？ | ✅ | §4.3.1 P2P 静默损坏 + §10.7 整芯片复位 |
| q23 | SPECviewperf 15 分项成绩？ | ✅ | §7.1.1 官方 11 项分项 + 代际/竞品对比 |
| q24 | 多卡部署的正确调优方式？ | ✅ | §4.3.2–4.3.4 链路抖动、NCCL、接地 |
| q25 | 长上下文的关键使能技术？ | ✅ | §4.5.2 DCP 与量化版本选择 |
| q26 | RTX 6000D 究竟被砍了什么？ | ✅ | §3.3.1 Tensor Core 实测保留率 |
| q27 | CAE/CFD 仿真表现如何？ | ✅ | §7.6 Fluent 实测与 NVLink 反例 |
| q28 | LoRA 微调是否值得？ | ✅ | §8.8 DDP 扩展与四卡反超 |

**完成度：28/28 已答**（q9 由 partial 升级为 answered——训练侧交叉点、FP64/BF16/带宽三维对比、优化器卸载约束已补齐，足以给出可执行边界）。

## 附录 B：本报告的可复现性

本报告全部数字可追溯到 `evidence.csv` 中的 **387 条**原文片段。校验命令：

```bash
python scripts/validate_research.py research/rtx-pro-6000
```

校验项：来源 ID 唯一性、证据引用的来源存在、主张引用的证据闭合（含反证）、日期可解析、prediction 类主张必须有 derivation、报告中的 `[src-<id>]` / `[c-<id>]` / `[e-<id>]` 引用均能解析。

当前校验结果：`sources=63, evidence=387, claims=253, claims_high=177, claims_disputed=1`

**阅读约定**：
- `[c-<id>]` = 主张 ID，指向 `claims.csv` 中一行
- `[e-<id>]` = 证据 ID，指向 `evidence.csv` 中的原文片段
- `[src-<id>]` = 来源 ID，指向 `sources.csv` 中的 URL 与抓取时间
### 稳定性、P2P 与 llama.cpp 生态（第二轮补充）

43. [NVIDIA 开发者论坛：整芯片复位故障（完整日志与排除项）](https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-gb202-recurring-full-chip-reset-during-sustained-llm-inference-requires-psu-power-cycle-to-recover/365739)（2026-04-06） — [src-forum-fullchip]
44. [NVIDIA 开发者论坛：Max-Q 版本 MMU 错误报告](https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-max-q-hardware-problem-multitude-of-mmu-errors-in-dmesg/381310)（2026-08-26） — [src-forum-mmufault]
45. [Unsloth PR #10646：P2P 必须按 NVLink 拓扑而非产品名开启](https://github.com/unslothai/unsloth/pull/10646)（2026-09） — [src-unsloth-p2p]
46. [llama.cpp PR #29353：GDN chunked kernel（含 PRO 6000 prefill 实测）](https://github.com/ggml-org/llama.cpp/pull/29353)（2026-10-14） — [src-llamacpp-29353]
47. [NVIDIA Blog：IFA 2026 本地 AI 加速（llama.cpp/vLLM 最高 1.9x）](https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/)（2026-09-03） — [src-nvidia-ifa]
48. [Hugging Face：BTL-3 Compact 在 RTX PRO 6000 上的 llama-bench 原始数据](https://huggingface.co/badtheorylabs/BTL-3-Compact/raw/7c48bf621a46be433032106ca888f02711d2530b/evidence/rtx-pro-6000-speed-2026-07-19.md)（2026-07-19） — [src-btl-llamacpp]
49. [Tower2 双卡部署验证记录（切分失败与副本方案）](https://raw.githubusercontent.com/Osmantic/MMBT-Messy-Model-Bench-Tests/refs/heads/main/benchmarks/gemma4-31b-q4/GEMMA4_31B_Q4_VERIFIED_RESULTS.md)（2026-10） — [src-osmantic-tower2]

### SPEC 官方结果（第二轮补充）

50. [SPECviewperf 15 官方结果汇总（含 11 项分项与 FHD/4K）](https://www.spec.org/gwpg/gpc.data/viewperf15/)（更新 2026-04-30） — [src-spec-vp15]
51. [SPECviewperf 15 单条提交明细：ThinkStation P8 + RTX PRO 6000 @4K](https://www.spec.org/gwpg/gpc.data/viewperf15/lenovo/P8_9965WX_RTX_PRO_6000_4K/results.html)（2025-11-12） — [src-spec-vp15-p8]

### 多卡实战 wiki（第二轮补充）

52. [RTX PRO 6000 Blackwell LLM Wiki（16 卡 PCIe 实战）](https://github.com/local-inference-lab/rtx6kpro) — [src-rtx6kpro-wiki]
53. [跨用户基准汇总（MTP、上下文缩放、NCCL、P2P）](https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/benchmarks/results.md) — [src-rtx6kpro-bench]
54. [功耗扫描：Workstation vs Server vs Max-Q（双卡交叉验证）](https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/blackwell-power-limit-sweep.md) — [src-rtx6kpro-power]
55. [PCIe 拓扑与 GPU 互连](https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/topology.md) — [src-rtx6kpro-topo]
56. [常见问题排查（NCCL/CUDA/SM120/PCIe 稳定性）](https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/troubleshooting/common-issues.md) — [src-rtx6kpro-issues]
57. [Blackwell 瓦特-性能交互面板](https://shihanqu.github.io/Blackwell-Wattage-Performance/) — [src-wattage-dash]
58. [CSDN：RTX 6000D 与 RTX PRO 6000 同口径实测对比（中文）](https://fjiang.blog.csdn.net/article/details/162849417)（2026-07-14） — [src-cn-6000d]

### CAE / LoRA / 云成本（第三轮补充）

59. [Exxact + DRD：Ansys Fluent GPU 基准（41.3M 单元，含 NVLink 对照）](https://www.exxactcorp.com/blog/benchmarks/ansys-fluent-gpu-benchmark-with-drd-exxact) — [src-exxact-fluent]
60. [Ansys：哪款 Blackwell GPU 的 Fluent ROI 最佳](https://ansys.synopsys.com/fr-fr/blog/which-nvidia-blackwell-gpu-delivers-best-fluent-roi) — [src-ansys-roi]
61. [Design & Reuse：Synopsys 部署 RTX PRO Server 于仿真负载](https://www.design-reuse.com/news/202529289-synopsys-deploys-ai-optimized-nvidia-rtx-pro-servers-for-advanced-simulation-workloads) — [src-designreuse-synopsys]
62. [Exxact：RTX PRO Blackwell LoRA 微调基准](https://www.exxactcorp.com/blog/benchmark/lora-fine-tuning-benchmark-on-nvidia-gpus) — [src-exxact-lora]
63. [Spheron：RTX PRO 6000 与 H100 微调及云租赁成本对照](https://www.spheron.network/blog/h100-vs-rtx-pro-6000-blackwell-fine-tuning-benchmark-2026/) — [src-spheron-h100]