# RSI-Inference Bench 与它那一族：判据的形状决定循环闭不闭

> 状态：完成
> 信息截止：2026-11-09
> 来源 22（14 份基准仓库原文 + 8 篇谱系论文）｜证据 62 ｜主张 15（13 高置信 / 2 medium）｜争议 0
>
> 本文件是**过程档案**：按时间记录做了什么、哪里错了、怎么修的。
> 结论请看 [paper/PAPER.md](./paper/PAPER.md)。

## 0　结论速览

全文论证在 [paper/PAPER.md](./paper/PAPER.md)。五条结论各自对应的主张：

1. 这一族基准的对象换过四代（Kaggle 竞赛 → 研究工程 → 后训练 → 内化进权重），每换一代判据都要重造；RSI-Inference Bench 是第三代的后半段，对象从「模型权重」换成「推理引擎」[c-four-generations]。
2. 它的三条赛道判据形状不同：day-0 是二元（pass/fail），另两条是连续（几何平均加速比）[c-three-tracks][c-judgment-shapes]。
3. 天花板不是「普遍不行」，而是「一半的题有人过、另一半没人过」——15 个 agent × 10 题共 412 次尝试只有 23 次全通过[c-ceiling-is-clustered]。
4. 失败主要是「差一点」：最强 agent 已做对 90.06% 的检查项，却因剩下 10% 一分不得[c-near-miss-gap]。
5. 名字里有 RSI，但循环没闭合——缺的那一段正是「谁来判」，而它至今由人在循环外持有[c-rsi-not-closed][c-method-not-judgment]。

另有四条支撑性判断：三条禁令各自对应一条被堵死的捷径[c-anti-shortcut]；agent 的回归分已能与人类维护者的修复同档[c-oracle-exceeded]；这一族把刷分做成了持续测量的量[c-hacking-institutionalized]；整族此前漏检的原因在检索面而非检索式[c-retrieval-gap]。

## 1　问题

「把 RSI-Inference Bench 和它相关的一系列都补进去。」

这句话里有两件事要先钉死，否则会写成两篇互不相干的摘要：

- **「它」是什么**：RSI-Inference Bench 是 Apple ML Research 的 37 题基准，**没有论文**（README 徽章写 `Paper: coming soon`，CITATION.cff 只有 `@misc` 指向仓库）。故它的一手材料全在仓库里。
- **「相关系列」是什么**：不是「也讲推理的论文」，而是**同一族评测装置**——给 agent 一个真实可执行环境 + 一个下游指标，判据是「交付物跑起来之后是多少」。这一族站内一篇都没有。

核心假设：

> 这一族基准的判别力不来自任务难度，而来自**判据能不能被独立重跑**。

这条假设可被反驳：找到「判据不可重跑但判别力很强」的基准即失效。第 7 章记了这条假设被削弱的地方。

## 2　方法与可复现

```
build_sources.py      14 份仓库原文 + 8 篇 arXiv 全文 -> sources.csv / documents.csv / documents/
build_claims.py       53 条证据 + 15 条主张（quote 逐条按构造回填，子串性质不靠手抄）
make_data.py          论文数据层，每行带 cite
make_figures.py       图（数值全部来自 paper/data/*.csv）
```

校验：

```
python scripts/validate_research.py research/rsi-inference-bench   # 档案层
python scripts/audit_paper.py research/rsi-inference-bench/paper   # 论文 vs 档案
python scripts/check_paper.py research/rsi-inference-bench         # 论文 vs 自己
```

## 3　逐轮记录

### r1　为什么它此前一次都没被检索到

查了一遍：站内 13 个归档里 12 个是纯 arXiv，`rsi-inference` 的 57 条来源 **100% 来自 arXiv**，其 `fetch_rsi.py` 只调 `ArxivProvider`。而这一族的锚点没有 arXiv 条目。故这不是「式子写得不够宽」，是**检索面根本不覆盖**。

**教训**：当一个待查对象的引用形式是 `@misc` + GitHub 仓库时，任何 arXiv-only 的流程都会稳定地漏掉它，且漏得毫无声响——因为校验器只检查「引用了的存不存在」，从不检查「该有的有没有」。

### r2　第一次写证据表时差点造假

leaderboard 的数字在原始 HTML 里写成 `.2667`（省略前导零），这不是合法 JSON。我先把内嵌对象抽出来、补零、缩进，存成 `rsi-leaderboard.json`，然后打算直接引它。

**这一步是错的**：加工过的 JSON 里，`"pass_at_1": 0.2667` 这句话在原始材料里**不存在**。E1 会被绕过（因为快照就是我加工的那个文件），但证据链实际断了。

改法：把原始 `docs/leaderboard.html` 逐字节存为 `leaderboard_raw.html`，所有引文改从它取——`"model_support":{"pass_at_1":.2667` 是原文子串。加工版保留，但 `parser_version` 明确标 `derived-json-v1`，且注明「它的每一个字都能在上一条里找到」。

**教训**：快照的「可信」不是它自己声称的，而是**它有没有被加工过**。加工后的文件当快照用，E1 会全绿，而 E1 校验的是「quote 是不是这个文件的子串」，不是「这个文件是不是原文」。

### r3　把 day-0 说成「纯二元判据」——被自己的证据推翻

初稿写「day-0 是唯一的二元判据赛道，因为起不起来只有两个结果」。核到 MiniMax-M3 那道题的任务书时发现两句话：

- `Efficient production serving is part of acceptance.`
- `Inadequate performance can fail even with correct`（输出）

也就是至少这一题把效率写进了验收，且性能不足即使输出正确也会失败。故准确说法是「**主判据**是二元，但至少一题叠加了连续判据」。

这两条被记为 `refutes` 立场的证据（e-007 / e-008），挂在 `c-judgment-shapes` 的 `counter_evidence_ids` 上。**反驳自己的证据也是证据，不该被删掉换成一句更顺的话。**

### r4　「天花板」不是一个数，是一张分布

一开始只写了「最强 agent pass@1 = 0.2667」。这个数字单独没有解释力——它可能是「所有题都过 26.7%」，也可能是「一半的题全过、一半全不过」。

逐题聚合后是后者：10 题里 5 题有 agent 全通过过、5 题全场 0 通过；15 个 agent × 10 题共 412 次尝试里只有 23 次全通过，且只有 6 个 agent 有过任何一次。这个形状才可行动——它指向「这 5 道题的判据或环境有问题」，而不是「agent 普遍不行」。

**教训**：聚合指标（pass@1、均值）会把分布形状吃掉，而形状常常是唯一可行动的结论。凡是要报一个率，先问它的分布长什么样。

### r5　oracle 与 agent 分不能直接相减

回归题 `regression_fp8_decode_throughput` 的 `task.toml` 里写着 `oracle_speedup = 1.206`（人类维护者的已合并修复），而排行榜上最强 agent 的回归赛道是 2.1899×。看上去「agent 是人类修复的 1.8 倍」。

**不能这么写。** oracle 是**单题、三形状**的几何平均；agent 的 regression_speedup 是**7 道回归题**的几何平均。分母不同，相减没有意义。

改成：量级上 agent 已经能与人类修复同档或更高，并把这个口径差异写进 `derivation`。这一条宁可写弱，也不写成一个精确但错误的倍数。

### r6　验证本身比 agent 干活还贵

核 `task.toml` 时注意到一个此前没预料到的事实：SD3 那道题的 `agent.timeout_sec = 30000`（8.33 小时），而 `environment.build_timeout_sec = 7200`（2 小时）——**重建一次引擎就给 2 小时**，验证器另有 3600 秒。

这说明这一族的成本结构不在「出题」，在「每道题都要能在任意机器上独立重建并复现同一判据」。配套证据：Pier 被 vendored 进 241 个文件；权重不分发但由 672 条 manifest、540 个 sha256 钉住。

**这条是本篇最反直觉的发现**：人们以为基准贵在题目设计，实际贵在**环境可重建性**。

### r7　「这一族已形成公共考场」——一个推断，降为 medium

DataMaster 同时在 MLE-Bench Lite 与 PostTrainBench 上评，RSI-Dojo 直接以 PostTrainBench 为主指标。看上去「公共考场」已经成型。

但往下推一步就变成推断：RSI-Inference Bench 的 leaderboard 快照里 15 个 agent 全是通用模型名、没有第三方团队自报名。这是**关于惯例的推断**，不是文档明写的规则。故 `c-shared-arena` 与 `c-spec-side` 都降到 `medium`，并各自在 `derivation` 里写明推断链。

## 4　已知缺口

1. **锚点没有论文。** RSI-Inference Bench 的 `Paper: coming soon` 徽章是 2026-10 的快照状态；如果论文后来发布了，本篇的口径层就需要补一次。这是全篇最脆的一处，因为方法学（为什么这样切三条赛道）本该由论文承担，现在只能从 README 的图注与 task.toml 反推。
2. **leaderboard 是滚动快照。** 我用的是 `2026-10-25T2208Z` 那一版（15 agent / 555 条计分结果）。分数会变，故所有涉及排名的陈述都绑定了这个快照 id。
3. **没有自跑实验。** 全篇数字二手，但每条都能点回仓库原文或 arXiv 全文。
4. **「相关系列」的边界是人工判断。** 8 篇谱系论文里，DataMaster / AutoTrainess / CLEAR 三条是我按「同一族装置」纳入的旁证，未被任何校验器覆盖。
5. **无法回答「这条线多久到 RSI」。** 语料里没人给时间线；`c-rsi-not-closed` 只定位，不预测。

## 5　未解决问题

- **判据能不能被 agent 自己改？** 全族没有一篇让 agent 去改「谁判它对」。RSI-Dojo 的作者把「让 agent 去演化评测」写成下一步，但没有做。这是 `c-rsi-not-closed` 的核心，也是这条线上唯一还没人占的位置。
- **pass@1 是不是过严？** 最强 agent 已做对 90.06% 的检查项却零分。基准作者是明确选择的（`A partial pass counts as a failure`）。这个选择让 day-0 的分数主要在度量「全对能力」而非「接近程度」——但反过来，若给部分分，本文最关心的「起不起来」这个二元事实就被稀释了。两种选择各自丢掉一半信息，目前无人给出折中。
- **8 小时预算是否恰好压在人类仍有优势的区段？** RE-Bench 报「给到 8 小时人类超过最好 agent」，而 RSI-Inference Bench 的 agent 预算正是 8.33 小时。这只是时间尺度的巧合，还是刻意的对照设计，材料里没写。

---

## 校验结果

`sources=22, evidence=62, claims=15, claims_high=13, claims_disputed=0, trace_events=14, c3_violations=0, subquestions=5, r2_violations=0, c1_violations=0`

由 `python scripts/validate_research.py research/rsi-inference-bench` 现算；E1 可校验 62 条、无法校验 0 条。

## 附录 A　子问题状态

| id | 问题 | 状态 |
|---|---|---|
| q1 | 三条赛道的判据、预算、验证各是什么 | ✅ answered |
| q2 | 从 MLE-bench 到它，对象怎么一路换 | ✅ answered |
| q3 | 天花板在哪，是能力问题还是判据问题 | ✅ answered |
| q4 | 离线 / pinned / 独立 verifier 各堵哪条捷径 | ✅ answered |
| q5 | 与 RSI 的关系：循环闭合了吗 | ⚠ partial |

q5 记 `partial` 的理由：位置能说清（判定权在循环外），但「为什么不闭合」在语料里只有作者的一句「下一步」，没有可核的失败案例。

## 6　参考文献

### 基准仓库（一手，无 arXiv）

- [src-ml-rsi-bench-readme] RSI-Inference Bench README —— 赛道定义与评分工序
- [src-ml-rsi-bench-leaderboard] docs/leaderboard.html —— 排行榜原始快照（2026-10-25T2208Z）
- [src-ml-rsi-bench-leaderboard-json] 同上，重排版（分析用，非一手）
- [src-ml-rsi-bench-task-day0-sd3] task/support_sd3_2xh100_sglang 说明书
- [src-ml-rsi-bench-task-day0-sd3-toml] 同题 task.toml —— 49 项检查与超时
- [src-ml-rsi-bench-task-day0-minimax] task/support_minimax_m3_4xb200_vllm 说明书
- [src-ml-rsi-bench-task-day0-minimax-toml] 同题 task.toml
- [src-ml-rsi-bench-task-regression] task/regression_fp8_decode_throughput 说明书
- [src-ml-rsi-bench-task-regression-toml] 同题 task.toml —— oracle 与 guard
- [src-ml-rsi-bench-task-optimize-qwen] task/optimize_qwen3_6_27b_1xh100_open 说明书
- [src-ml-rsi-bench-task-optimize-toml] 同题 task.toml
- [src-ml-rsi-bench-pier-readme] third_party/pier README
- [src-ml-rsi-bench-acknowledgements] ACKNOWLEDGEMENTS —— 上游依赖与可重建性
- [src-ml-rsi-bench-citation] CITATION.cff

### 谱系论文（arXiv）

- [src-arxiv-2410-07095] MLE-bench（2024-10-09）
- [src-arxiv-2411-15114] RE-Bench（2024-11-22）
- [src-arxiv-2603-08640] PostTrainBench（2026-03-09）
- [src-arxiv-2605-10906] DataMaster（2026-05-11）
- [src-arxiv-2606-31551] AutoTrainess（2026-06-30）
- [src-arxiv-2609-35561] RSI-Master（2026-09-28）
- [src-arxiv-2611-03698] RSI-Dojo（2026-10-29）
- [src-arxiv-2611-06263] CLEAR（2026-11-04）
