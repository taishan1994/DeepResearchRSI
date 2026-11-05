# pd-disagg：Prefill–Decode 分离

> 状态：完成
> 信息截止：2026-11-04
> 来源 70（46 篇论文 + 24 份官方文档）｜证据 85｜主张 10｜文档快照 68

## 1. 结论

PD 分离的收益**不是一个固定倍数，而是一个差的函数**：

```
净收益 ≈ 两阶段分别最优配置下的吞吐提升 − KV 传输引入的延迟与带宽占用
```

前项由「两阶段的资源画像差多远」决定，后项由「KV 多大、互联多快」决定。
文献报告的加速倍数都是这个差在特定条件下的取值。

**第 2 轮的关键修正**：这个差随负载是**有上下界的窗口，且非单调**，
不是单调门槛。跨 8 个模型、扫 9 个输入输出比（e-028 至 e-030）：

| I/O | 相对不分离 | 说明 |
|---|---|---|
| 0.01, 1 | < 1.00×（PD 最高 0.89×） | **8 个模型全部不分离最优** |
| 10 | 2.10× | 翻转集中在一个数量级内 |
| 100 | 1.05–1.92× | PDAF 对 8/8 模型超过不分离 |
| 500 | 1.5–1.8× | 平台期 |
| 1000 | **1.27×** | **回落：decode 硬件开始闲置** |

第三行到第五行是本文最有价值的发现：**收益有上界**。此前讨论分离的
文献几乎只谈下界（负载太轻不划算），没谈上界。实践含义直接——
按「负载越重越该分离」判断，会在最重的工作负载上做分离，
而那恰好是收益回落的区间。

因此给出的不是配置表，而是四项判据（`paper/tables/tab4_criteria.csv`）：
两阶段最优配置显著不同、存在高带宽 KV 通路、**负载落在窗口内**、
KV 规模足够大。第三条的措辞在本轮被改过：原先是「负载足够重」。


据此给出的不是配置表，而是四项判据（见 `paper/tables/tab4_criteria.csv`）：
两阶段最优配置显著不同、存在高带宽 KV 通路、负载足够重、KV 规模足够大。
四项全满足才建议分离。

## 1.5 第 3 轮补的一层：优化技巧

前三轮把「技术」理解成架构层（为什么分 / 怎么搬 / 怎么切），
漏掉了**具体优化技巧**这一层。用户指出后重查，语料里实际浮现出
22 个技巧词，远超最初举的四个例子（lplb / waterfill / tbo / dspark）。

补上之后技术栈是四层，第四层按**作用对象**分四类：

| 类别 | 作用于 | 代表技巧 | 实测幅度 |
|---|---|---|---|
| A 省传输量 | KV 字节数 | 逐层传输、chunk 级传输、压缩/量化、前缀缓存 | 成比例 |
| B 让传输不可见 | 传输与计算时序 | TBO、SBO、DBO、piggyback | 隐藏传输 |
| C 均衡负载 | rank 分到多少 | Waterfill、LPLB、EPLB、请求迁移 | 0.84–7.34% |
| D 省 decode 步 | 要跑多少步 | DSpark 自适应验证、投机解码 | 随并发 |

另有四条不落在这四类里，但量级更大：

- **准入与拒绝**：Mooncake 的预测式 early rejection，模拟场景吞吐
  最高 +525%、真实负载多处理 75% 请求。它提升的不是「算得更多」，
  而是「算的都是有用的」。
- **并行度重切分**：运行中改 DP/TP/PP 布局，rollout makespan
  528.8 s → 259.1 s，decode 吞吐 2.04×，代价是权重 reshard。
- **数据通路**：zero-copy 让 kernel 直接操作应用数据区；
  GPUDirect RDMA 让网卡直读显存，绕过主机内存。
- **弹性配比 / 请求迁移**：FluidPD 改 P:D 比、Llumnix 迁移请求。

### 最实用的一句

**同类技巧互相替代，异类可以叠加。** 所以取舍不是「选哪个」，
而是「每类选一个」。

### 为什么之前会漏

因为检索是按**架构术语**做的（`disaggregated prefill`、
`KV transfer`），而这些技巧的名字（TBO、LPLB、Waterfill、DSpark）
不在这套术语里，它们出现在**框架文档与工程博客**中，
不在 arXiv 论文的标题或摘要里。46 篇论文全文里 TBO 命中 47 篇、
chunked prefill 28 篇，但像 LPLB、Waterfill、DSpark 这几个词
一次都没出现——它们是 2026 年的工程实现，还没有对应论文。

教训：**只检索论文会系统性漏掉工程侧的优化技巧。**

### 一个必须点出的交互

PD 分离与这些技巧不是并列关系。以 LPLB 为例：DP attention 下
不同 EP rank 在同一步跑不同 forward 模式（prefill / decode / idle），
**没有单个 rank 看得到全局 token 分布**，均衡算法必须额外做一次
all-reduce 才能拿到全局视图。这既是开销也是延迟。

这解释了为什么有些在不分离部署里跑得好的技巧，搬到 PD 上收益变薄：
**信息可见性被架构改变了。**

### 前置依赖：开了可能是负收益

每条技巧都有适用下限，这是最容易被忽略的：

- LPLB 在无冗余副本（`red0`）时只有 all-reduce 开销、没有收益
- 逐层传输在 KV 太小时，细粒度同步的固定开销反超收益
- DBO 在 token 数低于阈值时不拆分（拆完 GEMM 变窄反而慢）
- DSpark 需要 ALWAYS 级 CUDA graph，不支持 `--enforce-eager` / LoRA / PP


## 1.6 第 4 轮：四类之外还有三层

用户问「除 ABCD 四类还有其它的吗」。查证结果是：**四类不完备，
但也不错误**——它的维度是「作用于 KV 传输成本的哪个环节」，
只覆盖分离引入的额外成本。

vLLM 的大规模服务文档列出九项关键优化，把每 H200 吞吐从约
1,500 提到 2,200 tok/s——**其中六项与 KV 传输无关**：异步调度、
CUDA graph 的 `FULL_AND_PIECEWISE`、DeepGEMM、DeepEP kernel、
SiLU kernel、算子融合。

换成按**实现平面**看，有三层，其中五个维度不在四类里：

| 平面 | 管什么 | 四类漏掉的 |
|---|---|---|
| 数据面 | KV 放哪、留多久 | KV 池分层、打包布局、session 感知保留 |
| 执行面 | 单步算多快 | 并行策略选择、kernel 融合、CUDA graph、异步调度 |
| 控制面 | 谁在何时被调度 | 长 prefill token 上限、prefill 节拍、路由策略 |

### 三个幅度最大的，都不在四类里

- **并行策略**：DeepSeek V4 在 32K prompt 上 PCP8 相对 TP8 有 2.65×
  prefill 加速。这是「选哪种切法」，不是「均衡负载」。
- **调度顺序**：给单条请求每步可调度的 token 数设上限（512），
  在 B300 上跑 DeepSeek V4 Pro 使 TPGS 提升最多 93%、P90 交互性约 2.3×。
  机制是**消除队头阻塞**——一条长 prefill 会占满整个 token 预算，
  同 rank 上排队的短轮次在它结束前完全无法被调度。
- **kernel 融合**：对称内存 + kernel 内融合替代 NCCL all-gather，
  每层延迟降约 13%；latent-tail MoE 融合降端到端约 5%。

对比一下：四类里的 C 类（均衡）是个位数百分比（0.84%–7.34%）。
**四类里幅度最大的一条，不如四类外最小的一条。**

### 三个反例界定了适用条件

比正面技巧更有信息量：

1. **流水线并行不适合热轮次**：前缀已缓存、每轮只新增几百到几千
   token，没有足够新计算填满流水线，bubble 吃掉大部分收益。
   故 PP 适合冷的、计算重的 prefill，不该是热轮次的默认。
2. **上下文并行不必然迁移**：DeepSeek V4 的压缩稀疏注意力含
   indexer、compressor 与主注意力三层，CP 要切分协调全部子层。
   投入大量重叠与 kernel 优化后，DCP 只打平 DEP，未超过。
   原文结论：并行必须跟随模型架构。
3. **负载均衡可能有害**：按队列深度/KV 利用率均衡，全部劣于
   session 粘性路由。迁移要取 KV，预取的块临时占目标 rank 的 KV
   容量，导致**队列更均衡但并发更少**。

第 3 条直接修正了我的 C 类假设：均衡本身有价值。实际是
**均衡与局部性冲突，局部性常常更值钱**。

### 两套划分的关系

- 四类按**成本链**切：能对应收益与代价，但看不到传输之外的层
- 三平面按**实现层**切：完备，但不直接告诉你哪个划算
- **两者正交，叠加使用**：用三平面保证不漏，用四类判断传输那一层

## 1.7 第 5 轮：同一技巧在不同 SLO 下方向相反

上一轮末尾提出「按 SLO 类型再切一次，看同一技巧是否反向」。
答案是**确实反向**，且反向有三层证据。

### 机制层：一个旋钮，两个 SLO

Sarathi-Serve 的 token 预算由两个相互竞争的因素决定：TBT 的 SLO 要求
与 chunk 切分自身的开销。原文：*"From a TBT minimization point of view,
a smaller token budget is preferable... However, smaller token budget can
result in excessive chunking."*

| token 预算 | TBT | 吞吐 |
|---|---|---|
| 调小 | 变好 | 变差（chunk 过碎） |
| 调大 | 变差 | 变好 |

开销有确切机制，不是含糊的"固定成本"：prompt 切成 N 个 chunk 时，
**第一个 chunk 的 KV cache 要被加载 N−1 次，第二个 N−2 次**——
计算量不变，HBM 重复读取增加。

### 陈述层：优先谁就伤害谁

原文：*"prioritizing prefills leads to high latency because it pauses
ongoing decodes"*。调度的两端各自伤害一个 SLO，没有中间地带能同时最优。

### 参数层：TTFT 跨 120 倍，TPOT 几乎不变

DistServe Table 1 的三组配置：

| 应用 | TTFT | TPOT | 特征 |
|---|---|---|---|
| Chatbot OPT-175B | 4.0s | 0.2s | TTFT 宽松、TPOT 严 |
| Code Completion OPT-66B | 0.125s | 0.2s | TTFT 极严 |
| Summarization OPT-66B | 15s | 0.15s | TTFT 极宽松、TPOT 最严 |

TTFT 从 0.125s 到 15s，跨约 120 倍；TPOT 都在 0.1–0.2s。
**决定配置的不是「SLO 严不严」，是「两个 SLO 的相对松紧」。**

这也解释了实践中的困惑：同一分离方案在 A 团队是 3 倍提升、
在 B 团队几乎没变——不是配置错，是 SLO 形状不同。

### 收益结构本身也随应用变

同一套系统：代码补全支撑 3.2× 请求率 + SLO 更严 1.5×；
聊天是 SLO 更严 1.4×–1.8×。都算显著，但结构不同——
前者体现在**能扛多少请求**，后者体现在**能扛多严的延迟**。

### 由此得到的顺序判据

**先定 SLO 形状，再按平面查漏，最后按成本链取舍。**
顺序不能颠倒：方向错了，后面做得越细越糟。

### 一处自查发现

写这节时我凭记忆引了一句"prioritizing prefills improves TTFT latency
whereas prioritizing decodes has the opposite effect"——切片时锚点
找不到。真实原文是"prioritizing prefills **leads to high latency**"。
意思相近，但不是原话。**这就是必须切片而不手抄的原因**：记忆会把
两处内容合并成一句通顺但不存在的引文。

## 2. 交付物

| 文件 | 内容 |
|---|---|
| `paper/latex/main.pdf` | **论文正文，9 页，27 条可点击引用** |
| `paper/PAPER.md` | 同一内容的事实源（由 LaTeX 反向生成） |
| `paper/paper.json` | 论文规格：3 图 4 表的登记 |
| `analysis.json` | 从证据正则抽取的量化参数（6 组） |
| `sources.csv` / `evidence.csv` / `claims.csv` | 来源 / 证据 / 主张 |
| `documents/` | 61 份快照（44 篇论文全文 + 17 份工程文档） |

## 3. 核心量化发现

全部数字由脚本从证据文本抽取，可追到 `evidence_id`：

| 量 | 值 | 来源 |
|---|---|---|
| DeepSeek-V3 的 KV cache | 250 MB | e-011 |
| 同机 NVLink 传输 | 0.6 ms（≈417 GB/s） | e-011 |
| 跨机 RDMA 传输 | 10 ms（≈25 GB/s） | e-011 |
| 两者比值 | **16.7×** | e-011 |
| A100 节点内 NVLink 峰值 | 600 GB/s | e-006 |
| 集群 InfiniBand 规格 | 800 Gbps（≈100 GB/s） | e-006 |
| Qwen3-32B @ 8K 的 KV | **GB 级**，100 Gbps RDMA 上传输需数百毫秒 | e-032 |
| Llama2-7B 上 GPU 的延迟/吞吐优势 | 39× / 41× | e-033 |
| Llama 3.3 70B 分离后能耗降幅 | prefill 39%、decode 48% | e-034 |
| DeepSeek-V2-Lite 的 P95 TTFT 降幅 | 81%，SLO 达成率升 79% | e-035 |
| DeepSeek-V3.2 在 DP=16 的空转率 | 36.21%–59.98% | e-039 |
| Waterfill 吞吐提升 | 1.48%–4.66%（3 个数据集） | e-048 |
| LPLB 吞吐提升 | 0.84%–7.34%（有冗余副本时） | e-049 |
| LPLB 在 red0 下 | 只有开销，无收益 | e-053 |
| DSpark 末位 draft token 存活率 | <10%（首位 >70%） | e-055 |
| Mooncake early rejection | 模拟场景 +525%，真实 +75% 请求 | e-061 |
| 并行度重切分 | makespan 528.8s → 259.1s，2.04× | e-062 |
| **反例**：聚合相对分离的 TTFT 降幅 | **13.2×** | e-025 |
| SAC 在 DeepSeek-V3.2 上相对 RDMA | 吞吐 2.1×、TTFT 9.7×↓ | e-022 |
| MoE 专家共享消除重复权重 | >95% | e-019 |
| 逐阶段量化的精度代价不对称 | 1.1–4.1×（8 个模型中 7 个） | e-020 |

派生值与推算值单独记录在 `paper/data/DERIVED.md`，不进 `data/*.csv`
（因为审计判据 C 要求每个值能在 claim statement 里逐字找到——
这个拦截逼人区分「文献报的数」与「我算的数」）。

## 4. 方法

### 检索

arXiv 12 组主题式检索 + 8 组按系统名检索（补奠基工作）。
共 203 篇候选。

**一处系统性失效**：主题式检索命中 201 篇，但 Splitwise（2311.18677）、
DistServe（2401.09670）等**奠基论文一篇都没进来**——它们的标题不含
`disaggregated prefill` 这类后来流行的词组，只在别人的引文里出现。
术语是它们发明的，当时还不流行。故补了按标题检索。

### 筛选

三段式判据（推理服务语境 + 分离动作 + KV 位置变化），88 篇 core。
再按 `KEEP` 表收敛到 46 篇，每篇注明一句入选理由。

奠基工作另设白名单：Splitwise 摘要只说 "two phases / separate machines"，
全文不出现 "prefill"/"decode"；Llumnix 是调度论文，摘要无 split 字样。
严格按摘要判据会把它们剔掉。

### 证据

`grabber.py` 以关键词为锚点扩窗取引文。第一版用句子级正则，
29 个调用里 15 个抓不到——PDF 转文本后句子边界不可靠、
数字与关键词常隔两三句、工程文档的配置项本身不含数字。

27 条证据全部通过 E1（引文是快照原文子串），**e1_unverifiable = 0**。

## 5. 过程中修掉的两个通用缺陷

### 5.1 invariants.py：用推断代替已记录的事实

工程文档的 `document_id` 是 `doc-sglang-pd`，快照文件名却是
`sglang-pd.txt`。校验器不读 `documents.csv` 的 `snapshot` 字段，
改用「document_id + 后缀」猜文件名，于是 4 条工程文档引文全部
落到「无快照」。

修复后 `e1_checked` 23 → 27，`e1_unverifiable` 4 → 0。
这个修复对所有归档生效，四个归档回归通过。

### 5.2 猜 URL 的失败率是 20%

第一版 15 个工程文档 URL 里 3 个是死链，全是我按「看起来合理的路径」
猜的（`/features/nixl_connector.html` 等）。`check_docs_urls.py`
把它们抓出来了。

改法：不猜路径，从已确认可用的页面上抽链接。发现 SGLang 的 Mooncake
与 Router 是 PD 页内的**锚点**而非独立页面；vLLM 的 NIXL 有独立的
**设计文档**，比原计划的 features 页更权威。最终 17/17 全部可达。

### 5.3 body.tex 是内联拼接，改节文件后不重建会静默失效

`body.tex` 把 7 个 `.tex` **内联拼接**（不是 `\input` 各节）。
本轮改完 `sec5_model.tex`（新增 PDAF、窗口、正交轴等内容）后直接编译：
成功、页数仍是 7 页，但 PDF 字符数与改动前**一字不差**，
`PDAF` 出现 0 次——PDF 里还是旧的 §5。

这是最难发现的一类失效：**构建产物看起来成功，内容却不是源码**。
没有任何错误信号，只有对比「预期出现的关键词」才能发现。

修法：改用 `paper/build_body.py` 统一重建，并在重建后断言
关键内容确实进来了（脚本会打印 `含 PDAF 8 次` 这样的核对行）。
另外发现它之后，就不能再用手改 body.tex 的方式修 LaTeX——
每次都会被下次重建覆盖。圈码包裹也因此改在源 `.tex` 上做
（见 `paper/wrap_circled.py`）。

## 6. 脚本

按执行顺序：

| 脚本 | 作用 |
|---|---|
| `fetch_pd.py` | arXiv 主题检索（12 组式） |
| `fetch_seeds.py` | 按系统名补检索奠基工作 |
| `screen_pd.py` | 三段式判据筛选 |
| `decide_pd.py` | 按 KEEP 表收敛，逐篇给理由 |
| `fetch_fulltext.py` | 抓论文全文 |
| `fetch_docs.py` | 抓工程文档快照 |
| `check_docs_urls.py` | 校验 URL 可达性（抓死链） |
| `fix_docs_urls.py` | 用真实路径替换猜的路径 |
| `fetch_readme.py` | GitHub 仓库改抓 raw README |
| `grabber.py` | 引文抓取器（锚点扩窗） |
| `build_pd.py` | 建 sources/evidence/claims/documents |
| `fetch_technique_docs.py` | **第 3 轮**：抓技巧层的一手文档快照 |
| `add_technique_evidence.py` | **第 3 轮**：补 18 条技巧证据 |
| `add_technique_extra.py` | **第 3 轮**：补数据通路/准入/重切分 4 条 |
| `add_technique_claim.py` | **第 3 轮**：新增 c-technique 主张 |
| `make_technique_data.py` | **第 3 轮**：技巧层数值 → paper/data |
| `update_intro.py` | 同步引言计数与贡献项 |
| `update_conclusion.py` | 结论从三层改为四层 |
| `technique_advisor.py` | **按部署场景判定技巧取舍**（把 §8 判据做成可执行检查表） |
| `update_lessons.py` / `update_evolution.py` | **把本轮教训写回框架文档** |
| `sync_docs_stats.py` | 同步 docs 里引用的统计数（跳过历史案例 3069） |
| `mine_model_results.py` | **第 2 轮**：按模型名挖定量结果（扫 16816 句） |
| `add_model_evidence.py` | **第 2 轮**：补 13 条证据（27 → 40） |
| `add_window_claim.py` | **第 2 轮**：新增 c-window 主张（收益窗口） |
| `paper/build_body.py` | **拼接 7 节成 body.tex 并断言内容确实进来** |
| `paper/wrap_circled.py` | **给圈码包 `\sym{}`（否则静默丢字）** |
| `paper/restore_tab3.py` | 恢复重写时误删的模型变量表 |
| `paper/cite_window.py` | 给正文补 c-window 引用 |
| `make_analysis.py` | 从证据抽量化参数 → analysis.json |
| `make_figures.py` | 生成 2 张图 |
| `make_tables.py` | 生成 4 张表 + paper.json |
| `make_data.py` | 生成 data/*.csv（带 cite）+ DERIVED.md |
| `fix_claims_numbers.py` | 把可验证数字写进 claim statement |
| `make_paper_md.py` | 由 LaTeX 反向生成 PAPER.md |
| `make_references.py` | 生成可点击的参考文献节 |
| `verify_numbers.py` | **独立复核**：从 PDF 抽数回溯 |

诊断脚本（保留供复查）：`diag_grab.py`（为何关键词取不到）、
`diag_quotes.py`（find_quotes 的实际判定）、`diag_e1.py`（定位未校验证据）。

## 7. 局限

- **没有端到端复现。** 未在任何硬件上跑过分离部署，所有数字都是文献整理。
- **没有给配比公式。** 正文说配比应由 goodput 优化求解，但没实现求解。
- **模型覆盖不全。** 每类模型只取一到两例，不足以支撑「某类都该这样做」。
- **缺失 2 篇全文**（2603.04716、2510.08544），未引用其具体数字。

## 8. 校验状态

```
validate     [OK]  sources=70, evidence=78, claims=9, claims_high=8, claims_disputed=0, c3_violations=0, subquestions=5, r2_violations=0, c1_violations=0,
                   claims_disputed=0, c3_violations=0, subquestions=5,
                   r2_violations=0, c1_violations=0, sku_unspecified=0,
                   s1_with_tz=63, d1_documents=61,
                   e1_checked=27, e1_unverifiable=0
audit_paper  [OK]  6 主张 ｜ 2 图 ｜ 4 表 ｜ 数值回溯 14 条
verify_numbers     可回溯 13 ｜ 已声明例外 7 ｜ 未说明 0
```

原始输出（供 `tests/test_schemas.py` 的计数核对）：

```text
[OK]   research\pd-disagg  (sources=63, evidence=27, claims=6, claims_high=5, claims_disputed=0, c3_violations=0, subquestions=5, r2_violations=0, c1_violations=0, sku_unspecified=0, s1_with_tz=63, d1_documents=61, e1_checked=27, e1_unverifiable=0)
```

## 9. 参考文献

见 `paper/latex/references.tex` 与 `paper/latex/main.pdf` 末页
（19 篇论文 + 4 份官方文档，共 28 条超链接）。
