# 过程笔记：specpilot

按时间顺序记下走过的弯路与判断依据。**只记会影响结论的东西**，不记操作流水。

## 1. 选题与边界

站内已有 `kernel-agent`、`cuda-kernel-rl`、`pd-disagg` 三篇相邻归档，都涉及「agent 在反馈里改系统」，但都不涉及投机解码，也都没有把**判定规则本身**当作研究对象。本文的问题因此定为：

> 一个自动优化循环要什么判据才敢说「改进了」？当改进量只有几个百分点、且奖励容易被 hack 时，判据怎么设计？

而不是「哪个 kernel 更快」。这个选择决定了后面所有取舍：机制（W12/TLV/树）只是必要的背景，重点在 §3（判据）与 §9（交付边界）。

## 2. 取证据：三次返工

### 2.1 第一版：正则兜白空格，55 条锚点挂 25 条

论文快照由 LaTeXML 转 HTML 再取文本，同一句话有多个渲染形态：

| 原意 | 快照里的样子 |
|---|---|
| `4.46×` | `4.46 × \times` |
| `Figure 3` | `Figure\xa0 3` |
| `τ(N)` | `τ ( N )` |
| `'s` | `’s` |
| `12 KB` | `12\u2009KB` |

第一版用 `\s*` 在正则里兜，仍挂 25 条，而且**每次失败都要回原文猜措辞**，往返十几次。

**改法**：给一句原文的**开头与结尾字面锚点**，在「去掉全部空白 + 同形归一」的检索串上 `find()`，再用索引映射回原文偏移取区间。好处：

- 不用记正则元字符（`(`、`{`、`[` 在原文里到处都是）；
- 不用猜空白形态；
- 未命中时能直接报出「锚点后 200 字实际是什么」，一轮改完。

取出的 quote 仍是原文的**连续区间**，不是拼接、不是改写。

### 2.2 第二版：quote 存了归一化文本，E1 判 20 条失败

我把「同形归一」也应用到了存储的 quote 上（`’` → `'`），校验器却拿原文比对——它的 `norm()` 只折叠空白、不做引号映射。于是 20 条被判「不是原文子串」。

**教训**：**检索可以归一，存储必须原文。** 检查器与数据用两套口径时，检查器报的是「我以为的样子」，不是「实际的样子」。这与 `kernel-agent` 记下的 `check_references.py` 把期望值写死是同一类毛病。

修正后 `e1_checked=73, e1_unverifiable=0`（当时；补入机制实现证据后为 81，见 §4.4）。

### 2.3 第三版：悬空引用审计误报 2 条

`research/scripts/launch.sh` 被正则截成 `scripts/launch.sh`，于是报「根目录 scripts/ 缺 launch.sh」。加负向后顾 `(?<![\w/.-])` 后消失。

结果从「12 条缺失」变成「**22 条引用、10 条缺失**」。**误报会掩盖真报**：如果不修，10 条真缺失里会混着 2 条假的，读者有理由怀疑另外 10 条也是假的。

## 3. 判断依据：为什么说「判据是贡献、机制是产物」

### 3.1 支持

1. **有对照。** 无成本模型的单 agent 循环三轮 1.34× vs 2.13×，且对照只碰了「每步 token 数」、没碰占步时 80% 的权重读取。
2. **有负结果。** 附录 F 的关闭方向都带测量依据（11-bit 慢 3×、48 节点树 −4.3%、每节点 0.17ms vs 值 0.063ms）。
3. **机制真的被替换过。** DSpark 复用三条、PRO 6000 移植两条、EAGLE-3 只复用两条——如果机制是贡献，这种替换会削弱结论；实际没有。
4. **判据有失效边界的直接证据。** 注入故障实验里准确率区间重叠、失配率分开 3×。

### 3.2 反对（记下来，不掩盖）

1. **对照只有一个 setting、一次运行。** 「成本模型有效」也可能是「这个 setting 恰好需要一个会看带宽的 agent」。
2. **机制带来的绝对增益很大。** 4.46× → 10.87× 里，W12 与 TLV 的贡献是可观的正数；说「机制只是产物」有贬低之嫌。更准确的说法是「机制可替换，判据不可替换」。
3. **判据本身不新。** 配对运行 + bootstrap 下界是实验方法学的常规做法；本文的贡献是把它**接进自动循环**并给出量级匹配的阈值。
4. **作者自己的框架也是「机制导向」的**：论文标题是 Algorithm Discovery **and** Systems Optimization，摘要先讲机制再讲判据。

结论因此写成：**判据是可迁移的部分，机制是可替换的产物**——而不是「机制不重要」。

## 4. 源码审计：从「没找到」到「作者裁掉了」

### 4.1 第一层证据（弱）

grep `token_forc`、`cost_model`、`master agent`、`memory.json`、`jobs.py`、`replay.py`：

| 词 | 命中 |
|---|---|
| `token_forc` | 0 |
| `cost_model` | 2（README 文字 + `techniques/budget.py` 注释） |
| `master agent` | 0 |
| `memory.json` | 0 |
| `jobs.py` | 0 |
| `replay.py` | 2（都是**引用**，不是文件） |

这只说明「我没找到」。而 `cudaslot.py` 的 docstring 引用 `jobs.Server.start` 与 `identity.INFRA_FILES`（两者都不在树里）时，线索变强了：**代码在引用不存在的东西**。

### 4.2 第二层证据（强）：系统性查「引用了但不存在」

写 `audit_dangling.py`，扫非 vendored 文本里所有 `research/<area>/<path>.md|py` 与根级 `scripts/*.py|sh` 引用，逐一 `exists()`：

```
22 条被引用路径 → 10 条不存在
  knowledge    存在 0 / 缺 7
  validation   存在 0 / 缺 2
  autoresearch 存在 1 / 缺 1（replay.py）
  bench        存在 2 / 缺 0
  scripts      存在 9 / 缺 0
```

缺失**集中**在知识库与验证两个区域，而机制侧（引擎、techniques、bench、scripts）完整。这不是随机缺口，是**裁剪**。

于是结论从「我没找到控制器」升级为「作者交付的是裁剪后的树，裁剪口在 knowledge/validation/replay 上」——后者可复查、可反驳（给出私有分支即可），前者只能算印象。

### 4.3 仍然不能说的

- 不能说「控制器不存在」——只能说「公开快照里没有」。
- 不能说「作者藏了东西」——裁剪可能有正当理由（内部数据、未整理、license）。
- 不能说「复现不了论文数字」——README 自报复现成功；只是复现的是**结果**，不是**循环**。

### 4.4 我自己的范围错误：把补丁当成了 vendored

这是本归档最重要的教训，而且是**我犯的**，不是仓库的问题。

第一版 `audit_repo.py` 写了：

```python
text_files = [p for p in files
              if p.suffix.lower() in (".py", ".sh", ".md", ".json", ".txt")
              and "python/sglang" not in p.as_posix()]   # ← 错
```

本意是排除 SGLang 的 vendored 副本（那个确实不该算进「作者的代码」）。但**补丁本体就住在**
`settings/<setting>/files/python/sglang/...` —— 这个路径同样含 `python/sglang` 子串。
于是一次性排除了 333 个 overlay 文件，包括：

```
specpilot_d5_w12.py      W12 权重格式 + stream-K GEMM + q_pass
specpilot_d8_tlv.py      two-level verify + QNOISE 故障注入钩子
specpilot_tree_gdn.py    snapshot-free GDN 树验证 + 三段 BF16 WY kernel
specpilot_d7_chain.py    prompt admission 的强制链
```

**后果**：我的 `component_hits` 检索（controller / memory / token_forcing / cost_model）
从来没在机制实现上跑过。结论碰巧没错（判定侧确实缺），但**理由不完整**——
我差点把「仓库有 183 个实现文件」写成「仓库是个空壳」，而那是错的。

修正：按路径**结构**判断是否 vendored，而不是按子串包含。

```python
def is_vendored(p: Path) -> bool:
    parts = p.relative_to(repo).parts
    return len(parts) >= 2 and parts[0] == "python" and parts[1] == "sglang"
```

`settings/x/files/python/sglang/...` 的 `parts[0]` 是 `settings`，于是被正确保留。

**教训与 §2.2 是同一条，只是方向相反**：那次是「检查器与数据口径不同」，
这次是「**过滤器的判据与意图不一致**」——用子串表达结构，结构一变就静默失效，
而且失效的方向是「把有当成无」，看起来像结论，其实只是没找。

修正后的直接产出是 c-032/c-033：机制侧 183 个实现文件全部在，连故障注入钩子都在；
而 c-027 的结论不变——缺的是判定侧。两条合起来才是准确的形状。

## 5. 数字纪律

正文里每个仓库数字都由脚本产出，没有手抄：

| 数字 | 出处 |
|---|---|
| 3098 文件 / 2023 `.py` / 62 `.cu` | `audit_repo.py` |
| 316 → 145（去重）/ 145,644 行 | 同上（按内容哈希去重） |
| 183 个机制实现 / 333 个 overlay | 同上（按文件名认定） |
| 272 个 `SPECPILOT_*` 开关 | 同上 |
| 6 个 setting 的 block / 开关 / overlay 数 | 同上（读 `config.json`） |
| 22 引用 / 10 缺失 | `audit_dangling.py` |
| 3 来源 / 81 证据 / 33 主张 / 29 高置信 / 1 争议 | `make_analysis.py` |

**316 → 145 这个去重是必须的**：同一份 overlay 文件在六个 setting 里各存一份，直接数会把重复算成原创代码。第一版没去重，报出「26.6 万行」——比真实值大一倍。

## 6. 校验结果

```
python scripts/validate_research.py research/specpilot
[OK]  (sources=3, evidence=81, claims=33, claims_high=29, claims_disputed=1,
       c3_violations=0, subquestions=7, r2_violations=0, c1_violations=0,
       sku_unspecified=0, s1_with_tz=3, d1_documents=17,
       e1_checked=81, e1_unverifiable=0)
1/1 通过

python tests/test_schemas.py
2 项失败，均在 pd-disagg（与本归档无关，见下）
```

**为什么排除 pd-disagg 的两项失败与本归档无关**：

| 检查 | 报错 | 判定依据 |
|---|---|---|
| `test_docs_quote_real_counts` | `research/README.md` 行 `[pd-disagg]` 声明 78 证据，实际 92 | `git diff` 显示该行在 HEAD 里就是这样，不是本归档改的 |
| `test_report_header_counts_match_data` | `pd-disagg/REPORT.md` 头 `(70,78,9,8)` vs 实际 `(70,92,11,10)` | 同上；`git show HEAD:research/pd-disagg/evidence.csv` 已是 92 行 |

同一条测试对 `specpilot` 的两项检查都通过（`test_docs_quote_real_counts` 逐 slug 配对时 specpilot 行 OK；头行计数 `(3,81,33,29)` == 实际）。

**这是本归档没有「顺手修好」别人的数据**：pd-disagg 的 CSV 在本次工作期间被另一个进程改过（mtime 10:49–11:06，同时 `research/rsi-serving/` 出现），把它按当前数字改 README 会掩盖那次未完成的编辑。

## 7. 已知未做

1. **没有真机复现。** 无 H100 / RTX PRO 6000，所有时延数字都是论文值。
2. **没有 diff `python/` 与上游 SGLang。** 那需要拉上游对照，超出本专题范围；但这会回答「裁剪掉了什么能力」。
3. **没有读论文的附录表 B（十五次晋级明细）。** 那张表能验证「门槛是否真的卡住了大部分改动」，但对本专题的主结论不必要。
4. **没有交叉核对 DDTree / EAGLE-2 / Sequoia 的原始论文。** 基线数字直接采用本文报告值。
