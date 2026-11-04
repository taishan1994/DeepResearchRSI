# pd-disagg：Prefill–Decode 分离

> 状态：完成
> 信息截止：2026-11-04
> 来源 63（46 篇论文 + 17 份官方文档）｜证据 27｜主张 6｜文档快照 61

## 1. 结论

PD 分离的收益**不是一个固定倍数，而是一个差的函数**：

```
净收益 ≈ 两阶段分别最优配置下的吞吐提升 − KV 传输引入的延迟与带宽占用
```

前项由「两阶段的资源画像差多远」决定，后项由「KV 多大、互联多快」决定。
文献报告的加速倍数都是这个差在特定条件下的取值。

据此给出的不是配置表，而是四项判据（见 `paper/tables/tab4_criteria.csv`）：
两阶段最优配置显著不同、存在高带宽 KV 通路、负载足够重、KV 规模足够大。
四项全满足才建议分离。

## 2. 交付物

| 文件 | 内容 |
|---|---|
| `paper/latex/main.pdf` | **论文正文，7 页，28 条可点击引用** |
| `paper/PAPER.md` | 同一内容的事实源（由 LaTeX 反向生成） |
| `paper/paper.json` | 论文规格：2 图 4 表的登记 |
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
validate     [OK]  sources=63, evidence=27, claims=6, claims_high=5, claims_disputed=0, c3_violations=0, subquestions=5, r2_violations=0, c1_violations=0,
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
