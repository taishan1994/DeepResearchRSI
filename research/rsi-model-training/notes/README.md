# notes/ — 过程笔记与中间产物

**这些文件不是数据源。** 归档的权威数据是上级目录的 `sources.csv` /
`evidence.csv` / `claims.csv`，由本目录说明的脚本从原始语料生成。

| 文件 | 是什么 | 谁读它 |
|---|---|---|
| `_resolved.json` | 按 arXiv ID 批量核对回来的元数据（66 篇） | `build_archive.py`、`codebook.py` |
| `_resolved_extra.json` | 标题检索补回的 7 篇（含两篇综述、LADDER、SiriuS） | 同上 |
| `_extra.json` | 标题检索（`ti:"..."`）的原始命中 | 同上（合并后去重） |
| `resolve_ids.py` | 核对脚本：为什么不信任记忆里的 ID | — |
| `resolve_extra.py` | 补取脚本：哪些论文不在检索池里 | — |
| `screen_buckets.py` | 粗筛脚本：1006 篇怎么分桶 | — |
| `coverage_check.py` | 引用覆盖：哪些主张/证据正文没用到 | — |
| `peek_pdf.py` | 逐页抽取 PDF 文本，人工看版面用 | — |

## 为什么中间语料要单独放

`candidates_rsi.json` 是 16 组检索式的并集（1006 篇），它**不包含**经典工作：
STaR、SPIN、Self-Rewarding 这些论文的标题里没有 self-improving / self-evolving
这类字面词，任何关键词式子都召不回来。

于是语料实际由三部分拼成：候选池 + 按 ID 核对回来的 + 按标题检索补回的。
若把补回来的部分与检索到的混为一谈，就会把「我本来就知道的」误读成
「检索覆盖到的」——这正是 `_resolved*.json` 被单独保留、而不并进
`candidates_rsi.json` 的原因。

## 一次真实事故

首轮凭记忆列了 66 个经典 ID，回收后 11 个是错的（标题配到了别的论文上，
例如 SiriuS 记成 A-MEM 的 2502.12110，LADDER 记成一份放疗规划论文）。
`resolve_ids.py` 就是为此写的：凡不在检索池里的 ID，一律回到 arXiv 元数据
核对标题，不靠回忆。

## 覆盖检查的口径

`coverage_check.py` 回答的是「已记录的主张是否在正文里被引用」。
它给出的是**待核实清单，不是错误清单**——「内容没写」与「写了没打标签」
都会被计入。本归档当前是 48/48 与 63/63（正文与论文两侧均闭合）。
