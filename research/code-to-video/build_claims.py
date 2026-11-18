"""code-to-video 的证据层与主张层。

## 组织原则

主张不按「文献罗列」组织，按**中间表示的类型**与**验证信号的来源**两个轴组织。
本族真正的分歧在这两个轴上，而不在画质：

  中间表示   Manim(2D 数学动画) / Blender(3D 场景) / SVG-CSS(Web 动画) / 通用 harness
  验证信号   只编译 / 编译+渲染 / 渲染+VLM 评分 / 渲染+程序真值比对 / 人评

后两类才是本族特有的能力：**程序本身提供真值**，故可以自动化验证；
端到端像素模型没有这条通路。

## E1 的落地方式

quote 由 resolve() 用正则跨空白匹配、取 m.group(0) 回填，
因此它必然是快照的逐字子串，不靠人眼抄写。

⚠️ 已踩过的坑（写在这里防止重复）：
  1. 多片段引文之间原文常有标点，分隔符只允许空白会漏 —— 用 (?:\s+|[,;:]\s*)
  2. 片段之间隔着整句时任何分隔符都不适用 —— 改用单片段
  3. arXiv HTML 里数字常是 LaTeX 重复渲染（"1.83 × 1.83\\times"）—— 绕过该片段
  4. 换行硬折行会被空白归一化合并 —— 该情况本身没问题，但片段不能跨句
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
AS_OF = "2026-11-18"

# (evidence_id, doc 前缀, 匹配片段, locator, stance, note, claim_id)
EVID = [
    # ===== 为什么要用代码：动机条 =====
    ("e-001", "doc-arxiv-2610-35864",
     ("they cannot reliably render an exact formula, a correct chart, a rule-consistent game or narration synchronized to on-screen events",),
     "1 Introduction / 动机", "supports",
     "本族最清晰的动机陈述：端到端扩散模型无法可靠渲染精确公式、正确图表、"
     "规则一致的游戏、与画面事件同步的旁白。四类都是**有唯一正确答案**的内容", "c-why-code"),
    ("e-002", "doc-arxiv-2610-14495",
     ("A program can be read, diffed, tested and audited; pixels", "can only be watched"),
     "Abstract", "supports",
     "本族的认识论表述：程序可读、可 diff、可测试、可审计；像素只能被观看。"
     "这句话把「代码中间表示」的价值锚在**可审计性**而非画质", "c-auditable"),
    ("e-003", "doc-arxiv-2609-34309",
     ("A program can execute correctly while violating the requested",),
     "Abstract", "supports",
     "⚠️ 本族最重要的理论贡献 P2V gap 的前置句：程序可以正确执行却违背请求。"
     "这一点是整族的存在理由——它说明「编译通过」不构成验收", "c-p2v-gap"),
    ("e-004", "doc-arxiv-2609-34309",
     ("We introduce and define the Program-to-Visual (P2V) gap as the discrepancy between program-level correctness and visual requirement satisfaction",),
     "1 Introduction / 定义", "supports",
     "P2V gap 的正式定义：程序级正确性与视觉要求满足度之间的落差。"
     "本族的全部工作都可读作对这一 gap 的不同应对", "c-p2v-gap"),
    # ===== 基准：测的是什么 =====
    ("e-010", "doc-arxiv-2610-35864",
     ("even the best system satisfies every core requirement on only 76.3",),
     "Findings / (1)", "supports",
     "VibeVideoBench：最强系统也只在 76.3% 的任务上满足**全部**核心要求。"
     "注意口径是「全部满足」，不是「部分得分」——这个口径比平均分严格得多", "c-vibevideo"),
    ("e-011", "doc-arxiv-2610-35864",
     ("239 self-contained tasks in English and Chinese span 12 categories",),
     "1 Introduction / 基准构成", "supports",
     "239 任务 / 12 类 / 中英双语；沙箱内禁用任何图像视频生成模型，"
     "强制只能写代码。这个限制使它能真正测「代码路线」而非「模型画质」", "c-vibevideo"),
    ("e-012", "doc-arxiv-2610-35864",
     ("three quarters of the lost videos are final renders that started too late, ran too slowly or never started",),
     "Findings / 交付轴", "supports",
     "⚠️ 最容易被忽略的发现：交付本身是第二根轴。四分之三的缺片是"
     "「最终渲染开始太晚 / 太慢 / 从未开始」——失败在工程而非创作", "c-delivery"),
    ("e-013", "doc-arxiv-2610-02205",
     ("PROWBench , comprising 170 programmatically constructed episodes and 600 proxy videos",),
     "1 Introduction", "supports",
     "PROWBench：170 个程序化 episode + 600 条代理视频。"
     "它测的是端到端视频模型是否忠于程序规定的事件，是本族的**镜像**："
     "程序给出真值，问像素模型能否对得上", "c-prowbench"),
    ("e-014", "doc-arxiv-2610-02205",
     ("Logic-Render Alignment assesses adherence to the prescribed timeline",),
     "Metrics", "supports",
     "两个指标都可自动化：Logic-Render Alignment 看时间轴是否遵守，"
     "Interaction Success Rate 用引擎日志当真值看事件是否在对应时刻被画出来", "c-prowbench"),
    ("e-015", "doc-arxiv-2603-13251",
     ("Syntactic Hallucinations", "Visual-Logic Drift"),
     "1 Introduction / 两类失败", "supports",
     "ManiBench 把 Manim 生成的失败分为两类：API 幻觉（引用了不存在或已废弃的 API）"
     "与视觉-逻辑漂移（时序错、缺因果）。这个二分很实用，因为它对应两种不同的修法", "c-failure-modes"),
    ("e-016", "doc-arxiv-2611-09769",
     ("reproducing webpage animations is substantially more difficult than reproducing static appearance",),
     "Findings / (1)", "supports",
     "AnimWeb-Bench：复现动画远难于复现静态外观。"
     "这一条把「有代码」与「有时序」两件事分开了——静态外观对了不代表动画对", "c-anim-web"),
    ("e-017", "doc-arxiv-2611-09769",
     ("explicit frame inspection and render feedback improve the reconstruction quality of coding agents",),
     "Findings / (2)", "supports",
     "显式看帧 + 渲染反馈能提升重建质量。这是本族「渲染即反馈」的正面证据", "c-render-feedback"),
    ("e-018", "doc-arxiv-2611-15789",
     ("agents inspect their own renders but fail to correct their errors",),
     "Observation 3", "supports",
     "⚠️ 本族最尖锐的负结果：agent 会看自己的渲染，却改不对错误。"
     "这直接反驳「给了视觉反馈就能自我纠正」的乐观假设", "c-blind-feedback"),
    ("e-019", "doc-arxiv-2609-15478",
     ("The best model reaches 88.6 Latent Similarity but retains only 53.7% of the spatiotemporal facts",),
     "Results", "supports",
     "⚠️ BVB：最好模型潜在相似度 88.6，却只保留 53.7% 的时空事实。"
     "「画面像」与「内容对」之间的巨大落差，是本族最需要警惕的评测陷阱", "c-look-vs-fact"),
    # ===== Manim 线：自改进 =====
    ("e-030", "doc-arxiv-2610-14495",
     ("a lesson that a static check can catch is compiled into a rule with a must-fail and a must-pass example",),
     "Method / 规则入库", "supports",
     "Reels-RSI 的记忆设计：规则要能被静态检查捕获，且必须带 must-fail 与 "
     "must-pass 两个例子才能入库。**记忆本身被单元测试**，这是本族独有的做法", "c-rsi-program"),
    ("e-031", "doc-arxiv-2610-14495",
     ("the rule learned in the field caught four latent defects in frames authored before it existed and none after",),
     "Field study / 结果", "supports",
     "关键结果：学到的规则抓出了**规则存在之前**产出的 4 个潜伏缺陷，"
     "而规则之后产出的片子里一个都没有。这说明规则是可迁移的，不只是过拟合当下", "c-rsi-program"),
    ("e-032", "doc-arxiv-2610-14495",
     ("that rules are an audit for a strong director (eight unguarded reels, no violation) and a guard for a weaker one (thirty violations unguarded versus five)",),
     "Field study / 反向结论", "supports",
     "⚠️ 最有价值的反向结论：规则对强导演起「审计」作用（8 部未加护栏的片子零违规），"
     "对弱导演才是「护栏」（未加保护 30 次违规 vs 加了 5 次）。"
     "故记忆机制的价值依模型强弱而变——这与「越多记忆越好」的直觉相反", "c-rule-depends"),
    ("e-033", "doc-arxiv-2606-30296",
     ("a dual-channel Episodic Memory Bank grown entirely from its own task stream, with no weight updates and no human seeds",),
     "Method / EMB", "supports",
     "ManimAgent 的双通道记忆：正例存成功理由、负例存已证实的坑，"
     "完全从自身任务流生长，无人工种子、不更新权重。", "c-memory-bank"),
    ("e-034", "doc-arxiv-2606-30296",
     ("blind human Pass@1 rises and reflection rounds fall as memory size grows",),
     "Results", "supports",
     "双通道记忆的效果方向：随记忆增长，盲测人评 Pass@1 上升、反思轮数下降。"
     "两个方向同时向好，说明它不是靠多轮试错换来的", "c-memory-bank"),
    ("e-035", "doc-arxiv-2611-08294",
     ("Its 24,034 render-verified, quality-filtered records preserve intermediate programs, execution errors, visual critiques, and corrective revisions",),
     "Method / 数据集", "supports",
     "ManimCode 的数据集价值不在规模而在**保存了中间态**："
     "中间程序、执行错误、视觉批评、修正动作。这才是可训练「修正能力」的资产", "c-feedback-astrain"),
    ("e-036", "doc-arxiv-2611-08294",
     ("a single 4B model, to write, review, and revise animation programs",),
     "Method / 模型", "supports",
     "一个 4B 模型同时会写、会审、会改。这反驳了「必须用闭源大模型才能做」的默认假设", "c-small-model"),
    ("e-037", "doc-arxiv-2604-18364",
     ("94% Render Success Rate (RSR)",),
     "Results / 最强配置", "supports",
     "ManimTrainer：Qwen3 Coder 30B + GRPO + RITL-DOC 达 94% 渲染成功率。"
     "⚠️ 注意口径：RSR 只表示「能渲染出视频」，不代表内容正确", "c-metric-ceiling"),
    ("e-038", "doc-arxiv-2604-18364",
     ("SFT generally improves code quality, while GRPO enhances visual outputs",),
     "Results / 训练策略", "supports",
     "两类训练的分工清晰：SFT 提代码质量，GRPO 提视觉质量。"
     "这对应 P2V gap 的两端——语法端与视觉端需要不同的信号", "c-two-ends"),
    ("e-039", "doc-arxiv-2602-10840",
     ("even the strongest model achieves only a 21.5% Avg@8 accuracy",),
     "Results", "supports",
     "⚠️ SimuScene：最强模型在物理动画上只有 21.5% Avg@8。"
     "这是本族最低的一组绝对值，说明「可执行且视觉正确」远未解决", "c-hardest-domain"),
    ("e-040", "doc-arxiv-2602-10840",
     ("a reinforcement learning pipeline that uses visual rewards from code-generated videos",),
     "Method / 视觉奖励", "supports",
     "用代码生成视频的视觉奖励训纯文本模型——「渲染即奖励」的干净实例。"
     "它把代码路线的可验证性直接变成了训练信号", "c-render-as-reward"),
    ("e-041", "doc-arxiv-2605-15585",
     ("render-feedback-aware constrained code generation",),
     "Problem formulation", "supports",
     "把问题形式化为「渲染反馈感知的约束代码生成」："
     "约束只有在渲染之后才可判。这个形式化精确指出了本族的难点所在", "c-formalization"),
    ("e-042", "doc-arxiv-2602-11790",
     ("they remain limited in scenarios that require strict logical rigor and precise knowledge representation",),
     "1 Introduction / 动机", "supports",
     "LASEV 的动机：端到端模型在要求严格逻辑与精确知识表示的场景受限。"
     "这与 e-001 相互印证，但角度不同——它强调的是**知识正确性**", "c-why-code"),
    ("e-043", "doc-arxiv-2604-05266",
     ("the animation-based instruction gives slightly better post-test scores (83% vs. 78%",),
     "User study", "supports",
     "唯一做了教学效果实验的工作：100 名本科生 A/B，后测 83% vs 78%。"
     "⚠️ 但它是半自动 HITL 管线，专家复核后才渲染——故这个数字不能归功于自动化", "c-pedagogy"),
    # ===== 效率层 =====
    ("e-050", "doc-arxiv-2611-22967",
     ("a finished film takes a median of 10 builds and costs $2.85 in model calls and 11 minutes",),
     "Motivation / 成本", "supports",
     "本族被忽略的成本量化：一部完成片中位 10 次 build、$2.85 模型调用、11 分钟", "c-build-cost"),
    ("e-051", "doc-arxiv-2611-22967",
     ("37.5% of the frames of a session",),
     "Motivation / 冗余", "supports",
     "37.5% 的帧在更早版本里已经画过，却重新渲染了一遍。"
     "这个冗余率说明 build 循环本身的浪费是结构性的", "c-build-cost"),
    ("e-052", "doc-arxiv-2611-22967",
     ("cuts the agent\u2019s wait by 36.3% against Rebuild",),
     "Results", "supports",
     "精确帧复用 + 阻塞感知调度：等待时间降 36.3%（对 Rebuild）/ 57.9%（对 Sequential）。"
     "注意两个基线不同，故这两个数字不可混用", "c-codereel"),
    # ===== Blender / Web / 通用 harness =====
    ("e-060", "doc-arxiv-2403-01248",
     ("a library learning mechanism that compiles common script functions into a reusable library",),
     "Method / library learning", "supports",
     "SceneCraft 的 library learning：把常用脚本函数编译成可复用库，"
     "实现「不调权重也能累积能力」。这是本族最早的记忆形态", "c-library-learning"),
    ("e-061", "doc-arxiv-2403-01248",
     ("models a scene graph as a blueprint, detailing the spatial relationships among assets",),
     "Method / 场景图", "supports",
     "先把场景建成场景图（含空间关系），再翻成数值约束写代码。"
     "「先规划后写码」这一模式在本族反复出现", "c-plan-then-code"),
    ("e-062", "doc-arxiv-2405-07065",
     ("Novices can use code-connected AI editing widgets to make targeted edits",),
     "System / 可编辑性", "supports",
     "LogoMotion 的独特指标是**可编辑性**：代码与 GUI 控件打通，"
     "非程序员能做有目标的局部修改。本族其它工作几乎都不管这件事", "c-editability"),
    # ===== 汇总：本族的边界 =====
    ("e-070", "doc-arxiv-2610-35864",
     ("counting missing videos as zero changes the ranking",),
     "Findings / 口径敏感", "supports",
     "把缺片算 0 会改变排名。故本族的「排名」对交付口径极敏感，"
     "引用任何排名都必须说明缺片如何处理", "c-metric-sensitivity"),
]


# (id, 陈述, confidence, derivation, subquestion, counter_evidence)
CLAIMS = [
    ("c-why-code",
     "这一族选择代码而非像素，不是因为画质，而是因为有一类内容**存在唯一正确答案**："
     "精确的公式、正确的图表、规则一致的交互、与画面事件同步的旁白。"
     "端到端视频模型在这四类上无法可靠渲染，而代码可以。",
     "high", "e-001 与 e-042 从两个不同角度给出同一动机", "q1", ""),
    ("c-auditable",
     "代码中间表示的核心价值是可审计性：程序可读、可 diff、可测试、可审计，"
     "而像素只能被观看。这使得「哪里错了」成为一个可以定位的问题，"
     "而不只是「结果不满意」。",
     "high", "e-002", "q1", ""),
    ("c-p2v-gap",
     "本族最关键的理论区分是 Program-to-Visual (P2V) gap：程序可以正确执行，"
     "却违背用户的视觉要求。故「编译通过」或「能渲染」都不构成验收，"
     "验收必须包含渲染后的视觉判定。",
     "high", "e-003/e-004", "q1", ""),
    ("c-vibevideo",
     "VibeVideoBench 是这一族目前最完整的通用基准：239 个任务、12 类、中英双语，"
     "沙箱内禁用任何图像视频生成模型，强制只能写代码；"
     "最强系统也只在 76.3% 的任务上满足全部核心要求。",
     "high", "e-010/e-011", "q4", ""),
    ("c-delivery",
     "「交付」是本族独立的第二根轴：四分之三的缺片源于最终渲染开始太晚、太慢或从未开始，"
     "即失败发生在工程而非创作。把缺片计 0 会改变排名。",
     "high", "e-012/e-070", "q5", ""),
    ("c-prowbench",
     "PROWBench 构成本族的镜像实验：它用程序化构造的 episode 提供真值，"
     "反过来检验端到端视频模型是否忠于程序规定的时间轴与事件。"
     "其两个指标（Logic-Render Alignment、Interaction Success Rate）均可自动化。",
     "high", "e-013/e-014", "q4", ""),
    ("c-failure-modes",
     "Manim 生成的失败可分为两类且修法不同：Syntactic Hallucinations（引用了不存在或"
     "已废弃的 API，可靠检索与版本约束修复）与 Visual-Logic Drift（时序错、缺因果，"
     "只能靠渲染后判定）。",
     "high", "e-015", "q5", ""),
    ("c-anim-web",
     "把同一思路搬到 Web 动画（CSS/SVG）后出现一个更强的结论："
     "复现动画显著难于复现静态外观。这说明「有代码」与「有时序」是两件不同的事，"
     "静态外观正确不蕴含动画正确。",
     "high", "e-016", "q2", ""),
    ("c-render-feedback",
     "显式看帧与渲染反馈能提升 agent 的重建质量——这是「渲染即反馈」的正面证据，"
     "在本族多个基准上方向一致。",
     "high", "e-017", "q3", "e-018"),
    ("c-blind-feedback",
     "但与上一条相反方向的证据同样明确：agent 会查看自己的渲染，却往往改不对错误。"
     "故「提供视觉反馈」本身不足以构成闭环，还缺「把视觉差异转成代码修改」这一步。",
     "high", "e-018", "q3", "e-017"),
    ("c-look-vs-fact",
     "「画面像」与「内容对」之间存在巨大落差：BVB 中最好模型潜在相似度达 88.6，"
     "却只保留 53.7% 的时空事实。故任何仅以感知相似度为指标的评测都会高估这一族的能力。",
     "high", "e-019", "q4", ""),
    ("c-rsi-program",
     "Reels-RSI 把自我改进移到程序层，并使记忆可被单元测试："
     "一条规则必须能被静态检查捕获，且带 must-fail 与 must-pass 两个例子才允许入库；"
     "实测中学到的规则抓出了规则存在之前产出的 4 个潜伏缺陷，而规则之后零违规。",
     "high", "e-030/e-031", "q2", ""),
    ("c-rule-depends",
     "记忆机制的价值依模型强弱而反转：对强导演，规则起「审计」作用（未加护栏的 8 部片子零违规）；"
     "对弱导演才是「护栏」（未加保护 30 次违规 vs 加了 5 次）。"
     "这与「记忆越多越好」的直觉相反。",
     "high", "e-032", "q3", ""),
    ("c-memory-bank",
     "ManimAgent 的双通道情节记忆完全从自身任务流生长（无人工种子、不更新权重）："
     "正例存成功理由、负例存已证实的坑；随记忆增长，盲测人评 Pass@1 上升且反思轮数下降。",
     "high", "e-033/e-034", "q2", ""),
    ("c-feedback-astrain",
     "ManimCode 的数据集价值不在规模而在保存中间态：中间程序、执行错误、视觉批评、"
     "修正动作。这使「修正能力」本身成为可训练对象，而非只训练「一次写对」。",
     "high", "e-035", "q2", ""),
    ("c-small-model",
     "一个 4B 模型即可同时承担写、审、改三个角色，说明这一族并非必须依赖闭源大模型；"
     "关键在于是否有高质量的反馈轨迹可学。",
     "high", "e-036", "q3", ""),
    ("c-metric-ceiling",
     "本族最常被引用的「渲染成功率」是个弱指标：ManimTrainer 最强配置达 94% RSR，"
     "但 RSR 只表示能渲染出视频，不代表内容或时序正确。"
     "引用该指标时必须与视觉/逻辑指标并列。",
     "high", "e-037", "q4", ""),
    ("c-two-ends",
     "P2V gap 的两端需要不同训练信号：SFT 提升代码质量（语法端），"
     "GRPO 提升视觉输出（视觉端）。故单一信号无法同时改善两端。",
     "high", "e-038", "q2", ""),
    ("c-hardest-domain",
     "物理动画是本族最难的子域：7,659 场景的 SimuScene 上最强模型仅 21.5% Avg@8。"
     "该数字远低于 Manim 教育动画与 Web 动画，说明「领域知识的视觉化」比「代码正确」难得多。",
     "high", "e-039", "q5", ""),
    ("c-render-as-reward",
     "代码路线的可验证性可直接转化为训练信号：用代码生成视频的视觉奖励训练纯文本模型，"
     "已在物理动画上验证有效。这是端到端像素模型难以复制的通路。",
     "high", "e-040", "q1", ""),
    ("c-formalization",
     "这一族最准确的问题形式化是「渲染反馈感知的约束代码生成」："
     "约束只有在渲染之后才可判定。该形式化解释了为何本族的反馈必须包含渲染，"
     "而不能只做静态检查。",
     "high", "e-041", "q1", ""),
    ("c-pedagogy",
     "教学效果上，LLM 生成的 Manim 动画略优于幻灯片（后测 83% vs 78%，p<0.001，100 人 A/B）；"
     "但该实验使用的是半自动 HITL 管线且经专家复核，故不能把效果归因于全自动化。",
     "high", "e-043", "q3", ""),
    ("c-build-cost",
     "本族被普遍忽略的成本是 build 循环本身：一部完成片中位 10 次 build、$2.85、11 分钟，"
     "且 37.5% 的帧是重复渲染。这说明「生成质量」之外还有一条独立的效率轴。",
     "high", "e-050/e-051", "q4", ""),
    ("c-codereel",
     "精确帧复用与阻塞感知调度把 agent 等待时间降低 36.3%（对 Rebuild）与 57.9%（对 Sequential）。"
     "两个数字基线不同，不可混用，也不可与生成质量类指标相减。",
     "high", "e-052", "q4", ""),
    ("c-library-learning",
     "SceneCraft 的 library learning 把常用脚本函数沉淀为可复用库，"
     "实现「不调权重也能累积能力」。这是本族最早的记忆形态，早于后续的情节记忆与规则库。",
     "high", "e-060", "q2", ""),
    ("c-plan-then-code",
     "「先规划后写码」在本族反复出现：SceneCraft 先建场景图再翻数值约束，"
     "OmniManim 先预测关键帧布局再写动画代码，LASEV 先解题再由插图 agent 写代码。"
     "三者在不同后端上收敛到同一模式。",
     "high", "e-061/e-041/e-042", "q2", ""),
    ("c-editability",
     "可编辑性是本族被严重低估的维度：LogoMotion 把代码与 GUI 控件打通，"
     "使非程序员能做有目标的局部修改；其余工作几乎都以「一次性交付」为目标，"
     "不讨论交付之后的修改成本。",
     "high", "e-062", "q3", ""),
    ("c-metric-sensitivity",
     "本族的排名对交付口径极敏感：把缺片计 0 会改变排名。"
     "故引用任何排名或对比都必须说明两点——缺片如何处理、"
     "以及评价是「全部核心要求满足」还是「平均分」。",
     "high", "e-070/e-010", "q4", ""),
]


def resolve(doc: str, parts) -> str | None:
    """在快照中定位引文，返回逐字子串（空白/标点归一化）。"""
    if isinstance(parts, str):
        parts = (parts,)
    files = sorted(p for p in DOCS.glob("*.txt") if p.name.startswith(doc))
    if not files:
        return None
    text = files[0].read_text(encoding="utf-8", errors="replace")
    flat = re.sub(r"\s+", " ", text)
    sep = r"(?:\s+|[,;:]\s*)"
    rx = re.compile(sep.join(re.escape(x).replace(r"\ ", r"\s+") for x in parts))
    m = rx.search(flat)
    return m.group(0) if m else None


def main() -> int:
    ev_rows = []
    fails = 0

    doc2src: dict[str, str] = {}
    with (HERE / "documents.csv").open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            doc2src[(row.get("document_id") or "").strip()] = \
                (row.get("source_id") or "").strip()

    for eid, doc, parts, loc, stance, note, cid in EVID:
        q = resolve(doc, parts)
        if q is None:
            print(f"[E1 FAIL] {eid} {doc} {str(parts)[:70]}")
            fails += 1
            continue
        st = sorted(p for p in DOCS.glob("*.txt") if p.name.startswith(doc))[0].name
        stem = Path(st).stem
        # 快照文件名用虚线（doc-arxiv-2610-35864-full），
        # 但 documents.csv 的主键用点线（doc-arxiv-2610.35864，与 source_id 同构）。
        # ⚠️ 若不转换，doc2src 查不到 -> evidence.source_id 为空 ->
        # C1 读到空串 -> 所有 high 置信被误报「缺一手支撑」。
        # 这与上一份归档的坑同源：**键名格式不一致**，表象像证据不足。
        docid = stem[:-5] if stem.endswith("-full") else stem
        m = re.match(r"doc-arxiv-(\d{4})-(\d{4,5})$", docid)
        if m:
            docid = f"doc-arxiv-{m.group(1)}.{m.group(2)}"
        src = doc2src.get(docid, "")
        if not src:
            print(f"[LINK FAIL] {eid}: docid={docid!r} 不在 documents.csv")
            fails += 1
            continue
        ev_rows.append([eid, src, docid, cid, q, loc, stance, note, cid])

    if fails:
        print(f"\n{fails} 条证据未匹配，先修 quote 再继续")
        return 1

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "source_id", "document_id", "claim_id", "quote",
                    "locator", "stance", "notes", "supports_claim"])
        w.writerows(ev_rows)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of", "confidence",
                    "evidence_ids", "counter_evidence_ids", "derivation", "notes"])
        for cid, stmt, conf, der, sq, counter in CLAIMS:
            eids = [e[0] for e in EVID if e[-1] == cid]
            w.writerow([cid, stmt, "answer", AS_OF, conf,
                        ";".join(eids), counter, der, f"subquestion={sq}"])

    print(f"evidence {len(ev_rows)} ／ claims {len(CLAIMS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
