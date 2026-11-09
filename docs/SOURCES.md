# 来源清单：这个项目目前搜过哪些地方

> **本文件由脚本生成，不要手改。**
> 生成：`python scripts/source_inventory.py`　｜校验：`python scripts/source_inventory.py --check`
> 生成时间：2026-11-09　｜数据源：`research/*/sources.csv`（14 个归档）

## 0　先看结论

共 **853** 条来源记录，按 URL 去重后是 **771** 个不同的地址。

两者差 82 条，来自两种**性质不同**的重复，不能混说：

- **跨归档复用 53 组**：同一篇论文被两篇综述分别引用，本就该有两份记录（多出 68 条）。
- **归档内同名 2 组**：同一个页面地址被登记成多个 source（多出 14 条）。这是刻意的——一个仓库的 14 份文件是 14 个**独立**的证据来源，但共享同一个 URL。最宽的一处是 `rsi-inference-bench` 的 14 份文件指向同一地址。

故「唯一地址数」应读作**不同的信息出处**，不是「不同的页面」。按 `source_id` 数会虚高，按 URL 数会低估同一仓库内的独立文件——两个数都得看，见第 6 节。

按站点看，最集中的三处是 GitHub（283 条）、arXiv（270 条）、NVIDIA（28 条），合计占 75%。

按性质看，学术来源 274 条（36%）、社区 282 条、官方 82 条。

⚠️ **一个必须注意的口径**：`academic` 占比高，不代表每一篇都是文献综述。`rsi-inference-bench` 这类归档的锚点根本没有论文（仓库 README 写 `Paper: coming soon`），它的来源是 `official`——工程仓库原文。只看总表会以为全项目都以 arXiv 为检索面。**逐归档的分布见第 1 节**，那一节才能看出这个差别。

## 1　逐归档

| 归档 | 记录数 | 唯一地址 | 主要性质 |
|---|---|---|---|
| `agent-serving-bench` | 14 | 14 | 学术（论文 / 预印本） 14 |
| `cuda-kernel-gen` | 36 | 36 | 学术（论文 / 预印本） 33、独立第三方（媒体 / 独立评测） 1 |
| `cuda-kernel-rl` | 20 | 20 | 学术（论文 / 预印本） 20 |
| `kernel-agent` | 35 | 35 | 学术（论文 / 预印本） 35 |
| `multi-platform-publish` | 13 | 13 | 厂商（产品与营销材料） 8、官方（厂商或项目自己的文档） 3 |
| `pd-disagg` | 70 | 70 | 学术（论文 / 预印本） 46、官方（厂商或项目自己的文档） 24 |
| `pro6000se-dsv41` | 26 | 25 | 社区（论坛 / 个人实测） 15、官方（厂商或项目自己的文档） 8 |
| `rsi-inference` | 57 | 57 | 学术（论文 / 预印本） 57 |
| `rsi-inference-bench` | 22 | 9 ⚠️ | 官方（厂商或项目自己的文档） 14、学术（论文 / 预印本） 8 |
| `rsi-model-training` | 53 | 53 | 学术（论文 / 预印本） 53 |
| `rsi-quant` | 34 | 34 | 学术（论文 / 预印本） 34 |
| `rsi-serving` | 23 | 23 | 学术（论文 / 预印本） 23 |
| `rtx-pro-6000` | 447 | 447 | 社区（论坛 / 个人实测） 270、官方（厂商或项目自己的文档） 44 |
| `specpilot` | 3 | 3 | 官方（厂商或项目自己的文档） 2、学术（论文 / 预印本） 1 |
| **合计** | **853** | **771** | — |

⚠️ 带记号的行表示「记录数远多于唯一地址」——这些归档把一个仓库的多份文件登记成了多个 source，每一份都是独立的证据来源，但共用一个 URL。明细见第 6 节归档内同名那一类。

## 2　按来源性质（`source_type`）

| 性质 | 唯一地址 | 占比 | 含义 |
|---|---|---|---|
| `community` | 282 | 36.6% | 社区（论坛 / 个人实测） |
| `academic` | 274 | 35.5% | 学术（论文 / 预印本） |
| `official` | 82 | 10.6% | 官方（厂商或项目自己的文档） |
| `independent` | 44 | 5.7% | 独立第三方（媒体 / 独立评测） |
| `vendor` | 39 | 5.1% | 厂商（产品与营销材料） |
| `press` | 28 | 3.6% | 新闻稿 / 报道 |
| `vendor-adjacent` | 12 | 1.6% | 厂商周边（合作方 / 生态） |
| `review` | 9 | 1.2% | 评测媒体 |
| `retail` | 1 | 0.1% | 零售页面 |

枚举定义见 [data-model.md](./data-model.md)。未出现在表里的类型表示目前一条都没有。

## 3　按信任层级（`trust_tier`）

| 层级 | 唯一地址 | 含义 |
|---|---|---|
| primary（自行产生观测） | 720 | 自行测量/发布该事实的那一方 |
| secondary（转述他人） | 42 | 转述别人的观测 |
| tertiary（聚合，无原始观测） | 9 | 只做索引聚合 |

⚠️ `trust_tier` 与 `source_type` **正交**：厂商自己的产品文档是 `vendor` + `primary`（它确实最先产生那些参数）；媒体转述同一份参数是 `press` + `secondary`。把权威性当来源性质是最常见的误标，见 data-model.md 的说明。

## 4　按站点

| 站点 | 唯一地址 | 说明 |
|---|---|---|
| GitHub | 283 | 代码仓库与 README；raw / api / media 四类子域已归并 |
| arXiv | 270 | 预印本；有 arXiv id 即可复现 |
| NVIDIA | 28 | 厂商自有文档与博客 |
| NVIDIA 开发者论坛 | 23 | 实测帖；单条可信度低，需交叉核对 |
| Hugging Face | 22 | 模型卡与数据集卡 |
| vLLM | 9 | 推理引擎官方文档 |
| joshua8.ai | 7 |  |
| techpowerup.com | 6 |  |
| SGLang | 5 | 推理引擎官方文档 |
| blendercloudrender.com | 3 |  |
| storagereview.com | 3 |  |
| inferencex.semianalysis.com | 3 |  |
| SPEC | 3 | 标准基准组织的公开测试结果 |
| forum.level1techs.com | 3 |  |
| pub.hpc-technologies.co.jp | 3 |  |
| developers.weixin.qq.com | 2 |  |
| registry.npmjs.org | 2 |  |
| api-docs.deepseek.com | 2 |  |
| blenderartists.org | 2 |  |
| exxactcorp.com | 2 |  |
| elsa-jp.co.jp | 2 |  |
| hongping-zh.github.io | 2 |  |
| eet-china.com | 2 |  |
| opendata.blender.org | 2 |  |
| render.janction.jp | 2 |  |
| formulamod.net | 2 |  |
| c114.net.cn | 2 |  |
| tariff.gatewaylines.com | 2 |  |
| 本仓库（自建产物） | 1 |  |
| open.xiaohongshu.com | 1 |  |
| wechatsync.com | 1 |  |
| xueyuan.yixiaoer.cn | 1 |  |
| yimeizhushou.com | 1 |  |
| cloud.tencent.com.cn | 1 |  |
| nvidia.github.io | 1 |  |
| deepinfra.com | 1 |  |
| pytorch.org | 1 |  |
| artificialanalysis.ai | 1 |  |
| qovery.com | 1 |  |
| cloud.tencent.cn | 1 |  |
| nvidianews.nvidia.com | 1 |  |
| cgchannel.com | 1 |  |
| post.smzdm.com | 1 |  |
| news.pconline.com.cn | 1 |  |
| technolynx.com | 1 |  |
| blog.us.fixstars.com | 1 |  |
| ithome.com | 1 |  |
| diy.zol.com.cn | 1 |  |
| cisco.com | 1 |  |
| docs.coreweave.com | 1 |  |
| shihanqu.github.io | 1 |  |
| fjiang.blog.csdn.net | 1 |  |
| ansys.synopsys.com | 1 |  |
| design-reuse.com | 1 |  |
| spheron.network | 1 |  |
| nodemall.co.kr | 1 |  |
| gdep.co.jp | 1 |  |
| archvizdaily.com | 1 |  |
| joshuaodmark.com | 1 |  |
| magik.net | 1 |  |
| helixml.tech | 1 |  |
| akash.network | 1 |  |
| discuss.vllm.ai | 1 |  |
| jared-hpc.com | 1 |  |
| 216.146.218.45 | 1 |  |
| media.3ds.com | 1 |  |
| compareaihardware.com | 1 |  |
| ansys.com | 1 |  |
| notanarchitect.io | 1 |  |
| cimdata.com | 1 |  |
| learn.microsoft.com | 1 |  |
| proxpc.com | 1 |  |
| epubs.stfc.ac.uk | 1 |  |
| ete.ua | 1 |  |
| blog.kubesimplify.com | 1 |  |
| haoailab.com | 1 |  |
| renrendaima.com | 1 |  |
| projects.blender.org | 1 |  |
| render.otoy.com | 1 |  |
| devtest.gamersnexus.net | 1 |  |
| inferencehub.org | 1 |  |
| gpuperhour.com | 1 |  |
| igorslab.de | 1 |  |
| sabareesh.com | 1 |  |
| hyperpc.ae | 1 |  |
| aquanode.io | 1 |  |
| semiconductorpackagingnews.com | 1 |  |
| confluence.slac.stanford.edu | 1 |  |
| hivenet.com | 1 |  |
| pny.com | 1 |  |
| wap.seccw.com | 1 |  |
| mlcommons.org | 1 |  |
| rocm.docs.amd.com | 1 |  |
| benchlife.info | 1 |  |
| m.mydrivers.com | 1 |  |
| ai.zol.com.cn | 1 |  |
| kitguru.net | 1 |  |
| iconnect007.com | 1 |  |
| gigazine.net | 1 |  |
| uz.kursiv.media | 1 |  |
| vast.ai | 1 |  |
| stargazerx0.github.io | 1 |  |

## 5　按发布年份

| 年份 | 唯一地址 |
|---|---|
| 2022 | 1 |
| 2023 | 6 |
| 2024 | 21 |
| 2025 | 99 |
| 2026 | 396 |
| （未标日期） | 248 |

「未标日期」多是产品文档与论坛帖——它们没有发布日，只有抓取日（`fetched_at`）。这一类不能拿来做时间线分析。

## 6　重复登记与冲突

**同一地址被重复登记：55 组**（多出 82 条记录），其中跨归档 53 组、归档内同名 2 组。

跨归档的那一类是**正常的**：一篇论文被两篇综述同时引用，本就该有两份记录。不正常的是同一地址在不同归档里被标了不同的 `source_type` 或 `trust_tier`——那样同一条证据的强度就取决于「你从哪个 id 数上去」。

**当前 0 组类型/层级冲突**（55 组重复地址的标注全部一致）。这一行是查过之后写的，不是省略。

### 6.1　跨归档复用（同一篇被多篇引用）

被两个以上归档同时引用的（说明它是这一族的地基）：

| 地址 | 归档数 | 归档 |
|---|---|---|
| https://arxiv.org/abs/2502.10517 | 5 | agent-serving-bench, cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference |
| https://arxiv.org/abs/2602.24286 | 4 | cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference |
| https://arxiv.org/abs/2606.26453 | 4 | cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference |
| https://arxiv.org/abs/2607.16241 | 4 | agent-serving-bench, cuda-kernel-gen, cuda-kernel-rl, rsi-inference |
| https://arxiv.org/abs/2609.18123 | 4 | agent-serving-bench, cuda-kernel-gen, rsi-inference, rsi-serving |
| https://arxiv.org/abs/2507.11948 | 3 | cuda-kernel-gen, cuda-kernel-rl, kernel-agent |
| https://arxiv.org/abs/2510.16996 | 3 | cuda-kernel-gen, kernel-agent, rsi-inference |
| https://arxiv.org/abs/2607.20468 | 3 | agent-serving-bench, rsi-inference, rsi-serving |
| https://arxiv.org/abs/2607.20908 | 3 | cuda-kernel-rl, kernel-agent, rsi-inference |
| https://arxiv.org/abs/2507.05687 | 2 | cuda-kernel-gen, cuda-kernel-rl |
| https://arxiv.org/abs/2507.14111 | 2 | cuda-kernel-gen, cuda-kernel-rl |
| https://arxiv.org/abs/2509.07506 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2510.17891 | 2 | cuda-kernel-gen, cuda-kernel-rl |
| https://arxiv.org/abs/2511.01884 | 2 | cuda-kernel-gen, kernel-agent |
| https://arxiv.org/abs/2511.06345 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2512.02551 | 2 | cuda-kernel-gen, cuda-kernel-rl |
| https://arxiv.org/abs/2601.06288 | 2 | rsi-inference, rsi-serving |
| https://arxiv.org/abs/2602.05885 | 2 | cuda-kernel-gen, cuda-kernel-rl |
| https://arxiv.org/abs/2602.13692 | 2 | rsi-inference, rsi-serving |
| https://arxiv.org/abs/2602.14293 | 2 | cuda-kernel-gen, rsi-inference |
| https://arxiv.org/abs/2603.12440 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2603.28342 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2604.01489 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2604.18616 | 2 | cuda-kernel-gen, rsi-inference |
| https://arxiv.org/abs/2604.26039 | 2 | rsi-inference, rsi-serving |
| https://arxiv.org/abs/2605.04956 | 2 | cuda-kernel-gen, kernel-agent |
| https://arxiv.org/abs/2605.06068 | 2 | agent-serving-bench, rsi-serving |
| https://arxiv.org/abs/2605.11581 | 2 | rsi-inference, rsi-serving |
| https://arxiv.org/abs/2605.21312 | 2 | pd-disagg, rsi-serving |
| https://arxiv.org/abs/2606.04847 | 2 | cuda-kernel-rl, kernel-agent |
| https://arxiv.org/abs/2606.17518 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2606.26758 | 2 | cuda-kernel-gen, kernel-agent |
| https://arxiv.org/abs/2606.30560 | 2 | agent-serving-bench, rsi-serving |
| https://arxiv.org/abs/2608.01804 | 2 | cuda-kernel-rl, kernel-agent |
| https://arxiv.org/abs/2608.25570 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2609.04523 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2609.23130 | 2 | rsi-inference, rsi-serving |
| https://arxiv.org/abs/2609.30059 | 2 | kernel-agent, rsi-inference |
| https://arxiv.org/abs/2610.04646 | 2 | agent-serving-bench, rsi-serving |
| https://arxiv.org/abs/2610.07792 | 2 | rsi-inference, rsi-serving |
| …… | | 另有 13 组，见 sources.csv |

### 6.2　归档内同名（同一页面登记成多个来源）

这些不是错误，但要知道「唯一地址数」为何低于「记录数」：

| 归档 | 该地址下的来源数 | 地址 |
|---|---|---|
| `rsi-inference-bench` | 14 | https://github.com/apple-aiml-research/ml-rsi-inference-bench |
| `pro6000se-dsv41` | 2 | https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md |

## 7　全量清单

按性质分组，组内按站点、再按标题排序。「归档」列写的是这条地址出现在哪些归档里——**一个地址只占一行**。

### 社区（论坛 / 个人实测）（`community`，282 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| **`ggml/src/ggml-cuda/btl3-avq-marker.h`（8,700 字节）**——**8 个 magic 常量 + 8 个 `i… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-avq-marker.h |
| **`ggml/src/ggml-cuda/ggml-cuda.cu`（235,681 字节，5,742 行）**中的 19 处 `btl3` 命中——*… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/ggml-cuda.cu |
| 8 卡 2 物理芯片 × 2 虚拟交换机 — 三种布线与崩溃触发的三条件 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/wrx90-cpayne-8gpu-2vs-per-chip.md |
| 8-GPU Group Comparison: Shared vs Separate CPU Root Complexes —— root complex… | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/wrx90-cpayne-8gpu-root-topology-comparison.md |
| [#11932][fix] Filter CUTLASS MoE GEMM tile configs by device shared memory on… | GitHub | 2026-04-02 | primary | rtx-pro-6000 | https://github.com/NVIDIA/TensorRT-LLM/pull/12704 |
| [Bug] CUDA caching allocator unable to satisfy 3-18 GiB contiguous allocation… | GitHub | 2026-05-04 | primary | rtx-pro-6000 | https://github.com/pytorch/pytorch/issues/182286 |
| [Bug] CUDA illegal memory access in flashinfer prefill replay during NGRAM sp… | GitHub | 2026-05-04 | primary | rtx-pro-6000 | https://github.com/sgl-project/sglang/issues/24361 |
| [Bug] NVFP4 MoE models crash on GB10 (SM121) during CUDA graph capture（issue … | GitHub | 2026-03-12 | primary | rtx-pro-6000 | https://github.com/flashinfer-ai/flashinfer/issues/2776 |
| [Bug] Qwen3-Next (Gated-DeltaNet) fails at warmup on consumer Blackwell sm120… | GitHub | 2026-06-25 | primary | rtx-pro-6000 | https://github.com/NVIDIA/TensorRT-LLM/issues/15634 |
| [Bug] TRTLLMGenFusedMoE + CUTLASS MoE both fail on SM120 with FP4 Qwen3-Next … | GitHub | 2026-03-05 | primary | rtx-pro-6000 | https://github.com/NVIDIA/TensorRT-LLM/issues/11932 |
| [Bug] WSL2 GPU passthrough has 16 GiB CUDA driver overhead on Blackwell sm_12… | GitHub | 2026-05-04 | primary | rtx-pro-6000 | https://github.com/microsoft/WSL/issues/40401 |
| [Bug]: DeepSeek-V4-Flash hangs after ~6 requests with cudagraph_mode=FULL_AND… | GitHub | 2026-04-27 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/40969 |
| [Bug]: FlashInfer attention backend causes CUDA illegal memory access on sm_1… | GitHub | 2026-08-28 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/54225 |
| [Bug]: Qwen3.6 hybrid Mamba models fail KV cache allocation on RTX PRO 6000 B… | GitHub | 2026-05-04 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/41619 |
| [Bug]: v0.28.0 — repeated illegal memory access / illegal instruction under p… | GitHub | 2026-09-20 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/57822 |
| [Bug]: Xiaomi MiMo v2.5 broken on SM12x（issue #41519，15 评论，2026-05-02 至 2026-… | GitHub | 2026-05-02 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/41519 |
| [Bug][DSV4][Blackwell SM12x] Indexer decode paged MQA logits broken when Deep… | GitHub | 2026-08-24 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/issues/53635 |
| [Bugfix] Fix CUDA illegal memory access in Marlin MoE c_tmp on SM 12.0a (re-f… | GitHub | 2026-09-01 | primary | rtx-pro-6000 | https://github.com/vllm-project/vllm/pull/43730 |
| [Issue]: NCCL hangs during AllReduce with P2P enabled on dual RTX Pro 6000's … | GitHub | 2026-01-26 | primary | rtx-pro-6000 | https://github.com/NVIDIA/nccl/issues/1999 |
| [SM120] Field report: DeepSeek-V4.1-Flash in production on 8x RTX PRO 6000 | GitHub | 2026-09-23 | primary | pro6000se-dsv41 | https://github.com/sgl-project/sglang/issues/40877 |
| [SM120] Field report: DeepSeek-V4.1-Flash on 8x RTX PRO 6000 | GitHub | 2026-09-13 | primary | pro6000se-dsv41 | https://github.com/vllm-project/vllm/issues/56700 |
| [Windows] RTX 5070 Ti (Blackwell sm_120) - CUDA compilation and runtime worka… | GitHub | 2026-05-05 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/issues/22696 |
| `.github/workflows/build-cuda-ubuntu.yml`（3,642 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.github/workflows/build-cuda-ubuntu.yml |
| `.github/workflows/build-cuda-windows.yml`（5,498 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.github/workflows/build-cuda-windows.yml |
| `.github/workflows/code-style.yml`（1,741 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.github/workflows/code-style.yml |
| `.github/workflows/release.yml`（57,190 字节，1,541 行）—— 发布流水线 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.github/workflows/release.yml |
| `artifacts/btl3-compact-gguf-dry-run.json`（910 字节）—— §10.134 说的那个「dry-run pro… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/artifacts/btl3-compact-gguf-dry-run.json |
| `artifacts/release/BTL-3-Compact-AVQ2.report.json`（1,058 字节）—— 发布产物的最终校验报告 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/artifacts/release/BTL-3-Compact-AVQ2.report.json |
| `btl3-avq.cu`（7,070 字节）——**AVQ2 解码器的 CUDA 主路径**， 三个 kernel：`transform_input` … | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-avq.cu |
| `btl3-avq.cuh`（156 字节）——只声明入口函数，无逻辑 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-avq.cuh |
| `btl3-int4.cu`（2,682 字节）——INT4 的 CUDA 内核，**它确实存在且可读** | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-int4.cu |
| `btl3-vocab.cu`（9,552 字节）——AVQ2 词表的 CUDA 内核， 含 FWHT、救助行（rescue）二分查找、以及一个 4 分量… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-vocab.cu |
| `community-benchmarks/ternary-bonsai/cuda-rtx-pro-6000-blackwell-linux.md`（1,… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/community-benchmarks/ternary-bonsai/cuda-rtx-pro-6000-blackwell-linux.md |
| `community-benchmarks/ternary-bonsai/README.md`（6,322 字节，90 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/community-benchmarks/ternary-bonsai/README.md |
| `docs/btl-3-compact-metal-runtime-2026-07-19.md`（2,601 字节）—— ⭐⭐⭐⭐⭐ 🔥 **它含一句足以… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/btl-3-compact-metal-runtime-2026-07-19.md |
| `docs/build.md` 的 「Non-Native Builds」（206-218）、「Override Compute Capability S… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md#L206-L336 |
| `docs/build.md` 的「Compilation」（189-206）与「Notes about GPU-accelerated backends… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md#L189-L206 |
| `docs/build.md`（master 原始文档，**46,343 字节 / 907 行**，2026-10 抓取；**`GGML_CUDA_MMQ… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md |
| `docs/patched-ollama-and-lmstudio.md`（10,347 字节）—— ⭐ **它是 §10.106 那场「stock en… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/patched-ollama-and-lmstudio.md |
| `ggml/src/ggml-cuda/CMakeLists.txt`（11,878 字节）—— ⭐⭐⭐⭐⭐ **它最终裁决了 §10.155 的矛盾**… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/CMakeLists.txt |
| `ggml/src/ggml-cuda/CMakeLists.txt`（master 分支原始源码，2026-10 抓取） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/CMakeLists.txt |
| `ggml/src/ggml-cuda/common.cuh`（60,827 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/common.cuh |
| `ggml/src/ggml-cuda/common.cuh`（master 原始源码，**65,408 字节**，2026-10 抓取） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/common.cuh |
| `ggml/src/ggml-cuda/mma.cuh`（63,456 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/mma.cuh |
| `ggml/src/ggml-cuda/mma.cuh`（master 原始源码，**69,917 字节**，2026-10 抓取；**`BLACKWEL… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mma.cuh |
| `ggml/src/ggml-cuda/mmf.cuh`（master 原始源码，**45,665 字节 / 926 行**，2026-10 抓取） + … | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmf.cuh |
| `ggml/src/ggml-cuda/mmq-config-blackwell.cuh`（master 原始源码，**3,550 字节**，2026-1… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmq-config-blackwell.cuh |
| `ggml/src/ggml-cuda/mmq-hopper-q1.cu`（26,385 字节，490 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/mmq-hopper-q1.cu |
| `ggml/src/ggml-cuda/mmq.cu` 的 `ggml_cuda_mmq_get_prec_env()` 与 `ggml_cuda_mmq… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmq.cu#L104-L127 |
| `ggml/src/ggml-cuda/mmq.cu`（master 原始源码，**22,671 字节**，2026-10 抓取；**`can_use_q… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cuda/mmq.cu |
| `ggml/src/ggml-cuda/mmq.cuh`（181,959 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/mmq.cuh |
| `ggml/src/ggml-cuda/template-instances/generate_cu_files.py`（4,115 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/template-instances/generate_cu_files.py |
| `ggml/src/ggml-cuda/template-instances/mmq-instance-q2_0.cu`（138 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/template-instances/mmq-instance-q2_0.cu |
| `gguf-py/gguf/gguf_writer.py`（60,100 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/gguf-py/gguf/gguf_writer.py |
| `native/llama.cpp/.github/workflows/` 下 52 个文件—— 🔥🔥🔥🔥🔥 **`build-cuda-ubuntu.y… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.github/workflows/ |
| `native/llama.cpp/CMakeLists.txt`（9,551 字节）—— 🔥🔥🔥🔥🔥 **`option(LLAMA_BUILD_TES… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/CMakeLists.txt |
| `native/llama.cpp/docs/btl3-avq-cuda-validation.md`（4,116 字节）—— 🔥🔥🔥🔥🔥 **它与 §1… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/docs/btl3-avq-cuda-validation.md |
| `native/llama.cpp/ggml/CMakeLists.txt`（21,778 字节）—— 🔥🔥🔥🔥🔥 **`option(GGML_CUDA… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/CMakeLists.txt |
| `native/llama.cpp/ggml/src/CMakeLists.txt`（20,026 字节）—— 🔥🔥🔥🔥🔥 **`ggml_add_bac… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/CMakeLists.txt |
| `native/llama.cpp/ggml/src/ggml-metal/ggml-metal-btl3.h`（6,989 字节）—— 🔥🔥🔥🔥🔥 **… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-metal/ggml-metal-btl3.h |
| `native/llama.cpp/ggml/src/ggml-metal/ggml-metal-btl3.metal`（13,359 字节）—— 🔥🔥🔥… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-metal/ggml-metal-btl3.metal |
| `native/llama.cpp/src/btl3-avq-contract.h`（2,627 字节）—— 🔥🔥🔥🔥🔥 **十个 magic 的唯一定义… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/btl3-avq-contract.h |
| `native/llama.cpp/src/btl3-avq.cpp`（11,368 字节）—— ⭐⭐⭐⭐⭐ **CPU 侧的参考实现 + 计算图构建，是… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/btl3-avq.cpp |
| `native/llama.cpp/src/btl3-vocab.cpp`（10,963 字节，293 行）—— 🔥🔥🔥🔥🔥 **行方向的分组数 `cod… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/btl3-vocab.cpp |
| `native/llama.cpp/tests/CMakeLists.txt`（17,891 字节）—— 🔥🔥🔥🔥🔥 **它给出五个 BTL-3 测试的注… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/CMakeLists.txt |
| `native/llama.cpp/tests/test-btl3-avq-cuda.cpp`（6,636 字节）—— 🔥🔥🔥🔥🔥 **这是真的 CUDA… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-avq-cuda.cpp |
| `native/llama.cpp/tests/test-btl3-avq.cpp`（14,672 字节）—— 🔥🔥🔥🔥🔥 **它是四类 magic 的唯… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-avq.cpp |
| `native/llama.cpp/tests/test-btl3-int4-cuda.cpp`（5,519 字节）—— ⭐⭐⭐⭐⭐ **它没有调用任何参… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-int4-cuda.cpp |
| `native/llama.cpp/tests/test-btl3-metal-vocab.cpp`（8,420 字节）—— 🔥🔥🔥🔥 **它是唯一一个真… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-metal-vocab.cpp |
| `native/llama.cpp/tests/test-btl3-metal.cpp`（15,289 字节，412 行）—— 🔥🔥🔥🔥🔥 **它不是纯测… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-metal.cpp |
| `native/llama.cpp/tests/test-btl3-model-load.cpp`（970 字节）—— 🔥🔥🔥🔥 **`model_par… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-model-load.cpp |
| `native/llama.cpp/tests/test-btl3-vocab-cuda.cpp`（7,338 字节）—— 🔥🔥🔥🔥🔥 **这是五个后端测… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-btl3-vocab-cuda.cpp |
| `papers/behavior-before-perplexity/ARTICLE-IMPLEMENTATION-APPENDIX.md` （7,918… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/ARTICLE-IMPLEMENTATION-APPENDIX.md |
| `papers/behavior-before-perplexity/ARTICLE.md`（19,240 字节）—— 长文工程记录，按时间顺序写，含失败… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/ARTICLE.md |
| `papers/behavior-before-perplexity/CLAIMS.md`（5,252 字节）—— 「**a claim ledger**… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/CLAIMS.md |
| `papers/behavior-before-perplexity/PAPER.tex`（23,347 字节，338 行）—— 「**the canon… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/PAPER.tex |
| `papers/behavior-before-perplexity/README.md`（2,168 字节）—— 论文目录的入口，含「贡献边界」一节 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/README.md |
| `Prism` benchmarks/layer_bench.py（13,277 字节，349 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/benchmarks/layer_bench.py |
| `Prism` benchmarks/tasks.py（13,918 字节，370 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/benchmarks/tasks.py |
| `Prism` pyproject.toml（620 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/pyproject.toml |
| `Prism` README.md（7,224 字节，162 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/README.md |
| `Prism` src/prism/agent.py（8,171 字节，226 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/agent.py |
| `Prism` src/prism/checkers.py（4,377 字节，107 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/checkers.py |
| `Prism` src/prism/context.py（7,496 字节，235 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/context.py |
| `Prism` src/prism/domains.py（5,529 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/domains.py |
| `Prism` src/prism/execution.py（8,788 字节，216 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/execution.py |
| `Prism` src/prism/llm.py（9,832 字节，243 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/llm.py |
| `Prism` src/prism/packer.py（17,883 字节，509 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/packer.py |
| `Prism` src/prism/planner.py（8,998 字节，238 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/planner.py |
| `Prism` src/prism/render.py（7,095 字节，194 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/render.py |
| `Prism` src/prism/tokens.py（896 字节，28 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/tokens.py |
| `Prism` src/prism/tools.py（13,612 字节，369 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/tools.py |
| `Prism` src/prism/trace.py（6,189 字节，154 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/trace.py |
| `Prism` src/prism/verifier.py（10,896 字节，270 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/verifier.py |
| `Prism` src/prism/verify.py（4,070 字节，120 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/Prism/main/src/prism/verify.py |
| `tools/btl3_gguf/signs.py`（1,804 字节）—— 🔥 **它是 §10.145 那个「种子符号」的实现，而它把 Torch 整… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/btl3_gguf/signs.py |
| Abnormally low FPS on dual RTX PRO 6000 Blackwell workstation across Isaac Si… | GitHub | 2026-04-11 | primary | rtx-pro-6000 | https://api.github.com/repos/isaac-sim/IsaacSim/issues/578 |
| ASRock WRX90 WS EVO + 3x Microchip root switch hierarchy - nvidia-smi NODE la… | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/wrx90-cpayne-microchip-switches.md |
| ASRock WRX90 WS EVO — 16 卡 4 交换机：三种布线变体，以及崩溃曾经发生过 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/wrx90-cpayne-16gpu-4switch.md |
| ASRock WRX90 WS EVO — 2 交换机扁平拓扑：跨交换机被一条上行锁死，以及「根交换机」的价值 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/wrx90-cpayne-2switch-flat.md |
| ASRockRack GENOAD24QM32 + EPYC 9575F — 16 卡 4 交换机：崩溃无法复现 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/asrockrack-turin-cpayne-16gpu.md |
| ASUS ESC8000A-E13P with Broadcom PEX890xx Switches — P2P 拓扑与一个硬件级仲裁 bug | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/asus-esc8000a-e13p-broadcom-switches.md |
| ASUS ESC8000A-E13P — PEX890xx Bug Report（提交给厂商的正式升级报告） | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/troubleshooting/asus-esc8000a-e13p-pex890xx-bug-report.md |
| Awesome LLM-Driven Kernel Generation | GitHub | 2026-01-22 | secondary | cuda-kernel-gen | https://github.com/flagos-ai/awesome-LLM-driven-kernel-generation |
| B12X 稠密 FP8 GEMM 对 DeepGEMM - DSV4-Flash 预填差距的完整分析（含 NCU 级归因） | GitHub | 2026-07-02 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/b12x-dense-fp8-gemm-vs-deepgemm.md |
| Benchmark Results -- RTX 6000 Pro Blackwell | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/benchmarks/results.md |
| Bonsai-demo `community-benchmarks/README.md`（12,958 字节，130 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/community-benchmarks/README.md |
| BTL-3 `AGENTS.md`（1,592 字节，42 行）—— 产品集成仓库的契约 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/AGENTS.md |
| BTL-3 `artifacts/conformance/btl-3-compact-layer13.report.json`（833 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/artifacts/conformance/btl-3-compact-layer13.report.json |
| BTL-3 `artifacts/conformance/btl-3-compact-layer47.report.json`（823 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/artifacts/conformance/btl-3-compact-layer47.report.json |
| BTL-3 `docs/btl-3-compact-gguf-exporter.md`（2,464 字节，69 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/btl-3-compact-gguf-exporter.md |
| BTL-3 `docs/compact-release-readme.md`（3,526 字节，111 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/compact-release-readme.md |
| BTL-3 `docs/launch-btl3-compact.md`（6,108 字节，173 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/launch-btl3-compact.md |
| BTL-3 `docs/launch-btl3-cuda.md`（5,814 字节，161 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/launch-btl3-cuda.md |
| BTL-3 `docs/rtx-pro-6000-speed-2026-07-19.md`（1,957 字节，58 行） | GitHub | 2026-07-19 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/docs/rtx-pro-6000-speed-2026-07-19.md |
| BTL-3 `ggml/src/ggml-cuda/btl3-int4.cuh`（164 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-int4.cuh |
| BTL-3 `ggml/src/ggml-cuda/btl3-vocab.cuh`（275 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml-cuda/btl3-vocab.cuh |
| BTL-3 `integrations/lmstudio/btl3-native/manifest.json`（113 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/manifest.json |
| BTL-3 `integrations/lmstudio/btl3-native/package.json`（320 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/package.json |
| BTL-3 `integrations/lmstudio/btl3-native/run-local`（255 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/run-local |
| BTL-3 `integrations/ollama/Modelfile`（171 字节，5 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/ollama/Modelfile |
| BTL-3 `launch/btl3-cuda-server.ps1`（3,395 字节，85 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/launch/btl3-cuda-server.ps1 |
| BTL-3 `launch/btl3-cuda-server`（3,658 字节，109 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/launch/btl3-cuda-server |
| BTL-3 `launch/btl3-ollama-bridge`（1,005 字节，30 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/launch/btl3-ollama-bridge |
| BTL-3 `launch/btl3-server`（2,505 字节，86 行，macOS arm64 专用） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/launch/btl3-server |
| BTL-3 `LICENSE`（1,072 字节，22 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/LICENSE |
| BTL-3 `native/llama.cpp/.gitignore`（1,864 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/.gitignore |
| BTL-3 `native/llama.cpp/common/arg.cpp`（192,432 字节，4,185 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/common/arg.cpp |
| BTL-3 `native/llama.cpp/common/dspark-markov.cu`（11,706 字节，303 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/common/dspark-markov.cu |
| BTL-3 `native/llama.cpp/common/dspark-markov.h`（2,885 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/common/dspark-markov.h |
| BTL-3 `native/llama.cpp/common/speculative.cpp`（97,104 字节，2,442 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/common/speculative.cpp |
| BTL-3 `native/llama.cpp/common/speculative.h`（4,503 字节，103 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/common/speculative.h |
| BTL-3 `native/llama.cpp/conversion/dspark.py`（8,010 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/conversion/dspark.py |
| BTL-3 `native/llama.cpp/docs/dspark-scope.md`（5,956 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/docs/dspark-scope.md |
| BTL-3 `native/llama.cpp/docs/speculative.md`（16,708 字节，331 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/docs/speculative.md |
| BTL-3 `native/llama.cpp/src/llama-context.cpp`（162,633 字节，4,475 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-context.cpp |
| BTL-3 `native/llama.cpp/src/llama-ext.h`（10,151 字节，211 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-ext.h |
| BTL-3 `native/llama.cpp/src/llama-graph.cpp`（114,732 字节，3,259 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-graph.cpp |
| BTL-3 `native/llama.cpp/src/llama-graph.h`（44,394 字节，1,235 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-graph.h |
| BTL-3 `native/llama.cpp/src/llama-model-loader.cpp`（75,536 字节，1,814 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-model-loader.cpp |
| BTL-3 `native/llama.cpp/src/llama-model.cpp`（126,236 字节，2,792 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/llama-model.cpp |
| BTL-3 `native/llama.cpp/src/models/dspark.cpp`（22,582 字节，409 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/models/dspark.cpp |
| BTL-3 `native/llama.cpp/tests/test-dspark-forward.cpp`（16,148 字节，381 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-dspark-forward.cpp |
| BTL-3 `native/llama.cpp/tests/test-dspark-loop.cpp`（12,212 字节，283 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-dspark-loop.cpp |
| BTL-3 `native/llama.cpp/tests/test-dspark-real-eval.cpp`（31,867 字节，602 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/tests/test-dspark-real-eval.cpp |
| BTL-3 `packaging/cuda/build-linux.sh`（1,289 字节，52 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/packaging/cuda/build-linux.sh |
| BTL-3 `packaging/cuda/build-windows.ps1`（2,227 字节，55 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/packaging/cuda/build-windows.ps1 |
| BTL-3 `packaging/cuda/Dockerfile`（1,847 字节，48 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/packaging/cuda/Dockerfile |
| BTL-3 `papers/behavior-before-perplexity/references.bib`（2,995 字节，84 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/references.bib |
| BTL-3 `papers/behavior-before-perplexity/RESEARCH_MANIFEST.json`（2,118 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/RESEARCH_MANIFEST.json |
| BTL-3 `papers/behavior-before-perplexity/SHA256SUMS`（1,298 字节，14 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/papers/behavior-before-perplexity/SHA256SUMS |
| BTL-3 `pytest.ini`（56 字节，6 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/pytest.ini |
| BTL-3 `src/btl3-avq.h`（1,582 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/src/btl3-avq.h |
| BTL-3 `tests/test_btl3_gguf_signs.py`（737 字节，27 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_btl3_gguf_signs.py |
| BTL-3 `tests/test_btl3_qwen35.py`（630 字节，26 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_btl3_qwen35.py |
| BTL-3 `tests/test_btl3_safetensor_view.py`（1,189 字节，38 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_btl3_safetensor_view.py |
| BTL-3 `tests/test_consumer_installer.py`（2,786 字节，82 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_consumer_installer.py |
| BTL-3 `tests/test_cuda_packaging.py`（6,289 字节，183 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_cuda_packaging.py |
| BTL-3 `tests/test_launch_release.py`（3,680 字节，110 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_launch_release.py |
| BTL-3 `tests/test_lmstudio_package.py`（2,768 字节，64 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_lmstudio_package.py |
| BTL-3 `tests/test_ollama_bridge.py`（9,337 字节，253 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_ollama_bridge.py |
| BTL-3 `tests/test_patched_ollama_package.py`（7,536 字节，198 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tests/test_patched_ollama_package.py |
| BTL-3 `THIRD_PARTY_NOTICES.md`（684 字节，21 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/THIRD_PARTY_NOTICES.md |
| BTL-3 `tools/__init__.py`（55 字节）与 `tools/btl3_gguf/__init__.py`（41 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/__init__.py |
| BTL-3 `tools/btl3_gguf/exporter.py`（18,357 字节，495 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/btl3_gguf/exporter.py |
| BTL-3 `tools/btl3_gguf/metadata.py`（4,183 字节，100 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/btl3_gguf/metadata.py |
| BTL-3 `tools/btl3_gguf/qwen35.py`（3,459 字节，99 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/btl3_gguf/qwen35.py |
| BTL-3 `tools/btl3_gguf/safetensor_view.py`（2,902 字节，91 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/btl3_gguf/safetensor_view.py |
| BTL-3 `tools/build_cuda_bundle.py`（6,797 字节，193 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/build_cuda_bundle.py |
| BTL-3 `tools/build_launch_release.py`（9,921 字节，288 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/build_launch_release.py |
| BTL-3 `tools/build_macos_arm64_bundle.py`（6,597 字节，190 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/build_macos_arm64_bundle.py |
| BTL-3 `tools/build_patched_ollama.py`（9,541 字节，271 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/build_patched_ollama.py |
| BTL-3 `tools/export_btl3_compact_gguf.py`（320 字节，17 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/export_btl3_compact_gguf.py |
| BTL-3 `tools/install_consumer_bundle.py`（5,065 字节，149 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/install_consumer_bundle.py |
| BTL-3 `tools/modal_consumer_gpu_bench.py`（3,203 字节，125 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/modal_consumer_gpu_bench.py |
| BTL-3 `tools/ollama_bridge.py`（18,873 字节，501 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/ollama_bridge.py |
| BTL-3 `tools/probe_windows_runner.ps1`（1,041 字节，39 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/probe_windows_runner.ps1 |
| BTL-3 `tools/validate_lmstudio_package.py`（5,299 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/tools/validate_lmstudio_package.py |
| BTL-3 LM Studio 插件 `model.yaml`（410 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/model.yaml |
| BTL-3 LM Studio 插件 `src/generator.ts`（7,285 字节，239 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/src/generator.ts |
| BTL-3 LM Studio 插件 `src/nativeRunner.ts`（5,943 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/integrations/lmstudio/btl3-native/src/nativeRunner.ts |
| BTL-3 内置 `ggml/src/ggml.c`（251,221 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/BTL-3/main/native/llama.cpp/ggml/src/ggml.c |
| btl-kernels `btl_kernels/manifest.py`（1,688 字节）与 `btl_kernels/__init__.py`（99… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-kernels/main/btl_kernels/manifest.py |
| btl-kernels `README.md`（1,038 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-kernels/main/README.md |
| btl-lab `AGENTS.md`（1,980 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/AGENTS.md |
| btl-lab `backends.json`（4,456 字节）—— 十条 lane 的状态矩阵 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/backends.json |
| btl-lab `btl_lab/bootstrap.py`（2,288 字节，46 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/bootstrap.py |
| btl-lab `btl_lab/checks.py`（2,290 字节，52 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/checks.py |
| btl-lab `btl_lab/cli.py`（11,130 字节，244 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/cli.py |
| btl-lab `btl_lab/research.py`（24,416 字节，437 行）—— 该仓库最大的文件 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/research.py |
| btl-lab `btl_lab/resources/backends.json`（805 字节）—— 同仓库的第二份 lane 表 | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/resources/backends.json |
| btl-lab `btl_lab/runtime_probe.py`（1,077 字节）与 `btl_lab/doctor.py`（4,612 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/runtime_probe.py |
| btl-lab `btl_lab/store.py`（6,048 字节，132 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/store.py |
| btl-lab `EXPERIMENT_TEMPLATE.md`（1,834 字节，33 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/EXPERIMENT_TEMPLATE.md |
| btl-lab `FOUNDATION_REVIEW_2026-09-09.md`（10,838 字节，79 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/FOUNDATION_REVIEW_2026-09-09.md |
| btl-lab `WORKFLOWS.md`（8,274 字节，85 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/WORKFLOWS.md |
| btl-measure `btl_measure/core.py`（7,198 字节，145 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-measure/main/btl_measure/core.py |
| btl-measure `README.md`（2,765 字节） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-measure/main/README.md |
| Collapse Report：PCIe 交换机拓扑下 RTX PRO 6000 跨交换机 P2P 写带宽塌陷 75–93% 的复现与方法 | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/collapse-report.md |
| Community daily summary 2026-10-24 (contains a 4x Server Edition measurement) | GitHub | 2026-10-25 | primary | pro6000se-dsv41 | https://github.com/local-inference-lab/rtx6kpro/blob/master/daily-summaries/2026-10/2026-10-25.md |
| Consolidated benchmark results (NCCL / power / cross-model) | GitHub | 2026-11-01 | primary | pro6000se-dsv41, rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/results.md |
| CUDA compilation fails on Blackwell (sm_120) with MXFP4: "Instruction mma wit… | GitHub | 2026-02-16 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/issues/19662 |
| DeepSeek-V4.1-Flash community R38 deployment archive | GitHub | 2026-10-05 | primary | pro6000se-dsv41 | https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash-community-r38.md |
| DeepSeek-V4.1-Flash serving profile on RTX PRO 6000 | GitHub | 2026-10-20 | primary | pro6000se-dsv41 | https://github.com/local-inference-lab/rtx6kpro/blob/master/models/deepseek-v4.1-flash.md |
| Docker 镜像与容器部署 - 镜像清单、启动参数、五个真实故障与 Docker vs Venv 实测 | GitHub | 2026-07-05 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/docker-images.md |
| DSpark: ours vs upstream vLLM — consolidation study | GitHub | 2026-07-03 | primary | pro6000se-dsv41, rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/dspark-upstream-consolidation.md |
| feat: SM120 (Blackwell Desktop) support for GLM-5.1 inference (PR #26928) | GitHub | 2026-06-01 | primary | rtx-pro-6000 | https://github.com/sgl-project/sglang/pull/26928 |
| Fix int32 offset overflow in SM120 page-split kernel | GitHub | 2026-08-07 | primary | rtx-pro-6000 | https://github.com/sgl-project/sglang/pull/34027 |
| fix(attention): add SM120 block size configuration for extend attention | GitHub | 2026-01-29 | primary | rtx-pro-6000 | https://github.com/sgl-project/sglang/pull/17908 |
| Gemma 4 31B QAT Q4_0 on Tower2: verified results | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Osmantic/MMBT-Messy-Model-Bench-Tests/refs/heads/main/benchmarks/gemma4-31b-q4/GEMMA4_31B_Q4_VERIFIED_RESULTS.md |
| ggml-cuda: fix blackwell native builds（PR #18361，26 评论，**2025-12-25 提出并当日合并**… | GitHub | 2025-12-25 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/pull/18361 |
| GitHub REST `git/trees/main?recursive=1`，返回 3,439 条目，`truncated=false` | GitHub | — | primary | rtx-pro-6000 | https://api.github.com/repos/Badtheorylabs/BTL-3/git/trees/main?recursive=1 |
| gpt-oss guide — benchmarks on RTX PRO 6000 Blackwell (discussion #15396) | GitHub | 2025-08-18 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/discussions/15396 |
| GPU Configurations & Rig Builds (RTX PRO 6000) | GitHub | 2026-10-01 | primary | pro6000se-dsv41, rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/gpu-configs.md |
| Inference Throughput: Qwen3.5-397B-A17B Quantizations | GitHub | 2026-03-14 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/inference-throughput/README.md |
| Intermittent GPU Bus Drops on Multi-PSU Open-Air Frames | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/troubleshooting/gpu-bus-drops-multi-psu-grounding.md |
| md RAID5 的 IO 调优现场记录（捷克语）- 与同仓库另一篇在三个关键参数上直接冲突 | GitHub | 2026-04-01 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/io-tuning.md |
| Misc. bug: Performance regression: CUDA sparse flash attention decode 1.6x sl… | GitHub | 2026-09-22 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/issues/29281 |
| NCCL Tuning Guide — 一个把 AMD 带宽硬编码为 16 GB/s 的上游缺陷，及其修复路径 | GitHub | 2026-04-20 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/nccl-tuning.md |
| NVFP4 量化 - 格式、检查点差异、性能代价，与一组静默损坏型内核缺陷 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/nvfp4-quantization.md |
| NVMe RAID 与 Docker I/O 优化 - 容器生命周期卡死 2-5 分钟的根因与 50-100x 修复 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/nvme-raid-io-optimization.md |
| PCIe Bandwidth & P2P Performance：RTX PRO 6000 Blackwell 系统的 P2P 带宽/延迟/NCCL Al… | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/main/hardware/pcie-bandwidth.md |
| PCIe Link Speed Flapping — 如何锁 Gen5 而不把一张卡锁死在 Gen2 | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/troubleshooting/pcie-link-speed-flapping-cpayne.md |
| PCIe Oneshot AllReduce — 一个只在 ≤4 卡有效、8 卡反而更慢的自定义通信内核 | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/pcie-oneshot-allreduce.md |
| PCIe Topology & GPU Interconnect | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/topology.md |
| PR #23705 `ci : reduce (disable SYCL and CANN builds/releases)`（2026-05-26 合并） | GitHub | 2026-05-26 | primary | rtx-pro-6000 | https://api.github.com/repos/ggml-org/llama.cpp/pulls/23705 |
| RTX PRO 6000 Blackwell LLM Wiki (repo index) | GitHub | 2026-10-20 | primary | pro6000se-dsv41, rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro |
| RTX PRO 6000 Blackwell — Power-Limit Sweep: Workstation vs Server vs Max-Q | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/hardware/blackwell-power-limit-sweep.md |
| RTX PRO 6000 Blackwell — Power-Limit Sweep: Workstation vs Server vs Max-Q（gp… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/dd2fba9126ae4a3435a591eef18162a0086bebe3/hardware/blackwell-power-limit-sweep.md |
| RTX6kPRO daily summaries（2026-02 至 2026-10 全 246 篇） | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/tree/master/daily-summaries |
| Self-Hosted Streaming TTS & Voice Cloning on RTX 5090 / RTX PRO 6000 — Fish A… | GitHub | 2026-08-01 | primary | rtx-pro-6000 | https://github.com/Genesis1231/fish-s2-rtx |
| Single RTX PRO 6000 Workstation Edition on Windows 11 (IST-DAS 2.25 bpw) | GitHub | 2026-10-31 | primary | pro6000se-dsv41 | https://github.com/Niko1221/Strata/issues/4816 |
| SM120 vs. SM100 Architecture | GitHub | 2026-10-01 | primary | pro6000se-dsv41, rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/hardware/sm120-vs-sm100-architecture.md |
| Troubleshooting -- Common Issues on RTX 6000 Pro Blackwell | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/troubleshooting/common-issues.md |
| vLLM pynccl (ctypes-loaded NCCL) hangs at ncclCommInitRank under libvgpu.so o… | GitHub | 2026-08-13 | primary | rtx-pro-6000 | https://github.com/Project-HAMi/HAMi/issues/2641 |
| W4A8-MX 极小解码内核 - 一个 M=1 专用内核从 108 到 20.6 微秒的全过程（并推翻前一日结论） | GitHub | 2026-07-03 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/b12x-w4a8mx-tiny-decode-kernel.md |
| 仓库 `Badtheorylabs/BTL-3`（**语言 C++，32,020 KB，pushed 2026-07-24**）——「**Native r… | GitHub | — | primary | rtx-pro-6000 | https://api.github.com/repos/Badtheorylabs/BTL-3 |
| 混合 NVFP4 装配 - 把质量敏感层留成 BF16（只多 1.7% 显存），并暴露模型结构 | GitHub | 2026-04-30 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/optimization/hybrid-nvfp4-assembly.md |
| 知乎开放平台 API 参考（CLI 设计用） | GitHub | 2026-09-24 | secondary | multi-platform-publish | https://github.com/dawnswwwww/zhihu-cli/blob/main/skills/zhihu-cli/references/api-reference.md |
| `README.md`（8,354 字节，2026-07-24 更新，retrieved 2026-10）——**上一轮那份 `llama-bench` … | Hugging Face | — | primary | rtx-pro-6000 | https://huggingface.co/badtheorylabs/BTL-3-Compact/raw/main/README.md |
| BTL-3 Compact — RTX PRO 6000 speed | Hugging Face | 2026-07-19 | primary | rtx-pro-6000 | https://huggingface.co/badtheorylabs/BTL-3-Compact/raw/7c48bf621a46be433032106ca888f02711d2530b/evidence/rtx-pro-6000-speed-2026-07-19.md |
| BTL-3 Compact — RTX PRO 6000 speed (2026-07-19 measured) | Hugging Face | 2026-07-19 | primary | rtx-pro-6000 | https://huggingface.co/badtheorylabs/BTL-3-Compact/blob/7c48bf621a46be433032106ca888f02711d2530b/evidence/rtx-pro-6000-speed-2026-07-19.md |
| DeepSeek-V4.1-Flash-1017 EXL3 3-bit for 2x RTX PRO 6000 Blackwell | Hugging Face | 2026-10-20 | primary | pro6000se-dsv41 | https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000 |
| Evaluation Report: Kolibri-1 FP8 on one RTX PRO 6000 (96 GB) — serving number… | Hugging Face | 2026-08-31 | primary | rtx-pro-6000 | https://huggingface.co/Aleph-Alpha/Kolibri-1/discussions/10 |
| EXL3 3-bit full results page (8x Server Edition node, KL noise floor, agentic… | Hugging Face | 2026-10-24 | primary | pro6000se-dsv41 | https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000/blob/main/recipe/results/RESULTS.md |
| Expert-pruned 2x RTX PRO 6000 recipe (224/384 experts, native FP4) | Hugging Face | 2026-10-28 | primary | pro6000se-dsv41 | https://huggingface.co/tacos4me/DeepSeek-V4.1-Flash-Prune-2xRTX6K |
| NVFP4 vs FP8 on an RTX PRO 6000 Blackwell (vLLM 0.24): sadly, FP4 is still no… | Hugging Face | 2026-09-20 | primary | rtx-pro-6000 | https://huggingface.co/nvidia/Qwen3.6-27B-NVFP4/discussions/8 |
| RTX PRO 6000 Blackwell 96GB vs GH200: LLM Fine-Tuning Benchmark | Hugging Face | 2026-06-05 | primary | rtx-pro-6000 | https://huggingface.co/blog/AlioLeuchtmann/rtx-6000-pro-vs-gh200-sft-benchmark |
| Running on 2 RTX Pro 6000 Blackwell GPUs at ~30 tps（Mistral-Medium-3.5-128B 双… | Hugging Face | 2026-05-02 | primary | rtx-pro-6000 | https://huggingface.co/mistralai/Mistral-Medium-3.5-128B/discussions/17 |
| Serving notes: single RTX PRO 6000 Blackwell (96 GB) — FP8 KV + an NVFP4 MTP … | Hugging Face | 2026-09-13 | primary | rtx-pro-6000 | https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4/discussions/15 |
| 模型讨论 #18「**Best way to run on Dual RTX 6000 Pro Blackwell?**」（10 条事件，2026-08-… | Hugging Face | — | primary | rtx-pro-6000 | https://huggingface.co/api/models/unsloth/DeepSeek-V4-Flash-0731-GGUF/discussions/18 |
| Blackwell Pro 6000 MHz degrading | NVIDIA 开发者论坛 | 2026-02-20 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/blackwell-pro-6000-mhz-degrading/355157 |
| Blackwell Pro 6000 MHz degrading | NVIDIA 开发者论坛 | 2026-07-08 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/blackwell-pro-6000-mhz-degrading/355157/17 |
| Deepseek v4 Flash on 2 Nodes（DGX Spark / GB10 Projects，20 帖，2026-05-04 至 2026… | NVIDIA 开发者论坛 | 2026-05-04 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/deepseek-v4-flash-on-2-nodes/368916 |
| DeepSeek-V4-Flash（official FP8）running across 2x DGX Spark — TP=2, MTP, 200K … | NVIDIA 开发者论坛 | 2026-05-16 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309 |
| DeepSeek-V4.1-Flash-1017 (EXL3 2.9bpw) on 2x DGX Spark with TensorFold: 57 to… | NVIDIA 开发者论坛 | 2026-10-18 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/deepseek-v4-1-flash-1017-exl3-2-9bpw-on-2x-dgx-spark-with-tensorfold-57-tok-s-text-92-tok-s-code-2-1-2-3x-the-vllm-kit/386125 |
| Degenerate logits at temperature > 0 — random CJK characters spliced into Eng… | NVIDIA 开发者论坛 | 2026-10-02 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/degenerate-logits-at-temperature-0-random-cjk-characters-spliced-into-english-output-vllm-deepseek-v4-flash-tp-2/384863 |
| Expert Parallelism using 6000 Pro PCIe Gen5 Vs B200 Nvlink | NVIDIA 开发者论坛 | 2026-07-27 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/expert-parallelism-using-6000-pro-pcie-gen5-vs-b200-nvlink/378258 |
| How to reflash bricked RTX PRO 6000 | NVIDIA 开发者论坛 | 2026-02-12 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/how-to-reflash-bricked-rtx-pro-6000/360472 |
| MIG not available on RTX PRO 6000 Blackwell – VBIOS requirement? | NVIDIA 开发者论坛 | 2026-04-10 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/mig-not-available-on-rtx-pro-6000-blackwell-vbios-requirement/366155 |
| MIG support on RTX Pro 6000 Blackwell（第 44 帖：Max-Q 成功启用 MIG） | NVIDIA 开发者论坛 | 2025-07-30 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/mig-support-on-rtx-pro-6000-blackwell/334906/44 |
| NVIDIA-branded RTX PRO 6000 WE warranty claim: PNY denies serial in writing, … | NVIDIA 开发者论坛 | 2026-10-07 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/nvidia-branded-rtx-pro-6000-we-warranty-claim-pny-denies-serial-in-writing-enterprise-support-closes-case-same-day-who-services-warranty-for-nvidi/380744/4 |
| PRO 6000 Blackwell WS: SW Power Cap ~600 MHz @ 600 W / 35°C — fix or RMA? | NVIDIA 开发者论坛 | 2026-07-15 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/pro-6000-blackwell-ws-sw-power-cap-600-mhz-600-w-35-c-fix-or-rma/376937 |
| Recurring Xid 8 (RC watchdog "GPU probably locked") on RTX PRO 6000 Blackwell… | NVIDIA 开发者论坛 | 2026-09-02 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/recurring-xid-8-rc-watchdog-gpu-probably-locked-on-rtx-pro-6000-blackwell-under-sustained-compute-595-84-and-610-43-02-open/382055 |
| RTX 6000 pro ws BIOS update to >= 98.02.55.00.00 how? | NVIDIA 开发者论坛 | 2025-08-23 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-6000-pro-ws-bios-update-to-98-02-55-00-00-how/342946 |
| RTX PRO 6000 Blackwell (GB202) - Recurring full chip reset during sustained L… | NVIDIA 开发者论坛 | 2026-04-06 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-gb202-recurring-full-chip-reset-during-sustained-llm-inference-requires-psu-power-cycle-to-recover/365739 |
| RTX PRO 6000 Blackwell + RTX 5090: Xid 79 fallen off the bus, 7 events, no pr… | NVIDIA 开发者论坛 | 2026-10-14 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-rtx-5090-xid-79-fallen-off-the-bus-7-events-no-precursor/385851 |
| RTX Pro 6000 Blackwell - Wrong temperature thresholds causes SW Power Cap, GP… | NVIDIA 开发者论坛 | 2026-03-05 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-wrong-temperature-thresholds-causes-sw-power-cap-gpu-throttled-to-510mhz-1-6-performance/362488 |
| RTX PRO 6000 Blackwell Max-Q (10de:2bb4): FLR fails on vfio-pci release after… | NVIDIA 开发者论坛 | 2026-10-25 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-max-q-10de-2bb4-flr-fails-on-vfio-pci-release-after-kvm-guest-shutdown-gpu-inaccessible-until-cold-power-cycle/386790 |
| RTX PRO 6000 Blackwell Max-Q hardware problem? Multitude of MMU errors in dme… | NVIDIA 开发者论坛 | 2026-08-26 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-pro-6000-blackwell-max-q-hardware-problem-multitude-of-mmu-errors-in-dmesg/381310 |
| Silent CUDA Compute Corruption on RTX PRO 6000 Blackwell | NVIDIA 开发者论坛 | 2026-08-29 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/silent-cuda-compute-corruption-on-rtx-pro-6000-blackwell/381759 |
| Support for a RTX Pro 6000 Blackwell Workstation Edition（支持层级实录） | NVIDIA 开发者论坛 | 2026-04-09 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/support-for-a-rtx-pro-6000-blackwell-workstation-edition/366144 |
| Where to find NVIDIA RTX PRO 6000 Blackwell Max-Q BIOS / vBIOS / firmware upd… | NVIDIA 开发者论坛 | 2026-02-11 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/where-to-find-nvidia-rtx-pro-6000-blackwell-max-q-bios-vbios-firmware-updates/360321 |
| RTX PRO 6000 Performance | blenderartists.org | 2026-07-24 | primary | rtx-pro-6000 | https://blenderartists.org/t/rtx-pro-6000-performance/1648521/2 |
| RTX PRO 6000 Performance（含 Blender Open Data 5.1.1 四卡对照） | blenderartists.org | 2026-07-24 | primary | rtx-pro-6000 | https://blenderartists.org/t/rtx-pro-6000-performance/1648521 |
| 小红书开放平台 API 实战：从资质申请到笔记/评论接口调用 | cloud.tencent.com.cn | 2026-09-01 | secondary | multi-platform-publish | https://cloud.tencent.com.cn/developer/article/2735161 |
| Support for RTX 6000 Blackwell 96GB card | discuss.vllm.ai | 2025-10-07 | primary | rtx-pro-6000 | https://discuss.vllm.ai/t/support-for-rtx-6000-blackwell-96gb-card/1707 |
| After updating the RTX Pro 6000 WS driver to version 595.71.05, the Perf stat… | forum.level1techs.com | 2026-05-15 | primary | rtx-pro-6000 | https://forum.level1techs.com/t/after-updating-the-rtx-pro-6000-ws-driver-to-version-595-71-05-the-perf-state-changed-to-p8/250239 |
| Question regarding MIG support on RTX Pro 6000（40 帖完整过程） | forum.level1techs.com | 2025-06-27 | primary | rtx-pro-6000 | https://forum.level1techs.com/t/question-regarding-mig-support-on-rtx-pro-6000/232627 |
| WIP: Blackwell RTX 6000 Pro / Max-Q Quickie Setup Guide on Ubuntu 24.04 LTS /… | forum.level1techs.com | 2025-05-11 | primary | rtx-pro-6000 | https://forum.level1techs.com/t/wip-blackwell-rtx-6000-pro-max-q-quickie-setup-guide-on-ubuntu-24-04-lts-25-04/230521 |
| 4× RTX PRO 6000 Blackwell on Water, and the One Card That Wouldn't Behave | sabareesh.com | 2026-06-12 | primary | rtx-pro-6000 | https://sabareesh.com/posts/blackwell-waterblock/ |
| Blackwell Wattage-Performance Dashboard | shihanqu.github.io | — | primary | rtx-pro-6000 | https://shihanqu.github.io/Blackwell-Wattage-Performance/ |

### 学术（论文 / 预印本）（`academic`，274 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| A Case Study of a Multi-Agent Kernel-Optimization Loop That Learns a New AI A… | arXiv | 2026-10-28 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2610.38329 |
| A Method for Layer Bit-Width Allocation in LLM Quantization via Performance M… | arXiv | 2026-08-28 | primary | rsi-quant | https://arxiv.org/abs/2608.28003 |
| A Self-Improving Coding Agent | arXiv | 2025-04-21 | primary | rsi-model-training | https://arxiv.org/abs/2504.15228 |
| A Survey of Self-Evolving Agents: What, When, How, and Where to Evolve on the… | arXiv | 2025-07-28 | primary | rsi-model-training | https://arxiv.org/abs/2507.21046 |
| A Survey on LLM Inference-Time Self-Improvement | arXiv | 2024-12-18 | primary | rsi-model-training | https://arxiv.org/abs/2412.14352 |
| A Target-Centric Survey of Quantization-Aware Training | arXiv | 2026-08-30 | primary | rsi-quant | https://arxiv.org/abs/2608.29667 |
| Absolute Zero: Reinforced Self-play Reasoning with Zero Data | arXiv | 2025-05-06 | primary | rsi-model-training | https://arxiv.org/abs/2505.03335 |
| Accuracy is Not Enough: A Divergence-Based Approach to Evaluate Fidelity Loss… | arXiv | 2026-09-07 | primary | rsi-quant | https://arxiv.org/abs/2609.07664 |
| Ada-MK: Adaptive MegaKernel Optimization via Automated DAG-based Search for L… | arXiv | 2026-05-12 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2605.11581 |
| AdaExplore: Failure-Driven Adaptation and Diversity-Preserving Search for Eff… | arXiv | 2026-04-17 | primary | rsi-inference | https://arxiv.org/abs/2604.16625 |
| ADOR: A Design Exploration Framework for LLM Serving with Enhanced Latency an… | arXiv | 2025-03-06 | primary | rsi-serving | https://arxiv.org/abs/2503.04253 |
| AE-LLM: Adaptive Efficiency Optimization for Large Language Models | arXiv | 2026-03-20 | primary | rsi-serving | https://arxiv.org/abs/2603.20492 |
| Afterburner: Reinforcement Learning Facilitates Self-Improving Code Efficienc… | arXiv | 2025-05-29 | primary | rsi-inference | https://arxiv.org/abs/2505.23387 |
| Agent Workflow Memory | arXiv | 2024-09-11 | primary | rsi-model-training | https://arxiv.org/abs/2409.07429 |
| Agent0: Unleashing Self-Evolving Agents from Zero Data via Tool-Integrated Re… | arXiv | 2025-11-20 | primary | rsi-model-training | https://arxiv.org/abs/2511.16043 |
| AgentDisCo: Towards Disentanglement and Collaboration in Open-ended Deep Rese… | arXiv | 2026-05-12 | primary | rsi-inference | https://arxiv.org/abs/2605.11732 |
| AgentEvolver: Towards Efficient Self-Evolving Agent System | arXiv | 2025-11-13 | primary | rsi-model-training | https://arxiv.org/abs/2511.10395 |
| Agentic Kernel Optimization: Generating State-of-the-Art GPU Kernels Without … | arXiv | 2026-05-25 | primary | kernel-agent | https://arxiv.org/abs/2608.14560 |
| AgenticCANN: Automated Ascend C Operator Generation via Knowledge-Augmented A… | arXiv | 2026-07-29 | primary | rsi-inference | https://arxiv.org/abs/2607.26661 |
| AgentKernelArena: Generalization-Aware Benchmarking of GPU Kernel Optimizatio… | arXiv | 2026-05-16 | primary | rsi-inference | https://arxiv.org/abs/2605.16819 |
| AgentPerfBench: A Benchmarking and Evaluation Suite for Inference Performance… | arXiv | 2026-09-28 | primary | agent-serving-bench | https://arxiv.org/abs/2609.34683 |
| AIConfigurator: Lightning-Fast Configuration Optimization for Multi-Framework… | arXiv | 2026-01-09 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2601.06288 |
| AlignQuant: Tile-Aligned Mixed-Precision Quantization for Efficient LLM Gener… | arXiv | 2026-10-05 | primary | rsi-quant | https://arxiv.org/abs/2610.07457 |
| AlphaEvolve: A coding agent for scientific and algorithmic discovery | arXiv | 2025-06-16 | primary | rsi-model-training | https://arxiv.org/abs/2506.13131 |
| Anatomy of a Quantized Agent: VRAM Stability and Forecasting in Code-Synthesi… | arXiv | 2026-08-15 | primary | rsi-quant | https://arxiv.org/abs/2608.15117 |
| APQF: Agentic Profiling-Guided Structured Pruning and Mixed-Precision Quantiz… | arXiv | 2026-08-06 | primary | rsi-quant | https://arxiv.org/abs/2608.05499 |
| Are LLM-Generated GPU Kernels Production-Ready? A Trace-Driven Benchmark and … | arXiv | 2026-07-16 | primary | rsi-inference | https://arxiv.org/abs/2607.14541 |
| ARK: Avoiding Routing Collisions for KV Cache Transfer in Disaggregated LLM I… | arXiv | 2026-10-30 | primary | pd-disagg | https://arxiv.org/abs/2610.41160 |
| ASAP: an Agentic Solution to Auto-optimize Performance of Large-Scale LLM Tra… | arXiv | 2025-11-05 | primary | rsi-inference | https://arxiv.org/abs/2511.03844 |
| Ask, Don't Equip: Question-Driven Coding Agents for Deep Kernel Optimization | arXiv | 2026-11-02 | primary | rsi-inference | https://arxiv.org/abs/2611.03517 |
| AsmEvo: Agentic Assembly-Level Optimization of AMD GPU Kernels with Functiona… | arXiv | 2026-08-21 | primary | rsi-inference | https://arxiv.org/abs/2608.20711 |
| Astra: A Multi-Agent System for GPU Kernel Performance Optimization | arXiv | 2025-09-09 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2509.07506 |
| Auditing the Product, Not the Recursion: The Evaluation Evidence Behind Recur… | arXiv | 2026-10-20 | primary | rsi-model-training | https://arxiv.org/abs/2610.27610 |
| AutoKernel: Autonomous GPU Kernel Optimization via Iterative Agent-Driven Sea… | arXiv | 2026-03-22 | primary | rsi-inference | https://arxiv.org/abs/2603.21331 |
| Automated Design of Agentic Systems | arXiv | 2024-08-15 | primary | rsi-model-training | https://arxiv.org/abs/2408.08435 |
| Automatic Model-Hardware Co-Adaptation for Heterogeneous AI Accelerators | arXiv | 2026-07-14 | primary | rsi-serving | https://arxiv.org/abs/2607.12875 |
| AutoTrainess: Teaching Language Models to Improve Language Models Autonomously | arXiv | 2026-06-30 | primary | rsi-inference-bench | https://arxiv.org/abs/2606.31551 |
| AutoTriton: Automatic Triton Programming with Reinforcement Learning in LLMs | arXiv | 2025-07-08 | primary | cuda-kernel-gen, cuda-kernel-rl | https://arxiv.org/abs/2507.05687 |
| AutoTuneBench: Trustworthy Measurement for Agent Auto-Tuning of LLM Serving E… | arXiv | 2026-09-16 | primary | agent-serving-bench, cuda-kernel-gen, rsi-inference, rsi-serving | https://arxiv.org/abs/2609.18123 |
| Ave: Guiding Agentic GPU Optimization Using Data-Flow Invariants | arXiv | 2026-04-16 | primary | cuda-kernel-gen, rsi-inference | https://arxiv.org/abs/2604.18616 |
| Beyond Accuracy: How Quantization Affects Coding Agents | arXiv | 2026-11-02 | primary | rsi-quant | https://arxiv.org/abs/2611.02368 |
| Beyond Experience: Knowledge-Guided Evolution for NPU Kernel Generation | arXiv | 2026-10-20 | primary | kernel-agent | https://arxiv.org/abs/2610.27588 |
| Beyond Pass@1: Self-Play with Variational Problem Synthesis Sustains RLVR | arXiv | 2025-08-19 | primary | rsi-model-training | https://arxiv.org/abs/2508.14029 |
| Beyond Prefill-Decode Disaggregation: Dissecting LLM Inference for Heterogene… | arXiv | 2026-07-28 | primary | pd-disagg | https://arxiv.org/abs/2607.25498 |
| Beyond Scalar Sensitivity: Activation-Aware Mixed-Precision LLM Quantization … | arXiv | 2026-09-22 | primary | rsi-quant | https://arxiv.org/abs/2609.25916 |
| Beyond Scaling: Self-Evolving LLM Agents for Hardware Kernel Optimization via… | arXiv | 2026-08-26 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2608.25570 |
| Bits and Memories: Measuring Verbatim Extraction Across LLM Quantization | arXiv | 2026-07-28 | primary | rsi-quant | https://arxiv.org/abs/2607.25451 |
| Breaking the Self-Confirming Loop: Diagnosing and Mitigating Systemic Reward … | arXiv | 2025-10-10 | primary | rsi-model-training | https://arxiv.org/abs/2510.08977 |
| CANNBot-CAKE: Collaborative Agentic Kernel Evolution for Ascend NPU | arXiv | 2026-10-22 | primary | rsi-inference | https://arxiv.org/abs/2610.31034 |
| CAT-Q: Cost-efficient and Accurate Ternary Quantization for LLMs | arXiv | 2026-06-25 | primary | rsi-quant | https://arxiv.org/abs/2606.26650 |
| CLEAR: Structured Specifications for Controllable Long-Horizon ML Research En… | arXiv | 2026-11-04 | primary | rsi-inference-bench | https://arxiv.org/abs/2611.06263 |
| CodeEvolve: an open source evolutionary coding agent for algorithmic discover… | arXiv | 2025-10-15 | primary | rsi-inference | https://arxiv.org/abs/2510.14150 |
| Combating the Memory Walls: Optimization Pathways for Long-Context Agentic LL… | arXiv | 2025-09-11 | primary | rsi-inference | https://arxiv.org/abs/2509.09505 |
| Compaction-Aware Reinforcement Learning For Ascend Triton Kernel Generation | arXiv | 2026-10-09 | primary | cuda-kernel-rl, kernel-agent | https://arxiv.org/abs/2610.23950 |
| Composable CXL Memory as a Kubernetes-Native Shared Memory for LLM Serving | arXiv | 2026-09-09 | primary | pd-disagg | https://arxiv.org/abs/2609.10790 |
| Compress and Forget: bitsandbytes Quantization Amplifies Proactive Interferen… | arXiv | 2026-08-19 | primary | rsi-quant | https://arxiv.org/abs/2608.18578 |
| CompressionBench: How can your coding agents compress LLMs? | arXiv | 2026-11-04 | primary | rsi-quant | https://arxiv.org/abs/2611.06858 |
| ConCuR: Conciseness Makes State-of-the-Art Kernel Generation | arXiv | 2025-10-08 | primary | cuda-kernel-gen | https://arxiv.org/abs/2510.07356 |
| Conjugate Compilation: Self-Improving Agentic Co-Compilation for Speculative … | arXiv | 2026-10-18 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2610.25012 |
| CuAsmRL: Optimizing GPU SASS Schedules via Deep Reinforcement Learning | arXiv | 2025-01-14 | primary | cuda-kernel-rl | https://arxiv.org/abs/2501.08071 |
| CUDA Agent: Large-Scale Agentic RL for High-Performance CUDA Kernel Generation | arXiv | 2026-02-27 | primary | cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference | https://arxiv.org/abs/2602.24286 |
| CUDA-L1: Improving CUDA Optimization via Contrastive Reinforcement Learning | arXiv | 2025-07-18 | primary | cuda-kernel-gen, cuda-kernel-rl | https://arxiv.org/abs/2507.14111 |
| CUDA-L2: Surpassing cuBLAS Performance for Matrix Multiplication through Rein… | arXiv | 2025-12-02 | primary | cuda-kernel-gen, cuda-kernel-rl | https://arxiv.org/abs/2512.02551 |
| CudaForge: An Agent Framework with Hardware Feedback for CUDA Kernel Optimiza… | arXiv | 2025-10-23 | primary | cuda-kernel-gen, kernel-agent | https://arxiv.org/abs/2511.01884 |
| CUDAHercules: Benchmarking Hardware-Aware Expert-level CUDA Optimization for … | arXiv | 2026-05-08 | primary | kernel-agent | https://arxiv.org/abs/2605.08467 |
| cuPilot: A Strategy-Coordinated Multi-agent Framework for CUDA Kernel Evoluti… | arXiv | 2025-12-18 | primary | rsi-inference | https://arxiv.org/abs/2512.16465 |
| CuTeGen: An LLM-Based Agentic Framework for Generation and Optimization of Hi… | arXiv | 2026-04-01 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2604.01489 |
| D2K-Bench: Can LLM Agents Turn Expert Designs into Efficient GPU Kernels? | arXiv | 2026-10-02 | primary | cuda-kernel-gen | https://arxiv.org/abs/2610.03226 |
| Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents | arXiv | 2025-05-29 | primary | rsi-model-training | https://arxiv.org/abs/2505.22954 |
| DataMaster: Data-Centric Autonomous AI Research | arXiv | 2026-05-11 | primary | rsi-inference-bench | https://arxiv.org/abs/2605.10906 |
| daVinci-kernel: Co-Evolving Skill Selection, Summarization, and Utilization v… | arXiv | 2026-06-15 | primary | rsi-inference | https://arxiv.org/abs/2606.16497 |
| Disaggregated Prefill and Decoding Inference System for Large Language Model … | arXiv | 2025-09-22 | primary | pd-disagg | https://arxiv.org/abs/2509.17542 |
| Disaggregated Quantization: Specializing LLM Prefill and Decode | arXiv | 2026-09-22 | primary | pd-disagg | https://arxiv.org/abs/2609.26333 |
| Displacement Is Not Direction: Evaluating Fidelity Metrics for Quantized LLM … | arXiv | 2026-06-17 | primary | rsi-quant | https://arxiv.org/abs/2606.19558 |
| DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large La… | arXiv | 2024-01-18 | primary | pd-disagg | https://arxiv.org/abs/2401.09670 |
| Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Bey… | arXiv | 2025-04-18 | primary | rsi-model-training | https://arxiv.org/abs/2504.13837 |
| Don't Regenerate, Debug: A Domain-Specific Agent for Repairing Near-Miss Acce… | arXiv | 2026-08-03 | primary | rsi-inference | https://arxiv.org/abs/2608.02712 |
| Dr. Kernel: Reinforcement Learning Done Right for Triton Kernel Generations | arXiv | 2026-02-05 | primary | cuda-kernel-gen, cuda-kernel-rl | https://arxiv.org/abs/2602.05885 |
| Drafting Agents, Not Just Tokens: Speculative Recursive Self-Improvement for … | arXiv | 2026-10-12 | primary | rsi-serving | https://arxiv.org/abs/2610.16491 |
| DRTriton: Large-Scale Synthetic Data Driven Reinforcement Learning for Triton… | arXiv | 2026-03-23 | primary | cuda-kernel-rl | https://arxiv.org/abs/2603.21465 |
| DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines | arXiv | 2023-10-05 | primary | rsi-model-training | https://arxiv.org/abs/2310.03714 |
| DualScale: Energy-Efficient Disaggregated LLM Serving via Phase-Aware Placeme… | arXiv | 2026-02-21 | primary | pd-disagg | https://arxiv.org/abs/2602.18755 |
| DynaServe: Unified and Elastic Execution for Dynamic Disaggregated LLM Serving | arXiv | 2025-04-12 | primary | pd-disagg | https://arxiv.org/abs/2504.09285 |
| EAServe: Encode-Aware Disaggregated Serving for Multimodal Large Language Mod… | arXiv | 2026-09-25 | primary | pd-disagg | https://arxiv.org/abs/2609.31551 |
| EdgeKernelBench: Unified LLM-Driven Kernel Generation for Edge Backends | arXiv | 2026-10-17 | primary | cuda-kernel-gen | https://arxiv.org/abs/2610.24648 |
| EGG: An Expert-Guided Agent Framework for Kernel Generation | arXiv | 2026-06-25 | primary | cuda-kernel-gen, kernel-agent | https://arxiv.org/abs/2606.26758 |
| EvoEngineer: Mastering Automated CUDA Kernel Code Evolution with Large Langua… | arXiv | 2025-10-04 | primary | cuda-kernel-gen | https://arxiv.org/abs/2510.03760 |
| Evolving Agent Teams | arXiv | 2026-10-27 | primary | kernel-agent | https://arxiv.org/abs/2610.36848 |
| ExpertPlex: A High-Goodput Disaggregated Serving System for MoE LLMs with Ada… | arXiv | 2026-07-20 | primary | pd-disagg | https://arxiv.org/abs/2607.18002 |
| FABRICA: Agentic CUDA-to-CSL Translation and Optimization for Wafer-Scale Sys… | arXiv | 2026-08-25 | primary | kernel-agent | https://arxiv.org/abs/2608.25124 |
| Faithfulness Is Not Free: Auditing Offline KV-Cache Quantization in Retrieval… | arXiv | 2026-08-31 | primary | rsi-quant | https://arxiv.org/abs/2608.30996 |
| FAMPWQ: Fisher Information-based Adaptive Mixed Precision Weight Quantization… | arXiv | 2026-08-24 | primary | rsi-quant | https://arxiv.org/abs/2608.24945 |
| FlashInfer-Bench: Building the Virtuous Cycle for AI-driven LLM Systems | arXiv | 2026-01-01 | primary | cuda-kernel-gen | https://arxiv.org/abs/2601.00227 |
| FlashRT: Agent Harness for Guiding Agents to Deploy Real-Time Multimodal Appl… | arXiv | 2026-07-20 | primary | agent-serving-bench | https://arxiv.org/abs/2607.18171 |
| Flat Score, Amplified Failures: How the Error Budget Masks Damage in Quantize… | arXiv | 2026-07-29 | primary | rsi-quant | https://arxiv.org/abs/2607.27275 |
| FluidPD: In-Place Elasticity for SLO-Aware Prefill-Decode Disaggregated LLM S… | arXiv | 2026-10-02 | primary | pd-disagg | https://arxiv.org/abs/2610.06917 |
| ForgeKernel: Self-Evolving Kernels Catching and Surpassing Experts and Agents | arXiv | 2026-11-03 | primary | rsi-inference | https://arxiv.org/abs/2611.04998 |
| FreeToken: Efficient Edge-Native MoE Serving with Bandwidth-Adaptive Execution | arXiv | 2026-08-17 | primary | rtx-pro-6000 | https://arxiv.org/html/2608.16157 |
| From Bits to Chips: An LLM-based Hardware-Aware Quantization Agent for Stream… | arXiv | 2026-01-07 | primary | rsi-serving | https://arxiv.org/abs/2601.03484 |
| From Inference Engine to Inference Control Plane: Connecting vLLM, llm-d, and… | arXiv | 2026-09-19 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2609.23130 |
| From RLVR to RLSVR: Task Transformation Induces Self-Verifiable Rewards for O… | arXiv | 2026-07-26 | primary | rsi-model-training | https://arxiv.org/abs/2607.23802 |
| From Tokens to Regions: CUDA-Sensitive Instruction Tuning for GPU Kernel Gene… | arXiv | 2026-06-15 | primary | cuda-kernel-gen | https://arxiv.org/abs/2606.16231 |
| Frontier: Towards Comprehensive and Accurate LLM Inference Simulation | arXiv | 2026-05-20 | primary | pd-disagg, rsi-serving | https://arxiv.org/abs/2605.21312 |
| God Does Not Play Dice: Enforcing Batch Invariance in Agentic Kernel Generati… | arXiv | 2026-10-27 | primary | cuda-kernel-gen | https://arxiv.org/abs/2610.36623 |
| GPU Forecasters: Language Models as Selective Surrogates for Kernel Runtime O… | arXiv | 2026-05-29 | primary | cuda-kernel-rl | https://arxiv.org/abs/2605.31464 |
| GPU Kernel Scientist: An LLM-Driven Framework for Iterative Kernel Optimizati… | arXiv | 2025-06-25 | primary | rsi-inference | https://arxiv.org/abs/2506.20807 |
| Group-Marginalized Self-Rewarding RL Drives Zero-Label Self-Evolving | arXiv | 2026-09-29 | primary | rsi-model-training | https://arxiv.org/abs/2609.36750 |
| Gödel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement | arXiv | 2024-10-06 | primary | rsi-model-training | https://arxiv.org/abs/2410.04444 |
| HAWK: Heterogeneity-Aware KV Cache Transfer for Efficient GPU-NPU Phase-Disag… | arXiv | 2026-10-21 | primary | pd-disagg | https://arxiv.org/abs/2610.29873 |
| HBM Is Not All You Need: Efficient Disaggregated LLM Serving across Memory-he… | arXiv | 2026-06-29 | primary | pd-disagg | https://arxiv.org/abs/2606.29986 |
| HIERA: Workload-Aware Planning Across Implementation Spaces for GPU Kernel Op… | arXiv | 2026-08-21 | primary | kernel-agent | https://arxiv.org/abs/2608.21157 |
| How Do Coding-Agent Harnesses Self-Evolve? An Empirical Study of Retrospectiv… | arXiv | 2026-10-26 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2610.34938 |
| How Far Can Disaggregation Go? A Design-Space Exploration of Attention-FFN Di… | arXiv | 2026-05-27 | primary | pd-disagg | https://arxiv.org/abs/2605.28302 |
| How Much of a Real Workload Can LLM-Generated GPU Kernels Actually Reach? | arXiv | 2026-09-17 | primary | cuda-kernel-gen | https://arxiv.org/abs/2609.21058 |
| HS-STaR: Hierarchical Sampling for Self-Taught Reasoners via Difficulty Estim… | arXiv | 2025-05-26 | primary | rsi-model-training | https://arxiv.org/abs/2505.19866 |
| Huawei Cloud Model-as-a-Service on the CloudMatrix384 SuperPod | arXiv | 2025-08-04 | primary | pd-disagg | https://arxiv.org/abs/2508.02520 |
| Improving Coherence and Persistence in Agentic AI for System Optimization | arXiv | 2026-03-22 | primary | rsi-inference | https://arxiv.org/abs/2603.21321 |
| Improving Efficiency of GPU Kernel Optimization Agents using a Domain-Specifi… | arXiv | 2026-03-30 | primary | rsi-inference | https://arxiv.org/abs/2603.29010 |
| Inference without Interference: Disaggregate LLM Inference for Mixed Downstre… | arXiv | 2024-01-20 | primary | pd-disagg | https://arxiv.org/abs/2401.11181 |
| InferenceBench: A Benchmark for Open-Ended LLM Inference Optimization by AI A… | arXiv | 2026-05-20 | primary | agent-serving-bench, rsi-inference, rsi-serving | https://arxiv.org/abs/2607.20468 |
| InfraDev: Can Coding Agents Develop AI Infrastructure, and How Can We Tell? | arXiv | 2026-10-27 | primary | agent-serving-bench | https://arxiv.org/abs/2610.36589 |
| Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating… | arXiv | 2024-04-01 | primary | rsi-model-training | https://arxiv.org/abs/2404.01413 |
| ISO-Bench: Can Coding Agents Optimize Real-World Inference Workloads? | arXiv | 2026-02-23 | primary | agent-serving-bench | https://arxiv.org/abs/2602.19594 |
| Iterative Reasoning Preference Optimization | arXiv | 2024-04-30 | primary | rsi-model-training | https://arxiv.org/abs/2404.19733 |
| K-Search: LLM Kernel Generation via Co-Evolving Intrinsic World Model | arXiv | 2026-02-22 | primary | cuda-kernel-gen | https://arxiv.org/abs/2602.19128 |
| Kernel-Smith: A Unified Recipe for Evolutionary Kernel Optimization | arXiv | 2026-03-30 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2603.28342 |
| KernelArc: A Multi-Agent Framework for GPU Kernel Optimization | arXiv | 2026-08-17 | primary | kernel-agent | https://arxiv.org/abs/2608.17071 |
| KernelBench-Verified: Do LLM-Generated Kernels Actually Beat PyTorch? | arXiv | 2026-06-26 | primary | agent-serving-bench, cuda-kernel-gen, cuda-kernel-rl, rsi-inference | https://arxiv.org/abs/2607.16241 |
| KernelBench: Can LLMs Write Efficient GPU Kernels? | arXiv | 2025-02-14 | primary | agent-serving-bench, cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference | https://arxiv.org/abs/2502.10517 |
| KernelBenchX: A Comprehensive Benchmark for Evaluating LLM-Generated GPU Kern… | arXiv | 2026-05-06 | primary | cuda-kernel-gen, kernel-agent | https://arxiv.org/abs/2605.04956 |
| KernelBlaster: Continual Cross-Task CUDA Optimization via Memory-Augmented In… | arXiv | 2026-02-15 | primary | cuda-kernel-gen, rsi-inference | https://arxiv.org/abs/2602.14293 |
| KernelBrain: Coarse-to-Fine, Budget-Aware Search for Agentic GPU Kernel Optim… | arXiv | 2026-05-19 | primary | rsi-inference | https://arxiv.org/abs/2608.02611 |
| KernelClaw: A Multi-Agent Framework for GPU Kernel Optimization with Dual-Mem… | arXiv | 2026-03-10 | primary | kernel-agent | https://arxiv.org/abs/2603.10085 |
| KernelEvolve: Scaling Agentic Kernel Coding for Heterogeneous AI Accelerators… | arXiv | 2025-12-29 | primary | rsi-inference | https://arxiv.org/abs/2512.23236 |
| KernelFoundry: Hardware-aware evolutionary GPU kernel optimization | arXiv | 2026-03-12 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2603.12440 |
| KernelOPT: Dispatch-Aware Agentic Search for GPU Kernel Optimization | arXiv | 2026-09-24 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2609.30059 |
| Kevin: Multi-Turn RL for Generating CUDA Kernels | arXiv | 2025-07-16 | primary | cuda-kernel-gen, cuda-kernel-rl, kernel-agent | https://arxiv.org/abs/2507.11948 |
| KForge: LLM-Driven Cross-Platform Kernel Generation for AI Accelerators | arXiv | 2026-06-01 | primary | rsi-inference | https://arxiv.org/abs/2606.02963 |
| KForge: Program Synthesis for Diverse AI Hardware Accelerators | arXiv | 2025-11-17 | primary | kernel-agent | https://arxiv.org/abs/2511.13274 |
| LADDER: Self-Improving LLMs Through Recursive Problem Decomposition | arXiv | 2025-03-02 | primary | rsi-model-training | https://arxiv.org/abs/2503.00735 |
| LaSeR: Reinforcement Learning with Last-Token Self-Rewarding | arXiv | 2025-10-16 | primary | rsi-model-training | https://arxiv.org/abs/2510.14943 |
| Layerwise Error Attribution for Fast and Robust Mixed-Precision Post-Training… | arXiv | 2026-10-07 | primary | rsi-quant | https://arxiv.org/abs/2610.09877 |
| LEAP: Lean Environment-Feedback via Adaptive Pruning for Code RL in GPU Kerne… | arXiv | 2026-08-03 | primary | cuda-kernel-rl, kernel-agent | https://arxiv.org/abs/2608.01804 |
| LeapQuant: Efficient Linear Attention with Accurate Recurrent State Quantizat… | arXiv | 2026-09-29 | primary | rtx-pro-6000 | https://arxiv.org/abs/2609.38166 |
| Less is more: learning what to profile for GPU kernel optimization | arXiv | 2026-10-27 | primary | cuda-kernel-gen | https://arxiv.org/abs/2610.36576 |
| Llumnix: Dynamic Scheduling for Large Language Model Serving | arXiv | 2024-06-05 | primary | pd-disagg | https://arxiv.org/abs/2406.03243 |
| LoongServe: Efficiently Serving Long-Context Large Language Models with Elast… | arXiv | 2024-04-15 | primary | pd-disagg | https://arxiv.org/abs/2404.09526 |
| Making LLMs Optimize Multi-Scenario CUDA Kernels Like Experts | arXiv | 2026-03-07 | primary | kernel-agent | https://arxiv.org/abs/2603.07169 |
| Masked Erosion: How Acceptance Gates Lose Redundant Safeguards in Self-Improv… | arXiv | 2026-10-28 | primary | rsi-model-training | https://arxiv.org/abs/2610.38392 |
| MaxKernel: Agentic Kernel Generation for TPUs | arXiv | 2026-09-03 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2609.04523 |
| Measuring the Checker: Mutation Analysis for GPU-Kernel Benchmark Oracles | arXiv | 2026-09-02 | primary | cuda-kernel-rl | https://arxiv.org/abs/2609.22220 |
| Measuring the Energy Cost of Completing Tasks with Quantized Language-Model A… | arXiv | 2026-10-23 | primary | rsi-quant | https://arxiv.org/abs/2610.32417 |
| Meta-Rewarding Language Models: Self-Improving Alignment with LLM-as-a-Meta-J… | arXiv | 2024-07-28 | primary | rsi-model-training | https://arxiv.org/abs/2407.19594 |
| Minima-KV: Retention-Preserving KV Cache Compression with Mixed-Format Paged … | arXiv | 2026-08-31 | primary | rtx-pro-6000 | https://arxiv.org/html/2608.23834 |
| Mitigating Model Collapse through Dreaming Learning | arXiv | 2026-10-21 | primary | rsi-model-training | https://arxiv.org/abs/2610.30009 |
| MKEvolve: A Modular Multi-Agent Framework for Kernel Code Generation | arXiv | 2026-06-20 | primary | rsi-inference | https://arxiv.org/abs/2607.20501 |
| MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering | arXiv | 2024-10-09 | primary | rsi-inference-bench | https://arxiv.org/abs/2410.07095 |
| Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | arXiv | 2024-06-24 | primary | pd-disagg | https://arxiv.org/abs/2407.00079 |
| Multi-turn RL with Structural and Performance Aware Rewards for CUDA Kernel G… | arXiv | 2026-07-23 | primary | cuda-kernel-rl, kernel-agent, rsi-inference | https://arxiv.org/abs/2607.20908 |
| MultiAlloc: Budget-Aware Precision Allocation for KV Cache Quantization | arXiv | 2026-10-13 | primary | rsi-quant | https://arxiv.org/abs/2610.18642 |
| MultiKernelBench: A Multi-Platform Benchmark for Kernel Generation | arXiv | 2025-07-20 | primary | cuda-kernel-gen | https://arxiv.org/abs/2507.17773 |
| MusaCoder: Native GPU Kernel Generation with Full-Stack Training on Moore Thr… | arXiv | 2026-06-03 | primary | cuda-kernel-rl, kernel-agent | https://arxiv.org/abs/2606.04847 |
| MXSens: Sensitivity-Aware Mixed-Precision Quantization for Efficient LLM Infe… | arXiv | 2026-07-20 | primary | rsi-quant | https://arxiv.org/abs/2607.17733 |
| Nexus:Proactive Intra-GPU Disaggregation of Prefill and Decode in LLM Serving | arXiv | 2025-07-09 | primary | pd-disagg | https://arxiv.org/abs/2507.06608 |
| NKI-Agent: Domain-Specific Fine-Tuning and Agentic Tool Use for Neuron Kernel… | arXiv | 2026-07-05 | primary | kernel-agent | https://arxiv.org/abs/2607.04395 |
| On-Policy Self-Training: Data-Free Self-Improvement in Large Language Models | arXiv | 2026-10-23 | primary | rsi-model-training | https://arxiv.org/abs/2610.32770 |
| Optimizing CUDA like a Human: Micro-Profiling Tools as Expert Surrogates for … | arXiv | 2026-06-24 | primary | cuda-kernel-gen, cuda-kernel-rl, kernel-agent, rsi-inference | https://arxiv.org/abs/2606.26453 |
| OptiML: An End-to-End Framework for Program Synthesis and CUDA Kernel Optimiz… | arXiv | 2026-02-12 | primary | kernel-agent | https://arxiv.org/abs/2602.12305 |
| PD-Swap: Prefill-Decode Logic Swapping for End-to-End LLM Inference on Edge F… | arXiv | 2025-12-12 | primary | pd-disagg | https://arxiv.org/abs/2512.11550 |
| Performance Analysis of Hardware-Accelerated 10-Bit 4:2:2 Encoding with Split… | arXiv | 2026-06-28 | primary | rtx-pro-6000 | https://arxiv.org/abs/2606.29179 |
| PostTrainBench: Can LLM Agents Automate LLM Post-Training? | arXiv | 2026-03-09 | primary | rsi-inference-bench | https://arxiv.org/abs/2603.08640 |
| PRAGMA: A Profiling-Reasoned Multi-Agent Framework for Automatic Kernel Optim… | arXiv | 2025-11-09 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2511.06345 |
| Prefill-Decode Aggregation or Disaggregation? Unifying Both for Goodput-Optim… | arXiv | 2025-08-04 | primary | pd-disagg | https://arxiv.org/abs/2508.01989 |
| Prefill/Decode-Aware Evaluation of LLM Inference on Emerging AI Accelerators | arXiv | 2026-06-14 | primary | pd-disagg | https://arxiv.org/abs/2606.17104 |
| ProofWright: Towards Agentic Formal Verification of CUDA | arXiv | 2025-11-15 | primary | cuda-kernel-rl | https://arxiv.org/abs/2511.12294 |
| Prorsa: Unleashing the Potential of Prefill-Decode Disaggregation in Agentic … | arXiv | 2026-10-12 | primary | pd-disagg | https://arxiv.org/abs/2610.16592 |
| Q-PACE: Dynamic Precision Allocation for Quantization-Aware Training | arXiv | 2026-10-06 | primary | rsi-quant | https://arxiv.org/abs/2610.09183 |
| Q-Strata: Hierarchical Bit Allocation for Mixed-Precision Quantization of Mix… | arXiv | 2026-08-31 | primary | rsi-quant | https://arxiv.org/abs/2608.30564 |
| QATFactory: A Versatile, Deployment-Aligned Framework for Quantization-aware … | arXiv | 2026-09-30 | primary | rsi-quant | https://arxiv.org/abs/2609.39223 |
| QiMeng-Kernel: Macro-Thinking Micro-Coding Paradigm for LLM-Based High-Perfor… | arXiv | 2025-11-25 | primary | cuda-kernel-gen | https://arxiv.org/abs/2511.20100 |
| QuantiBias: Benchmarking Quantization-Induced Bias in LLMs | arXiv | 2026-07-23 | primary | rsi-quant | https://arxiv.org/abs/2607.21063 |
| Quantization Error Is Spectrally Flat: A Single Random Probe Is a Calibrated,… | arXiv | 2026-09-27 | primary | rsi-quant | https://arxiv.org/abs/2609.33923 |
| Quiet-STaR: Language Models Can Teach Themselves to Think Before Speaking | arXiv | 2024-03-14 | primary | rsi-model-training | https://arxiv.org/abs/2403.09629 |
| R-Zero: Self-Evolving Reasoning LLM from Zero Data | arXiv | 2025-08-07 | primary | rsi-model-training | https://arxiv.org/abs/2508.05004 |
| RAGEN: Understanding Self-Evolution in LLM Agents via Multi-Turn Reinforcemen… | arXiv | 2025-04-24 | primary | rsi-model-training | https://arxiv.org/abs/2504.20073 |
| RaMP: Runtime-Aware Megakernel Polymorphism for Mixture-of-Experts | arXiv | 2026-04-28 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2604.26039 |
| RE-Bench: Evaluating frontier AI R&D capabilities of language model agents ag… | arXiv | 2024-11-22 | primary | rsi-inference-bench | https://arxiv.org/abs/2411.15114 |
| Recoverability and Verifier Strength: Two Measured Preconditions for Unattend… | arXiv | 2026-10-20 | primary | rsi-model-training | https://arxiv.org/abs/2610.27465 |
| Recursa: Toward Recursively Self-Improving Foundation Model Systems | arXiv | 2026-11-02 | primary | rsi-model-training | https://arxiv.org/abs/2611.04035 |
| Recursive Self-Improvement in AI: From Bounded Self-Refinement to Autonomous … | arXiv | 2026-07-08 | primary | rsi-model-training | https://arxiv.org/abs/2607.07663 |
| Reflexion: Language Agents with Verbal Reinforcement Learning | arXiv | 2023-03-20 | primary | rsi-model-training | https://arxiv.org/abs/2303.11366 |
| Reinforced Self-Training (ReST) for Language Modeling | arXiv | 2023-08-17 | primary | rsi-model-training | https://arxiv.org/abs/2308.08998 |
| ReRound: Reconstructive Rounding to Resolve Midpoint Ambiguity in Calibration… | arXiv | 2026-08-11 | primary | rsi-quant | https://arxiv.org/abs/2608.11045 |
| Revisiting Disaggregated Large Language Model Serving for Performance and Ene… | arXiv | 2025-11-14 | primary | pd-disagg | https://arxiv.org/abs/2601.08833 |
| ROCm InferaSim: Cut LLM Serving Trial Costs and Deploy the Best Configuration | arXiv | 2026-11-02 | primary | rsi-serving | https://arxiv.org/abs/2611.04032 |
| RSI Arena: Towards Recursive Self-Improvement with Human Feedback | arXiv | 2026-10-24 | primary | rsi-model-training | https://arxiv.org/abs/2610.33624 |
| RSI-Master: Structuring Experiments to Guide Autonomous Model Improvement | arXiv | 2026-09-28 | primary | rsi-inference-bench | https://arxiv.org/abs/2609.35561 |
| RSI-Opt: Recursive Self-Improvement Optimizer Agents For Model Training | arXiv | 2026-10-23 | primary | rsi-model-training | https://arxiv.org/abs/2610.32026 |
| RSIFlow: Adaptive Self-Improvement Workflows with an Evolving Meta-Agent | arXiv | 2026-10-15 | primary | rsi-inference | https://arxiv.org/abs/2610.21791 |
| RTP-LLM: High-Performance Alibaba LLM Inference Engine | arXiv | 2026-05-28 | primary | pd-disagg | https://arxiv.org/abs/2605.29639 |
| SAC: Disaggregated KV Cache System for Sparse Attention LLMs with CXL | arXiv | 2026-06-18 | primary | pd-disagg | https://arxiv.org/abs/2606.19746 |
| Same Bit Width, Different Outcomes: Post-Training Quantization of Text-to-Spe… | arXiv | 2026-09-24 | primary | rsi-quant | https://arxiv.org/abs/2609.28974 |
| Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergen… | arXiv | 2026-09-04 | primary | rsi-quant | https://arxiv.org/abs/2609.04748 |
| SARA: SLO-Aware Resource Allocation for Disaggregated Agentic LLM Services | arXiv | 2026-09-22 | primary | pd-disagg | https://arxiv.org/abs/2609.26763 |
| Saying, Not Knowing: Aggressively GGUF-Quantized Small Language Models Still … | arXiv | 2026-10-03 | primary | rsi-quant | https://arxiv.org/abs/2610.04403 |
| SEIS: Self-Evolving Inference Systems | arXiv | 2026-10-03 | primary | agent-serving-bench, rsi-serving | https://arxiv.org/abs/2610.04646 |
| Self-Adapting Language Models | arXiv | 2025-06-12 | primary | rsi-model-training | https://arxiv.org/abs/2506.10943 |
| Self-Challenging Language Model Agents | arXiv | 2025-06-02 | primary | rsi-model-training | https://arxiv.org/abs/2506.01716 |
| Self-Evolving Coding Agents via Harness-Policy Optimization | arXiv | 2026-10-16 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2610.22791 |
| Self-Improvement with Auxiliary Rewards: Learning from Verified Traces and Ev… | arXiv | 2026-10-30 | primary | rsi-model-training | https://arxiv.org/abs/2610.41296 |
| Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models | arXiv | 2024-01-02 | primary | rsi-model-training | https://arxiv.org/abs/2401.01335 |
| Self-Rewarding Language Models | arXiv | 2024-01-18 | primary | rsi-model-training | https://arxiv.org/abs/2401.10020 |
| Self-Taught Evaluators | arXiv | 2024-08-05 | primary | rsi-model-training | https://arxiv.org/abs/2408.02666 |
| semi-PD: Towards Efficient LLM Serving via Phase-Wise Disaggregated Computati… | arXiv | 2025-04-28 | primary | pd-disagg | https://arxiv.org/abs/2504.19867 |
| ServeLearnBench: How Well Can Agents Self-Improve from Serving Experience? | arXiv | 2026-10-06 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2610.07792 |
| ServerBench: How can your coding agents design specialized LLM serving system… | arXiv | 2026-11-04 | primary | agent-serving-bench | https://arxiv.org/abs/2611.06841 |
| ServeTwin: A Benchmark-Validated Simulator for Distributed LLM Architecture E… | arXiv | 2026-10-02 | primary | pd-disagg | https://arxiv.org/abs/2610.02732 |
| ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution | arXiv | 2025-09-17 | primary | rsi-model-training | https://arxiv.org/abs/2509.19349 |
| Silent Failures in Quantized LLM Reasoning: A Taxonomy-Based Analysis of Holl… | arXiv | 2026-07-10 | primary | rsi-quant | https://arxiv.org/abs/2607.09999 |
| Simthesizer: An Agent-Driven Simulation Framework for LLM Serving Systems | arXiv | 2026-08-25 | primary | agent-serving-bench | https://arxiv.org/abs/2608.24650 |
| SiriuS: Self-improving Multi-agent Systems via Bootstrapped Reasoning | arXiv | 2025-02-07 | primary | rsi-model-training | https://arxiv.org/abs/2502.04780 |
| SLO-Aware Compute Resource Allocation for Prefill-Decode Disaggregated LLM In… | arXiv | 2026-03-05 | primary | pd-disagg | https://arxiv.org/abs/2603.04716 |
| SOL-ExecBench: Speed-of-Light Benchmarking for Real-World GPU Kernels Against… | arXiv | 2026-03-19 | primary | cuda-kernel-gen | https://arxiv.org/abs/2603.19173 |
| SPAD: Specialized Prefill and Decode Hardware for Disaggregated LLM Inference | arXiv | 2025-10-09 | primary | pd-disagg | https://arxiv.org/abs/2510.08544 |
| SpecGen: Accelerating Agentic Kernel Optimization with Speculative Generation | arXiv | 2026-06-16 | primary | kernel-agent, rsi-inference | https://arxiv.org/abs/2606.17518 |
| SpecPilot: Autonomous Algorithm Discovery and Systems Optimization for Specul… | arXiv | 2026-11-02 | primary | rsi-serving, specpilot | https://arxiv.org/abs/2611.02501 |
| SpectrumKV: Per-Token Mixed-Precision KV Cache Transfer for Prefill-Decode Di… | arXiv | 2026-06-07 | primary | pd-disagg | https://arxiv.org/abs/2606.08635 |
| Splitwise: Efficient generative LLM inference using phase splitting | arXiv | 2023-11-30 | primary | pd-disagg | https://arxiv.org/abs/2311.18677 |
| SplitZip: Ultra Fast Lossless KV Compression for Disaggregated LLM Serving | arXiv | 2026-05-03 | primary | pd-disagg | https://arxiv.org/abs/2605.01708 |
| Stage-Aware Communication Scheduling for Disaggregated LLM Serving | arXiv | 2026-03-18 | primary | pd-disagg | https://arxiv.org/abs/2603.17456 |
| STaR: Bootstrapping Reasoning With Reasoning | arXiv | 2022-03-28 | primary | rsi-model-training | https://arxiv.org/abs/2203.14465 |
| STARK: Strategic Team of Agents for Refining Kernels | arXiv | 2025-10-19 | primary | cuda-kernel-gen, kernel-agent, rsi-inference | https://arxiv.org/abs/2510.16996 |
| SWE-Serve: Benchmarking Agentic Engineering for Production Inference Serving | arXiv | 2026-09-22 | primary | agent-serving-bench | https://arxiv.org/abs/2609.26777 |
| SwizzlePerf: Hardware-Aware LLMs for GPU Kernel Performance Optimization | arXiv | 2025-08-27 | primary | cuda-kernel-gen | https://arxiv.org/abs/2508.20258 |
| Taming Request Imbalance: SLO-Aware Scheduling for Disaggregated LLM Inference | arXiv | 2026-05-04 | primary | pd-disagg | https://arxiv.org/abs/2605.02329 |
| Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | arXiv | 2024-03-04 | primary | pd-disagg | https://arxiv.org/abs/2403.02310 |
| The Curse of Recursion: Training on Generated Data Makes Models Forget | arXiv | 2023-05-27 | primary | rsi-model-training | https://arxiv.org/abs/2305.17493 |
| The FM Agent | arXiv | 2025-10-30 | primary | kernel-agent | https://arxiv.org/abs/2510.26144 |
| The Illusion of Equivalency: Statistical Characterization of Quantization Eff… | arXiv | 2026-07-09 | primary | rsi-quant | https://arxiv.org/abs/2607.08734 |
| The Serialized Bridge: Understanding and Recovering LLM Serving Performance u… | arXiv | 2026-06-22 | primary | rtx-pro-6000 | https://arxiv.org/abs/2606.23969 |
| The Structure of Quantization Damage in LLMs: Why the Next Bit Should Be Spen… | arXiv | 2026-09-01 | primary | rsi-quant | https://arxiv.org/abs/2609.01587 |
| The Workload-Router-Pool Architecture for LLM Inference Optimization: A Visio… | arXiv | 2026-03-22 | primary | pd-disagg | https://arxiv.org/abs/2603.21354 |
| Threshold-Based Exclusive Batching for LLM Inference | arXiv | 2026-05-30 | primary | rtx-pro-6000 | https://arxiv.org/abs/2606.00516 |
| ThunderAgent: A Simple, Fast and Program-Aware Agentic Inference System | arXiv | 2026-02-14 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2602.13692 |
| TileQuant: Tile as the Precision-Allocation Unit for LLM Mixed-Precision Post… | arXiv | 2026-11-04 | primary | rsi-quant | https://arxiv.org/abs/2611.07217 |
| Topology-Aware Data Movement for Disaggregated GPU Inference | arXiv | 2026-04-19 | primary | pd-disagg | https://arxiv.org/abs/2607.28633 |
| Toward Training Superintelligent Software Agents through Self-Play SWE-RL | arXiv | 2025-12-21 | primary | rsi-model-training | https://arxiv.org/abs/2512.18552 |
| Towards Automated Kernel Generation in the Era of LLMs | arXiv | 2026-01-22 | primary | cuda-kernel-gen | https://arxiv.org/abs/2601.15727 |
| Towards Certificate-Driven Software Porting: A Self-Improving Agentic Harness… | arXiv | 2026-09-28 | primary | rsi-inference | https://arxiv.org/abs/2609.34069 |
| Towards Cold-Start Drafting and Continual Refining: A Value-Driven Memory App… | arXiv | 2026-03-11 | primary | cuda-kernel-rl | https://arxiv.org/abs/2603.10846 |
| Towards High-Goodput LLM Serving with Prefill-decode Multiplexing | arXiv | 2025-04-20 | primary | pd-disagg | https://arxiv.org/abs/2504.14489 |
| Towards Load-Aware Prefill Deflection for Disaggregated LLM Serving | arXiv | 2026-07-02 | primary | pd-disagg | https://arxiv.org/abs/2607.02043 |
| Towards Robust Agentic CUDA Kernel Benchmarking, Verification, and Optimizati… | arXiv | 2025-09-16 | primary | rsi-inference | https://arxiv.org/abs/2509.14279 |
| TPLA: Tensor Parallel Latent Attention for Efficient Disaggregated Prefill an… | arXiv | 2025-08-21 | primary | pd-disagg | https://arxiv.org/abs/2508.15881 |
| TraceLab: Characterizing Coding Agent Workloads for LLM Serving | arXiv | 2026-06-29 | primary | agent-serving-bench, rsi-serving | https://arxiv.org/abs/2606.30560 |
| TraCT: Disaggregated LLM Serving with CXL Shared Memory KV Cache at Rack-Scale | arXiv | 2025-12-20 | primary | pd-disagg | https://arxiv.org/abs/2512.18194 |
| Training LLM Agents to Automate LLM Post-Training with RSI-Dojo | arXiv | 2026-10-29 | primary | rsi-inference-bench | https://arxiv.org/abs/2611.03698 |
| TritonBench: Benchmarking Large Language Model Capabilities for Generating Tr… | arXiv | 2025-02-20 | primary | cuda-kernel-gen | https://arxiv.org/abs/2502.14752 |
| TritonRL: Training LLMs to Think and Code Triton Without Cheating | arXiv | 2025-10-18 | primary | cuda-kernel-gen, cuda-kernel-rl | https://arxiv.org/abs/2510.17891 |
| Trustworthy Recursive Self-Improvement in the Era of Large Models: Foundation… | arXiv | 2026-10-26 | primary | rsi-model-training | https://arxiv.org/abs/2610.35193 |
| V-STaR: Training Verifiers for Self-Taught Reasoners | arXiv | 2024-02-09 | primary | rsi-model-training | https://arxiv.org/abs/2402.06457 |
| Verify Less, Evolve More: Training Idea-Level Critics for Verification-Effici… | arXiv | 2026-10-06 | primary | rsi-inference, rsi-serving | https://arxiv.org/abs/2610.08993 |
| VibeServe: Can AI Agents Build Bespoke LLM Serving Systems? | arXiv | 2026-05-07 | primary | agent-serving-bench, rsi-serving | https://arxiv.org/abs/2605.06068 |
| Voyager: An Open-Ended Embodied Agent with Large Language Models | arXiv | 2023-05-25 | primary | rsi-model-training | https://arxiv.org/abs/2305.16291 |
| When Calibration Depends on the Scoring Rule: Quantized Biomedical LLM Classi… | arXiv | 2026-08-04 | primary | rsi-quant | https://arxiv.org/abs/2608.03854 |
| When Does Disaggregation Pay? Simulating Prefill--Decode--Attention--FFN Spec… | arXiv | 2026-08-04 | primary | pd-disagg | https://arxiv.org/abs/2608.03741 |
| When LLMs Modify Themselves: Convergence, Values, and Stopping in Iterative S… | arXiv | 2026-10-31 | primary | rsi-model-training | https://arxiv.org/abs/2611.01304 |
| Where Does the Energy Go? Profiling LLM Agent Inference on Blackwell GPUs | arXiv | 2026-08-31 | primary | rtx-pro-6000 | https://arxiv.org/abs/2609.29707 |
| Why Self-Rewarding Works: Theoretical Guarantees for Iterative Alignment of L… | arXiv | 2026-01-30 | primary | rsi-model-training | https://arxiv.org/abs/2601.22513 |
| XFP: Quality-Targeted Adaptive Codebook Quantization with Sparse Outlier Sepa… | arXiv | 2026-05-14 | primary | rtx-pro-6000 | https://arxiv.org/abs/2605.14844 |
| NAMD 3.0.2 - GPU-offload Performance: stmv benchmark（两次下载超时，PDF 0 页） | epubs.stfc.ac.uk | — | primary | rtx-pro-6000 | https://epubs.stfc.ac.uk/manifestation/64246471/STFC-CONF-2026-003.pdf |
| FastH3 NVFP4 on RTX PRO 6000 (sm120) | haoailab.com | 2026-08-01 | primary | rtx-pro-6000 | https://haoailab.com/FastVideo/inference/fasth3_rtx_pro_6000/ |
| RTX PRO 6000 Blackwell FP16 End-to-End Baseline（2026-06-08） | hongping-zh.github.io | 2026-06-08 | primary | rtx-pro-6000 | https://hongping-zh.github.io/updates/2026-06-08-rtx-pro6000-fp16-e2e/ |
| RTX PRO 6000 Blackwell: Phase-Separated Energy Profiling（2026-06-03） | hongping-zh.github.io | 2026-06-03 | primary | rtx-pro-6000 | https://hongping-zh.github.io/updates/2026-06-03-rtx-pro6000-blackwell-phase/ |

### 官方（厂商或项目自己的文档）（`official`，82 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| cuda, hip: GDN chunked kernel | GitHub | 2026-09-24 | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/pull/29353 |
| DeepSeek-V4.1-Flash on Ascend NPU | GitHub | 2026-10-01 | primary | pro6000se-dsv41 | https://github.com/vllm-project/vllm-ascend/blob/main/docs/source/tutorials/models/DeepSeek-V4.1-Flash.md |
| DeepSeek: 3FS | GitHub | — | primary | pd-disagg | https://github.com/deepseek-ai/3FS |
| DeepSeek: open-infra-index | GitHub | — | primary | pd-disagg | https://github.com/deepseek-ai/open-infra-index |
| feat(recipes): declare RTX PRO 6000 Server Edition driver floor | GitHub | 2026-08-28 | primary | rtx-pro-6000 | https://github.com/NVIDIA/aicr/pull/2446 |
| Improving DeepEP MoE Load Balance in SGLang with Waterfill and LPLB | GitHub | 2026-06-26 | primary | pd-disagg | https://github.com/bojieli/ai-infra-book/blob/b069b6971faf6c4701b57a8b025462b9f2694b8f/references/framework-history/2026-09-08/ep-reconfiguration/sglang-waterfill-lplb-2026.md |
| LMCache | GitHub | — | primary | pd-disagg | https://github.com/LMCache/LMCache |
| Mooncake: KVCache-centric Disaggregated Architecture | GitHub | — | primary | pd-disagg | https://github.com/kvcache-ai/Mooncake |
| NVIDIA AI Blueprints RAG — MIG 切片 Helm 配置（RTX PRO 6000 SE） | GitHub | — | primary | rtx-pro-6000 | https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/deploy/helm/mig-slicing/values-mig-rtx6000.yaml |
| NVIDIA: NIXL (Inference Xfer Library) | GitHub | — | primary | pd-disagg | https://github.com/ai-dynamo/nixl |
| One million tokens prompt club · Discussion #24622 | GitHub | — | primary | rtx-pro-6000 | https://github.com/ggml-org/llama.cpp/discussions/24622 |
| RSI-Inference Bench README：赛道定义、评分工序、仓库入口 | GitHub | 2026-10-16 | primary | rsi-inference-bench | https://github.com/apple-aiml-research/ml-rsi-inference-bench |
| SpecPilot: engines, configs, model links and scripts for six settings | GitHub | 2026-11-02 | primary | specpilot | https://github.com/StargazerX0/SpecPilot |
| Studio: gate GGML_CUDA_P2P on a confirmed NVLink fabric, not a product name | GitHub | 2026-09-09 | primary | rtx-pro-6000 | https://github.com/unslothai/unsloth/pull/10646 |
| vLLM: Dual Batch Overlap (DBO) 设计文档 | GitHub | — | primary | pd-disagg | https://github.com/vllm-project/vllm/blob/main/docs/design/dbo.md |
| DeepSeek-V4.1-Flash model card (KV cache compression) | Hugging Face | 2026-09-10 | primary | pro6000se-dsv41 | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash |
| DeepSeek-V4.1-Flash Technical Report | Hugging Face | 2026-09-10 | primary | pro6000se-dsv41 | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf |
| facebook/KernelLLM model card | Hugging Face | 2025-06-30 | primary | cuda-kernel-gen | https://huggingface.co/facebook/KernelLLM |
| GPU Performance and Sharing Characteristics — RTX vWS Sizing Guide | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/vgpu/sizing/virtual-workstation/latest/right-gpu.html |
| Hardware-Rooted AI Security That Won't Slow You Down | NVIDIA | 2026-07-02 | primary | rtx-pro-6000 | https://developer.nvidia.com/blog/hardware-rooted-ai-security-that-wont-slow-you-down/ |
| List of NVIDIA-Certified Systems（官方认证系统完整清单，含 RTX PRO 6000 Server Edition 条目） | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/certification-programs/latest/nvidia-certified-systems.html |
| MIG User Guide — Getting Started with MIG（含 RTX PRO Blackwell 附加前提） | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/getting-started-with-mig.html |
| MIG User Guide — Supported GPUs | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/supported-gpus.html |
| NVIDIA Data Center Drivers — Driver Lifecycle | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/datacenter/tesla/drivers/latest/driver-lifecycle.html |
| NVIDIA Data Center Drivers — Supported Drivers and CUDA Toolkit Versions | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/datacenter/tesla/drivers/latest/supported-drivers-and-cuda-toolkit-versions.html |
| NVIDIA Dynamo Documentation | NVIDIA | — | primary | pd-disagg | https://docs.nvidia.com/dynamo/ |
| NVIDIA RTX PRO AI Factory — Appendix (BOM/交换机/线缆) | NVIDIA | 2026-05-18 | primary | rtx-pro-6000 | https://docs.nvidia.com/enterprise-reference-architectures/rtx-pro-ai-factory/latest/appendix.html |
| NVIDIA RTX PRO AI Factory — Components | NVIDIA | 2026-05-18 | primary | rtx-pro-6000 | https://docs.nvidia.com/enterprise-reference-architectures/rtx-pro-ai-factory/latest/components.html |
| NVIDIA RTX PRO AI Factory — Networking Physical Topologies | NVIDIA | 2026-05-18 | primary | rtx-pro-6000 | https://docs.nvidia.com/enterprise-reference-architectures/rtx-pro-ai-factory/latest/networking-physical-topologies.html |
| NVIDIA RTX PRO AI Factory — Overview | NVIDIA | 2026-05-18 | primary | rtx-pro-6000 | https://docs.nvidia.com/enterprise-reference-architectures/rtx-pro-ai-factory/latest/overview.html |
| NVIDIA RTX PRO AI Factory — Software | NVIDIA | 2026-05-18 | primary | rtx-pro-6000 | https://docs.nvidia.com/enterprise-reference-architectures/rtx-pro-ai-factory/latest/software.html |
| NVIDIA RTX PRO Blackwell GPU Architecture（v1.1，49 页，含附录 A 完整规格表） | NVIDIA | — | primary | rtx-pro-6000 | https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/quadro-product-literature/pdf/NVIDIA-RTX-Blackwell-PRO-GPU-Architecture-v1_1.pdf |
| NVIDIA RTX PRO Server | NVIDIA | — | primary | rtx-pro-6000 | https://www.nvidia.com/en-us/data-center/products/rtx-pro-server.md |
| NVIDIA Virtual GPU Software Packaging, Pricing, and Licensing Guide (DA-09924… | NVIDIA | 2024-08-01 | primary | rtx-pro-6000 | https://www.nvidia.com/content/dam/en-zz/Solutions/design-visualization/solutions/resources/documents1/Virtual-GPU-Packaging-and-Licensing-Guide.pdf |
| NVIDIA Virtual GPU Software — Validated Platforms（VMware vSphere 发布说明） | NVIDIA | — | primary | rtx-pro-6000 | https://docs.nvidia.com/vgpu/latest/grid-vgpu-release-notes-vmware-vsphere/validated-platforms.html |
| RMA Policy — Thresholds for Row Remapping | NVIDIA | 2026-10-01 | primary | rtx-pro-6000 | https://docs.nvidia.com/deploy/a100-gpu-mem-error-mgmt/615/rma-policy-thresholds-for-row-remapping.html |
| RTX PRO 6000 Blackwell Max-Q Workstation Edition | NVIDIA | — | primary | rtx-pro-6000 | https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000-max-q/ |
| RTX PRO 6000 Blackwell Server Edition | NVIDIA | 2025-03-18 | primary | pro6000se-dsv41 | https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/ |
| RTX PRO 6000 Blackwell Server Edition | NVIDIA | — | primary | rtx-pro-6000 | https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition.md |
| RTX PRO 6000 Blackwell Workstation Edition | NVIDIA | 2025-03-18 | primary | pro6000se-dsv41, rtx-pro-6000 | https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/ |
| Sparks Fly: NVIDIA Accelerates Local AI at IFA 2026 | NVIDIA | 2026-09-03 | primary | rtx-pro-6000 | https://blogs.nvidia.com/blog/local-ai-ifa-next-gen-agents-nv-pair-rtx-spark/ |
| Where AI and Graphics Converge: NVIDIA Blackwell Universal Data Center GPU | NVIDIA | 2025-03-18 | primary | rtx-pro-6000 | https://blogs.nvidia.com/blog/rtx-pro-6000-blackwell-server-edition/ |
| RTX 6000 Pro Server power limit of 450W instead of expected 600W | NVIDIA 开发者论坛 | 2025-09-15 | primary | rtx-pro-6000 | https://forums.developer.nvidia.com/t/rtx-6000-pro-server-power-limit-of-450w-instead-of-expected-600w/345003 |
| DeepSeek-V4.1 — SGLang cookbook | SGLang | 2026-09-15 | primary | pro6000se-dsv41 | https://docs.sglang.io/cookbook/autoregressive/DeepSeek/DeepSeek-V4_1 |
| SGLang: EPD Disaggregation | SGLang | — | primary | pd-disagg | https://docs.sglang.io/docs/advanced_features/epd_disaggregation |
| SGLang: Expert Parallelism（含 TBO / SBO 官方定义） | SGLang | — | primary | pd-disagg | https://docs.sglang.io/docs/advanced_features/expert_parallelism |
| SGLang: KV Cache Sharing | SGLang | — | primary | pd-disagg | https://docs.sglang.io/docs/advanced_features/kv_cache_sharing |
| SGLang: PD Disaggregation | SGLang | — | primary | pd-disagg | https://docs.sglang.io/docs/advanced_features/pd_disaggregation |
| SPECviewperf 15 Results Overview | SPEC | 2026-04-30 | primary | rtx-pro-6000 | https://www.spec.org/gwpg/gpc.data/viewperf15/ |
| SPECviewperf 15.0 Results - LENOVO ThinkStation P8 / RTX PRO 6000 4K | SPEC | 2025-11-12 | primary | rtx-pro-6000 | https://www.spec.org/gwpg/gpc.data/viewperf15/lenovo/P8_9965WX_RTX_PRO_6000_4K/results.html |
| SPECviewperf 15.0 官方结果 — Lenovo ThinkStation P3 Tower Gen2 / RTX PRO 6000 / F… | SPEC | — | primary | rtx-pro-6000 | https://www.spec.org/gwpg/gpc.data/viewperf15/lenovo/P3_TWR_G2_Ultra_9_285K_RTX_PRO_6000_FHD/results.html |
| Ansys GPU Compute Capabilities — Release 2026 R1（官方 GPU 求解器支持矩阵） | ansys.com | — | primary | rtx-pro-6000 | https://www.ansys.com/content/dam/it-solutions/platform-support/2026-r1/ansys-2026-r1-gpu-compute-capabilities.pdf |
| DeepSeek-V4.1-Flash: Smarter, Faster, More Efficient | api-docs.deepseek.com | 2026-09-10 | primary | pro6000se-dsv41 | https://api-docs.deepseek.com/news/news260910.md |
| Models & Pricing | api-docs.deepseek.com | 2026-09-10 | primary | pro6000se-dsv41 | https://api-docs.deepseek.com/quick_start/pricing |
| Computing Projections for NERSC/S3DF | confluence.slac.stanford.edu | 2026-10-20 | primary | rtx-pro-6000 | https://confluence.slac.stanford.edu/spaces/PSDMInternal/pages/716922293/Computing+Projections+for+NERSC+S3DF |
| DeepInfra Blog | deepinfra.com | — | secondary | pd-disagg | https://deepinfra.com/blog |
| 发布草稿（freepublish/submit） | developers.weixin.qq.com | — | primary | multi-platform-publish | https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_submit |
| 新增草稿（draft/add） | developers.weixin.qq.com | — | primary | multi-platform-publish | https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add |
| NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition データシート | elsa-jp.co.jp | — | primary | rtx-pro-6000 | https://www.elsa-jp.co.jp/wp-content/uploads/2025/03/Datasheet_NVIDIA_RTX_PRO_6000_Blackwell_Max-Q_Workstation_Edition.pdf |
| NVIDIA RTX PRO 6000 Blackwell Server Edition データシート（2026-04-08） | elsa-jp.co.jp | — | primary | rtx-pro-6000 | https://www.elsa-jp.co.jp/wp-content/uploads/2026/04/NVIDIA_RTX_PRO_6000_Server_Edition_Datasheet.pdf |
| Run Siemens NX using NVIDIA RTX PRO 6000 Blackwell GPUs on Azure Virtual Desk… | learn.microsoft.com | — | primary | rtx-pro-6000 | https://learn.microsoft.com/en-us/industry/manufacturing/architecture/siemens-azure-blackwell |
| Dassault Systèmes: Windows 11 64-bit Certified Workstation List（含 RTX PRO 600… | media.3ds.com | — | primary | rtx-pro-6000 | https://media.3ds.com/support/certified_hardware/Windows_11_64-bit.html |
| MLCommons Sets Participation Record with New MLPerf Inference v6.1 Benchmark … | mlcommons.org | 2026-09-16 | primary | rtx-pro-6000 | https://mlcommons.org/2026/09/mlperf-inference-v6-1-results/ |
| TensorRT-LLM: Disaggregated Serving | nvidia.github.io | — | primary | pd-disagg | https://nvidia.github.io/TensorRT-LLM/features/disagg-serving.html |
| NVIDIA Blackwell RTX PRO Comes to Workstations and Servers | nvidianews.nvidia.com | 2025-03-18 | primary | rtx-pro-6000 | https://nvidianews.nvidia.com/news/nvidia-blackwell-rtx-pro-workstations-servers-agentic-ai |
| 开放平台 API 文档导航（/api/doc/list） | open.xiaohongshu.com | — | primary | multi-platform-publish | https://open.xiaohongshu.com/api/doc/list |
| Blender Benchmark Script 3.1.1（官方基准脚本源码） | opendata.blender.org | 2026-10-27 | primary | rtx-pro-6000 | https://opendata.blender.org/cdn/BlenderBenchmark2.0/script/blender-benchmark-script-3.1.1.tar.gz |
| Blender Open Data 全量快照 opendata-2026-10-27（434,774 行 / 1,040,927 条记录 / 1.8GB） | opendata.blender.org | 2026-10-27 | primary | rtx-pro-6000 | https://opendata.blender.org/snapshots/opendata-latest.zip |
| Blender 官方 issue #147954（Cycles 基准场景 GPU 占用率）与 #150282（5.0 重型场景翻倍） | projects.blender.org | 2025-10-13 | primary | rtx-pro-6000 | https://projects.blender.org/blender/blender/issues/147954 |
| Serving DeepSeek-V4 on GB300 with SGLang | pytorch.org | 2026-11-04 | primary | pd-disagg | https://pytorch.org/blog/serving-deepseek-v4-on-gb300-with-sglang-5x-higher-throughput-at-the-same-interactivity-since-day-0/ |
| OctaneBench 2025.2 Results（官方结果数据库，含多 GPU 配置） | render.otoy.com | 2026-10-27 | primary | rtx-pro-6000 | https://render.otoy.com/octanebench/results.php |
| AMD Instinct MI350 Series microarchitecture | rocm.docs.amd.com | 2026-10-01 | primary | rtx-pro-6000 | https://rocm.docs.amd.com/en/latest/reference/gpu-arch/mi350.html |
| SpecPilot project page | stargazerx0.github.io | 2026-11-02 | secondary | specpilot | https://stargazerx0.github.io/specpilot-project-page/ |
| Adaptive Verification in vLLM: DSpark confidence-scheduled verification | vLLM | 2026-08-14 | primary | pd-disagg | https://vllm.ai/blog/2026-08-14-dspark-adaptive-verification |
| vLLM Large Scale Serving: DeepSeek @ 2.2k tok/s/H200 with Wide-EP | vLLM | 2025-12-17 | primary | pd-disagg | https://vllm.ai/blog/2025-12-17-large-scale-serving |
| vLLM x AgentX: Optimizing for Real-World Agentic Serving | vLLM | 2026-09-08 | primary | pd-disagg | https://vllm.ai/blog/2026-09-08-vllm-agentx |
| vLLM: Disaggregated Prefilling | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/features/disagg_prefill/ |
| vLLM: KV Transfer Config | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/api/vllm/config/kv_transfer/ |
| vLLM: Mooncake Connector 使用 | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/features/mooncake_connector_usage/ |
| vLLM: NIXL KV Cache Lease 设计 | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/design/nixl_kv_cache_lease/ |
| vLLM: NIXL KV Push Connector 设计 | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/design/nixl_kv_push_connector/ |
| vLLM: Optimization and Tuning | vLLM | — | primary | pd-disagg | https://docs.vllm.ai/en/latest/configuration/optimization/ |

### 独立第三方（媒体 / 独立评测）（`independent`，44 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| PassMark Videocard Benchmark — RTX PRO 6000 Blackwell Server Edition（G3D Mark… | 216.146.218.45 | — | primary | rtx-pro-6000 | http://216.146.218.45/gpu.php?gpu=RTX+PRO+6000+Blackwell+Server+Edition&id=6962 |
| `scripts/_zz37b.py`（证据密度的字节归一审计脚本） | GitHub | — | primary | rtx-pro-6000 | https://github.com/taishan1994/DeepResearchRSI/blob/main/scripts/_zz37b.py |
| `vllm-vs-sglang.md`（4,414 字节，108 行）—— 🔥🔥🔥🔥🔥 **vLLM 0.17.0rc1 与 SGLang 0.5.9 在… | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/benchmarks/inference-throughput/vllm-vs-sglang.md |
| B70 ECC and usable VRAM：ECC 开关到底是容量收益还是带宽收益 | GitHub | 2026-06-01 | primary | rtx-pro-6000 | https://github.com/steveseguin/b70-optimization-lab/blob/main/learn/b70-ecc-and-vram.html |
| Blackwell datacenter image compatibility (B200 sm_100 / B300 sm_103) | GitHub | 2026-08-03 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/nebius/nebius-physical-ai/refs/heads/main/docs/workbench/blackwell-datacenter-image-compatibility.md |
| FlashAttention 4 on RTX PRO 6000 | GitHub | 2026-09-28 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/nebius/nebius-physical-ai/refs/heads/main/docs/workbench/flash-attention.md |
| GLM-5.2 EXL3 四卡复现包：250W 功耗封顶下的热特性与 C1/C2/C4 连续扫描 | GitHub | 2026-07-30 | primary | rtx-pro-6000 | https://github.com/0xSero/glm52-exl3-4x-rtx-pro-6000 |
| MTP Quality Evaluation：MTP 是否影响模型精度（GPQA Diamond / GSM8K，双引擎） | GitHub | 2026-03-13 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/mtp-quality-evaluation.md |
| perf(moe): extend bounded SM120 BF16 TC decode through eight tokens | GitHub | 2026-08-20 | primary | rtx-pro-6000 | https://github.com/flashinfer-ai/flashinfer/pull/7190 |
| Qwen TP2 decode：Max-Q 双卡上社区 SGLang 与 LIL vLLM 的对照 | GitHub | 2026-09-22 | primary | rtx-pro-6000 | https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/qwen38-tp2-sglang.md |
| Qwen3-Coder-Next-FP8 单卡 Server Edition：128K 模型长度 / 48 并发 vLLM 基准 | GitHub | 2026-03-05 | primary | rtx-pro-6000 | https://github.com/cloudrift-ai/emmy/blob/298b7255fc4236b00937fd75fd3766a0f3f50f0e/experiments/Qwen3-Coder-Next-FP8/optimal_mcr_pro6000_vllm/2026-03-05_01-15-36_a64f1bc9/pro6000x1_mc48_np80_mcr48_vllm_benchmark.txt |
| RTX FA4 optimization and FA2 comparison — September 30, 2026 | GitHub | 2026-09-30 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/nebius/nebius-physical-ai/refs/heads/main/docs/workbench/fa4-rtx-optimization.md |
| sm_120 Image Catalog | GitHub | 2026-08-03 | primary | rtx-pro-6000 | https://raw.githubusercontent.com/nebius/nebius-physical-ai/refs/heads/main/docs/workbench/sm120-image-catalog.md |
| 本数据集证据强度分布自审计（第二十七轮） | GitHub | 2026-10-27 | primary | rtx-pro-6000 | https://github.com/taishan1994/DeepResearchRSI/blob/main/research/rtx-pro-6000/claims.csv |
| fp64-emu：在整数张量核心上用余数系仿真 FP64 GEMM（RARE） | Hugging Face | 2026-09-01 | primary | rtx-pro-6000 | https://huggingface.co/kernels/phanerozoic/fp64-emu |
| One vLLM flag doubled the concurrency a single card holds | Hugging Face | 2026-09-15 | primary | rtx-pro-6000 | https://huggingface.co/blog/ecohash-ai/one-vllm-flag-doubled-the-concurrency-a-single-car |
| Qwen3.8-27B EXL3 K5/K6 — serialized attention, v5 body-only KL evidence | Hugging Face | 2026-09-08 | primary | rtx-pro-6000 | https://huggingface.co/malaiwah/Qwen3.8-27B-EXL3-K5K6-hydrated |
| Best GPU for architectural visualization in 2026: real numbers from a working… | archvizdaily.com | 2026-07-11 | primary | rtx-pro-6000 | https://archvizdaily.com/posts/best-gpu-for-archviz-2026 |
| HAMi Dynamic MIG on RTX PRO 6000: A Live Kubernetes Test | blog.kubesimplify.com | 2026-08-11 | primary | rtx-pro-6000 | https://blog.kubesimplify.com/dynamic-mig-in-kubernetes-with-hami |
| Ansys Fluent GPU Benchmark with DRD & Exxact | exxactcorp.com | — | primary | rtx-pro-6000 | https://www.exxactcorp.com/blog/benchmarks/ansys-fluent-gpu-benchmark-with-drd-exxact |
| LoRA Fine Tuning Benchmark on NVIDIA RTX PRO Blackwell GPUs | exxactcorp.com | — | primary | rtx-pro-6000 | https://www.exxactcorp.com/blog/benchmark/lora-fine-tuning-benchmark-on-nvidia-gpus |
| 【全网首份】价值百元的RTX 6000D与RTX Pro 6000实测对比 | fjiang.blog.csdn.net | 2026-07-14 | primary | rtx-pro-6000 | https://fjiang.blog.csdn.net/article/details/162849417 |
| GLM-5.3-Flash on RTX PRO 6000: TP2 Benchmarks on 2, 4 or 8 GPUs | helixml.tech | 2026-09-14 | primary | rtx-pro-6000 | https://helixml.tech/blog/glm53-flash-tp2-rtx-pro-6000 |
| Alphacool: 1-Slot Water Coolers for RTX PRO and Radeon AI PRO | igorslab.de | 2026-10-08 | secondary | rtx-pro-6000 | https://www.igorslab.de/en/alphacool-announces-1-slot-water-block-rtx-pro-blackwell-radeon-ai-pro/ |
| AI Chips for LLM Inference: Specs, Pricing & Benchmarks | inferencex.semianalysis.com | — | primary | rtx-pro-6000 | https://inferencex.semianalysis.com/chips |
| Qwen 3.5 397B-A17B — GB300 NVL72 与 RTX PRO 6000 每美元性能 | inferencex.semianalysis.com | — | primary | rtx-pro-6000 | https://inferencex.semianalysis.com/zh/compare-per-dollar/qwen-3-5-gb300-vs-rtx6000pro |
| Qwen 3.5 397B-A17B — H200 vs RTX PRO 6000 — Performance per Dollar | inferencex.semianalysis.com | 2026-07-31 | primary | rtx-pro-6000 | https://inferencex.semianalysis.com/compare-per-dollar/qwen-3-5-h200-vs-rtx6000pro |
| TRT-LLM vs vLLM vs llama.cpp on Blackwell（RTX PRO 6000 上的四引擎同条件对比） | jared-hpc.com | 2026-06-28 | primary | rtx-pro-6000 | https://jared-hpc.com/posts/four-inference-engines-blackwell-qwen3-moe/ |
| Chasing an 8% Decode Regression in vLLM Nightlies on Desktop Blackwell | joshua8.ai | 2026-04-13 | primary | rtx-pro-6000 | https://joshua8.ai/vllm-nightly-decode-regression-qwen35/ |
| Do LLM Inference Engines Actually Get Faster With Updates? | joshua8.ai | 2026-02-15 | primary | rtx-pro-6000 | https://joshua8.ai/llm-inference-benchmark-update/ |
| Running LLMs on NVIDIA Blackwell: vLLM, SGLang, and NVFP4 | joshua8.ai | — | primary | rtx-pro-6000 | https://joshua8.ai/blackwell-inference/ |
| Running MiniMax-M2.5 on a Single RTX 6000 Blackwell: 68 Tokens/s with 64K Con… | joshua8.ai | 2026-02-28 | primary | rtx-pro-6000 | https://joshua8.ai/minimax-m25-rtx-6000-blackwell-sglang-guide/ |
| Twice as Fast on the Same Card: Eight Weeks Later — Qwen3.8-Flash-Next on an … | joshua8.ai | 2026-10-22 | primary | rtx-pro-6000 | https://joshua8.ai/qwen38-flash-next-penny-royal-rtx-pro-6000/ |
| vLLM v0.16.0 Delivers Up to 20% Higher Throughput on Blackwell GPUs | joshua8.ai | 2026-02-25 | primary | rtx-pro-6000 | https://joshua8.ai/vllm-v016-blackwell-throughput-benchmark/ |
| Why Speculative Decoding Didn't Speed Up My 120B Model | joshua8.ai | 2025-12-12 | primary | rtx-pro-6000 | https://joshua8.ai/speculative-decoding-experiment/ |
| I Bought an RTX Pro 6000 from Provantage. Here's What Was Actually Inside. | joshuaodmark.com | 2026-06-11 | primary | rtx-pro-6000 | https://joshuaodmark.com/blog/provantage-counterfeit-rtx-pro-6000 |
| The Gen1 Revelation: A Single Diagnostic Command That Exposed the Full Scope … | magik.net | — | primary | rtx-pro-6000 | https://magik.net/blog/llmopt/seg_3/chunk_2/the_gen1_revelation.html |
| GROMACS Benchmark（Server / Max-Q / RTX 5090 三平台对照） | pub.hpc-technologies.co.jp | 2025-12-19 | primary | rtx-pro-6000 | https://pub.hpc-technologies.co.jp/hpc-benchmark/gromacs-benchmark/ |
| LAMMPS Benchmark（LJ liquid，RTX PRO 6000 SE 单卡） | pub.hpc-technologies.co.jp | 2025-09-18 | primary | rtx-pro-6000 | https://pub.hpc-technologies.co.jp/hpc-benchmark/lammps-benchmark/ |
| Llama 3 8B LoRA 微调实测（RTX PRO 6000 Blackwell Server Edition） | pub.hpc-technologies.co.jp | 2025-09-29 | primary | rtx-pro-6000 | https://pub.hpc-technologies.co.jp/hpc-benchmark/nvidia-rtx-pro-6000-blackwell-server-edition-gpu-llama-finetuning-benchmark/ |
| GPUs (graphics processing units) from China: 50% import duty (HTS 8542.31.00.… | tariff.gatewaylines.com | 2026-10-27 | secondary | rtx-pro-6000 | https://tariff.gatewaylines.com/examples/gpus-graphics-processing-units-8542-31-00-40-from-china |
| GPUs (graphics processing units) from Taiwan: 0% import duty (HTS 8542.31.00.… | tariff.gatewaylines.com | 2026-10-27 | secondary | rtx-pro-6000 | https://tariff.gatewaylines.com/examples/gpus-graphics-processing-units-8542-31-00-40-from-taiwan |
| GPU Database: NVIDIA RTX PRO 6000（请求被反爬替换为诱饵页） | techpowerup.com | — | primary | rtx-pro-6000 | https://www.techpowerup.com/gpu-specs/rtx-pro-6000.c4290 |
| 70 条速度声明的逐条可比性判定审计表 | 本仓库（自建产物） | 2026-11-03 | primary | cuda-kernel-gen | `research/cuda-kernel-gen/claims_audit.csv`（仓库内文件） |

### 厂商（产品与营销材料）（`vendor`，39 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| `nvidia-cutlass-dsl` 4.5.0: `nvvm.mma.block_scale` lowering produces PTX reje… | GitHub | 2026-05-11 | primary | rtx-pro-6000 | https://github.com/NVIDIA/cutlass/issues/3227 |
| ArtiPub AI README | GitHub | — | primary | multi-platform-publish | https://github.com/crawlab-team/artipub/blob/master/README.md |
| Bonsai-demo `README.md`（24,840 字节，529 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/README.md |
| btl-lab `btl_lab/advance.py`（9,866 字节，161 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/advance.py |
| btl-lab `btl_lab/measure.py`（6,711 字节，116 行） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/Badtheorylabs/btl-lab/main/btl_lab/measure.py |
| Feature Request: Support sm_120 (5090 and blackwell 6000 pro)（issue #236，29 评… | GitHub | 2025-12-01 | primary | rtx-pro-6000 | https://github.com/deepseek-ai/DeepGEMM/issues/236 |
| Integrate main APIs and SM120 kernels while preserving nv_dev features（PR #44… | GitHub | 2026-09-15 | primary | rtx-pro-6000 | https://github.com/deepseek-ai/DeepGEMM/pull/447 |
| NCCL 2.30.4 NVLS 回归：高专家数 MoE 在无 NVLink 硬件上权重加载阶段挂死（issue #2167，由 vllm#40969 上… | GitHub | 2026-05-10 | primary | rtx-pro-6000 | https://github.com/NVIDIA/nccl/issues/2167 |
| Omniperf: NVIDIA B200 (Blackwell) 基准数据集 | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://media.githubusercontent.com/media/NVIDIA/omniperf/main/docs/data/b200.json |
| Omniperf: NVIDIA L40 (ADA) 基准数据集 | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://media.githubusercontent.com/media/NVIDIA/omniperf/main/docs/data/l40_ada.json |
| Omniperf: NVIDIA RTX PRO 6000 Blackwell SE 基准数据集 | GitHub | 2026-03-17 | primary | rtx-pro-6000 | https://media.githubusercontent.com/media/NVIDIA/omniperf/main/docs/data/rtx_pro_6000.json |
| Running DeepSeek R1 on 8x RTX 6000 PRO（issue #5581，label: not a bug，24 评论，202… | GitHub | 2025-06-29 | primary | rtx-pro-6000 | https://github.com/NVIDIA/TensorRT-LLM/issues/5581 |
| Ternary Bonsai 2 27B 白皮书（14 页，366,237 字节，2026-09） | GitHub | — | primary | rtx-pro-6000 | https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/bonsai-2-27b-whitepaper.pdf |
| 掘金 MCP 服务器 README | GitHub | — | primary | multi-platform-publish | https://github.com/iceycn/juejin-release-mcp/blob/main/README.md |
| 文章同步助手（Wechatsync）README | GitHub | 2026-03-24 | primary | multi-platform-publish | https://github.com/wechatsync/Wechatsync/blob/v2/README.md |
| `prism-ml/Ternary-Bonsai-2-27B-gguf` KNOWN_ISSUES.md（17,107 字节，191 行） | Hugging Face | — | primary | rtx-pro-6000 | https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/KNOWN_ISSUES.md |
| `prism-ml/Ternary-Bonsai-2-27B-gguf` 模型卡（23,200 字节，312 行） | Hugging Face | — | primary | rtx-pro-6000 | https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md |
| NVIDIA RTX 6000 Blackwell Server Edition: Tests, Benchmarks & Comparison | Hugging Face | 2025-08-30 | primary | rtx-pro-6000 | https://huggingface.co/blog/HOSTKEY/nvidia-rtx-6000-blackwell-server-edition-tests-ben |
| What 96 GB on one card actually buys you | Hugging Face | 2026-09-14 | primary | rtx-pro-6000 | https://huggingface.co/blog/ecohash-ai/what-96-gb-on-one-card-actually-buys-you |
| Advanced Sensor Physics, Customization, and Model Benchmarking Coming to NVID… | NVIDIA | 2025-05-18 | primary | rtx-pro-6000 | https://developer.nvidia.com/blog/advanced-sensor-physics-customization-and-model-benchmarking-coming-to-nvidia-isaac-sim-and-nvidia-isaac-lab/ |
| Cadence Taps NVIDIA Blackwell to Accelerate AI-Driven Engineering Design and … | NVIDIA | 2025-05-07 | primary | rtx-pro-6000 | https://blogs.nvidia.com/blog/cadence-millennium-nvidia-blackwell/ |
| NVIDIA Blackwell and NVIDIA CUDA 12.9 Introduce Family-Specific Architecture … | NVIDIA | 2025-05-01 | primary | rtx-pro-6000 | https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/ |
| NVIDIA vGPU 19.0 Enables Graphics and AI Virtualization on NVIDIA Blackwell G… | NVIDIA | 2025-08-05 | primary | rtx-pro-6000 | https://developer.nvidia.com/blog/nvidia-vgpu-19-0-enables-graphics-and-ai-virtualization-on-nvidia-blackwell-gpus/ |
| Which NVIDIA Blackwell GPU Delivers the Best Fluent ROI? | ansys.synopsys.com | — | primary | rtx-pro-6000 | https://ansys.synopsys.com/fr-fr/blog/which-nvidia-blackwell-gpu-delivers-best-fluent-roi |
| RTX PRO 6000 Blackwell Workstation Edition rendering benchmarks: Blender, Oct… | blendercloudrender.com | — | primary | rtx-pro-6000 | https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-pro-6000-blackwell-workstation-edition |
| Bykski GPU Water Block For NVIDIA RTX Pro 6000, All Metal Structure, N-RTXPRO… | formulamod.net | 2026-10-27 | primary | rtx-pro-6000 | https://www.formulamod.net/products/bykski-gpu-water-block-for-nvidia-rtx-pro-6000-all-metal-structure-water-cooling-cooler-n-rtxpro6000-sr |
| Bykski RTX Pro 6000 600W AIO Water Cooling, 360 Radiator, B-FRD-RTXPRO6000-WS | formulamod.net | 2026-10-27 | primary | rtx-pro-6000 | https://www.formulamod.net/products/bykski-all-in-one-gpu-water-cooling-for-nvidia-rtx-pro-6000-water-cooling-system-liquid-cooler-360-radiator-b-frd-rtxpro6000-ws |
| HYPERPC AMPERE X ULTRA workstation: 4x RTX 6000 Blackwell for computing and n… | hyperpc.ae | 2026-10-27 | primary | rtx-pro-6000 | https://hyperpc.ae/project/clients/ampere-x-ultra-for-ai |
| NVIDIA RTX PRO 6000 Blackwell Server Edition（SKU: TCSRTXPRO6000SE-PB） | pny.com | 2026-07-01 | primary | rtx-pro-6000 | https://www.pny.com/en-eu/nvidia-rtx-pro-6000-blackwell |
| The Biggest Molecular Dynamics Hardware Comparison: 5090 vs Pro 6000 vs H100/… | proxpc.com | 2026-01-05 | tertiary | rtx-pro-6000 | https://www.proxpc.com/blogs/the-biggest-molecular-dynamics-hardware-comparison-5090-vs-pro-6000-vs-h100-h200 |
| Self-Hosting DeepSeek V4.1-Flash: The Exact GPU Setup You Need | qovery.com | 2026-10-30 | secondary | pro6000se-dsv41 | https://www.qovery.com/blog/self-host-deepseek-v4-1-flash-gpu-setup-own-cloud |
| @wechatsync/cli 包元数据 | registry.npmjs.org | — | primary | multi-platform-publish | https://registry.npmjs.org/@wechatsync/cli |
| multi-publisher（mpub）README 与元数据 | registry.npmjs.org | 2026-10-22 | primary | multi-platform-publish | https://registry.npmjs.org/multi-publisher |
| Blender on an RTX PRO 6000 (96 GB), paid by the second：实测每帧 GPU 秒与价格 | render.janction.jp | 2026-10-26 | primary | rtx-pro-6000 | https://render.janction.jp/rtx-pro-6000-blender-rendering |
| JANCTION Render Benchmarks：按分辨率/帧数/采样数的 GPU 秒矩阵（含 CSV 原始数据） | render.janction.jp | 2026-10-01 | primary | rtx-pro-6000 | https://render.janction.jp/benchmarks |
| Cadence Unveils Millennium M2000 Supercomputer with NVIDIA Blackwell Systems … | semiconductorpackagingnews.com | 2025-05-07 | primary | rtx-pro-6000 | https://www.semiconductorpackagingnews.com/uploads/2/Millennium_Press_Release_5_7_25_FINAL.pdf |
| 文章同步助手官网 | wechatsync.com | 2026-03-24 | primary | multi-platform-publish | https://www.wechatsync.com/ |
| 新媒体多账号内容批量分发，一键同步至各大平台 | xueyuan.yixiaoer.cn | 2026-11-06 | secondary | multi-platform-publish | https://xueyuan.yixiaoer.cn/article/47005 |
| 易媒助手官网 | yimeizhushou.com | 2026-11-02 | primary | multi-platform-publish | https://www.yimeizhushou.com/ |

### 新闻稿 / 报道（`press`，28 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| AMD发布MI350P PCIe AI加速卡：CDNA4架构、144GB HBM3E、专攻推理部署 | ai.zol.com.cn | 2026-05-08 | secondary | rtx-pro-6000 | https://ai.zol.com.cn/1177/11772128.html |
| 鎖定 NVIDIA RTX Pro 6000 96GB，AMD Instinct MI350P PCIe 運算卡提供 144GB HBM3e 記憶體 | benchlife.info | 2026-07-24 | secondary | rtx-pro-6000 | https://benchlife.info/amd-instinct-m350p-wtih-cdna-4-and-144gb-hbm3e/ |
| 美对华电子产品关税再推迟一年 GPU涨价风险暂缓 | c114.net.cn | 2025-12-04 | secondary | rtx-pro-6000 | https://www.c114.net.cn/industry/41777.html |
| 英伟达 RTX PRO 6000 Blackwell 全线涨价，较去年首发价高出 55% | c114.net.cn | 2026-06-13 | secondary | rtx-pro-6000 | https://www.c114.net.cn/industry/90315.html |
| NVIDIA launches 72GB RTX PRO 5000 Blackwell GPU | cgchannel.com | 2025-12-22 | secondary | rtx-pro-6000 | https://www.cgchannel.com/2025/12/nvidia-launches-new-72gb-rtx-pro-5000-blackwell-gpu/ |
| Synopsys Embraces NVIDIA RTX PRO Servers to Accelerate Compute-Heavy Simulati… | cimdata.com | 2025-08-28 | secondary | rtx-pro-6000 | https://www.cimdata.com/en/industry-summary-articles/item/28273-synopsys-embraces-nvidia-rtx-pro-servers-to-accelerate-compute-heavy-simulation-workloads |
| DeepSeek V4.1 Flash 部署完整指南 | cloud.tencent.cn | 2026-09-10 | tertiary | pro6000se-dsv41 | https://cloud.tencent.cn/developer/article/2740943 |
| Synopsys Deploys AI-Optimized NVIDIA RTX PRO Servers for Advanced Simulation … | design-reuse.com | — | secondary | rtx-pro-6000 | https://www.design-reuse.com/news/202529289-synopsys-deploys-ai-optimized-nvidia-rtx-pro-servers-for-advanced-simulation-workloads |
| RTX 6000D中国特供版深度拆解：性能降约23%，纯计算设计与水冷改造实测 | diy.zol.com.cn | 2026-02-12 | secondary | rtx-pro-6000 | https://diy.zol.com.cn/1133/11334549.html |
| 哪家硬件最可靠：Intel AMD CPU打平手、NVIDIA公版显卡最稳 | eet-china.com | 2026-02-02 | secondary | rtx-pro-6000 | https://www.eet-china.com/mp/a472169.html |
| 美国出台新规：禁止向中企境外子公司出口AI芯片！（BIS 2026-05-31 指引解读） | eet-china.com | 2026-06-01 | secondary | rtx-pro-6000 | https://www.eet-china.com/mp/a499125.html |
| The most reliable CPUs, GPUs, motherboards, etc. in 2025 selected by manufact… | gigazine.net | 2026-02-05 | secondary | rtx-pro-6000 | https://gigazine.net/gsc_news/en/20260205-most-reliable-hardware-2025-puget-systems/ |
| Nvidia's Blackwell Chips Made in Arizona Still Head to Taiwan for Final Assem… | iconnect007.com | 2025-10-27 | secondary | rtx-pro-6000 | https://iconnect007.com/article/147447/nvidias-blackwell-chips-made-in-arizona-still-head-to-taiwan-for-final-assembly/147444 |
| 英伟达 RTX PRO 6000 演示同时跑 4 个《赛博朋克 2077》 | ithome.com | 2025-08-27 | tertiary | rtx-pro-6000 | https://www.ithome.com/0/878/374.htm |
| Nvidia RTX Pro 6000 beats the RTX 5090 in gaming | kitguru.net | 2025-06-02 | secondary | rtx-pro-6000 | https://www.kitguru.net/components/graphic-cards/joao-silva/nvidia-rtx-pro-6000-beats-the-rtx-5090-in-gaming/ |
| AMD发布MI350P：四年来首款PCIe Instinct加速卡！144GB显存、600W功耗 | m.mydrivers.com | 2026-05-08 | secondary | rtx-pro-6000 | http://m.mydrivers.com/newsview/1120792.html |
| 96GB显存要9万元！RTX PRO 6000专业卡首测：只比5090快了区区9% | news.pconline.com.cn | 2025-05-16 | tertiary | rtx-pro-6000 | https://news.pconline.com.cn/1926/19268483.html |
| Azure Virtual Desktop with RTX PRO 6000: Validation shows up to 30 Siemens NX… | notanarchitect.io | 2025-10-26 | secondary | rtx-pro-6000 | https://notanarchitect.io/azure-virtual-desktop-with-rtx-pro-6000-validation-shows-up-to-30-siemens-nx-users-per-gpu/ |
| 96GB GDDR7显存加持！英伟达对RTX PRO 6000涨价 至16000美元直接翻1倍 | post.smzdm.com | 2026-08-13 | tertiary | rtx-pro-6000 | https://post.smzdm.com/p/a3morm8k/ |
| 工作站显卡一开 ECC，显存和带宽都跟着缩水？先看清代价再决定开不开 | renrendaima.com | 2026-10-17 | tertiary | rtx-pro-6000 | https://www.renrendaima.com/article/28804 |
| ASRock's TempGuard Failed to Stop a PSU-Side Connector Meltdown on a $15,000 … | techpowerup.com | 2026-09-14 | secondary | rtx-pro-6000 | https://www.techpowerup.com/352658/asrocks-tempguard-failed-to-stop-a-psu-side-connector-meltdown-on-a-usd-15-000-rtx-pro-6000-rig |
| NVIDIA Has January Discontinuation Dates Set for RTX 5090 and RTX 5080 16 GB,… | techpowerup.com | 2026-10-21 | secondary | rtx-pro-6000 | https://www.techpowerup.com/353942/nvidia-has-january-discontinuation-dates-set-for-rtx-5090-and-rtx-5080-16-gb-claims-leaker |
| NVIDIA Readies GeForce RTX 5090 SE Graphics Card | techpowerup.com | 2026-07-10 | secondary | rtx-pro-6000 | https://www.techpowerup.com/350658/nvidia-readies-geforce-rtx-5090-se-graphics-card |
| NVIDIA Readies Rubin-based GeForce RTX 60-series with Massive RT Performance … | techpowerup.com | 2026-03-30 | secondary | rtx-pro-6000 | https://www.techpowerup.com/347848/nvidia-readies-rubin-based-geforce-rtx-60-series-with-massive-rt-performance-gains |
| NVIDIA Reportedly Ending the RTX 5090, Reserves GB202 Silicon for Workstation… | techpowerup.com | 2026-10-10 | tertiary | rtx-pro-6000 | https://www.techpowerup.com/353578/nvidia-reportedly-ending-the-rtx-5090-reserves-gb202-silicon-for-workstation-gpus |
| Nvidia doubles RTX PRO 6000 price to $16,000 amid memory shortages | uz.kursiv.media | 2026-08-13 | secondary | rtx-pro-6000 | https://uz.kursiv.media/en/2026-08-13/nvidia-doubles-rtx-pro-6000-price-to-16000-amid-memory-shortages/ |
| Everything We Know (and Don't) About the NVIDIA RTX PRO 5500 | vast.ai | 2026-10-01 | secondary | rtx-pro-6000 | https://vast.ai/article/everything-we-know-about-the-nvidia-rtx-pro-5500 |
| 英伟达瞄准GPU软件订阅收入 黄仁勋提出每块GPU每年约2000美元 | wap.seccw.com | 2026-10-26 | secondary | rtx-pro-6000 | https://wap.seccw.com/Document/detail/id/51627.html |

### 厂商周边（合作方 / 生态）（`vendor-adjacent`，12 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| RTX PRO 6000 hardware MIG fleets（Nebius Physical AI 生产部署文档） | GitHub | 2026-10-20 | primary | rtx-pro-6000 | https://github.com/nebius/nebius-physical-ai/blob/main/docs/fleet-rtx-pro-6000-mig.md |
| RTX PRO 6000 Blackwell vs H100 vs H200: Which GPU Do You Actually Need? (2026) | akash.network | 2026-08-25 | secondary | rtx-pro-6000 | https://akash.network/the-bid/rtx-pro-6000-blackwell-vs-h100-vs-h200-2026/ |
| RTX PRO 5000 vs RTX PRO 6000: Specs, VRAM & Price | aquanode.io | 2026-10-27 | secondary | rtx-pro-6000 | https://www.aquanode.io/compare/gpu/rtx-pro-5000-vs-rtx-pro-6000 |
| AI Performance: MLPerf Inference on Cisco UCS X580p PCIe Node with NVIDIA H20… | cisco.com | 2026-09-30 | secondary | rtx-pro-6000 | https://www.cisco.com/c/en/us/products/collateral/servers-unified-computing/ucs-x-series-modular-system/mlperf-inference-ucs-x580p-wp.html |
| BOXX APEXX 8R (1x RTX PRO 6000 Blackwell) — 整机规格与起价 | compareaihardware.com | — | tertiary | rtx-pro-6000 | https://compareaihardware.com/ai-workstation/boxx-apexx-8r-1x-rtx-pro-6000-blackwell |
| RTX PRO 6000 Blackwell Server Edition (High Memory) | docs.coreweave.com | — | secondary | rtx-pro-6000 | https://docs.coreweave.com/platform/instances/gpu/rtxp6000-8x |
| NVIDIA RTX PRO 6000 Blackwell シリーズ製品比較ベンチマークレポート | gdep.co.jp | — | secondary | rtx-pro-6000 | https://www.gdep.co.jp/information/news/nvidia-rtx-pro-6000-blackwell_benchmark_report/ |
| RTX PRO 6000 BLACKWELL Price: $0.69/hr on RunPod | gpuperhour.com | 2026-10-27 | secondary | rtx-pro-6000 | https://gpuperhour.com/rent/rtx-pro-6000-blackwell |
| RTX 5090 VRAM for AI: what fits in 32GB? | hivenet.com | 2026-08-17 | secondary | rtx-pro-6000 | https://www.hivenet.com/post/rtx-5090-vram-for-ai-what-fits-in-32gb |
| RTX PRO 6000 Rental Pricing 2026: from $0.92/hr | inferencehub.org | 2026-10-27 | secondary | rtx-pro-6000 | https://inferencehub.org/gpus/rtx-pro-6000 |
| RTX PRO 6000 Blackwell 종합 가이드, Workstation·Max-Q·Server 정리 | nodemall.co.kr | 2026-05-15 | tertiary | rtx-pro-6000 | https://nodemall.co.kr/article/nodetalk/12/281/ |
| RTX PRO 6000 96GB Training Benchmark vs H100 (2026) | spheron.network | 2026-09-13 | secondary | rtx-pro-6000 | https://www.spheron.network/blog/h100-vs-rtx-pro-6000-blackwell-fine-tuning-benchmark-2026/ |

### 评测媒体（`review`，9 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| Inference Serving Configurations | artificialanalysis.ai | 2026-10-30 | primary | pro6000se-dsv41 | https://artificialanalysis.ai/hardware-inference-stack/configs |
| RTX 5090 rendering benchmarks: Blender, Octane and V-Ray scores | blendercloudrender.com | — | primary | rtx-pro-6000 | https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-5090 |
| RTX PRO 6000 Blackwell Server Edition rendering benchmarks | blendercloudrender.com | — | primary | rtx-pro-6000 | https://blendercloudrender.com/benchmarks/gpu/nvidia-geforce-rtx-pro-6000-blackwell-server-edition |
| Evaluating LLM Fine-tuning Efficiency on NVIDIA RTX 6000 Blackwell Max-Q | blog.us.fixstars.com | 2026-02-04 | primary | rtx-pro-6000 | https://blog.us.fixstars.com/evaluating-llm-fine-tuning-efficiency-on-nvidia-rtx-6000-blackwell-max-q/ |
| NVIDIA RTX PRO 6000 Blackwell Benchmarks & Tear-Down \| Thermals, Gaming, LLM… | devtest.gamersnexus.net | 2025-09-25 | primary | rtx-pro-6000 | https://devtest.gamersnexus.net/gpus/nvidia-rtx-pro-6000-blackwell-benchmarks-tear-down-thermals-gaming-llm-acoustic-tests |
| Dell Precision 7875 Review: Threadripper PRO 9995WX Meets Dual RTX PRO 6000 B… | storagereview.com | 2026-03-18 | primary | rtx-pro-6000 | https://www.storagereview.com/review/dell-precision-7875-review-threadripper-pro-9995wx-meets-dual-rtx-pro-6000-blackwell-gpus |
| HP Z8 Fury G6i Review: One Xeon, up to Four Blackwell GPUs | storagereview.com | 2026-06-23 | primary | rtx-pro-6000 | https://www.storagereview.com/review/hp-z8-fury-g6i-review-one-xeon-up-to-four-blackwell-gpus |
| NVIDIA RTX PRO 6000 Workstation GPU Review: Blackwell Architecture and 96 GB … | storagereview.com | 2025-10-07 | primary | rtx-pro-6000 | https://www.storagereview.com/review/nvidia-rtx-pro-6000-workstation-gpu-review-blackwell-architecture-and-96-gb-for-pro-workflows |
| RTX PRO 6000 Blackwell Server Edition vs RTX 5090 | technolynx.com | — | primary | rtx-pro-6000 | https://www.technolynx.com/lynxbench-ai/compare/rtx-pro-6000-blackwell-server-edition-vs-rtx-5090/ |

### 零售页面（`retail`，1 条）

| 标题 | 站点 | 发布 | 层级 | 归档 | 地址 |
|---|---|---|---|---|---|
| RTX PRO 6000 Blackwell: 96 GB GDDR7, MIG and 600 W | ete.ua | 2026-06-08 | secondary | rtx-pro-6000 | https://ete.ua/en/rtx-pro-6000-blackwell-96-gb-gddr7/ |
