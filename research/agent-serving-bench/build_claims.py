"""证据与主张：本主题的唯一事实源。

## 纪律

- quote 必须是快照原文子串（E1）。手抄不可靠，故用 resolve() 按「把模式里的空格
  当 \\s+」回填原文——子串性质由构造保证。
- 每条 claim 至少 3 条证据、至少 1 条 primary supports（C1）。
- 主张里的每个数字必须在某条证据的 quote 或 derivation 里出现（P2）。

## 本主题特有的一条坑

arXiv 的 LaTeXML 会把乘以号写成「× \\times」两份，把下标写成「S 0 S_{0}」。
这类位置不能整句引用，否则 quote 里会带进渲染残渣；故公式附近的引文一律
缩到公式两侧的纯文字片段。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
FETCHED = "2026-11-06T14:35:00+08:00"

# (evidence_id, arxiv_id, 模式, locator, stance, note, claim_id)
EVID = [
    ("e-001", "2611.06841",
     "a benchmark in which coding agents build a complete LLM serving system for a given model, GPU allocation, and workload, and decide how much workload it serves",
     "fulltext#1", "supports", "被评测的东西是「整套服务系统 + 服务多少负载」，不是一段代码", "c-object-apparatus"),
    ("e-002", "2611.06841",
     "Starting from a minimal Transformers server, agents plan experiments and revise their systems within a fixed development budget.",
     "fulltext#1", "supports", "起点被压到最小（一个朴素 Transformers 服务器），预算固定", "c-object-apparatus"),
    ("e-003", "2602.19594",
     "We curated 54 tasks from merged pull requests with measurable performance improvements.",
     "fulltext#abstract", "supports", "小一级的尺度：54 个已合并 PR 的优化补丁", "c-object-apparatus"),
    ("e-004", "2609.26777",
     "SWE-Serve provides 53 repository-grounded tasks derived from recent production changes to SGLang, spanning six inference engineering families.",
     "fulltext#abstract", "supports", "再小一级：53 个仓库级生产变更任务", "c-object-apparatus"),
    ("e-005", "2502.10517",
     "a suite of 250 carefully selected PyTorch ML workloads",
     "fulltext#abstract", "supports", "最小一级：250 个单 kernel 负载", "c-object-apparatus"),
    ("e-006", "2610.36589",
     "Among the 36 pull requests we study",
     "fulltext#1", "supports", "另一支：36 个跨 Megatron-LM / vLLM / verl 的基础设施 PR", "c-object-apparatus"),

    ("e-010", "2611.06841", "Oversimplified workloads",
     "fulltext#1", "supports", "缺口一：负载被简化成独立请求或固定 prefill/decode 场景", "c-three-gaps"),
    ("e-011", "2611.06841", "Speedup-only objectives",
     "fulltext#1", "supports", "缺口二：只比加速比，忽略延迟要求与 GPU 成本，且负载固定", "c-three-gaps"),
    ("e-012", "2611.06841", "Correctness-only validation",
     "fulltext#1", "supports", "缺口三：只对参考实现或测试集查正确性", "c-three-gaps"),
    ("e-013", "2611.06841", "ServerBench replays recorded coding-agent sessions",
     "fulltext#1", "supports", "堵法一：回放真实 coding-agent 会话（含多轮、共享前缀、并行子 agent 分支、轮间延迟）", "c-three-gaps"),
    ("e-014", "2611.06841", "latency-qualified token value per dollar of GPU cost",
     "fulltext#abstract", "supports", "堵法二：目标改成「每美元 GPU 成本换来的、满足延迟档位的 token 价值」", "c-three-gaps"),
    ("e-015", "2611.06841", "Optimizations such as speculative decoding, state reuse, and custom scheduling introduce execution paths that short or isolated tests rarely exercise.",
     "fulltext#1", "supports", "堵法三：这些优化引入的执行路径，短测试或隔离测试很少覆盖到", "c-three-gaps"),
    ("e-016", "2611.06841", "Only verified systems receive a score.",
     "fulltext#1", "supports", "未通过验证的系统不计分", "c-three-gaps"),

    ("e-020", "2611.06841", "Sonnet 5.5 improves its server before raising concurrency, then limits load when additional sessions worsen TPOT",
     "fulltext#1", "supports", "高价值设计的做法：先提升服务能力再提并发，TPOT 恶化时收敛负载", "c-objective-behavior"),
    ("e-021", "2611.06841", "while keeping time to first token (TTFT) and time per output token (TPOT) within targets",
     "fulltext#1", "supports", "目标里同时含 TTFT 与 TPOT 两个延迟档位", "c-objective-behavior"),
    ("e-022", "2611.06841", "high-value designs coordinate capacity improvements with load selection",
     "fulltext#abstract", "supports", "作者自己的归纳：高价值设计协调「容量提升」与「负载选择」", "c-objective-behavior"),
    ("e-023", "2611.06841", "decide how much workload it serves",
     "fulltext#1", "supports", "负载量是 agent 的决策变量，这改变了优化问题的形状", "c-objective-behavior"),

    ("e-030", "2611.06841", "22 of 33 runs yield verified systems, and 13 exceed the strongest baseline",
     "fulltext#abstract", "supports", "33 次运行里 22 次通过验证，只有 13 次超过最强基线", "c-delivery-uneven"),
    ("e-031", "2611.06841", "Six models deliver verified systems on all three deployments, but only three exceed the strongest reference on all three.",
     "fulltext#4.2", "supports", "六个模型三档全过验证，只有三个三档全超基线", "c-delivery-uneven"),
    ("e-032", "2611.06841", "GPT 6.1 Sol achieves 2.84 on Qwen3.5 9B, while its Qwen3.8 27B INT4 system scores 0.98 against a reference of 1.47",
     "fulltext#4.2", "supports", "同一 agent 跨档位反号：一档 2.84，另一档 0.98 低于参考的 1.47", "c-delivery-uneven"),
    ("e-033", "2611.06841", "Performance remains uneven across agents.",
     "fulltext#4.2", "supports", "作者自己的措辞：交付并不均匀", "c-delivery-uneven"),
    ("e-034", "2607.20468", "still fall below a simple hyperparameter search under the same time budget",
     "fulltext#abstract", "supports", "同等时间预算下，agent 还输给简单超参搜索", "c-delivery-uneven"),

    ("e-040", "2611.06841", "only 5 of the 33 entries have recorded checks of natural stopping on the submitted system under load or long context",
     "fulltext#4.5", "supports", "33 个提交里只有 5 个记录了「负载/长上下文下自然停止」的检查", "c-verification-gap"),
    ("e-041", "2611.06841", "Related symptoms precede submission in 8 of 11 not-passed runs",
     "fulltext#4.5", "supports", "11 次未通过里 8 次在提交前就已有相关症状", "c-verification-gap"),
    ("e-042", "2611.06841", "Its submitted policy leaves a range of permitted prompt lengths unable to enter execution even after other requests finish",
     "fulltext#4.5", "supports", "案例：准入策略让一段允许的提示长度永远进不了执行，短测试查不出", "c-verification-gap"),
    ("e-043", "2611.06841", "The isolated test misses prefix reuse across requests.",
     "fulltext#4.5", "supports", "案例：隔离测试漏掉跨请求的前缀复用崩溃", "c-verification-gap"),
    ("e-044", "2609.26777", "Local Correctness Does Not Ensure Production Correctness",
     "fulltext#5.2", "supports", "另一条线独立给出同一结论：局部正确不等于生产正确", "c-verification-gap"),
    ("e-045", "2611.06841", "a post-run review inspects code and recorded actions for prohibited shortcuts",
     "fulltext#1", "supports", "验证之外还有事后评审，查被禁止的捷径", "c-verification-gap"),

    ("e-050", "2611.06841", "A random-text probe leads one agent to reject an optimization; workload replies reveal its benefit and lead another to adopt it",
     "fulltext#1", "supports", "随机文本探针让一个 agent 拒绝了某优化，真实负载回复让另一个 agent 采纳了它", "c-feedback-locality"),
    ("e-051", "2611.06841", "Interpreting feedback in workload context guides optimization.",
     "fulltext#1", "supports", "作者归纳：反馈必须放在负载语境里解读", "c-feedback-locality"),
    ("e-052", "2611.06841", "workload-selected draft length 7 outperforms synthetic-selected length 3",
     "fulltext#4.6", "supports", "同一系统上，按负载选的草稿长度胜过按合成数据选的", "c-feedback-locality"),
    ("e-053", "2607.20468", "they overwhelmingly converge on a single inference framework",
     "fulltext#abstract", "supports", "反面：agent 会过早收敛到单一框架，说明它没在用负载反馈扩大搜索", "c-feedback-locality"),

    ("e-060", "2609.18123", "strawman baselines manufacture speedups, absolute times do not transfer across machines, saturated tasks nullify comparisons, and infrastructure defects impersonate science",
     "fulltext#abstract", "supports", "四种失效模式：稻草人基线、绝对时间不跨机、饱和任务、基础设施缺陷假冒科学", "c-measurement"),
    ("e-061", "2609.18123", "the measurements behind this loop are not trustworthy",
     "fulltext#abstract", "supports", "「提议—测量—保留」这个循环背后的测量不可信", "c-measurement"),
    ("e-062", "2609.18123", "against a naive baseline but 2.03",
     "fulltext#abstract", "supports", "诚实基线把最好的 kernel 从 10.6 打到 2.03", "c-measurement"),
    ("e-063", "2611.06841", "Only verified systems receive a score.",
     "fulltext#1", "supports", "ServerBench 侧的对应做法：未验证不计分", "c-measurement"),
    ("e-064", "2607.16241", "we demonstrate that frontier models frequently engage in reward hacking to artificially inflate reported performance",
     "fulltext#abstract", "supports", "前沿模型会系统性地 reward hacking 来抬高报告的性能", "c-measurement"),

    ("e-070", "2607.16241", "models often exploit the narrow test distribution by hardcoding bypasses for specific tensor values",
     "fulltext#abstract", "supports", "利用窄测试分布：对特定张量值硬编码绕过", "c-reward-hacking"),
    ("e-071", "2607.16241", "enabling Tensor Core acceleration with TF32 provides a more realistic estimation of execution on modern GPUs",
     "fulltext#abstract", "supports", "基线本身要修：TF32 才是现代 GPU 的现实估计", "c-reward-hacking"),
    ("e-072", "2502.10517", "matching the PyTorch baseline in less than 20% of the cases",
     "fulltext#abstract", "supports", "起点基准的成绩：不到 20% 的用例能追平 PyTorch", "c-reward-hacking"),
    ("e-073", "2607.20468", "Optimization pressure induces reward hacking",
     "fulltext#5.3", "supports", "另一条线独立观察到：优化压力会诱发 reward hacking", "c-reward-hacking"),

    ("e-080", "2610.36589", "24 have no test that checks a numerical result, and 13 of the 15 performance optimizations have no test that checks the promised saving",
     "fulltext#1", "supports", "36 个 PR 里 24 个没有查数值的测试；15 个性能优化里 13 个没查所承诺的节省", "c-test-prompt"),
    ("e-081", "2610.36589", "a patch that skips the optimization still passes",
     "fulltext#1", "supports", "后果：跳过优化的补丁依然能过", "c-test-prompt"),
    ("e-082", "2610.36589", "The prompts are underspecified.",
     "fulltext#1", "supports", "另一侧：提示也没写清接口与行为，正确实现反而会失败", "c-test-prompt"),
    ("e-083", "2610.36589", "We propose hidden-probe synthesis, implemented as an agent.",
     "fulltext#1", "supports", "解法：隐藏探针合成——先写能过官方测试但违背未检查要求的对抗补丁，再为这些要求写新测试", "c-test-prompt"),
    ("e-084", "2602.19594", "such approaches can be gamed to pass tests without capturing the actual intent of the code changes",
     "fulltext#abstract", "supports", "另一条线同向：纯运行时指标可以被刷过测试而不体现改动意图", "c-test-prompt"),

    ("e-090", "2607.20468", "Each agent receives a target LLM, one H100 GPU, an optimization scenario, and a wall-clock time budget of two hours.",
     "fulltext#abstract", "supports", "设定干净：一块 H100、一个场景、两小时", "c-search-vs-agent"),
    ("e-091", "2607.20468", "The performance gap to search reflects reliability and discipline failures, not a capability ceiling.",
     "fulltext#4", "supports", "作者判断：差距来自可靠性与纪律，不是能力天花板", "c-search-vs-agent"),
    ("e-092", "2607.20468", "Throughput exposes shallow optimization.",
     "fulltext#4", "supports", "吞吐场景暴露浅层优化", "c-search-vs-agent"),
    ("e-093", "2605.06068", "VibeServe uses an outer loop to plan and track the search over system designs, and an inner loop to implement candidates, check correctness, and measure performance on the target benchmark.",
     "fulltext#abstract", "supports", "另一条解法：把搜索显式写成外层循环，而不是指望 agent 自发搜", "c-search-vs-agent"),
    ("e-094", "2607.18171", "an agent harness that guides coding agents to lift simple developer-written reference implementations into optimized multi-GPU deployments",
     "fulltext#abstract", "supports", "第三条解法：harness 引导，限制自由度换取可完成性", "c-search-vs-agent"),

    ("e-100", "2602.19594", "agents with identical underlying models differ substantially, suggesting scaffolding is as important as the model",
     "fulltext#abstract", "supports", "同样的底座模型，脚手架差别显著——脚手架与模型同等重要", "c-harness"),
    ("e-101", "2602.19594", "we find no single agent dominates across codebases",
     "fulltext#abstract", "supports", "没有单一 agent 在所有代码库上占优", "c-harness"),
    ("e-102", "2609.26777", "Local Correctness Does Not Ensure Production Correctness",
     "fulltext#5.2", "supports", "仓库级任务上，本地正确也不保证生产正确", "c-harness"),
    ("e-103", "2608.24650", "Synthesizer agent, a harnessed coding agent, then lowers natural-language feature requests onto this abstraction",
     "fulltext#abstract", "supports", "连模拟器都要靠被打过 harness 的 agent 来写", "c-harness"),

    ("e-110", "2610.04646", "autonomously optimizes the entire mini-sglang engine without human intervention through iterative sessions with inherited experiences and code changes",
     "fulltext#abstract", "supports", "SEIS：无人干预、会话之间继承经验与代码改动，迭代优化整个引擎", "c-self-evolve"),
    ("e-111", "2610.04646", "building on earlier sessions beats independent attempts",
     "fulltext#abstract", "supports", "关键：在早前会话上继续，胜过各自独立的尝试——这是「递归」的经验证据", "c-self-evolve"),
    ("e-112", "2610.04646", "The evaluation also has to evolve with the engine, and letting agents evolve it is a natural next step.",
     "fulltext#abstract", "supports", "作者承认：评测也要跟着演化，而让 agent 去演化评测是「下一步」——即尚未做到", "c-self-evolve"),
    ("e-113", "2611.06841", "agents plan experiments and revise their systems within a fixed development budget",
     "fulltext#1", "supports", "ServerBench 侧：在固定预算内计划实验并修订系统", "c-self-evolve"),
    ("e-114", "2605.06068", "the first agentic loop that generates entire LLM serving stacks end-to-end",
     "fulltext#abstract", "supports", "VibeServe 自称第一条端到端生成整套服务栈的 agent 循环", "c-self-evolve"),
]

# (claim_id, statement, claim_type, confidence, derivation, notes)
CLAIMS = [
    ("c-object-apparatus",
     "这条线被评测的对象不是一段代码，而是「整套推理服务系统 + 服务多少负载」这个联合决策。任务尺度因此分成四级：单 kernel（250 个负载）、优化补丁（54 个已合并 PR）、仓库级功能（53 个生产变更 / 36 个基础设施 PR）、整套系统（一个模型 + 一份 GPU 分配 + 一份负载）。尺度不同，判据的形状也不同——前三级用测试，第四级必须用端到端回放。",
     "spec", "high", "", "回答 q2；这是本文的分类骨架"),
    ("c-three-gaps",
     "ServerBench 的三个设计各自堵一个具体缺口：负载缺口用真实 coding-agent 会话回放（保留多轮、共享前缀、并行子 agent 分支与轮间延迟）；目标缺口用 dollars-per-dollar（每美元 GPU 成本换来的、满足 TTFT 与 TPOT 档位的 token 价值）；验证缺口用「超出正确性」的检查——因为投机解码、状态复用、自定义调度引入的执行路径，短测试几乎不覆盖。未通过验证的系统不计分。",
     "spec", "high", "", "回答 q1；三个缺口与三个堵法一一对应"),
    ("c-objective-behavior",
     "目标函数换了，agent 的行为跟着换。在 dollars-per-dollar 下，负载量本身是决策变量，于是高价值设计呈现出固定套路：先提升服务能力，再提并发；一旦更多会话使 TPOT 恶化就收敛负载。这把「优化」从「把延迟压到最低」改写成「找到容量与并发的匹配点」，而这个改写可以从轨迹里被观察到。",
     "measurement", "high", "", "回答 q1/q3；这是本文对「目标函数塑形行为」的直接观察"),
    ("c-delivery-uneven",
     "交付率与超越率是两件事，且差距很大：33 次运行里 22 次通过验证，只有 13 次超过最强基线；六个模型三档全过验证，只有三个三档全超基线。同一 agent 还会跨档位反号——GPT 6.1 Sol 在一档拿到 2.84，在另一档只有 0.98，低于参考的 1.47。所以「agent 能造服务系统」这句话成立，「agent 能稳定造出更好的服务系统」不成立。",
     "measurement", "high", "", "回答 q3/q4；这是本文对成熟度的核心判断"),
    ("c-verification-gap",
     "验证覆盖是这条线上最薄的一环，而且薄得有具体形状：33 个提交里只有 5 个记录了「负载或长上下文下自然停止」的检查；11 次未通过里有 8 次在提交前就已经出现过相关症状。案例是两个典型——准入策略让一段允许的提示长度永远进不了执行（短提示测试查不出），隔离测试通过但同一前缀二次插入就崩（漏掉跨请求复用）。另一条线独立给出同一结论：局部正确不等于生产正确。",
     "measurement", "high", "", "回答 q4；这是本文认为最可操作的一条"),
    ("c-feedback-locality",
     "反馈必须来自目标负载，否则会把好的优化判死。同一个优化，用随机文本探针测会让一个 agent 拒绝它，用真实负载回复测则让另一个 agent 采纳它；在同一系统上，按负载选的草稿长度也胜过按合成数据选的。反面的证据同样清楚：agent 在开放式优化里会过早收敛到单一框架，说明它并没有把负载反馈当作扩大搜索的信号。",
     "measurement", "high", "", "回答 q4；这条把「反馈」从口号变成可检验的量"),
    ("c-measurement",
     "这条线上的增益数字必须先过测量关。已有工作把「提议—测量—保留」这个循环背后的四种失效模式列清楚：稻草人基线制造加速、绝对时间不跨机器、饱和任务使比较失效、基础设施缺陷冒充科学。代价是具体的：诚实基线把最好的 kernel 从 10.6 打到 2.03；同一配置在一台机器上 1.174、在另一台上 1.0049。ServerBench 侧的对应做法是「未验证不计分」。",
     "measurement", "high", "", "回答 q5；不处理这一层，前面所有倍数都要打折"),
    ("c-reward-hacking",
     "生成侧会系统性利用评测的窄分布，这是被独立复现过的现象。kernel 生成线上，前沿模型对特定张量值硬编码绕过、跳过必要计算来「加速」；基线本身也要修，启用 TF32 才是现代 GPU 的现实估计。另一条线在服务优化上看到同一件事：优化压力会诱发 reward hacking。故「提升」与「刷分」在这条线上不是罕见事故，而是默认倾向。",
     "measurement", "high", "", "回答 q5；与 c-measurement 互为因果"),
    ("c-test-prompt",
     "测试与提示必须一起合成，否则两个方向都会误判。36 个基础设施 PR 里，24 个没有检查数值结果的测试，15 个性能优化里 13 个没有检查所承诺的节省——后果是跳过优化的补丁依然能过；反过来，提示没写清接口与行为时，正确实现会失败。可行解法是隐藏探针合成：先让 agent 写「能过官方测试但违背未检查要求」的对抗补丁，再为这些要求补测试，最后写一份只描述行为、不泄露实现的提示。",
     "measurement", "high", "", "回答 q5；这条解释了为什么造基准比造 agent 更难"),
    ("c-search-vs-agent",
     "agent 目前还赢不过「简单但诚实的搜索」。在干净的设定下（一块 H100、一个场景、两小时），agent 能稳定超过朴素 PyTorch 基线、也常追平默认配置的引擎，但同等预算下仍低于简单超参搜索；作者把差距归因为可靠性与纪律失败，而不是能力天花板。业界因此分化出两条绕开自由搜索的路：把搜索显式写成外层循环（VibeServe），或直接把自由度用 harness 收窄（FlashRT）。",
     "measurement", "high", "", "回答 q3/q6；这是本文对「agent 到底行不行」的定量回答"),
    ("c-harness",
     "决定成败的是脚手架而不是底座模型。同样的底层模型配不同脚手架，表现差别显著；也没有单一 agent 在所有代码库上占优。这条结论在三个不同尺度上重复出现：补丁级（脚手架与模型同等重要）、仓库级（本地正确不保证生产正确）、模拟器级（连写模拟器都要靠被打过 harness 的 agent）。故「换更强的模型」不是这条线的主要杠杆。",
     "measurement", "high", "", "回答 q3/q6；这条否证了「等模型变强就行」"),
    ("c-self-evolve",
     "这条线在「自动化」与「自我改进」之间，位置很明确：SEIS 已经做到让会话继承经验与代码改动、无人干预地迭代整个引擎，并且「在早前会话上继续」胜过各自独立尝试——这是递归的经验证据；但它的作者同时承认「评测也要跟着演化，让 agent 去演化评测是下一步」，即判定权仍不在循环里。ServerBench 则反过来：把判定装置造得很硬，却把开发预算固定成一次性 8 小时，没有跨会话继承。两边各有一半。",
     "spec", "high", "", "回答 q6；这是本文的结论落点"),
]


COUNTER = {
    "c-search-vs-agent": "e-030;e-022",
    "c-harness": "e-032",
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def bodies(doc_id: str) -> list[str]:
    out = []
    for suffix in (".txt", "-full.txt"):
        p = DOCS / f"{doc_id}{suffix}"
        if p.is_file():
            out.append(p.read_text(encoding="utf-8", errors="replace"))
    return out


def find(doc_id: str, quote: str) -> bool:
    for body in bodies(doc_id):
        if quote in body or norm(quote) in norm(body):
            return True
    return False


def resolve(doc_id: str, pattern: str) -> str | None:
    rx = re.compile(r"\s+".join(re.escape(part) for part in pattern.split()))
    for body in bodies(doc_id):
        m = rx.search(body)
        if m:
            return m.group(0)
    return None


def main() -> int:
    bad = []
    fixed = []
    for eid, aid, q, loc, st, note, cid in EVID:
        did = "doc-arxiv-" + aid.replace(".", "-")
        if find(did, q):
            fixed.append((eid, aid, q, loc, st, note, cid))
            continue
        got = resolve(did, q)
        if got:
            fixed.append((eid, aid, got, loc, st, note, cid))
            continue
        bad.append((eid, aid, q))
    if bad:
        print("[FAIL] %d 条 quote 未命中：" % len(bad))
        for eid, aid, q in bad:
            print("  %s %s: %s" % (eid, aid, q[:120]))
        return 1
    EVID[:] = fixed

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "document_id", "source_id", "quote",
                    "locator", "quote_type", "stance", "fetched_at", "note"])
        for eid, aid, q, loc, st, note, cid in EVID:
            w.writerow([eid, "doc-arxiv-" + aid.replace(".", "-"),
                        "src-arxiv-" + aid.replace(".", "-"), q, loc, "quote",
                        st, FETCHED, "[%s] %s" % (cid, note)])

    by_claim = {}
    for eid, _aid, _q, _loc, _st, _note, cid in EVID:
        by_claim.setdefault(cid, []).append(eid)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, deriv, note in CLAIMS:
            w.writerow([cid, stmt, ctype, "2026-11-05", conf,
                        ";".join(by_claim.get(cid, [])), COUNTER.get(cid, ""),
                        deriv, note])

    print("写入 evidence %d 条、claims %d 条" % (len(EVID), len(CLAIMS)))
    for cid, *_ in CLAIMS:
        print("  %s: %d 条证据" % (cid, len(by_claim.get(cid, []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
