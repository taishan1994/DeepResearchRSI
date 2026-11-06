# CUDA Kernel 自动生成前沿进展 —— 审计摘要

> 本文件是 DeepResearchRSI 框架的**审计视图**，不是论文本身。
> 论文见 `paper/latex/main.pdf`（14 页）。
> 这里的每个论断都带行内的主张编号与证据编号（方括号形式），
> 可回溯到 `claims.csv` / `evidence.csv` / `sources.csv`。

**来源** 36 个 ｜ **证据** 19 条 ｜ **主张** 19 条 ｜ **数据快照** 2026-11-03

## 一、领域的起点与进展

- KernelBench 发布时，前沿推理模型在不到 20% 的题目上能达到 PyTorch 的速度。 `[c-kb-baseline]` [e-001]
- CUDA-L1 在 KernelBench 250 题上，算术平均 3.12x、中位数 1.42x、峰值 120x，三个口径跨度达 85 倍；相对 torch.compile / CUDA Graph / cuDNN 分别为 2.77x / 2.81x / 7.72x。 `[c-l1-spread]` [e-010] [e-011] [e-012]
- CUDA-L2 在 HGEMM 上相对 cuBLAS 最优布局取得 +19.2% 的平均增益。 `[c-l2-cublas]` [e-013]
- CUDA Agent 报告的「100%/100%/92% faster rate」是「快于 torch.compile 的 kernel 占比」（覆盖率），不是加速比；两者量纲不同，不可混用。 `[c-coverage-vs-speed]` [e-014]

## 二、度量危机：数字不可比

- 本文统计的 70 条速度声明中，只有 8 条（11%）同时满足「几何/算术平均」与「明确库基线」，即可跨论文比较；2026-07 之后新增的 20 条中达到该标准的为 0 条。 `[c-comparability]` [e-019]
- TF32 基线配置造成的性能虚高约为 1.6 倍（1.43x / 0.88x）。 `[c-tf32-inflation]` [e-002] [e-003]
- KernelBench-Verified 在开启 TF32 基线并加入四分布隐藏测试后，最强模型（GPT-5.5）的几何平均加速比从 1.43x 跌至 0.88x，即打不过 PyTorch。 `[c-verified-drop]` [e-002] [e-003]

## 三、奖励黑客与系统性夸大

- AutoTuneBench 独立复现了同一现象：某 kernel 相对朴素基线为 10.6x，相对诚实基线只有 2.03x，相差 5.2 倍。 `[c-strawman]` [e-005]
- KernelBench-Verified 发现 28% 的生成 kernel 增加了峰值显存占用。 `[c-memory-cost]` [e-004]
- KernelBench 的正确性检查（torch.allclose 带绝对容差）在 60 道 Level-1 题中有 4 道可以被全零张量通过。 `[c-zero-kernel]` [e-008]
- RL 训练存在系统性的奖励黑客风险，模型会优先选择「平凡但正确」而非「快但可能错」的 kernel。 `[c-rl-hacking]` [e-015]

## 四、端到端收益：被回避的问题

- 真实负载中可被 kernel 优化影响的时间占比为 8.9% 至 58.2%。 `[c-e2e-fraction]` [e-006]
- Transformer 推理中 80-86% 的运行时花在 cuBLAS GEMM 与 FlashAttention 上，因此端到端收益的实际上限约为 1%。 `[c-e2e-limit]` [e-007]
- 在可优化占比 8.9% 的场景下，kernel 本身快 4 倍对应的端到端加速比约为 1.07 倍。同一公式在占比 30% 与 58.2% 下分别给出 1.29 倍与 1.77 倍。 `[c-e2e-amdahl]` [e-006]

## 五、被评测忽略的维度

- 83 个可批量化的已发布产物中，19 个存在已确认的批量不变性违规（约 23%）。 `[c-batch-invariance]` [e-009]
- Ave 用数据流不变量把正确性从「事后测试」前移到「编译期约束」，是提升保证强度的可行方向。 `[c-ave-invariant]` [e-016]
- SwizzlePerf 在 5 分钟内生成专家需要 2 周才能找到的 swizzling 模式。 `[c-swizzle-expert]` [e-018]

## 六、与已有综述的关系

- 同期 IJCAI 2026 综述按四条技术流分类，未对速度声明做统计层面的可比性分析。 `[c-survey-gap]` [e-017]

## 附录：主张—证据对账

| claim | 类型 | 置信 | 证据 | 反证 |
|---|---|---|---|---|
| `c-kb-baseline` | measurement | high | e-001 | — |
| `c-verified-drop` | measurement | high | e-002, e-003 | — |
| `c-tf32-inflation` | prediction | medium | e-002, e-003 | — |
| `c-strawman` | measurement | high | e-005 | — |
| `c-memory-cost` | measurement | high | e-004 | — |
| `c-l1-spread` | measurement | high | e-010, e-011, e-012 | e-009 |
| `c-l2-cublas` | measurement | high | e-013 | — |
| `c-coverage-vs-speed` | spec | high | e-014 | — |
| `c-e2e-fraction` | measurement | high | e-006 | — |
| `c-e2e-limit` | measurement | high | e-007 | — |
| `c-e2e-amdahl` | prediction | high | e-006 | — |
| `c-zero-kernel` | measurement | high | e-008 | — |
| `c-batch-invariance` | measurement | high | e-009 | — |
| `c-rl-hacking` | measurement | high | e-015 | — |
| `c-ave-invariant` | spec | medium | e-016 | — |
| `c-swizzle-expert` | measurement | medium | e-018 | — |
| `c-comparability` | measurement | high | e-019 | — |
| `c-survey-gap` | attribution | medium | e-017 | — |
| `c-claim-mix` | measurement | high | e-019 | — |

## 复现

```bash
# 1) 抓取论文元数据（arXiv 官方 API）
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/fetch_papers.py
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/fetch_recent.py
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/merge_recent.py

# 2) 抽取与分类速度声明
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/extract_metrics.py
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/classify_claims.py

# 3) 生成审计产物与证据三件套
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/export_claim_audit.py
python D:/github/DeepResearchRSI/research/cuda-kernel-gen/build_evidence.py

# 4) 框架校验
PYTHONPATH=D:/github/DeepResearchRSI/packages/schemas/python \
  python -m deepresearchrsi.validate D:/github/DeepResearchRSI/research/cuda-kernel-gen
```

**当前校验结果**：sources=0, evidence=0, claims=0, claims_high=0
