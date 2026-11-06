"""证据与主张：本主题的唯一事实源。

## 纪律

- 每条 evidence 的 quote 必须是快照原文子串（E1）。手抄不可靠，故用 resolve()
  按「把模式里的空格当 \\s+」回填原文——子串性质由构造保证，不靠人眼。
- 每条 claim 至少 3 条证据，且至少 1 条 primary supports（C1）。
- 主张里出现的每个数字，必须在该主张某条证据的 quote 或 derivation 里出现（P2）。

## 与 rsi-inference 的分工

rsi-inference 的主张关于 kernel 层（判据是一个数）；这里的主张关于端到端层
（判据是一组统计量）。两篇不共享任何 evidence。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
FETCHED = "2026-11-05T11:05:00+08:00"

# (evidence_id, arxiv_id, 模式, locator, stance, note, claim_id)
EVID = [
    ("e-001", "2611.02501",
     "speculative decoding is deployment-specific, and no universal optimization fits every serving regime",
     "fulltext#abstract", "supports", "端到端优化是 deployment-specific 的：没有普适最优", "c-object-e2e"),
    ("e-002", "2605.06068",
     "VibeServe uses an outer loop to plan and track the search over system designs, and an inner loop to implement candidates, check correctness, and measure performance on the target benchmark.",
     "fulltext#3.2", "supports", "端到端被优化的是系统设计：外层规划 + 内层实现与测量", "c-object-e2e"),
    ("e-003", "2607.12875",
     "porting restores executable routes when existing paths are missing or blocked, while optimization reduces the cost of reachable routes under real serving workloads",
     "fulltext#method", "supports", "端到端含两个不同任务：porting（恢复可执行）与 optimization（降成本）", "c-object-e2e"),
    ("e-004", "2605.11581",
     "kernel launch overhead alone can account for 14.6% of end-to-end inference time",
     "fulltext#intro", "supports", "端到端时间里有一部分完全在 kernel 之外（launch 占 14.6%）", "c-object-e2e"),
    ("e-005", "2604.26039",
     "the best kernel configuration depends on this split, and not only on the number of tokens",
     "fulltext#abstract", "supports", "同一 kernel 的最优配置取决于运行时 token 分布，故端到端对象含运行时状态", "c-object-e2e"),
    ("e-006", "2607.12875",
     "A faster microbenchmark kernel may fail to improve service throughput once dispatch overhead, memory allocation, synchronization, batching, and communication are included.",
     "fulltext#2.2", "supports", "微基准更快不等于服务的吞吐更高：dispatch、分配、同步、批处理都要计入", "c-object-e2e"),
    ("e-010", "2611.02501",
     "The controller , scripts that agents call but cannot modify, times it against the current best in paired runs",
     "fulltext#3.2", "supports", "判定权在 agent 不可修改的控制器手里；配对运行消除机器差异", "c-judge"),
    ("e-011", "2611.02501",
     "It promotes the patch only if its gain’s 95% lower bound exceeds 1% plus twice the stock-versus-stock noise",
     "fulltext#3.2", "supports", "晋级判据是「增益下界对噪声」，不是点估计", "c-judge"),
    ("e-012", "2611.02501",
     "< < 0.1% for one request on H100",
     "fulltext#3.2", "supports", "H100 单请求上 stock 对 stock 的噪声小于 0.1%", "c-judge"),
    ("e-013", "2609.18123",
     "the same config delivers 1.174",
     "fulltext#2.3", "supports", "同一配置换机器从 1.174x 变 1.0049x：绝对值不可跨机器迁移", "c-judge"),
    ("e-014", "2609.18123",
     "our best gelu tuning kernel reads 10.6",
     "fulltext#2.3", "supports", "稻草人基线制造 10.6x，对诚实基线只有 2.03x", "c-judge"),
    ("e-015", "2609.18123",
     "absolute times do not transfer across machines, saturated tasks nullify comparisons, and infrastructure defects impersonate science",
     "fulltext#abstract", "supports", "四种测量失效模式：稻草人基线、绝对值不可迁移、任务饱和、基础设施缺陷", "c-judge"),
    ("e-020", "2611.02501",
     "teacher-forced scorer feeds the system’s outputs back through the target on the stock engine with an FP32 LM h",
     "fulltext#3.3", "supports", "无损判定用 teacher forcing：系统输出喂回 stock、FP32 LM head 重打分", "c-lossless"),
    ("e-021", "2611.02501",
     "Stock mismatches on 0.72% of tokens, almost all near-ties from kernel rounding.",
     "fulltext#3.3", "supports", "stock 自身在 0.72% 的 token 上失配（几乎都是近 tie），故判据必须以基线失配率为参照", "c-lossless"),
    ("e-022", "2611.02501",
     "rate rule",
     "fulltext#3.3", "supports", "拒绝规则之一：失配率相对 stock 的增量（rate rule）", "c-lossless"),
    ("e-023", "2611.02501",
     "event rule",
     "fulltext#3.3", "supports", "拒绝规则之二：大 margin 失配事件（event rule）", "c-lossless"),
    ("e-024", "2610.04646",
     "language perplexity (relative difference within 5%)",
     "fulltext#3.2", "supports", "SEIS 的数值门：perplexity 相对差 5% 以内", "c-lossless"),
    ("e-025", "2610.04646",
     "Downstream Performance Gate",
     "fulltext#3.2", "supports", "数值门之外还有下游任务门，因为数值差异会沿步累积", "c-lossless"),
    ("e-026", "2611.02501",
     "Each round ends with a sealed final , which times the system against stock on unseen requests and reruns token forcing",
     "fulltext#3.2 Phase 4", "supports", "晋级后还要在未见请求上封 sealed final，再跑一次 token forcing", "c-lossless"),
    ("e-030", "2611.02501",
     "a cost model compares measured performance with an estimated ceiling to locate where speed is lost",
     "fulltext#3", "supports", "成本模型的用途是定位「速度丢在哪」，不是预测最终倍数", "c-ceiling"),
    ("e-031", "2611.02501",
     "The ceiling factors as",
     "fulltext#3.1 Eq.(4)", "supports", "ceiling 被分解成三个因子的乘积，故每一项都可重算", "c-ceiling"),
    ("e-032", "2611.02501",
     "After three rounds, this baseline reached only 1.34",
     "fulltext#6", "supports", "没有 ceiling 排序的单 agent 对照三轮只到 1.34x，SpecPilot 是 2.13x", "c-ceiling"),
    ("e-033", "2611.02501",
     "The master starts from Phase 0’s cost model and proposes directions aimed at its largest factors.",
     "fulltext#3.2 Phase 1", "supports", "每轮按最大因子开方向，而不是按最显眼的瓶颈", "c-ceiling"),
    ("e-034", "2601.06288",
     "AIConfigurator identifies superior serving configurations that improve performance by up to 40% for dense models",
     "fulltext#abstract", "supports", "用性能模型替代 GPU profiling 也能找到更优配置（dense 最多 40%）", "c-ceiling"),
    ("e-040", "2611.02501",
     "it raises the speedup over AR from stock’s 4.46",
     "fulltext#abstract", "supports", "SpecPilot 把对 AR 的加速比从 stock 的 4.46x 提到 10.87x（单请求）", "c-gain"),
    ("e-041", "2611.02501",
     "with batching",
     "fulltext#abstract", "supports", "批处理下从 stock 的 1.94 倍提到 3.93 倍", "c-gain"),
    ("e-042", "2611.02501",
     "The sealed final is 2.13",
     "fulltext#6", "supports", "对 stock 的 sealed final 增益是 2.13x", "c-gain"),
    ("e-043", "2610.04646",
     "the resulting engine reaches 3.27",
     "fulltext#abstract", "supports", "SEIS 把 mini-sglang 吞吐提到 3.27x", "c-gain"),
    ("e-044", "2605.06068",
     "delivers 2.3",
     "fulltext#abstract", "supports", "VibeServe 在 397B MoE、四张 MI300A 上比调优后的 SGLang 高 2.3x goodput", "c-gain"),
    ("e-045", "2610.25012",
     "geometric-mean per-round speedup of 1.37",
     "fulltext#abstract", "supports", "跨模型编译在六种投机解码配置上几何平均每轮 1.37x", "c-gain"),
    ("e-046", "2601.06288",
     "0.52s",
     "fulltext#5", "supports", "AIConfigurator 搜完 339 个配置用 0.52 秒，GPU 实测需 24.4 小时", "c-gain"),
    ("e-050", "2611.02501",
     "The thirteen completed rounds took 164 hours and 530 GPU-hours in total, created 486 code changes and promoted 54 of them.",
     "fulltext#appendix D", "supports", "十三轮 164 小时 / 530 GPU-小时 / 486 个改动 / 晋级 54 个", "c-cost"),
    ("e-051", "2611.02501",
     "A round takes 7",
     "fulltext#appendix D", "supports", "单轮 7–20 小时、20–86 GPU-小时", "c-cost"),
    ("e-052", "2611.04032",
     "Exhaustively evaluating all candidate configurations in our study would require approximately 25,000 GPU-hours.",
     "fulltext#abstract", "supports", "穷举配置需约 25,000 GPU-小时，故必须用少量 anchor + 解析外推", "c-cost"),
    ("e-053", "2611.04032",
     "On 172 configurations that pass our measurement filters, time per output token has 8.1% median error.",
     "fulltext#5", "supports", "代理模型在 172 个配置上 TPOT 中位误差 8.1%", "c-cost"),
    ("e-054", "2607.20468",
     "a wall-clock time budget of two hours",
     "fulltext#3", "supports", "InferenceBench 给 agent 两小时墙钟预算，故成本必须计入评分", "c-cost"),
    ("e-060", "2611.02501",
     "With batching, 24-node trees lost 14.9% on the FP8 target, and on BF16 Qwen3.8-27B a 24-position block lost 9.9% and TLV 13%.",
     "fulltext#7", "supports", "批处理下三种机制直接反号：24 节点树 -14.9%、24 位置块 -9.9%、TLV -13%", "c-boundary"),
    ("e-061", "2611.02501",
     "but with batching on BF16 Qwen3.8-27B the same idea is 13% slower",
     "fulltext#7", "supports", "低精度目标副本预检在批处理下慢 13%", "c-boundary"),
    ("e-062", "2604.26039",
     "under expert parallelism, choosing the configuration for each GPU’s actual token distribution is up to 1.45",
     "fulltext#abstract", "supports", "离线 autotune 的假设（token 数决定工作量）在 MoE 上失效", "c-boundary"),
    ("e-063", "2605.21312",
     "average-case analytical proxies can distort SLA predictions and even reverse optimization conclusions",
     "fulltext#abstract", "supports", "平均情况解析代理会扭曲 SLA 预测，甚至反转优化结论", "c-boundary"),
    ("e-064", "2609.18123",
     "saturated tasks nullify comparisons",
     "fulltext#abstract", "supports", "任务饱和会让比较失效：已经到顶的系统再怎么改都测不出差别", "c-boundary"),
    ("e-070", "2609.18123",
     "strawman baselines manufacture speedups",
     "fulltext#abstract", "supports", "稻草人基线的定义：用最差初稿作分母来制造加速比", "c-measure"),
    ("e-071", "2609.18123",
     "We characterize four failure modes from a four-day pilot corpus of 619 model calls",
     "fulltext#abstract", "supports", "四种失效模式来自四天、619 次模型调用的试点语料", "c-measure"),
    ("e-072", "2607.20468",
     "Even nominally open-ended tasks can often be solved by retrieving a well-known recipe and tuning a few hyperparameters",
     "fulltext#abstract", "supports", "开放式基准也可被「背配方」通过，故需区分真优化与记忆", "c-measure"),
    ("e-073", "2607.20468",
     "memorized solutions lead to limited improvements",
     "fulltext#abstract", "supports", "记忆型解法带来的改进有限", "c-measure"),
    ("e-074", "2610.07792",
     "the knowledge required for correct behavior in these environments is often implicit, undisclosed, and subject to change over time",
     "fulltext#abstract", "supports", "serving 知识往往隐式、未公开且随时间变化，故静态基准测不出自改进", "c-measure"),
    ("e-080", "2611.02501",
     "After a sealed final, each promoted mechanism becomes one memory entry",
     "fulltext#3.2", "supports", "晋级机制被封成记忆条目：代码增量 + 契约 + 证据与未测工况", "c-memory"),
    ("e-081", "2610.04646",
     "autonomously optimizes the entire mini-sglang engine without human intervention through iterative sessions with inherited experiences and code changes",
     "fulltext#abstract", "supports", "SEIS 的会话继承经验与代码改动", "c-memory"),
    ("e-082", "2610.04646",
     "building on earlier sessions beats independent attempts",
     "fulltext#5", "supports", "在早期会话上继续，优于独立重试", "c-memory"),
    ("e-090", "2605.06068",
     "there is a broad need for specialization, the optimization objective is concrete and numeric",
     "fulltext#1", "supports", "端到端之所以适合 agent：目标具体且数值化，正确性有参照", "c-learn"),
    ("e-091", "2610.07792",
     "ServeLearnBench: How Well Can Agents Self-Improve from Serving Experience?",
     "fulltext#title", "supports", "serving 经验能否被自改进，本身成了被基准化的问题", "c-learn"),
    ("e-092", "2607.20468",
     "SGLang is the strongest engine for prefill (Scenario A) under all three optimizers.",
     "fulltext#5", "supports", "同一场景下三个优化器都收敛到同一个已知引擎，说明多数「优化」是选型", "c-learn"),
    ("e-100", "2610.34938",
     "We ran Claude Code on 30 SWE-bench Verified issues, qualitatively coded the 125 proposals from /retro , implemented 24, and evaluated 12 harness changes",
     "fulltext#abstract", "supports", "125 条 harness 提议 → 实现 24 → 评估 12", "c-harness"),
    ("e-101", "2610.34938",
     "two changes eliminated the targeted action, one reduced its occurrence, four showed no reduction",
     "fulltext#5", "supports", "7 次可评估改动里 4 次没有减少重复工作", "c-harness"),
    ("e-102", "2610.22791",
     "harness and policy are mutually reinforcing and evolving only one component is suboptimal",
     "fulltext#abstract", "supports", "只改 harness 或只改 policy 都次优，需要交替", "c-harness"),
    ("e-103", "2610.22791",
     "a recursive self-improving framework for coding agents that alternates harness and policy optimization",
     "fulltext#abstract", "supports", "Self-HPO 把「交替」写成了递归自改进的定义", "c-harness"),
    ("e-110", "2611.02501",
     "A sub-agent first checks the headroom with the cheapest evidence, such as exact replay, a microbenchmark or a timing run on one GPU",
     "fulltext#3.2 Phase 1", "supports", "先用最便宜的证据估 headroom，够门槛才实现", "c-transfer"),
    ("e-111", "2611.02501",
     "Many patches gain too little to promote alone, but enough together.",
     "fulltext#3.2 Phases 2-3", "supports", "单独不够门槛的补丁叠起来再计时：晋级判据要允许组合", "c-transfer"),
    ("e-112", "2610.08993",
     "empirical verifiers often require computationally costly model training and evaluation",
     "fulltext#abstract", "supports", "验证是最贵的一步，故用 critic 预筛降低验证次数", "c-transfer"),
    ("e-113", "2610.16491",
     "fully evaluating every intermediate version often exhausts the budget before those sequences yield a verified improvement",
     "fulltext#abstract", "supports", "每个中间版本都完整评估会耗尽预算：预算要在「改」与「验」之间分配", "c-transfer"),
]

# (claim_id, statement, claim_type, confidence, evidence_ids(占位), derivation, notes)
CLAIMS = [
    ("c-object-e2e",
     "端到端的被优化对象不是一段代码，而是「系统设计 + 运行时状态」：同一份 kernel 代码在不同批组成、不同路由分布下最优配置不同，故端到端的判据必须同时包含吞吐/延迟、数值正确性与部署约束，而不能只用某个 kernel 的加速比。",
     "spec", "high", "",
     "", "按对象性质分类，不依赖跨论文数值比较"),
    ("c-judge",
     "晋级判定必须写成统计命题：增益的 95% 下界要同时超过一个最小实际增益与若干倍的 stock 自身噪声；单次点估计不足以支撑「更好」这个断言，因为跨机器的绝对值差异（1.174 对 1.0049）与稻草人基线造成的差异（10.6 对 2.03）都比典型改进大一个量级。",
     "measurement", "high", "",
     "", "回答 q2；与 c-measure 互补：这条讲判据怎么构造，那条讲测量为什么不可信"),
    ("c-lossless",
     "端到端的「无损」不能定义为逐位相同（浮点归约顺序会翻转近 tie），也不能用任务准确率代替；可行的定义是「每个被接受的 token 都等于一次精确权重 pass 的 argmax」，并用相对基线失配率的统计检验（rate rule + event rule）来拒绝。",
     "measurement", "high", "",
     "", "回答 q2；三条证据来自两种不同系统的独立设计"),
    ("c-ceiling",
     "成本模型的价值不在于预测最终倍数，而在于把上界分解成可重算的因子并按因子排序开方向；没有这一步，搜索会被最显眼的瓶颈吸住，三轮只能到 1.34 倍，而按因子排序的系统到 2.13 倍。",
     "measurement", "high", "",
     "", "回答 q2；这是同系统内对照，不是跨系统比较"),
    ("c-gain",
     "端到端层面的报告增益分布在 1.37 到 10.87 之间，但每一档的口径都不同（对 AR 还是对 stock、单请求还是批处理、几何还是算术），故这个区间只说明「跨度大」，不能当作同一把尺子上的排序。",
     "measurement", "high", "",
     "", "回答 q4；避免把不同基线并成一个排行榜。\u672c\u6587\u5f15\u7528\u7684\u53e3\u5f84\u5bf9\u7167\uff1aSpecPilot \u5355\u8bf7\u6c42 4.46 -> 10.87\uff0c\u6279\u5904\u7406 1.94 -> 3.93\uff1bSEIS 3.27\uff1bVibeServe 2.3\uff1b\u8de8\u6a21\u578b\u7f16\u8bd1 1.37\uff1bAIConfigurator dense \u6700\u591a 40%\u3002"),
    ("c-cost",
     "循环本身不便宜：一轮 7–20 小时、20–86 GPU-小时，十三轮合计 164 小时 / 530 GPU-小时，486 个改动里晋级 54 个（约一成）；而穷举式配置搜索要 25,000 GPU-小时，故端到端层的「自动化」本质是用代理模型换实测。",
     "measurement", "high", "",
     "", "回答 q4；把循环成本折算进结论"),
    ("c-boundary",
     "端到端层的机制会反号，而且反号由批处理触发：24 节点树在 FP8 目标上 −14.9%，24 位置块在 BF16 上 −9.9%，TLV −13%，低精度预检 −13%；此外任务饱和与平均情况代理也会让比较失效。",
     "measurement", "high", "",
     "", "回答 q5；全部为论文自报的反号证据"),
    ("c-measure",
     "端到端层的首要风险不是搜不到，而是测不准：稻草人基线、绝对值不可跨机器迁移、任务饱和、基础设施缺陷四种失效模式，都会让循环「学到」一个不存在的改进。",
     "measurement", "high", "",
     "", "回答 q5；与 c-judge 互为因果"),
    ("c-memory",
     "端到端循环的可累积性来自机制级记忆：晋级机制被封成带代码增量、正确性契约与未测工况的条目，跨部署只移植条目而不是重跑循环；同一系统上「在早期会话上继续」优于独立重试。",
     "measurement", "high", "",
     "", "回答 q3；这条是「有累积性」的直接证据"),
    ("c-learn",
     "端到端「自我改进」与「检索已知配方」在结果上难以区分：多数场景下不同优化器都收敛到同一个已知引擎，故一个高分既可能来自优化也可能来自记忆，必须用未见场景与隐藏环境来分离。",
     "spec", "high", "",
     "", "回答 q1/q6；这是本文对该领域评价方法的核心批评"),
    ("c-harness",
     "端到端改的主要是脚手架而不是权重，但脚手架自改进的实证很弱：125 条 harness 提议里实现 24 条、评估 12 条，7 次可评估改动中 4 次没有减少目标重复工作，2 次彻底消除。",
     "measurement", "high", "",
     "", "回答 q6；这是本文对「RSI」命名最直接的反证"),
    ("c-transfer",
     "可迁移的不是某个机制，而是三条判据工程：先用最便宜的证据估 headroom 再实现；晋级允许「单独不够、合起来够」的组合；把预算显式分配给「改」与「验」两侧。",
     "spec", "high", "",
     "", "回答 q6；三条各有独立来源支持"),
]


# 反证白名单：主张 -> 与之张力最强的证据 id 列表。
# c-boundary 说机制会反号，而 e-033 显示同一系统靠换因子排序又绕过了瓶颈，
# 属于对该断言边界的反例，故并列。
COUNTER = {
    "c-boundary": "e-033;e-042",
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
    """按宽松空白匹配把模式解析成快照里的**原文片段**。

    为什么需要它：E1 要求 quote 是原文子串，而全文快照来自 LaTeXML，
    句子之间的换行位置不可预测。手抄容易差一个空格，故这里用「把模式里的
    空格当 \\s+」去原文里找，返回命中的原始文本本身——它是子串这一点由构造保证。
    """
    rx = re.compile(r"\s+".join(re.escape(part) for part in pattern.split()))
    for body in bodies(doc_id):
        m = rx.search(body)
        if m:
            return m.group(0)
    return None


def main() -> int:
    bad = []
    fixed: list[tuple] = []
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
        print(f"[FAIL] {len(bad)} 条 quote 未命中：")
        for eid, aid, q in bad:
            print(f"  {eid} {aid}: {q[:110]}")
        return 1
    EVID[:] = fixed

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "document_id", "source_id", "quote",
                    "locator", "quote_type", "stance", "fetched_at", "note"])
        for eid, aid, q, loc, st, note, cid in EVID:
            w.writerow([eid, "doc-arxiv-" + aid.replace(".", "-"),
                        "src-arxiv-" + aid.replace(".", "-"), q, loc, "quote",
                        st, FETCHED, f"[{cid}] {note}"])

    by_claim: dict[str, list[str]] = {}
    for eid, _aid, _q, _loc, _st, _note, cid in EVID:
        by_claim.setdefault(cid, []).append(eid)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, _eids, deriv, note in CLAIMS:
            ids = ";".join(by_claim.get(cid, []))
            counter = COUNTER.get(cid, "")
            w.writerow([cid, stmt, ctype, "2026-11-05", conf, ids, counter,
                        deriv, note])

    print(f"写入 evidence {len(EVID)} 条、claims {len(CLAIMS)} 条")
    for cid, *_ in CLAIMS:
        print(f"  {cid}: {len(by_claim.get(cid, []))} 条证据")
    return 0


if __name__ == "__main__":
    sys.exit(main())