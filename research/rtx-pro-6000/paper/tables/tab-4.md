| claim_id | claim_type | sku | 陈述摘要 |
|---|---|---|---|
| c-1m-feasible | measurement | unspecified | 百万 token上下文在 RTX PRO 6000 上已可端到端跑通：DeepSeek V4 Flash 在 llama.cpp 上成功生成了第 1,048,573 个 token（满 1,048,576 上下文）。 |
| c-gn-70b-capacity-domain | measurement | unspecified | LM Studio 的 Llama 3.3 70B Q4_K_S 测试中 PRO 6000 比 5090 提升 928%、比 4090 提升 1141%，而这个数量级差距的来源不是算力而是显存容量：到某个点其它卡显存耗尽，工作站卡在最大的 Llama 模型里连一半显存都没用到。作者自己给出了这个解释。 |
| c-ix-paradox | derivation | unspecified | 这里有一个必须说清的**悖论**：RTX PRO 6000 的 **$/chip/hr 最低（0.68，是 GB300 的 29%）**，但**每百万 token 成本最高（$0.19–0.36，是 GB300 的 10–18 倍）**。原因是**低芯片成本无法弥补低并发**——**买得起不等于用得起**。 |
| c-ix-perdollar | measurement | unspecified | SemiAnalysis InferenceX 的每美元数据给出比本报告此前引用更完整的图景：Qwen 3.5 397B-A17B（8k/1k、FP4）下，**GB300 NVL72 的每百万 token 成本在 56/88/121 tok/s/user 三个交互性档位分别是 $0.02/$0.02/$0.02，而 RTX PRO 6000 是 $0.19/$0.25/$0.36**——GB300 的成本效率分别高出 **1047% / 1320% / 1597%**。 |
| c-llamacpp-decode-parity | measurement | unspecified | 在 llama.cpp 单流 decode 下，RTX PRO 6000 与 RTX 5090 接近持平——因为两者带宽同为 1792 GB/s，decode 受带宽限制。 |
| c-llamacpp-prefill | measurement | unspecified | llama.cpp 上 RTX PRO 6000 的 prefill 吞吐：Qwen3.5-35B-A3B-Q8_0 达 16,459 tok/s（2048 token 提示），Qwen3.8-27B-Q8_0 达 4,757 tok/s。 |
| c-omni3-vs-l40-median | derivation | unspecified | ⭐ RTX PRO 6000 相对 L40 Ada 的中位加速比为 1.09×、胜率 78%；p10 为 0.95、p90 为 1.28、最差 0.85×、最好 1.67×。⚠️ 即两者显存差 2.0 倍，而实际吞吐差中位仅 1.09 倍。 |
| c-slac-h100-vs-rtx | measurement | unspecified | ⭐ SLAC 的逐路径规格对比给出了一个比「谁更快」更实用的框架：FP32 上 RTX PRO 6000 约 125 对 H100 NVL 约 60 TFLOPS（2.1 倍）；但 FP64 上约 2.0 对约 30（H100 领先 15 倍）、带宽 1.79 对 3.9 TB/s（H100 领先 2.2 倍）；价格约 13k 对约 28k 美元（RTX 便宜 2.1 倍）。 |
| c-slac-power-favors-h100 | measurement | unspecified | ⚠️ 但机架密度下功耗倾向 H100：约 1.5 倍性能每瓦。即 RTX PRO 6000 在「每美元性能」上胜出，在「每瓦性能」上落后——两个指标指向不同的卡。 |
| c-sr-96gb-unique | measurement | unspecified | 96 GB 的不可替代性在 120B 模型上得到直接验证：RTX 5090 无法加载或执行 120B 模型、甚至常处理不了 70B，而 PRO 6000 能以 163.15 tok/s 完成 GPT-OSS 120B 的 500 词生成（首字 0.193 秒、总 9.543 秒）。这是容量带来的能力差异，不是速度差异。 |
| c-sr-blender-narrow | measurement | unspecified | 在 StorageReview 的受控并排测试中，PRO 6000 相对 RTX 5090 的 Blender 4.4 领先幅度只有 6.0%/4.5%/8.3%（三场景），平均约 6.3% —— 这是该评测全部项目中差距最小的一组，与 Open Data 众测显示的「两者几乎相同」方向一致。 |
| c-sr-int8-saturates | measurement | unspecified | INT8 量化推理上 PRO 6000 与 RTX 5090 基本持平（79,064 对 79,272，5090 略高 0.3%）。作者指出 INT8 负载对显存带宽与容量的依赖较低，因此这解释了为何该项目的差异远小于 FP16 项目。 |
| c-sr-renderer-split | derivation | unspecified | 同一批评测中，PRO 6000 在 Blender（+6.3%）、LuxMark（+1.7%~5.0%）、Geekbench（+2.5%）上领先 5090，却在 V-Ray（−21.7%）与 SDXL FP16（−2.6%）上落后。因此「PRO 6000 是否比 5090 快」这个问题在所有渲染器上都没有统一答案，必须逐项看。 |
| c-sr-token-vs-score | derivation | unspecified | Procyon 文本生成的 token 速率与总分给出了不同的图景：PRO 6000 相对 5090 的 token 速率优势仅 1.5%-5.9%，但总分优势达 8%-18%。说明该基准的总分包含首字延迟等其它分量，单看 token/s 会低估工作站卡的相对优势。 |
| c-sr-vray-loses | measurement | unspecified | V-Ray 6 上 RTX 5090 以 14,764 vpaths 领先 PRO 6000 的 12,128，领先幅度 21.7%。这独立复现了 Open Data 与 Drop & Render 里「消费级 5090 在渲染上不吃亏」的方向，并给出了更大的差距。 |
| c-the-bonsai-readme-has-no-pro-6000-data | measurement | unspecified | ⚠️⚠️⚠️ **这份 24,840 字节的 README 里，「96 GB」「RTX PRO」「5090」「4090」的计数全是 0**： Speed Benchmarks 段只有一句「**See community-benchmarks/ for results on different hardware**」； 故它对 PRO 6000 的性能**零贡献** |
| c-vgpu-l40s-56 | measurement | unspecified | NVIDIA 宣称 RTX PRO 6000 相对 L40S 最高 5.6 倍加速（Llama 3 70B），分项为 Siemens UFX 2.3x、Dassault Abaqus 2x、Autodesk Arnold 1.9x、Omniverse 3.5x。 |
