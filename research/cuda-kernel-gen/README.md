# CUDA Kernel 自动生成综述（2025—2026）

一篇以「一个数字能证明什么」为准的中文综述，覆盖 2025-02 至 2026-11 的 **98 篇**论文。

本目录是 DeepResearchRSI 框架下的一个研究归档，结构遵循 `research/rtx-pro-6000` 的约定：

```
cuda-kernel-gen/
├── brief.yaml              研究简报（问题拆解、时间范围、排除项）
├── sources.csv             36 个来源（arXiv 为主 + 内部审计产物）
├── evidence.csv            18 条证据（逐字引文，可回查）
├── claims.csv              18 条主张（含 claim_type / confidence / as_of）
├── claims_audit.csv        70 条速度声明的逐条可比性判定（可审计）
├── claim_audit_summary.json 上述判定的汇总
├── REPORT.md               框架审计视图（每条论断带 claim 引用）
├── run.json                运行轨迹（21 条 trace）
└── paper/                  论文本体
    ├── PAPER.md            事实源，全文正文 44,063 字符 / 640 行
    ├── PAPER.pdf           成品，14 页双栏，9 图 13 表
    ├── papers.json         98 篇论文的 arXiv 元数据与摘要全文
    ├── speed_claims.json   70 条速度声明及其语义分类
    ├── figures/*.png       9 张图
    ├── tables/*.csv        5 张表
    ├── latex/              LaTeX 源与编译产物
    └── *.py                全部生成与校验脚本
```

## 产物

| 文件 | 说明 |
|---|---|
| `paper/PAPER.pdf` | **成品**。NeurIPS 风格双栏，14 页，9 图 13 表 |
| `paper/PAPER.md` | **事实源**。全文正文 44,063 字符 / 640 行 |
| `REPORT.md` | **审计视图**。带 `[c-xxx]` / `[e-xxx]` 引用的摘要 |
| `paper/papers.json` | 98 篇论文的 arXiv 元数据 |
| `paper/speed_claims.json` | 70 条速度声明的语义分类 |
| `claims_audit.csv` | 逐条可比性判定，含理由，可重跑核对 |

## 核心结论

**这个领域 21 个月内取得了实质进展，但幅度被系统性夸大，且端到端意义远小于 benchmark 数字。**

- 从「不到 20% 的题目能打平 PyTorch」到「九成快于 `torch.compile`」——这是真的
- 但把基线校正到同等条件（TF32 + 隐藏测试），最强模型几何平均回落到 **0.88x**
- 70 条速度声明中，**只有 8 条（11%）可跨论文比较**（几何/算术平均 + 明确库基线）
- 可比性还在恶化：2026-07 之后新增的 20 条中，达标的 **0 条**
- 同一系统换基线可从 **1.42x 到 120x**（跨度 85 倍）
- Transformer 推理中 80–86% 时间在 cuBLAS/FlashAttention，可优化空间仅 8.9%–58.2%，
  **端到端收益上限约 1%**

## 复现

全部命令在 `paper/` 下执行（脚本用 `Path(__file__).parent` 定位，无需改路径）：

```bash
cd paper

python fetch_papers.py          # 抓取初版 58 篇 -> papers.json
python fetch_recent.py          # 抓取 2026-07..11 新增 40 篇 -> recent_2026h2.json
python merge_recent.py          # 合并为 98 篇
python extract_metrics.py       # 抽取量化指标 -> extracted.json
python classify_claims.py       # 分类速度声明 -> speed_claims.json
python make_figures.py          # 9 张图 -> figures/
python make_tables.py           # 5 张表 -> tables/（内置数字回溯自检）
python fix_heading_levels.py    # 修正章/节层级（## N.M -> ### N.M，幂等）
python fix_figure_titles.py     # 去掉图内「图 N」编号（编号只归 caption）
python fix_figure_captions.py   # 写实体图注（按图片路径定位，幂等）
python add_table_captions.py    # 给表格补题注（幂等）
python md_to_tex.py .           # Markdown -> LaTeX
```

编译 PDF：

```bash
cd paper/latex
xelatex main.tex    # 跑两遍，交叉引用才正确
```

框架侧（在仓库根目录）：

```bash
python research/cuda-kernel-gen/export_claim_audit.py
python research/cuda-kernel-gen/build_evidence.py
python research/cuda-kernel-gen/build_report.py
python research/cuda-kernel-gen/build_run.py

PYTHONPATH=packages/schemas/python \
  python -m deepresearchrsi.validate research/cuda-kernel-gen
```

## 校验

论文侧（`paper/` 下）：

| 脚本 | 检查内容 |
|---|---|
| `verify_numbers.py` | 26 项数字核对：正文百分比 vs 实测、表格数值 vs arXiv 摘要。期望值实时计算，不写死 |
| `check_latex.py` | X1–X8 版式：逐页充盈、缺字、溢出、行宽、内容完整、图注同页、图注无重复编号、图号与内容对应 |
| `check_pdf_content.py` | Markdown 残留、章节完整性、图表编号 |
| `check_citations.py` | 27 个 arXiv 编号逐个向官方 API 核实存在 |
| `audit_figure_text.py` | 图内文字无「图 N」残留、无过期数字 |
| `audit_captions.py` | 无空壳题注、无重复 |
| `test_x7.py` / `test_x8.py` | 用反例验证 X7/X8 真能报错，而非永远通过 |

框架侧：`validate.py` 全绿（c1/c3/r2 违规均为 0），
`tests/test_schemas.py` 26 项、`tests/test_facets.py` 7 项通过。

当前状态：**全部通过**（26/26、X1–X8 全绿、27/27、X7 2/2、X8 4/4）。

## 已知局限

1. **定量分析基于摘要而非全文**。98 篇全文的人工核对超出单次调研的可靠范围。第 5 章的统计应理解为「摘要层面」的度量质量，是下界估计。
2. **70 条声明来自正则抽取**，可能漏掉非标准表述（如「提升 15 个百分点」）。
3. **「可跨论文比较的 8 条」是保守下界**——有些论文可能在正文报告了严格数字而摘要未提。

## 数据来源

arXiv 官方 API（`export.arxiv.org/api/query`），非二手转述。抓取时间 2026-11-03。
`browse-export` 端点会 429 限流，必须走 `export.arxiv.org`，且调用间隔约 3 秒。

## 与已有综述的区别

同期已有 IJCAI 2026 综述《Towards Automated Kernel Generation in the Era of LLMs》
（[arXiv:2601.15727](https://arxiv.org/abs/2601.15727)），按 LLM4Kernel / Agent4Kernel /
Datasets / Benchmarks 四分类组织，覆盖面广。

本文不重复其分类工作，补四件它未做的事：

1. 量化度量缺陷（第 5 章）——70 条声明逐条分类，给出「只有 11% 可比」的实证
2. 拆解奖励黑客（第 6 章）——用受控实验说明性能数字如何被系统性夸大
3. 提出能力分层（第 3 章）——用「语法/语义/性能」三层解释各方法成败
4. 追问端到端收益（第 7 章）——用真实负载剖析说明 benchmark 加速比的实际意义上限

定位是**批判性补充**，不是替代。
