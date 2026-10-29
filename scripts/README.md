# scripts/ — 本地开发工具

不承担研究逻辑，只做**校验、生成与导出**。所有脚本都是单文件、零第三方依赖、可直接 `python scripts/xxx.py` 运行。

## 公开脚本

### `new_research.py` — 脚手架

```bash
python scripts/new_research.py --slug <slug> --question "<研究问题>" [--title "<标题>"] [--topic "<主题>"]
```

例：

```bash
python scripts/new_research.py --slug rtx-pro-6000 --question "RTX PRO 6000 的性能到底如何？" --title "RTX PRO 6000 性能分析"
```

生成 `research/<slug>/`：`brief.yaml`（含 `q1` 子问题骨架）、`sources.csv`、`evidence.csv`、`claims.csv`（均含表头）、`REPORT.md`、`notes/` 空目录。

用途：让新研究从第一秒就满足 S1/D1/E1/C1/C2/R1 等不变量，而不是事后补齐。

### `validate_research.py` — 归档自洽性校验

```bash
python scripts/validate_research.py research/rtx-pro-6000   # 单个
python scripts/validate_research.py research/*              # 全部
python scripts/validate_research.py                         # 默认 research/ 下所有子目录
```

委托给 `packages/schemas/python/deepresearchrsi/validate.py`，检查：

| 类别 | 检查项 |
|---|---|
| ID | `src-` / `e-` / `c-` 前缀，各表内唯一 |
| 来源 | `url` 非空、`fetched_at` 非空（**S1**）、`published_at` 可解析、`source_type` 与 `trust_tier` 枚举合法 |
| 证据 | `quote` 非空（**E1**）、`source_id` 存在 |
| 主张 | 至少一条 `evidence_ids`、引用可解析、`prediction` 必须带 `derivation`（**C2**） |
| 报告 | `REPORT.md` 中 `[c-*]` / `[e-*]` 引用不得悬空 |

退出码：全通过为 `0`，任一失败为 `1`。

### `audit_uncited.py` — 已记录但正文未引用

```bash
python scripts/audit_uncited.py research/rtx-pro-6000
```

**为什么存在**：校验器只能检查「正文引用的 id 是否存在」，无法检查「已记录的主张是否在正文中被引用」。后者一旦缺失，prose 与 CSV 就会脱节，而所有自动检查仍然通过。

输出：主张总数 / 已引用 / 未引用（含百分比），再按 `confidence` 与 `as_of` 分布，最后列待核实清单。

⚠️ 它给出的是**待核实清单**，不是错误清单——「内容没写」与「写了没打标签」都会被计入，需要人工区分。

### `audit_coverage.py` — 来源覆盖率

```bash
python scripts/audit_coverage.py research/rtx-pro-6000
```

统计每个来源被多少条证据覆盖、每条证据被多少条主张引用，用来发现「登记了很多来源但只读了少数」这类偏差。**分母是「已登记的来源数」，不是「存在的资料数」**——这一点必须写在结论里，否则覆盖率会被读成完整度。

### `audit_duplicate_sources.py` — 重复来源（只读）

```bash
python scripts/audit_duplicate_sources.py research/rtx-pro-6000
```

按 URL 归一化（去协议、去 `www.`、去尾斜杠、去 fragment）分组，报告同一 URL 被登记为多个 `source_id` 的情况。

**只读，不合并。** 合并需要一条裁决规则（保留哪个 id、证据怎么迁移、主张的 `evidence_ids` 怎么改），而这条规则属于研究决策，不属于工具。

### `audit_id_drift.py` — `document_id` 命名漂移

```bash
python scripts/audit_id_drift.py research/rtx-pro-6000
python scripts/audit_id_drift.py research/*
```

**为什么存在**（第 229 轮）：跑「双向孤儿检查」时发现 5 个 `source_id` 各对应两个 `document_id`。核对后确认每一对都是同一份文档被写了两个名字——不是真的有两份文档。故 `distinct(document_id)` 这个数被高估了。

这个缺陷之所以长期没被发现，是因为既有的检查器只朝两个方向看：`validate.py` 的 C1 从 claim 往 evidence 看，孤儿检查从 source 往 evidence 看。**两个方向都不是「同一来源内的 `document_id` 是否唯一」。**

输出每组漂移的：各 id 的证据条数、正文出现次数、是否等于 `doc-<source stem>`，以及三种候选归一规则各自的结论。

⚠️ **本脚本不自动归一。** 三种规则在本归档里给出不同答案：`doc-6k-power`(10) 与 `doc-rtx6kpro`(10) 打平使多数派失效；`doc-blender`(3) 多数派指向短名但 stem 规则指向长名；而 stem 规则整体只覆盖 349/440 组，故它不是一个可推广的归档惯例。**裁决留给人。**

### `fix_stray_closer.py` — 修复未闭合的字符串

```bash
python scripts/fix_stray_closer.py scripts/_zzNNa.py
```

扫一个待运行脚本里「跨行的中文引号"…"没有闭合」这类错误，并就地修好。用于批量生成 CSV 的脚本，避免 `SyntaxError` 在写入中途才暴露。

### `audit_confidence.py` — `confidence` 的构造规则

```bash
python scripts/audit_confidence.py research/rtx-pro-6000
```

**为什么存在**（第 231 轮）：第 230 轮读 `Prism` 时发现，
`ExecReport.signal` 把权重全写在一个函数里，故那个分数是**可复算**的；
而本归档的 `confidence` 从来没有任何构造规则。于是它「既是一个序关系、
又是一个不可复算的量」。本脚本把这句话量化。

检查三件事：

1. **S2 违规**——`access != open` 却标 `high`/`medium`（应为 0）；
2. **C1 精确违规**——`high` 但**含**非 `primary` 证据。
   ⚠️ 这与 `validate.py` 的 C1 **不同**：后者判据是「**至少一条** `primary`」，
   本脚本判据是「**全部**都是 `primary`」。两个数都对，量的不是同一个东西。
3. **三条候选规则的解释力**——用来证明「没有一条够用」。

**实测（2026-10-28，2,020 条主张）**：

| 候选规则 | 命中 | 解释力 |
|---|---|---|
| A 全部 `primary` ⇒ `high` | 1831 | 90.6% |
| B 全部 `primary` 且 ≥2 条证据 ⇒ `high` | 1025 | 50.7% |
| C 全 `primary` 且非 `interpretation` | 1686 | 83.5% |

反例：169 条全部证据都是 `primary` 却不是 `high`（157 medium / 6 low / 6 disputed）。

⚠️ **本脚本不重算 `confidence`。** 三条规则都远低于 100%，重算会把大批 `high`
降级，而那是研究决策而不是工具能做的。工具能做的最后一件事，
是把它自己做不到的那件事变成可复现的输出。

退出码：`0` 无 S2/C1 精确违规；`1` 有违规（当前 20 条 C1 精确违规）；`2` 输入缺失。

## 内部工具（下划线前缀）

以下脚本是**操作性工具**，不保证接口稳定，主要服务于人工/代理批量写归档。

### `_append_csv.py` — 安全追加

```bash
python scripts/_append_csv.py <目标.csv> <新增行.csv>
```

**为什么存在**：直接用 `csv.DictWriter` 或字符串拼接写这些 CSV 时，一旦某行列数不对（常见原因：中文引号里的 ASCII 逗号、英寸符号 `"`），会在写入中途抛错并把目标文件**截断**——本项目历史上真实发生过一次数据丢失。

本脚本的做法：先读 `utf-8-sig`，**逐行校验列数必须等于目标表头列数**，全部通过后才写 `.tmp` 再用 `Path.replace()` 原子替换。任何一行不合规就整体中止，目标文件不变。

### `_repair_csv.py` — 列错位修复

```bash
python scripts/_repair_csv.py <目标.csv>
```

处理英寸符号（如 `5.4 H x 12.0" L`）导致的列错位，把会造成歧义的 ASCII `"` 替换为 `″`（U+2033）后重新对齐。

## 约定

- **不要**用 `csv.DictWriter` 写 `sources.csv` / `evidence.csv` / `claims.csv`——必须用 `_append_csv.py`。
- 写 CSV 时统一 `quoting=csv.QUOTE_ALL, lineterminator="\n"`，编码 `utf-8-sig`。
- 脚本报错时**不要**用 `git checkout -- <csv>` 回滚：会把未提交的相邻工作一起丢掉。先 `git status` 确认范围。
- 本目录是工具，**不属于研究产物**。提交时 `git add research/`（或明确路径），**不要** `git add scripts/`，否则会把临时草稿一起提交。

## 论文层（r257 新增）

研究档案本身不是交付物；交付物是论文。这一层把 `research/<slug>/` 的
CSV 渲染成一份可提交的文稿，并保证「论文里的每个数字都能回到一条主张」。

| 脚本 | 作用 |
|---|---|
| `render_paper.py` | 读 `paper.json` + `paper/data/*.csv`，生成 `figures/*.png` 与 `tables/*.md` |
| `render_paper_pdf.py` | 把 `PAPER.md` 排成中文 PDF（嵌入宋体/黑体，含中文禁则断行） |
| `audit_paper.py` | 校验引用闭合、图表落地、数值可回溯到 claim -> evidence |
| `check_paper.py` | 校验论文**自身**一致：编号连续、图表被引用、自述数字属实、术语统一、交叉引用有效 |
| `check_layout.py` | 校验 PDF 的**物理形态**：每页字数、图注同页、表格行不跨页、不越右边距、无缺字 |
| `sync_paper_counts.py` | 把正文里的自述数字（「引用了 N 条主张」）与档案同步 |
| `build_paper.py` | 一条命令跑完上面全部**加档案层校验**，并在最后做一致性校验 |

### 四道校验各防什么

档案、论文、论文自身、PDF 物理形态——四个层次，四种失败方式：

| 层 | 脚本 | 失败长什么样 | 它防的是 |
|---|---|---|---|
| 档案 | `validate_research.py` | 引用闭合断了、证据等级不合法 | 档案烂掉 |
| 论文 vs 档案 | `audit_paper.py` | 论文里的数字在档案里找不到 | **编造** |
| 论文 vs 它自己 | `check_paper.py` | 图 7 不存在、说「12 条」而实际 14 条 | **自相矛盾** |
| PDF 的物理形态 | `check_layout.py` | 图注跑到下一页、表格行被劈开、7 页空白 | **能读但没法用** |

⭐ 前三道都只看**内容之间的关系**，没有一道看内容的**物理呈现**——
所以曾经有 7 页空白页（每页只有几个字）全部通过了前三道校验。
第四道是为此补的。

### 为什么需要一个独立的 paper 层

研究档案里的 `REPORT.md` 是**流水账**：它按发现顺序追加，包含大量自我更正、
撤回与旁支。论文是**有选择的呈现**：它必须对读者负责，只保留能支撑论点的材料。

两者不能是同一份文件。但两者必须共享同一批证据——否则论文就会开始生产
档案里没有的数字。`paper/` 目录的存在，就是为了让这种「共享」变成机器可检的：

```
paper/data/*.csv   每一行都有 cite 列 -> claims.csv 里的一个 claim_id
paper.json         每张图/表声明 cites  -> 同上
audit_paper.py     顺着 claim -> evidence_ids -> quote 逐层核对数值
```

### 三处硬约束

1. **数字不许凭空出现**。`render_paper.py` 在出图前校验 `cite` 列，
   缺一条就拒绝生成。
2. **图不许静默变成方块**。`render_paper.py` 把 matplotlib 的
   missing-glyph 警告升级为硬错误——中文字体缺失会直接报错而不是悄悄出图。
3. **PDF 不许越界**。`render_paper_pdf.py` 按显示宽度断行，
   中英混排留 12% 余量，实测 0 处越出右边距。
4. **图不许只在图注里出现**。`check_paper.py` 要求每张图在正文至少被引用一次。
   曾经 10 张图全部零引用——它们只作为 `![图 N]` 嵌在文里，正文从不提。
5. **自述数字不许过期**。`check_paper.py` 会把正文里「本文引用的 N 条主张」
   与实际引用数比对。这个错误在四个不同轮次各复发一次，故 `sync_paper_counts.py`
   把修法也固化了。

### 用法

```bash
# 全量重建（档案校验 -> 图 -> 表 -> PDF -> 三道论文层校验）
python scripts/build_paper.py research/rtx-pro-6000/paper

# 只校验，不写文件（可放进 CI）
python scripts/build_paper.py research/rtx-pro-6000/paper --check
```

### 两份文档该怎么读

`research/<slug>/` 下有两份长文档，规模相差约 50 倍：

| | `paper/PAPER.md` 与 `.pdf` | `REPORT.md` |
|---|---|---|
| 性质 | 综述：已收敛的判断 | 工作档案：逐轮发现与失败记录 |
| 组织轴 | 按**论证** | 按**时间** |
| 读者 | 想知道结论 | 想核对过程或接手 |

**`REPORT.md` 记录「我怎么知道的」，`PAPER.md` 给出「我知道什么」。**

两份**不合并**，因为组织轴不同：按时间组织要读完近 700 节才知道结论，
按论证组织则看不到「结论是怎么被推翻又重建的」——而后者恰恰最该保留。

同步是**单向**的：档案是唯一真相源，论文只能引用它。
论文若引入档案里没有的数字，`audit_paper.py` 直接失败。

只想知道结论，读论文的 `§3.4`（预填解码之别）与 `§9`（成本悖论）；
要核对某个数字，按正文的方括号标记到 `claims.csv`，再按 `evidence_ids`
到 `evidence.csv` 取原文——三级可追。

### 校验器输出里的 `sku_unspecified`

`validate_research.py` 的成功输出里包含 `sku_unspecified=N`。
这个数表示有多少条主张提到了目标产品、但来源没写明是哪个 SKU。

它不是警告，而是一个**欠账计量**：修它需要补来源，而不是改数字。
把它写进成功输出而不是单独的报告，是因为「看不到的债不会还」。
### sku 分类：`classify_sku.py` / `test_classify_sku.py` `classify_sku.py` 给 `claims.csv` 的 `sku` 列做分类。核心规则是**作用域**： 一个 SKU 名称只修饰它附近的那个产品名。 这条规则被四版失败逼出来，每一版都在修一个具体误判： 1. 用功耗当证据 → 把整机功耗判成 Max-Q。改为只用显式 SKU 名。 2. 产品身份与 SKU 判定混在一起 → 「PRO 5000 72GB 版规格」因其证据提到 6000 而被判 unspecified。 改为产品身份只看陈述。 3. SKU 名全文任意位置都算 → PRO 4500 的 Workstation Edition 让 PRO 6000 的主张被判 ws。 改为只在产品名附近取。 4. 单一窗口宽度 → 60 太宽（WS<->5090 对照标注误判）、42 太窄（WS 的 16-pin 漏判）。 改为双窗口：完整 SKU 名 60、多义缩写 12。 `test_classify_sku.py` 有 10 条回归用例，每一条对应上面的一次误判。 改规则必须先让这 10 条继续通过。 python scripts/test_classify_sku.py python scripts/classify_sku.py 两个纪律：`unspecified` 是正式取值（表示来源确实没写），不是失败； RTX 6000D 是独立产品，不是第四个 SKU。
### 论文自检：`check_paper.py` / `test_check_paper.py` `audit_paper.py` 与 `check_paper.py` 的分工： | 脚本 | 查什么 | 防什么 | |---|---|---| | `audit_paper.py` | 论文与**档案**是否一致 | 造假 | | `check_paper.py` | 论文与**它自己**是否一致 | 自相矛盾 | `check_paper.py` 的七项检查： - **I1** 章节编号连续 - **I2** 小节编号与所属章一致（3.2 必须在第 3 章内） - **I3** 图/表编号连续且每个都被引用 - **I4** 图引用编号与图片文件名一致 - **I5** 正文自述数字与实际一致（「本文引用的 N 条主张」这类） - **I6** 术语统一（括号内的中英并列不算不统一） - **I7** 交叉引用 `§X.Y` 的指向存在 I5 上线时立刻抓到一个真缺陷：正文写着「本文引用的 29 条主张」， 而实际已是 36 条。这类数字每加一节就会过期，靠人读发现不了。 `test_check_paper.py` 是**负向测试**：故意注入 5 类缺陷，确认每条都能拦住。 一个检查器如果只会在正确输入上说 OK，它就不是检查器，是印章。 python scripts/check_paper.py python scripts/test_check_paper.py 两者都已接入 `build_paper.py`，故每次重建都会跑。
### 排版健康度：`check_layout.py` / `test_check_layout.py` 四道校验各管一层： | 脚本 | 查什么 | 防什么 | |---|---|---| | `validate_research.py` | 档案层：引用闭合、证据等级 | 档案破碎 | | `audit_paper.py` | 论文与**档案**是否一致 | 造假 | | `check_paper.py` | 论文与**它自己**是否一致 | 自相矛盾 | | `check_layout.py` | PDF 的**物理形态** | 能读但没法看 | 为什么需要第四个：r261 那份 29 页 PDF 里有 7 页只有 40-97 个字 （一个表格行被拆到两页、每页只剩一个词），三个校验器一个都没报。 它们查引用、查数值、查编号，**没人查「这一页是不是空的」**。 检查项： - **L1** 逐页字数下限（300 字，排除首页末页） - **L2** 图与图注同页，且正文确实引用该图 - **L3** 表格行不跨页 - **L4** 文字不越出右边界 - **L5** 无 U+FFFD、字体已嵌入 L2 的第一版判错了两件事，都值得记住： 1. 把「图在页首、上方无正文」判为缺陷。**这是错的**—— 图浮到页首是 LaTeX 的标准做法（[t] 浮动体），不是排版错误。 2. 判定时把页眉文字算成了「图上方的正文」，于是永远不报警。 真正的缺陷只有两种：图注被挤到下一页、正文从未引用该图。 后一条在本项目里**全部 10 张图都犯了**——它们只在图注里出现过， 正文从未写过「如图 N 所示」。这不是格式问题： **图必须在正文被引用，否则它只是插图，不是论据。** `test_check_layout.py` 是负向测试，而且不是伪造 PDF—— 它**真的把渲染器改回有缺陷的版本**重新生成，确认 L1/L3 能拦住（5 个 FAIL）， 再恢复。修好后 23 页，缺陷版 27 页。 python scripts/check_layout.py research/rtx-pro-6000/paper/PAPER.pdf --verbose python scripts/test_check_layout.py
