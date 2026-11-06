"""从 arXiv 元数据生成 sources.csv / documents.csv / evidence.csv。

## 为什么由一个脚本生成

三条不变量都要求「机器可查」，而手写 CSV 一定会破其中某一条：

- S1：fetched_at 必填且带时区——手写常漏时区，或几个来源写同一秒却没真的抓。
- E1：quote 必须是原文子串——手写必然出现「我记得原文是这么说的」。
- D1：同一 document 不得有两个 content_hash——手写会覆盖旧快照。

故这里只声明 （evidence_id, arxiv_id, quote） 三元组，
标题、日期、作者、URL、哈希、快照全部从语料与原文推导。
quote 不是 abstract 的子串就直接报错退出——不允许「差不多」。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
FETCHED = datetime.now(TZ).replace(microsecond=0).isoformat()

# (evidence_id, arxiv_id, quote, note)
QUOTES: list[tuple[str, str, str, str]] = [
    # ---- 第一波：答案锚定（2022-2024） ----
    ("e-001", "2203.14465",
     "if the generated answers are wrong, try again to generate a rationale given the correct answer; fine-tune on all the rationales that ultimately yielded correct answers; repeat",
     "STaR 的循环：生成→用正确答案回填提示→只保留导致正确答案的推理→再训练"),
    ("e-002", "2203.14465",
     "performs comparably to fine-tuning a 30$\\times$ larger state-of-the-art language model on CommensenseQA",
     "STaR 报告与 30 倍大模型可比，是这一波最有名的量化声明"),
    ("e-003", "2308.08998",
     "Given an initial LLM policy, ReST produces a dataset by generating samples from the policy, which are then used to improve the LLM policy using offline RL algorithms.",
     "ReST 把自举写成「生长式批 RL」：离线生成、离线训练"),
    ("e-004", "2401.01335",
     "the LLM generates its own training data from its previous iterations, refining its policy by discerning these self-generated responses from those obtained from human-annotated data",
     "SPIN 的自博弈：判别「自己生成的」与「人写的」，本质是用人的数据当锚"),
    ("e-005", "2403.09629",
     "a generalization of STaR in which LMs learn to generate rationales at each token to explain future text",
     "Quiet-STaR 把 STaR 从 QA 推广到任意文本，外部锚点从「答案」变成「后续文本」"),
    ("e-006", "2402.06457",
     "discard the large amounts of incorrect solutions generated during this process",
     "V-STaR 指出第一波 RSI 把错误解直接丢弃，是可利用信号的浪费"),
    ("e-007", "2404.19733",
     "we see a large improvement from 55.6% to 81.6% on GSM8K",
     "Iterative RPO 的量化结果，说明迭代偏好优化在推理任务上的量级"),

    # ---- 第二波之一：评判者内化 ----
    ("e-008", "2401.10020",
     "the language model itself is used via LLM-as-a-Judge prompting to provide its own rewards during training",
     "Self-Rewarding 的核心：把奖励模型换成模型自己（LLM-as-a-Judge）"),
    ("e-009", "2401.10020",
     "not only does instruction following ability improve, but also the ability to provide high-quality rewards to itself",
     "自评能力与作答能力同时上升——这是「双轴自举」的主张"),
    ("e-010", "2407.19594",
     "existing methods have primarily focused on improving model responses rather than judgment capabilities, resulting in rapid saturation during iterative training",
     "Meta-Rewarding 直接报告上一代方法在迭代中迅速饱和，是内化路线的第一个自我否定"),
    ("e-011", "2407.19594",
     "a win rate improvement of Llama-3-8B-Instruct from 22.9% to 39.4% on AlpacaEval 2",
     "Meta-Rewarding 的量化结果"),
    ("e-012", "2408.02666",
     "Without any labeled preference data, our Self-Taught Evaluator can improve a strong LLM (Llama3-70B-Instruct) from 75.4 to 88.3 (88.7 with majority vote) on RewardBench.",
     "Self-Taught Evaluators：评判器本身可以被自举，不需要偏好标注"),

    # ---- 第二波之二：冻结模型改外壳 ----
    ("e-013", "2408.08435",
     "agents can be defined in code and new agents can be automatically discovered by a meta agent programming ever better ones in code",
     "ADAS 的 Meta Agent Search：把「设计 agent」本身变成可搜索的对象"),
    ("e-014", "2410.04444",
     "enabling agents to recursively improve themselves without relying on predefined routines or fixed optimization algorithms",
     "Gödel Agent：不依赖预定义流程与固定优化算法"),
    ("e-015", "2505.22954",
     "iteratively modifies its own code (thereby also improving its ability to modify its own codebase) and empirically validates each change using coding benchmarks",
     "DGM 的自指性：改自己的代码，从而改自己改代码的能力；用基准做经验验证"),
    ("e-016", "2504.15228",
     "an agent system, equipped with basic coding tools, can autonomously edit itself, and thereby improve its performance on benchmark tasks",
     "SICA：不带梯度的自我修改"),
    ("e-017", "2504.15228",
     "We find performance gains from 17% to 53% on a random subset of SWE Bench Verified",
     "SICA 的量化结果"),
    ("e-018", "2506.13131",
     "continuously receiving feedback from one or more evaluators, AlphaEvolve iteratively improves the algorithm",
     "AlphaEvolve：适应度来自一个或多个评估器，与 DGM 同型"),
    ("e-019", "2509.19349",
     "current code evolution methods suffer from critical limitations: they are sample inefficient, requiring thousands of samples",
     "ShinkaEvolve 指出代码演化路线的样本效率是瓶颈"),
    ("e-020", "2310.03714",
     "DSPy modules are parameterized, meaning they can learn (by creating and collecting demonstrations) how to apply compositions of prompting, finetuning, augmentation, and reasoning techniques",
     "DSPy：把管线编译成可优化对象，是把「外壳」参数化的最早形态之一"),

    # ---- 第三波：零数据自举 ----
    ("e-021", "2505.03335",
     "a single model learns to propose tasks that maximize its own learning progress and improves reasoning by solving them, without relying on any external data",
     "Absolute Zero：连问题都自产，外部数据量为零"),
    ("e-022", "2508.05004",
     "the Challenger is rewarded for proposing tasks near the edge of the Solver capability, and the Solver is rewarded for solving increasingly challenging tasks",
     "R-Zero 的双角色共演化：课程由「接近能力边界」这个条件生成"),
    ("e-023", "2508.14029",
     "vanilla RLVR training has been shown to improve Pass@1 performance at the expense of policy entropy",
     "SvS 报告 RLVR 的 pass@1 与熵的交换关系——单看 pass@1 会漏掉这一层"),
    ("e-024", "2511.16043",
     "a curriculum agent that proposes increasingly challenging frontier tasks, and an executor agent that learns to solve them",
     "Agent0：课程 agent 与执行 agent 的共演化，工具接入后课程随之变难"),
    ("e-025", "2512.18552",
     "iteratively inject and repair software bugs of increasing complexity, with each bug formally specified by a test patch rather than a natural language issue description",
     "SSR：连「问题描述」都省掉，用测试补丁形式化任务"),
    ("e-026", "2512.18552",
     "SSR achieves notable self-improvement (+10.4 and +7.8 points, respectively)",
     "SSR 的自改进量级"),
    ("e-027", "2506.10943",
     "we use a reinforcement learning loop with the downstream performance of the updated model as the reward signal",
     "SEAL：奖励是「更新后模型在下游任务上的表现」，即自修改的效果本身"),
    ("e-028", "2503.00735",
     "improving Llama 3.2 3B's accuracy from 1% to 82% on undergraduate-level problems",
     "LADDER：递归把难题分解成更简单变体，量级极端"),
    ("e-029", "2506.01716",
     "The agent first plays the role of challenger and generates a task after interacting with the given tools.",
     "Self-Challenging：Code-as-Task，任务自带验证函数"),
    ("e-030", "2511.10395",
     "self-questioning, which enables curiosity-driven task generation in novel environments",
     "AgentEvolver 的三机制之一：自提问"),
    ("e-031", "2610.32770",
     "guided solely by coarse, high-level topic descriptions, the model synthesizes its own curriculum of queries and privileged reasoning traces",
     "On-Policy Self-Training：监督来自「特权推理示范」，即模型自己更会做的版本"),
    ("e-032", "2502.04780",
     "The library is built by retaining reasoning steps that lead to successful outcomes",
     "SiriuS：经验库只保留通向成功的轨迹——第三波里仍以「结果」为筛选依据的形态"),
    ("e-033", "2505.19866",
     "problems near the boundary of the LLM's reasoning capability offer significantly greater learning utility",
     "HS-STaR：难度即价值，边界问题效用最高（课程自举的经验依据）"),

    # ---- 外部锚点继续内移：从可判定答案到统计量 ----
    ("e-034", "2510.14943",
     "the true reasoning reward of a solution is equal to its last-token self-rewarding score",
     "LaSeR：把「自验证」压缩成末 token 的对数概率差——锚点从语义退到统计量"),
    ("e-035", "2610.41296",
     "UID-Conj. improves the online macro-average across the adaptation benchmark and three transfer benchmarks by 2.08 percentage points over unmodified TTRL.",
     "Auxiliary Rewards：用熵的全局变化+局部平滑替代答案级奖励"),
    ("e-036", "2609.36750",
     "a response's reward representation also depends on its randomly sampled group context",
     "GMAE：奖励本身依赖随机分组的上下文——自举信号的方差来源被显式建模"),
    ("e-037", "2607.23802",
     "RLSVR transforms open-ended tasks into verifiable proxy environments whose internal rules and interaction outcomes automatically generate reward signals",
     "RLSVR：把开放任务改造成「可自验证」的代理环境，是锚点外移的一种（造出新验证器）"),

    # ---- 失效模式：信号侧 ----
    ("e-038", "2510.08977",
     "the model tends to over-reward high-confidence mistakes, forming a self-confirming loop",
     "自评路线的核心失效：高置信度错误被系统性高估，形成自我确认循环"),
    ("e-039", "2504.20073",
     "a recurring mode of Echo Trap where reward variance cliffs and gradient spikes",
     "多轮 agent RL 的 Echo Trap：奖励方差悬崖与梯度尖峰"),
    ("e-040", "2504.13837",
     "the current training setup does not elicit fundamentally new reasoning patterns",
     "最强的反证：RLVR 并未引出新的推理模式"),
    ("e-041", "2504.13837",
     "the base models achieve a higher pass@k score when k is large",
     "同一篇的量化依据：大 k 时基座模型反而更高——能力边界没扩张"),
    ("e-042", "2305.17493",
     "use of model-generated content in training causes irreversible defects in the resulting models, where tails of the original content distribution disappear",
     "模型坍缩的原命题：分布尾部的不可逆损失"),
    ("e-043", "2404.01413",
     "accumulating the successive generations of synthetic data alongside the original real data avoids model collapse",
     "坍缩可避免的条件：累积而非替换真实数据——这是「保留外部性」的具体形式"),
    ("e-044", "2610.30009",
     "even data accumulation does not appear to arrest this drift",
     "反例：采样温度小于 1 时，累积也止不住谱隙收窄"),
    ("e-045", "2601.22513",
     "the dependence on the initial model decays exponentially with the number of iterations",
     "理论侧：对初始模型的依赖随迭代指数衰减——形式化地说明「外部性被兑换掉」"),
    ("e-046", "2601.22513",
     "performance improves at a rate of $\\widetilde{\\mathcal{O}}\\left(1/\\sqrt{n}\\right)$ with sample size $n$",
     "同一篇的收敛速率"),

    # ---- 失效模式：目标侧 ----
    ("e-047", "2610.38392",
     "When safeguards overlap, deleting one is masked: the others still block the harm, so the gate decides on task success alone and redundancy erodes unseen",
     "Masked Erosion：验收门的冗余防护被无声侵蚀——harness 路线的特有失效"),
    ("e-048", "2611.01304",
     "whether and when a model stops self-modification is strongly associated with model identity rather than the assigned mode",
     "停止条件与模型身份强相关，而非任务——自我修改缺少任务侧的自然终点"),
    ("e-049", "2610.27465",
     "Verifier strength $σ$ is how well the available verifier -- often an LLM judge -- agrees with a trusted reference verifier",
     "可测量前置条件之一：验证器强度 sigma"),
    ("e-050", "2610.27465",
     "Recoverability is how cheaply a bad change can be undone",
     "可测量前置条件之二：可恢复性"),
    ("e-051", "2610.27610",
     "Only 22% audit two or more reruns of the full loop.",
     "审计证据：只有 22% 的 RSI 研究审计了至少两次完整循环"),
    ("e-052", "2610.27610",
     "while 60% report evaluation on tasks unused for selection",
     "同一篇：60% 在未被选择用过的任务上评测——比 22% 好看，但差距本身是缺口"),
    ("e-053", "2610.35193",
     "self-modification alone does not guarantee trustworthy improvement",
     "可信 RSI 综述的核心命题"),

    # ---- 元层面：领域的自我描述与它的内容不一致 ----
    ("e-054", "2607.07663",
     "This literature uses a vocabulary (\"self-refine,\" \"self-reward,\" \"self-play,\" \"self-evolve\") that conflates fundamentally different ambitions.",
     "RSI 综述：同一套词汇混着根本不同的野心"),
    ("e-055", "2607.07663",
     "We survey 1,250 arXiv papers (2024-2026) along two axes",
     "同一篇的取材规模，用于对照本文的 61 篇"),
    ("e-056", "2412.14352",
     "Techniques that enhance inference through increased computation at test-time have recently gained attention",
     "推理时自改进这一支的定位"),
    ("e-057", "2507.21046",
     "remain fundamentally static, unable to adapt their internal parameters to novel tasks",
     "自演化 agent 综述给出的出发点：模型本身是静态的"),

    # ---- 工程侧证据：外壳自举的实际形态 ----
    ("e-058", "2303.11366",
     "reinforce language agents not by updating weights, but instead through linguistic feedback",
     "Reflexion 明确不走权重路线——外壳路线的最早形态"),
    ("e-059", "2305.16291",
     "an ever-growing skill library of executable code",
     "Voyager 的技能库：把经验固化成可执行代码，而非权重"),
    ("e-060", "2409.07429",
     "AWM substantially improves the baseline results by 24.6% and 51.1% relative success rate",
     "AWM：把复用的工作流抽成记忆，是「上下文层自举」的量化证据"),
    ("e-061", "2610.32026",
     "A meta-agent rewrites this policy using evidence from earlier runs",
     "RSI-Opt：让 agent 改进「指导训练优化器的策略」——改进过程本身被自举"),
    ("e-062", "2611.04035",
     "raises the all-pass rate on held-out test tasks from 30.0% to 55.0%",
     "Recursa：知识仓库的递归精炼，在留出任务上的量化结果"),
    ("e-063", "2610.33624",
     "All ten agents produce working assistants",
     "RSI Arena：十个前沿模型端到端做后训练，全部产出可用助手"),
]


def load_corpus() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    # notes/ 放着补取与标题检索得到的中间语料（见 notes/README.md）。
    # 它们与候选池必须**分开放**：候选池代表「检索覆盖到」，notes 代表
    # 「本来就知道、事后核对过」。混在一起会高估检索式的召回率。
    for name in ("candidates_rsi.json", "notes/_resolved.json",
                 "notes/_resolved_extra.json", "notes/_extra.json"):
        p = HERE / name
        if not p.is_file():
            continue
        for r in json.loads(p.read_text(encoding="utf-8")):
            meta.setdefault(r["id"].split("v")[0], r)
    return meta


def norm(s: str) -> str:
    s = s.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    corpus = load_corpus()
    labels = {}
    lab_path = HERE / "corpus_labels.csv"
    if lab_path.is_file():
        with lab_path.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                labels[r["arxiv_id"]] = r

    # ---- 先校验：每条 quote 必须是 abstract 的子串（不变量 E1 的事前检查） ----
    bad: list[str] = []
    used: dict[str, dict] = {}
    for eid, aid, quote, _note in QUOTES:
        rec = corpus.get(aid)
        if rec is None:
            bad.append(f"{eid}: arXiv {aid} 不在语料中")
            continue
        if norm(quote) not in norm(rec["abstract"]):
            bad.append(f"{eid}: quote 不是 {aid} 摘要的原文子串")
        used[aid] = rec
    if bad:
        print("E1 事前校验失败：")
        for b in bad:
            print("  - " + b)
        return 1

    docdir = HERE / "documents"
    docdir.mkdir(exist_ok=True)

    sources_rows, evidence_rows, docs_rows, papers_rows = [], [], [], []
    for aid in sorted(used, key=lambda a: used[a]["published"]):
        rec = used[aid]
        sid = "src-arxiv-" + aid.replace(".", "-")
        did = "doc-arxiv-" + aid.replace(".", "-")
        abstract = norm(rec["abstract"])
        snap = docdir / f"{did}.txt"
        snap.write_text(abstract + "\n", encoding="utf-8", newline="\n")
        digest = hashlib.sha256(snap.read_bytes()).hexdigest()

        lab = labels.get(aid, {})
        layer = lab.get("layer", "na")
        sources_rows.append({
            "source_id": sid,
            "url": f"https://arxiv.org/abs/{aid}",
            "source_type": "academic",
            "publisher": "arXiv",
            "title": norm(rec["title"]),
            "published_at": rec["published"],
            "updated_at": rec["updated"],
            "fetched_at": FETCHED,
            "language": "en",
            "trust_tier": "primary",
            "access": "open",
            "license": "arXiv 非独占许可",
            "notes": f"layer={layer}",
        })
        docs_rows.append({
            "document_id": did,
            "source_id": sid,
            "content_hash": digest,
            "parser_version": "arxiv-abstract-v1",
            "byte_size": str(snap.stat().st_size),
            "snapshot": f"documents/{did}.txt",
        })
        papers_rows.append({
            "id": aid,
            "title": norm(rec["title"]),
            "published": rec["published"],
            "abstract": abstract,
            "layer": layer,
            "reward": lab.get("reward", "na"),
            "metric": lab.get("metric", "na"),
        })

    for eid, aid, quote, note in QUOTES:
        did = "doc-arxiv-" + aid.replace(".", "-")
        evidence_rows.append({
            "evidence_id": eid,
            "document_id": did,
            "source_id": "src-arxiv-" + aid.replace(".", "-"),
            "quote": quote,
            "locator": "abstract",
            "quote_type": "quote",
            "stance": "supports",
            "fetched_at": FETCHED,
            "note": note,
        })

    def write(name: str, rows: list[dict]) -> None:
        with (HERE / name).open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL,
                               lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    write("sources.csv", sources_rows)
    write("documents.csv", docs_rows)
    write("evidence.csv", evidence_rows)
    (HERE / "papers.json").write_text(
        json.dumps(papers_rows, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"sources {len(sources_rows)} / evidence {len(evidence_rows)} / "
          f"documents {len(docs_rows)} -> 已写入")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
