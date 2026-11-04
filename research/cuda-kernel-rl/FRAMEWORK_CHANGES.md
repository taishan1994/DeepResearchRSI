# 本轮的框架改进（cuda-kernel-rl 专题）

记于 2026-11-04。这份文档记录**做专题时发现的框架缺口**，以及补法。
放在归档根目录，因为它同时是「这次研究做了什么」的说明和
「框架因此长了什么」的记录。

## 1. 关键词检索收进 `services/providers`

### 缺口

框架原本只有 `fetch_papers.py`：按**已知 arXiv ID 列表**批量取元数据。
那份 ID 列表是人工挑的。但做新专题时起点不是「我知道有哪些论文」，
而是「这个方向有哪些论文」——需要关键词检索。

产业链上的后果：`cuda-kernel-gen` 和 `cuda-kernel-rl` 各写了一份
requests + XML 解析 + 限速 + 429 退避，几乎逐行相同。

### 补法

新增 `packages/providers/python/deepresearchrsi_providers/arxiv.py`，
实现 `services/providers/README.md` 里定义的 `SearchProvider` 契约：

```python
provider = ArxivProvider()
hits = provider.search_many([q1, q2, q3], limit=100)   # 多式并集去重
```

`search_many` 保留每篇被哪条式子召回（`query` 字段），
用于判断「检索式是否够全」——全被单一式子命中说明其余冗余。

### 验收

**不是「代码能跑」，而是「新旧实现产出相同」**：
同一组 10 个检索式，旧脚本与新 provider 各跑一遍，
候选池 80 篇、交集 80、零差异。

没有这个对比，「换个地方实现」与「能力退化」无法区分。

测试：`tests/test_providers_arxiv.py`（25 项，含离线解析与在线检索）。

## 2. P2 支持「计数型派生值」的重算

### 缺口

`audit_paper.py` 的 P2（数值可回溯）要求每个数字都能在某条
`evidence.quote` 里逐字找到。这对观测值正确（1.43x 就该来自论文原文），
但用于**统计值**就错了：

论文里的「9 篇用结果型奖励」「4 篇用 GRPO」是本文对语料的统计，
这些数不会长在文献摘要里。

### 曾经的空转（必须记下来）

为了让审计通过，我最初给 CSV 加了 `value` / `cite` 两列，
但列名与审计期望不符（审计要 `(value, cite)`，我写了 `(form, papers)`）。
结果每一行都被 `continue` 跳过，`checked` 恒为 0，
审计输出「数值回溯 0 条」然后报 `[OK]`。

**这是最危险的一种通过：检查写了，但一行都没查。**

### 补法

给 `recompute` 加「计数」通道，与既有的 Amdahl 分支并列：

    derivation 里写：  计数 outcome=9
    审计重算：        从 papers.json 数 outcome 标签的篇数，等于 9 才放行

还支持：

    计数 quarter 2025-Q3=3     # 时间线图每根柱子
    计数 unnamed=7             # 特殊：既无 GRPO 也无 PPO 也无对比式

关键是 **derivation 只声明口径，篇数由审计独立重算**。
若 derivation 里写死数字，审计只是核对「derivation == 图」，
两者可以一起错。

### 验收

`数值回溯 19 条`（此前 0 条），且 `[OK]`。
反例仍然过不了：把图里的 9 改成 10，审计重算得 9，报错。

## 3. `sync_report_counts.py` 会误改无关文档

### Bug

加 `--slug X` 后 `results` 只剩一个归档，
`sync_eval_cases()` 就无条件把它的计数写进 `evals/cases/README.md`——
而那个文件讲的是 rtx-pro-6000。

实际发生的破坏：447 来源被改成 20 来源。

「只有一个候选」被当成「就是这个候选」。

### 补法

必须先确认该文件**提到了**本次处理的归档，才允许改写：

```python
mentioned = [s for s in results if s in text]
if not mentioned:
    return ["... 未提及任何本次处理的归档，跳过"]
```

### 验收

`tests/test_sync_report.py`（3 项）+ 真实仓库哈希比对（`--slug cuda-kernel-rl`
跑一遍，`evals/cases/README.md` 的 hash 不变）。

## 顺带修掉的一个既有漂移

跑测试时发现 `evals/cases/README.md` 说「2997 证据」，实际 3002。
这不是本轮引入的，是 rtx-pro-6000 归档增长后文档没跟上。
用修好的工具以 `--slug rtx-pro-6000` 同步，2997 -> 3002、2233 -> 2238。

## 4. 第二轮：全文抓取与 E1 的多快照校验

### 起因是一次真实的错误

第一轮的论文里写了：

    「没有任何工作报告『加了中间奖励之后，最终加速比是否真的提高』
      的对照实验。」

并把它列为本方向最重要的空白。

第二轮抓到全文后发现这句话是错的。TritonRL 表 3 消融了 plan 奖励权重 α，
α=0 时 correct 37.0，α=0.1 时 56.0——19 个百分点的因果证据；
Dr. Kernel 更直接，训练了有/无反作弊检查两个模型并列对比。

**错在把「摘要里没有」当成「论文里没有」。** 摘要用来推销结论，
天然不写实验设计。用摘要的沉默论证文献的空白，等于把自己的取材边界
写成了别人的缺陷。

### 补法一：`fetch_fulltext.py`

arXiv 自 2023 年起为多数论文提供 HTML 版（`arxiv.org/html/<id>vN`）。
抓 `<article>` 内的正文，删 script/style/nav，在参考文献处截断。
13 篇 core 成功 12 篇（CUDA Agent 是最新预印本，尚无 HTML）。

### 补法二：E1 支持多快照 + 跨来源归一

⚠️ 这一步踩了一个坑，值得记下来。

最初让 E1 **优先用全文**，理由是「全文包含摘要，判据更严」。
结果 14 条摘要级证据全部失败。原因不是证据错，而是同一句话在两种来源里
**表示不同**：

    摘要快照（Atom API）：   ... by up to 26%, and on average 9%.
    全文快照（LaTeXML）：    ... by up to $26\%$, and on average $9\%$.

LaTeXML 把数学包成 `$...$`、把百分号转成 `\%`。用全文校验摘要级引文，
会把正确证据判成伪造——**这比不检查更糟，因为它会训练人去改对的证据**。

正解是**任一快照匹配即通过**，并加一层 `relaxed()` 归一
（去 `$`、`\%`、`\command`、花括号），只用于跨来源比对。
去掉的只是排版标记，不是文字，所以不违反「quote 必须是原文字串」。

`write_snapshot()` 同时加了 `variant` 参数：摘要写 `<did>.txt`，
全文写 `<did>-full.txt`，各自登记一行 `documents.csv`。
若共用一个文件名，D1 会把「摘要→全文」误判为改版。

### 一个隐蔽的正则陷阱

第一次补表 3 数字时，5 条证据只成功 2 条。失配原因是 LaTeXML 在表格里
把 `/` 两侧写成 `\xa0/\xa0`（不换行空格），而我的正则用了普通空格。
肉眼完全看不出差别。

**教训：从 HTML 抽取的文本，正则里一律用 `\s*`，不要写死普通空格。**

### 验收

- `e1_checked=37, e1_unverifiable=0`（37 条证据全部实校）
- 摘要级与正文级证据各自命中对应快照
- 反例验证：把表 3 的 37 改成 41，审计 P2 立刻报「在主张及其全部证据里都找不到」

## 5. 图表清单是硬编码的，新图会静默漏检

加 fig4 时发现 `build_paper_json.py` 的 `FIGURES` / `TABLES` 是手写清单。
新图不进清单就**不会出现在 paper.json**，于是 P3（无凭空图表）不会检查它。

这与第 2 节的「P2 空转」是同一族问题：**检查的上限是它知道的对象集合。**

补法：把 fig4、tab3 登记进清单。顺带发现 tab3 未登记时，
`md_to_tex.py` 按出现顺序把它编成 tab3，又从 `TABLE_TITLES` 取不到标题，
回退成首列表头——PDF 里出现了一个叫「α」的表。
已在 `md_to_tex.py` 里留注释说明「表的标题必须来自 paper.json，不能靠推断」。

## 6. 参考文献：从 sources.csv 生成，不手写

### 需求

把 20 篇来源的标题与链接排到 PDF 最后。

### 做法

`make_references.py` 从 `sources.csv` 生成 `REFERENCES_SECTION.md`，
`md_to_tex.py` 在排版时把它接到正文末尾。**不写进 PAPER.md**——
否则「论文源文件」与「文献表的真实来源（sources.csv）」会各存一份 20 条清单，
改一处忘另一处。

按 layer 分三组（core / adjacent / infra），**组内按发表日期降序**。
排序用两趟：先按 source_id 升序定稳定的次级顺序，再按日期降序——
单趟 key 配 `reverse=True` 会把次级键也倒过来。

### 挖出的三个真 bug

**一、`inline()` 完全不转义普通文字。**

它原先只处理粗体与行内代码。正文里恰好没有裸的 `_ % & #`，
所以一直没暴露。参考文献里 `make_references.py` 的下划线一出现，
XeLaTeX 立刻报 `Missing $ inserted`——`_` 在数学模式外是非法字符。

修法是占位符法：**先把要保留的 LaTeX 结构挖成占位符 → 转义剩下的文字
→ 再把占位符填回去**。若先转义再替换，`\href{...}` 的花括号与反斜杠
会被一并转义，生成 `\textbackslash{}href` 这种垃圾。

**二、哨兵用了字面 `\x00`，同函数里的 `\f` 被当成换页符。**

stash 占位符写成 `f"\x00{n}\x00"` 本身没错，但同一函数内还有
`repr` 出来的路径含 `\f`、`\a`，Python 把它们当转义序列，
静默吞掉字母（实测 `fetch_rl.py` 变成 `etch_rl.py`）。
改用 `NUL = chr(0)` 构造，正则也用 `NUL` 拼接。
顺带把 docstring 改成 raw string，消掉 `SyntaxWarning: '\h'`。

**三、URL 不可断导致整段标题逐词拆行。**

加入 20 条 arXiv 链接后，PDF 出现
「Micro- / Profiling Tools as Expert Surrogates for LLM-Based GPU /
Kernel / Optimization」这种一列碎词。

不是标题太长，是**没有断点**——与正文标点溢出同源（缺的是断行点，
不是弹性）。解法三件事一起做：`xurl` 让 `\url` 可在任意字符处断行、
`\UrlBreaks` 补 `/ . - _ :`、参考文献环境用 `\raggedright`。
效果：标题恢复成完整行。

### 新增两个检查

**`tests_inline.py`（11 项）** —— `inline()` 是整篇 PDF 的唯一文字入口，
它错一次整篇都错。固定住「输入 → 期望输出」，任何退化立刻显形。

**`check_references.py`** —— 从 PDF 提取链接注解与可见文本，
与 `sources.csv` 做**双向**比对：少了报「漏」、多了报「可能编造」。
理由：20 条里少一条，翻页时不会有人数得出来。

这个检查自己出过一次假警报：先用 `replace("\n","")` 拉平全文，
导致 URL 与下一条编号粘连，20/20 全报缺失。第二版又漏了
「URL 与中文括号同一行」的情形，第三版把页脚页码 `7`
粘到了最后一条 URL 上（`abs/2502.105177`）。三次都是提取逻辑的错，
不是文献的错——**假警报比不检查更容易让人放弃检查**，故每个修正都留了注释。

反例验证：从 `sources.csv` 临时删掉一条，检查立刻报
「1 个链接不在 sources.csv 里（可能编造）」。

## 未做但应该做的

- `services/ingestion`：把抓到的原始 HTML/PDF 落成 `documents/` 快照。
  本轮是手工从 `papers.json` 导出摘要作为快照，不是通用流程。
- `research/rtx-pro-6000` 的 3002 条证据仍无快照（`e1_checked=0`）。
