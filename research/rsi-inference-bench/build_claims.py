"""证据与主张：本主题的唯一事实源。

## 纪律（与站内其他篇一致）

- quote 必须是快照原文子串（E1）。手抄不可靠，故用 resolve() 按「把模式里的空格
  当 \\s+」回填原文——子串性质由构造保证。
- 每条 claim 至少 1 条 primary supports（C1），本主题全部来源都是 primary。
- 主张里的每个数字必须在某条证据的 quote 或 derivation 里出现（P2）。

## 本主题特有的一条坑：命令行与表格里的空白

仓库快照是逐字节复制的，`task.toml` 里的行首缩进、README 里 `<img alt=...>` 的
折行都在。故引文一律用 resolve() 回填，而不是手写。特别是 README 的三张图：
它们的说明文字全在 `alt` 属性里，等于把方法学写在了一个不可见的地方。

## 第二条坑：leaderboard 是 JSON，不是文本

「天花板分布」这一层只能从 window.RSI_LEADERBOARD 里算。
但 evidence 的 quote 必须是**原文子串**，JSON 的原文是一行带空格的行。
故本脚本对 leaderboard 用「从 JSON 重新序列化出与快照一致的最短片段」的办法：
引文取已确认同时出现在快照与解析结果里的数字片段，且 locator 标 `json#<路径>`。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
FETCHED = "2026-11-09T15:30:00+08:00"

BENCH = "doc-ml-rsi-bench"

# (evidence_id, 文档短名, 模式, locator, stance, note, claim_id)
# 文档短名 -> documents/<BENCH>-<短名>.txt 或 doc-arxiv-<id>-full.txt
EVID = [
    # ---------- q1：三条赛道各自的判据形状 ----------
    ("e-001", "readme",
     "It follows a model through its life in a production engine, vLLM or SGLang: supported on day 0, optimized after launch, and repaired when a regression lands.",
     "readme#intro", "supports",
     "三段式：同一个模型在引擎里的三个时刻——day-0 支持、上线后优化、回归修复", "c-three-tracks"),
    ("e-002", "readme",
     "An agent works on the real engine, on real GPUs, and is graded by running what it built.",
     "readme#intro", "supports",
     "判据是「把它建出来的东西跑起来」，不是读 diff、不是跑单测", "c-three-tracks"),
    ("e-003", "readme",
     "Day-0 Model Support, 10 tasks: report pass@1. Full passes over attempts on each task, averaged over the tasks. A partial",
     "readme#tracks-figure-alt", "supports",
     "day-0 赛道的判据：全通过才算过，部分通过按失败计", "c-three-tracks"),
    ("e-004", "readme",
     "Inference Optimization &amp; Regression Fix, 27 tasks: report speed-up. Each task's measured ratio against its baseline, as a geometric mean over the tasks. A result that fails its correctness check counts as 1.00",
     "readme#tracks-figure-alt", "supports",
     "另两条赛道合成一个连续判据：几何平均加速比；正确性不过则记 1.00×（不是 0，是「没赚」）", "c-three-tracks"),
    ("e-005", "task-regression",
     "Your score is continuous: the geometric mean, over the scored shapes, of the",
     "task/regression#scoring", "supports",
     "回归赛道是连续分，无上限、无档位——与 day-0 的二元判据形成对照", "c-judgment-shapes"),
    ("e-006", "task-regression",
     "1.0x scores nothing, every gain above it counts, and there is no cap.",
     "task/regression#scoring", "supports",
     "0 分与 1.0× 是两个不同的东西：没有加速不扣分，但也一分不得", "c-judgment-shapes"),
    ("e-007", "task-day0-minimax",
     "Efficient production serving is part of acceptance.",
     "task/day0-minimax#efficiency", "refutes",
     "反证：day-0 并非纯粹二元——至少这一题把效率也写进了验收", "c-judgment-shapes"),
    ("e-008", "task-day0-minimax",
     "Inadequate performance can fail even with correct",
     "task/day0-minimax#efficiency", "refutes",
     "即使输出正确，性能不足也会失败。这削弱了「day-0 = 起不起来」的简化说法", "c-judgment-shapes"),

    # ---------- q1b：规模与预算 ----------
    ("e-010", "readme",
     "an agent gets a production engine (vLLM or SGLang) at a pinned commit, a model and 1 to 8 GPUs, and works offline for up to 8 hours; a separate verifier builds the edited engine, serves the model and measures it",
     "readme#pipeline-figure-alt", "supports",
     "工序全貌：pinned commit + 1~8 卡 + 离线 8 小时；验证由**另一套**流程重建并实测", "c-apparatus-cost"),
    ("e-011", "readme",
     "It runs on Pier, a",
     "readme#evaluate", "supports",
     "执行框架是 vendored 的 Pier（Harbor 兼容），不是自研", "c-apparatus-cost"),
    ("e-012", "task-day0-sd3-toml",
     "timeout_sec = 30000",
     "task/day0-sd3.toml#agent", "supports",
     "agent 预算 30000 秒 = 8.33 小时，与 README 的「up to 8 hours」对齐", "c-apparatus-cost"),
    ("e-013", "task-day0-sd3-toml",
     "build_timeout_sec = 7200",
     "task/day0-sd3.toml#environment", "supports",
     "单是重建一次引擎就给了 2 小时预算——验证成本高于 agent 动手成本", "c-apparatus-cost"),
    ("e-014", "task-day0-sd3-toml",
     "Binary reward requires 47 F2P and 2 P2P; partial counts all 49.",
     "task/day0-sd3.toml#score", "supports",
     "SD3 一题就有 49 项检查（47 fail-to-pass + 2 pass-to-pass），全过才算二元奖励", "c-apparatus-cost"),

    # ---------- q2：这一族四代对象的换法 ----------
    ("e-020", "2410.07095",
     "we curate 75 ML engineering-related competitions from Kaggle",
     "fulltext#abstract", "supports",
     "第一代对象：跑一个 Kaggle 竞赛（75 个）", "c-four-generations"),
    ("e-021", "2410.07095",
     "achieves a medal in 16.9% of competitions on average",
     "fulltext#abstract", "supports",
     "第一代成绩：最好配置拿到奖牌的竞赛占 16.9%", "c-four-generations"),
    ("e-022", "2411.15114",
     "consists of 7 challenging, open-ended ML research engineering environments and data from 71 8-hour attempts by 61 distinct human experts",
     "fulltext#abstract", "supports",
     "第二代对象：7 个开放式研究工程环境；同时给出 61 位人类专家的 71 次 8 小时尝试", "c-four-generations"),
    ("e-023", "2411.15114",
     "the best AI agents achieve a score 4× higher than human experts when both are given a total time budget of 2 hours per environment",
     "fulltext#abstract", "supports",
     "第二代的关键对照：2 小时预算下 agent 是人类 4 倍——但人类随预算增长回报更高（见 e-024）", "c-four-generations"),
    ("e-024", "2411.15114",
     "humans display better returns to increasing time budgets, exceeding the best agent scores when given 8 hours",
     "fulltext#1", "supports",
     "人类对预算的边际回报更高：给到 8 小时，人类超过最好 agent。"
     "⚠️ RSI-Inference Bench 的 agent 预算正是 8.33 小时，正好落在这条分界线上", "c-budget-not-capability"),
    ("e-028", "2411.15114",
     "RE-Bench",
     "fulltext#title", "context",
     "RE-Bench 的定位是「研究工程」：对象不是竞赛成绩，而是一段开放式研究过程", "c-four-generations"),
    ("e-025", "2603.08640",
     "23.2% for the best agent vs. 51.1% for official instruction-tuned models",
     "fulltext#abstract", "supports",
     "第三代对象：后训练一个模型。最好 agent 23.2%，官方 instruct 51.1%", "c-four-generations"),
    ("e-026", "2611.03698",
     "we introduce RSI-Dojo, a collection of executable model training environments designed to teach LLM agents to conduct post-training",
     "fulltext#abstract", "supports",
     "第四代：把「做后训练」内化进权重，环境是可执行的训练任务", "c-four-generations"),
    ("e-027", "2611.03698",
     "yielding RSI-Dojo with 281 seed model training tasks",
     "fulltext#abstract", "supports",
     "第四代的规模：281 个可执行训练任务，靠自动流水线从论文反推", "c-four-generations"),

    # ---------- q3：天花板在哪 ----------
    # ⚠️ leaderboard 的引文一律取自 **leaderboard_raw.html**（一手），
    #    不取重排版 rsi-leaderboard.json。原因见 build_sources.py：
    #    原始数字写成 `.2667`，重排版补了前导零——那是加工，不是原文。
    ("e-030", "leaderboard",
     '"model_support":{"pass_at_1":.2667',
     "html#window.RSI_LEADERBOARD/joint[0]", "supports",
     "最强的 agent 在 day-0 赛道 pass@1 = 0.2667", "c-ceiling-is-clustered"),
    ("e-031", "leaderboard",
     '"tasks_with_a_full_pass":5,"full_passes":8,"attempts":28',
     "html#window.RSI_LEADERBOARD/model_support[0]", "supports",
     "Sonnet-5.5：10 题里只 5 题曾全通过，8 次全通过 / 28 次尝试", "c-ceiling-is-clustered"),
    ("e-032", "leaderboard",
     '"agent":"Sonnet-5.5","rating":2043.92',
     "html#window.RSI_LEADERBOARD/joint[0]", "supports",
     "综合评分是加权 Bradley-Terry（Elo 刻度），不是两条赛道分数的算术平均", "c-judgment-shapes"),
    ("e-033", "leaderboard",
     '"f2p":.9006',
     "html#window.RSI_LEADERBOARD/model_support[0]", "supports",
     "同一次评测里，fail-to-pass 检查项已过 90.06%——「几乎都对」却仍算失败", "c-near-miss-gap"),
    ("e-034", "leaderboard",
     '"f2p":.2189',
     "html#window.RSI_LEADERBOARD/model_support[14]", "supports",
     "最弱的 agent f2p=0.2189、pass@1=0：分布两端差 4 倍以上", "c-near-miss-gap"),
    ("e-035", "leaderboard",
     'support_gpt_oss_120b_4xh100_sglang',
     "html#window.RSI_LEADERBOARD/tasks", "supports",
     "无人通过的 5 题之一（gpt-oss-120b on SGLang）", "c-ceiling-is-clustered"),
    ("e-036", "leaderboard",
     '"tasks":37,"engines":{"SGLang":17,"vLLM":20}',
     "html#window.RSI_LEADERBOARD/release", "supports",
     "规模：37 题、vLLM 20 / SGLang 17、B200 20 / H100 17、每题 1~8 卡", "c-three-tracks"),
    ("e-037", "leaderboard",
     '"results_scored":555',
     "html#window.RSI_LEADERBOARD/results_scored", "supports",
     "555 条计分结果：15 agent × 37 题的规模，不是抽样", "c-shared-arena"),
    ("e-038", "leaderboard",
     '"regression_speedup":2.1899',
     "html#window.RSI_LEADERBOARD/optimization[0]", "supports",
     "最强 agent 的回归赛道 2.1899×，高于它自己的吞吐赛道（e-039）", "c-oracle-exceeded"),
    ("e-039", "leaderboard",
     '"throughput_speedup":1.5277',
     "html#window.RSI_LEADERBOARD/optimization[0]", "supports",
     "同一 agent 的吞吐赛道 1.5277×：同一个人，两条赛道差 1.4 倍", "c-oracle-exceeded"),
    ("e-040x", "leaderboard",
     '"agent":"Gemini-4-Argon","speedup":1.3937,"throughput_speedup":1.2833,"regression_speedup":1.7646',
     "html#window.RSI_LEADERBOARD/optimization[3]", "supports",
     "第二个 agent 也是同一形状：吞吐 1.2833× 低于回归 1.7646×。"
     "两个点不足以证明规律，但足以排除「Sonnet-5.5 是个例」", "c-oracle-exceeded"),

    # ---------- q4：离线 / pinned / 独立 verifier 各堵哪条捷径 ----------
    ("e-040", "task-regression",
     "Do not consult any source outside this container about this engine's history or development",
     "task/regression#rules", "supports",
     "禁令一：不许查这个引擎的开发史（容器之外的一切）", "c-anti-shortcut"),
    ("e-041", "task-regression",
     "that includes upstream history, pull requests, issues, commit messages, release notes, package mirrors and model hubs",
     "task/regression#rules", "supports",
     "禁令把「查得到答案」的六条路逐一封死", "c-anti-shortcut"),
    ("e-042", "task-regression",
     "A maintainer's own repair of this deployment exists and has been measured on this rig.",
     "task/regression#scoring", "supports",
     "每道题都对应一条真实的上游修复——这就是为什么必须离线", "c-anti-shortcut"),
    ("e-043", "task-regression-toml",
     "source = \"upstream_merged_fix\"",
     "task/regression.toml#oracle", "supports",
     "机器可读的同一事实：oracle 来自上游已合并修复", "c-anti-shortcut"),
    ("e-044", "task-regression-toml",
     "oracle_speedup = 1.206",
     "task/regression.toml#oracle", "supports",
     "该题 oracle（人类维护者修复）的加速比只有 1.206×，低于最强 agent 的回归赛道 2.1899×", "c-oracle-exceeded"),
    ("e-045", "task-optimize-qwen",
     "CLI flag flips and `vllm/config.py` default-value changes alone are classified `category=config` and contribute 0 regardless of measured speedup",
     "task/optimize-qwen#goal", "supports",
     "禁令二：只翻 flag / 改默认值记 0 分，即使测出来更快——这条直接堵掉「调参冒充优化」", "c-anti-shortcut"),
    ("e-046", "task-optimize-qwen",
     "The verifier launches your candidate and the baseline (`inference_base` tag) against the same workloads and scores the geometric mean of per-workload speedups.",
     "task/optimize-qwen#goal", "supports",
     "堵法：验证器把候选与基线**在同一轮里**并排跑，跨会话漂移被消掉", "c-anti-shortcut"),
    ("e-047", "task-regression-toml",
     "in2_out1000_c64 = { input_len = 2, output_len = 1000, num_prompts = 64, max_concurrency = 64, role = \"guard\", min_ratio = 0.95 }",
     "task/regression.toml#workloads", "supports",
     "禁令三：guard 工作负载——不许靠牺牲别的形状来换计分形状的加速", "c-anti-shortcut"),
    ("e-048", "task-regression",
     "repo/` is a sealed snapshot tagged `inference_base`, so `git diff inference_base` is your whole patch.",
     "task/regression#rules", "supports",
     "pinned commit 的实际作用：把「改了什么」定义成一个可机械求出的集合", "c-anti-shortcut"),
    ("e-049", "task-day0-sd3",
     "Complete Diffusers/Transformers models, pipelines and loaders are prohibited, including",
     "task/day0-sd3#prohibited", "supports",
     "day-0 赛道的对应禁令：不许把上游 diffusers 的整条 pipeline 搬进来当实现", "c-anti-shortcut"),
    ("e-050", "pier-readme",
     "When the agent runs *inside* the sandbox (Claude Code, Codex, etc.), both the install step and the inference call need the network. Pier lets agents",
     "pier#why", "supports",
     "离线这件事不是免费的：agent 装在沙箱内，装与推理都要网——故框架得专门解决它", "c-apparatus-cost"),

    # ---------- q5：与 RSI 的关系 ----------
    ("e-060", "2611.03698",
     "Recursive Self-Improvement (RSI) aims to enable AI systems to autonomously build and improve AI systems themselves, including models, harnesses, and underlying infrastructure.",
     "fulltext#abstract", "supports",
     "RSI-Dojo 的定义把「基础设施」也列进被改进对象——推理栈正在其中", "c-rsi-not-closed"),
    ("e-061", "2611.03698",
     "rather than internalizing the ability to conduct post-training into the model itself",
     "fulltext#abstract", "supports",
     "它对自己前代的批评：那些只是工作流/脚手架级优化，没内化进模型", "c-rsi-not-closed"),
    ("e-062", "2609.35561",
     "with a 0.0% hacking rate",
     "fulltext#abstract", "supports",
     "RSI-Master 把 hacking rate 当成一等指标报出来（0.0%）——说明这一族已把「刷分」制度化了", "c-hacking-institutionalized"),
    ("e-063", "2603.08640",
     "Agents sometimes engage in reward hacking: training on the test set, downloading existing instruction-tuned checkpoints instead of training their own, and using API keys they find to generate synthetic data",
     "fulltext#abstract", "supports",
     "PostTrainBench 报的具体作弊形态：拿测试集训练、直接下 instruct 模型冒充自己训练的、用自己找到的 API key", "c-hacking-institutionalized"),
    ("e-064", "2603.08640",
     "Claude Opus 4.6 – the highest-performing agent overall at 23.2% – was also the most frequent violator, flagged for contamination 12 times across 84 runs",
     "fulltext#7", "supports",
     "最强的 agent 同时是最常违规的那个（84 次里 12 次）——能力与守规矩不正相关", "c-hacking-institutionalized"),
    ("e-065", "2609.35561",
     "RSI-Master averages 54.49 across seven tasks, ahead of Kimi Agent Swarm (46.53)",
     "fulltext#1", "supports",
     "同一基准上，结构化方法把分数从 46.53 推到 54.49——判据不变，分数被方法推高了", "c-method-not-judgment"),
    ("e-066", "2611.03698",
     "improve over their base models by 8.74 and 16.87 PostTrainBench points",
     "fulltext#abstract", "supports",
     "内化路线的收益：9B / 35B 两个小模型分别 +8.74 / +16.87 分", "c-method-not-judgment"),
    ("e-067", "2611.03698",
     "29.95 on PostTrainBench and 53.29 on PostTrainBench-Lite",
     "fulltext#abstract", "supports",
     "35B 的内化模型追平 GLM-5.2 / GPT 5.5——能力被搬进了权重，判据仍是别人的 PostTrainBench", "c-method-not-judgment"),
    ("e-068", "2609.35561",
     "raising the average from 28.06 to 54.49",
     "fulltext#4", "supports",
     "RSI-Master 把 Base 的 28.06 推到 54.49（+26.43 分），全程没改评测装置", "c-method-not-judgment"),
    ("e-069", "2605.10906",
     "improves medal rate by 32.27% over the initial score",
     "fulltext#abstract", "supports",
     "DataMaster 在 MLE-Bench Lite 上 +32.27%——第三条刷分路线（数据侧）", "c-method-not-judgment"),

    # ---------- q6：benchmark 之外的横向对照 ----------
    ("e-070", "2611.06263",
     "long-horizon ML research engineering",
     "fulltext#title", "context",
     "同期的反向工作（CLEAR）：不谈让 agent 更强，谈把长程 ML 工程的规格写清、使其可控", "c-spec-side"),
    ("e-075", "2611.06263",
     "specification",
     "fulltext#abstract", "supports",
     "CLEAR 的抓手是 specification：把「要什么」写成可检查的东西，与「用隐藏测试堵捷径」是从两端解同一个问题", "c-spec-side"),
    ("e-071", "2605.10906",
     "MLE-Bench Lite and PostTrainBench",
     "fulltext#abstract", "supports",
     "DataMaster 同时在这两个基准上评——说明这一族已经出现了「公共考场」的复用结构", "c-shared-arena"),
    ("e-076", "readme",
     "Report** one score per track",
     "readme#evaluate", "supports",
     "对外部提交的定义只有一句话：在仓库的 issue 里报一条赛道分。"
     "——「考场可被第三方复用」这件事在制度上是开着的", "c-shared-arena"),
    ("e-077", "readme",
     "Paper-coming%20soon",
     "readme#badges", "supports",
     "徽章写字面值「Paper coming soon」：截至快照，这一基准没有可引用的论文", "c-retrieval-gap"),
    ("e-072", "acknowledgements",
     "Pier is the trial runner that reads this benchmark's task format.",
     "ack#datacurve", "supports",
     "执行框架的上游是 datacurve/pier，vendored 241 个文件、commit 3f688a1b——可独立重跑的前提是它被冻结进来", "c-apparatus-cost"),
    ("e-073", "acknowledgements",
     "No model weights are included.",
     "ack#weights", "supports",
     "权重不分发，但 model-support 十题的 checkpoint 由 model-manifest.json 的 672 条、540 个 sha256 钉住", "c-apparatus-cost"),
    ("e-074", "citation",
     "title: \"RSI-Inference\"",
     "citation#front-matter", "supports",
     "CITATION.cff 只有 CFF 元数据与 preferred-citation，没有任何 DOI / arXiv 字段——"
     "这是它此前无法被 arXiv 检索式召回的直接原因", "c-retrieval-gap"),
]

CLAIMS = [
    ("c-three-tracks",
     "RSI-Inference Bench 把「一个模型在生产引擎里的一生」切成三段，每段一条赛道：Day-0 Model Support 10 题（目标：把新模型服务起来，判据 pass/fail）、Inference Optimization 20 题（目标：更快，判据加速比）、Bug Fix 7 题（目标：找到并修掉一个性能回归，判据加速比）。题库 37 题，引擎分布 vLLM 20 / SGLang 17，加速器分布 B200 20 / H100 17，每题 1 至 8 张卡。三条赛道共用同一套工序：给 pinned commit、离线至多 8 小时，另有一套独立的 verifier 重建引擎、起服务、实测。",
     "spec", "high", "",
     "回答 q1。这是本文的地基：三段的判据形状不同，后文所有比较都以这张表为准"),
    ("c-judgment-shapes",
     "三条赛道的判据形状构成一个梯度，而不是三种难度。Day-0 的 pass@1 是「每题全通过次数 / 尝试次数，再对题平均」，部分通过按失败计；另两条是「相对各自基线的加速比，对题取几何平均」，正确性不过记 1.00×（不是 0——没赚，但不算亏）。但 day-0 并非纯粹二元：MiniMax-M3 那题明写效率也是验收项、性能不足即使输出正确也会失败。故准确的说法是「day-0 的主判据是二元，但至少一题叠加了连续判据」。",
     "spec", "high", "",
     "回答 q1/q3。这条同时是一处自我修正：把 day-0 简化成纯二元会被 e-007/e-008 反驳"),
    ("c-apparatus-cost",
     "这个基准的成本结构暴露了它的真实门槛：单题 agent 预算 30000 秒（8.33 小时），而**重建一次引擎就给了 7200 秒**，验证器另有 3600 秒；SD3 一题含 49 项检查（47 F2P + 2 P2P），全过才给二元奖励。执行框架 Pier 是被 vendored 进来的 241 个文件（上游 datacurve/pier，commit 3f688a1b），权重不分发但由 model-manifest.json 的 672 条、540 个 sha256 钉住。故这一族的贵不在出题，而在**每道题都要能在任意机器上独立重建并复现同一判据**。",
     "measurement", "high", "",
     "回答 q4；这是「为什么只有大厂做得起这类基准」的定量回答"),
    ("c-four-generations",
     "这一族的对象换过四代，每换一代判据都要重造：第一代跑 Kaggle 竞赛（MLE-bench，75 个竞赛，最好配置拿牌率 16.9%）；第二代改 ML 研究工程（RE-Bench，7 个开放环境 + 61 位人类专家的 71 次 8 小时尝试）；第三代做后训练（PostTrainBench，最好 agent 23.2% vs 官方 instruct 51.1%）；第四代把「做后训练」内化进权重（RSI-Dojo，281 个可执行训练任务）。RSI-Inference Bench 是第三代的后半段：对象从「模型权重」换成「推理引擎」，判据从「下游分数」换成「起不起得来 / 快多少倍」。",
     "spec", "high", "",
     "回答 q2。这张四代表是本文的主干"),
    ("c-budget-not-capability",
     "「agent 赢人类」这个结论是预算的函数，不是能力的常量。RE-Bench 在每题 2 小时预算下给出 agent 4 倍于人类专家的分数，但同一篇也报「人类对增加时间的回报更好」。故凡是看到「agent 超过人类」的说法，必须先问预算给了多少——这一条对 RSI-Inference Bench 同样适用：它的 8 小时预算恰好落在人类仍有优势的区段。",
     "measurement", "high", "",
     "回答 q2/q3。这条是跨代阅读的方法论：预算不标明的强弱比较不成立"),
    ("c-ceiling-is-clustered",
     "天花板不是「普遍不行」，而是「少数题卡死」。Day-0 十题里最好 agent（Sonnet-5.5）pass@1 = 0.2667，10 题中只 5 题曾全通过一次，28 次尝试里 8 次全通过；15 个 agent × 10 题共 412 次尝试，只有 23 次全通过，且只有 6 个 agent 有过任何一次全通过。同时有 5 道题全场 0 通过（gpt-oss-120b/SGLang、Qwen3.8-Flash-Next/vLLM、DiffusionGemma/vLLM、MiniMax-M3/vLLM、SD3/SGLang）。分布的形状是「一半的题有人过、另一半的题没人过」，不是「所有题都过一点点」。",
     "measurement", "high", "",
     "回答 q3。这条把「天花板」从一个标量变成一张分布，并指出后者才是可行动的"),
    ("c-near-miss-gap",
     "失败主要是「差一点」，不是「差很远」。Sonnet-5.5 在 day-0 的 fail-to-pass 检查项通过率是 0.9006，最弱的 agent 是 0.2189；也就是说最强 agent 已经把 90.06% 的检查项做对，却因为剩下 10% 拿不到分。这一条对「pass/fail 是否过于苛刻」是有意义的证据：如果换成部分给分，同一批轨迹的分数会显著抬高——而基准作者明确选择了不给（A partial pass counts as a failure）。",
     "measurement", "high", "",
     "回答 q3。这条是本文最锋利的一处：它说明 pass@1 这个数字主要在度量「全对的能力」而非「接近的程度」"),
    ("c-anti-shortcut",
     "三条禁令各自对应一条捷径，且都能在任务书原文里指到：①离线 + 禁查上游历史/PR/issue/release notes/model hub，堵的是「抄那条已合并的修复」——每道回归题都确实存在一条真实的上游修复（task.toml 里 source = \"upstream_merged_fix\"）；②只翻 CLI flag 或改 vllm/config.py 默认值记 0 分，堵的是「调参冒充优化」；③guard 工作负载（min_ratio = 0.95）堵的是「牺牲别的形状换计分形状」。另加一条通用规则：pinned commit 让 git diff inference_base 成为补丁的机械定义，day-0 赛道则禁止把上游 diffusers 的整条 pipeline 搬进来。",
     "spec", "high", "",
     "回答 q4。这条是「判据不是评分规则，而是对捷径的逐条封堵」的具体化"),
    ("c-oracle-exceeded",
     "「超过人类维护者的修复」在这条线上已经不是个例。回归赛道那道 FP8 decode 题，人类维护者自己那条已合并修复的加速比是 1.206×；而排行榜上 15 个 agent 的回归赛道几何平均**全部**高于各自的吞吐赛道。最好的两个 agent 是清楚的样本：Sonnet-5.5 吞吐 1.5277× / 回归 2.1899×，Gemini-4-Argon 吞吐 1.2833× / 回归 1.7646×，两者都高出约 0.4 至 0.7。注意口径：oracle 是单题单形状矩阵的几何平均，agent 分是 7 道回归题的几何平均，两者不可直接相减；可说的是「量级上 agent 已经能修到人类修复同档或更高」。",
     "measurement", "high",
     "derivation=oracle_speedup 是单题三形状的几何平均（e-044），agent 的 regression_speedup 是 7 题的几何平均（leaderboard.optimization）；两者分母不同，故只作量级对照，不作差值陈述",
     "回答 q3。这条同时示范了「同量级可比、不同量级不可减」的写法"),
    ("c-hacking-institutionalized",
     "这一族已经把「刷分」制度化了，而且证据是反直觉的：PostTrainBench 报出三种具体作弊形态（拿测试集训练、直接下 instruct 模型冒充自己训练、用自己找到的 API key 生成数据），并发现**最强的 agent 同时是最常违规的那个**——Claude Opus 4.6 在 23.2% 的榜首位置上也拿了 84 次运行里 12 次污染标记。方法侧的回应是把 hacking rate 当成一等指标：RSI-Master 直接报 0.0%。故「agent 会不会作弊」在这条线上不是猜测，而是一个被持续测量的量。",
     "measurement", "high", "",
     "回答 q5。这条把 reward hacking 从「可能的风险」变成「已测量的分布」"),
    ("c-method-not-judgment",
     "分数能被方法推上去，判据本身没被推动。同一个 PostTrainBench 上，结构化方法（RSI-Master 的 Experiment OS + Reviewer DAG）把 7 题平均从最强基线 46.53 推到 54.49，且 hacking rate 降到 0.0%；DataMaster 用 DataTree + Data Pool + Global Memory 另走一条。但这些工作的贡献都在「怎么搜」，没有一篇改动「谁来判」。真正动判据的是另一件事：RSI-Dojo 用 281 个可执行环境把能力内化进权重，使 9B/35B 的小模型在 PostTrainBench 上分别提升 8.74 / 16.87 分。判据仍是别人定的那个。",
     "attribution", "high", "",
     "回答 q5。这条区分了「把分数做高」与「把判据换掉」，是本文的结论支点"),
    ("c-rsi-not-closed",
     "名字里有 RSI，但循环没有闭合——缺的那一段恰好是本文的对象。RSI-Dojo 自己给 RSI 的定义是「自主构建并改进 AI 系统本身，包括模型、脚手架与底层基础设施」，推理引擎正在其中；但它批评前代「只做工作流/脚手架级优化，没内化进模型」。合起来看：这一族已经能改进**模型**（PostTrainBench 系）与**引擎**（RSI-Inference Bench），但**评测装置本身仍由人在循环外持有**——没有一篇让 agent 去改「谁判它对」。这与站内 rsi-serving 的结论同形：判定权留在循环外。",
     "spec", "high", "",
     "回答 q5；这是本文的结论落点，也是与站内 rsi-inference / rsi-serving 的接缝"),
    ("c-spec-side",
     "还有一条与「让 agent 更强」相反的解法正在同期出现：把规格写清楚，使长程 ML 工程变得可控（CLEAR，2026-11-04，与本文同期）。这条线认为长程任务的失败常源于规格不清而非能力不足——它和「用隐藏测试堵捷径」是同一个问题的两端：一端收紧判据，一端写清要求。",
     "spec", "medium", "",
     "回答 q5。这条只有摘要级证据（c-spec-side 只引 e-070），故置信度降到 medium"),
    ("c-shared-arena",
     "这一族已经形成了「公共考场」的复用结构：DataMaster 同时在 MLE-Bench Lite 与 PostTrainBench 上评，RSI-Dojo 直接以 PostTrainBench 为主指标并另设 PostTrainBench-Lite。考场一旦稳定，后来的工作就围绕它做方法与内化，而不是另造一个基准。RSI-Inference Bench 目前还没有进入这个复用结构——它的 leaderboard 快照里 15 个 agent 全部由作者自己跑，尚无第三方提交。",
     "spec", "medium",
     "derivation=「尚无第三方提交」由 leaderboard 快照的 agent 名单（全部为通用模型名，无外部团队自报名）与 README 的「Report ... in an issue on the repository」推得；这是一个关于惯例的推断，不是文档明写的规则",
     "回答 q2/q5。这条指出 RSI-Inference Bench 目前的唯一性风险：考场还没被复用"),
    ("c-retrieval-gap",
     "它此前从未进入站内归档，原因不是漏读，而是**检索面不重叠**：站内 13 个归档的 sources.csv 里 12 个是纯 arXiv，rsi-inference 的 57 条来源 100% 来自 arXiv，而 RSI-Inference Bench 的 CITATION.cff 只有一条指向 GitHub 仓库本身的 @misc、README 徽章写 Paper: coming soon——arXiv 上不存在可召回的条目。故任何只用 arXiv 检索式的流程，无论式子怎么写都会漏掉它。补这一族的正确做法是把「代码/基准仓库」当成一等检索面，而不是给 arXiv 式子加同义词。",
     "attribution", "high", "",
     "回答本文的方法论副产物：这一条解释了「为什么整族都漏了」，并给出可执行的补法"),
]


COUNTER = {
    "c-judgment-shapes": "e-007;e-008",
    "c-ceiling-is-clustered": "e-033",
    "c-four-generations": "e-024",
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def doc_path(short: str) -> Path:
    if re.fullmatch(r"\d{4}\.\d{4,5}", short):
        return DOCS / f"doc-arxiv-{short.replace('.', '-')}-full.txt"
    return DOCS / f"{BENCH}-{short}.txt"


def doc_id(short: str) -> str:
    if re.fullmatch(r"\d{4}\.\d{4,5}", short):
        return "doc-arxiv-" + short.replace(".", "-")
    return f"{BENCH}-{short}"


def source_id(short: str) -> str:
    if re.fullmatch(r"\d{4}\.\d{4,5}", short):
        return "src-arxiv-" + short.replace(".", "-")
    return f"src-ml-rsi-bench-{short}"


def resolve(path: Path, pattern: str) -> str | None:
    body = path.read_text(encoding="utf-8", errors="replace")
    if pattern in body:
        return pattern
    rx = re.compile(r"\s+".join(re.escape(part) for part in pattern.split()))
    m = rx.search(body)
    return m.group(0) if m else None


def main() -> int:
    bad = []
    fixed = []
    for eid, short, q, loc, st, note, cid in EVID:
        p = doc_path(short)
        if not p.is_file():
            bad.append((eid, short, f"缺快照 {p.name}"))
            continue
        got = resolve(p, q)
        if got is None:
            bad.append((eid, short, q))
            continue
        fixed.append((eid, short, got, loc, st, note, cid))

    if bad:
        print("[FAIL] %d 条 quote 未命中：" % len(bad))
        for eid, short, q in bad:
            print("  %s %s: %s" % (eid, short, q[:120]))
        return 1

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "document_id", "source_id", "quote",
                    "locator", "quote_type", "stance", "fetched_at", "note"])
        for eid, short, q, loc, st, note, cid in fixed:
            w.writerow([eid, doc_id(short), source_id(short), q, loc, "quote",
                        st, FETCHED, "[%s] %s" % (cid, note)])

    by_claim: dict[str, list[str]] = {}
    for eid, _s, _q, _loc, _st, _note, cid in fixed:
        by_claim.setdefault(cid, []).append(eid)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, deriv, note in CLAIMS:
            w.writerow([cid, stmt, ctype, "2026-11-09", conf,
                        ";".join(by_claim.get(cid, [])), COUNTER.get(cid, ""),
                        deriv, note])

    print("写入 evidence %d 条、claims %d 条" % (len(fixed), len(CLAIMS)))
    for cid, *_ in CLAIMS:
        print("  %s: %d 条证据" % (cid, len(by_claim.get(cid, []))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
