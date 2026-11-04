"""生成 sources / documents / evidence / claims 四张表。

## 本专题的论证主线

    CUDA kernel 的 RL 训练，难点不在算法，在**奖励**。

理由：kernel 生成的奖励天然可验证（能编译、能跑、快不快），
这正是 RLVR 的理想场景。但正因为奖励是「跑出来的一个数」，
它同时是**可被作弊的目标**：

    只求 correct 不求 fast  →  trivial kernel 拿满分
    只求 fast 不求 correct →  用错的算法换速度
    基线不诚（不开 TF32）   →  加速比虚高

故近两年的方法演进，本质是**奖励设计的演进**：
从「一个标量」到「结构化分解 + 反作弊 + 多轮塑形」。

## 证据纪律

`evidence.quote` 必须是 arXiv 摘要的**原文子串**（ADR-0002 的 E1）。
写完后脚本自检，E1 由框架的 `invariants.check_e1_substring` 复核。

不写「我认为」的转述。转述只能进 `claims.statement` 或 `derivation`。
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "candidates_rl.json"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
FETCHED = NOW.isoformat()
AS_OF = NOW.date().isoformat()
PARSER = "arxiv-abstract-v1"

papers: dict[str, dict] = {}
for p in json.loads(CANDS.read_text(encoding="utf-8")):
    papers[p["id"]] = p
# KernelBench 与 Cold-Start 两篇不在本轮的检索候选池里（检索式没覆盖到），
# 但它们是论证必需的：前者是领域基准，后者讲冷启动课程。
# 从既有的 cuda-kernel-gen 归档补入，而不是凭记忆编造。
_OLD = HERE.parent / "cuda-kernel-gen" / "paper" / "papers.json"
if _OLD.is_file():
    for p in json.loads(_OLD.read_text(encoding="utf-8")):
        papers.setdefault(p["id"], p)


def aid_of(source_id: str) -> str:
    m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", source_id)
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def src_id(aid: str) -> str:
    return "src-arxiv-" + aid.replace(".", "-")


def doc_id(aid: str) -> str:
    return "doc-arxiv-" + aid.replace(".", "-")


# ---------------------------------------------------------------- 纳入范围
# 只把真正用于论证的论文写入 sources（不是候选池全部）。
# 每篇都要在 claim 里被引用，否则是「收了不用」。
CORE = [
    "2507.11948",  # Kevin：多轮 RL
    "2507.14111",  # CUDA-L1：对比式 RL
    "2507.05687",  # AutoTriton：Triton RL
    "2510.17891",  # TritonRL：HRD 分解
    "2512.02551",  # CUDA-L2：HGEMM + RL
    "2602.05885",  # Dr. Kernel：PR/PRS 反作弊
    "2602.24286",  # CUDA Agent：大规模 agentic RL
    "2603.21465",  # DRTriton：合成数据驱动
    "2606.04847",  # MusaCoder：稀疏奖励与稳定性
    "2607.20908",  # Multi-turn RL：结构化奖励
    "2608.01804",  # LEAP：环境反馈剪枝
    "2610.23950",  # Compaction-Aware：上下文压实
    "2501.08071",  # CuAsmRL：SASS 层深度 RL（谱系起点）
]
ADJACENT = [
    "2605.31464",  # GPU Forecasters：性能代理，降低奖励成本
    "2606.26453",  # Micro-Profiling：profiling 当环境信号
    "2603.10846",  # Cold-Start Drafting
    "2511.12294",  # ProofWright：形式化验证
]
INFRA = [
    "2607.16241",  # KernelBench-Verified：基线校正
    "2609.22220",  # Measuring the Checker：变异分析
    "2502.10517",  # KernelBench：基准本身
]
INCLUDED = CORE + ADJACENT + INFRA


# ---------------------------------------------------------------- 证据
evidence: list[dict] = []
EID = 0


def grab(aid: str, pattern: str, note: str,
         quote_type: str = "quote", stance: str = "supports") -> str:
    """从摘要中截取一段**原文**，返回 evidence_id（空串表示未命中）。"""
    global EID
    p = papers.get(aid)
    if not p:
        print(f"  [!] 论文不在候选池：{aid}")
        return ""
    ab = p["abstract"]
    m = re.search(pattern, ab, re.I)
    if not m:
        print(f"  [!] 正则未命中 {aid}: {pattern[:50]}")
        return ""
    s, e = m.span()
    # 扩展到句子边界，仍保证是原文子串
    left = ab.rfind(". ", 0, s)
    left = 0 if left < 0 else left + 2
    right = ab.find(". ", e)
    right = len(ab) if right < 0 else right + 1
    quote = ab[left:right].strip()
    EID += 1
    eid = f"e-{EID:03d}"
    evidence.append({
        "evidence_id": eid,
        "document_id": doc_id(aid),
        "source_id": src_id(aid),
        "quote": quote,
        "locator": "abstract",
        "quote_type": quote_type,
        "stance": stance,
        "fetched_at": FETCHED,
        "note": note,
    })
    return eid


print("抽取证据…")
# 谱系起点：SASS 层 RL
# ⚠️ 摘要里没有 "reinforcement learning" 这个短语（标题才有），
# 正文用 "RL agent"。首次按前者匹配会静默失配。
ev_cuasmrl = grab(
    "2501.08071", r"training an RL agent",
    "CuAsmRL 用 RL agent 学习 SASS 调度，是 LLM 之前的最早形态")
ev_cuasmrl_res = grab(
    "2501.08071", r"up to \$?26",
    "CuAsmRL 的量化结果：最高 26%，平均 9%——谱系起点处的参照")

# 多轮交互成为共识
ev_kevin = grab(
    "2507.11948", r"highly iterative",
    "Kevin 指出 kernel 编写本质是迭代过程，执行反馈是天然奖励")
ev_kevin2 = grab(
    "2507.11948", r"verifiable rewards",
    "Kevin 明确 kernel 具备可验证奖励（正确性 + 加速比），适合 RL")

# 对比式奖励
ev_l1 = grab(
    "2507.14111", r"contrastive RL",
    "CUDA-L1 用对比式 RL，把「相对基线的差异」作为学习信号")
ev_l1_res = grab(
    "2507.14111", r"average speedup of x[\d.]+",
    "CUDA-L1 报告算术平均 3.12x")

# Triton 方向
ev_autotriton = grab(
    "2507.05687", r"reinforcement learning",
    "AutoTriton 将 RL 用于 Triton 编程")
ev_tritonrl = grab(
    "2510.17891", r"reward hacking",
    "TritonRL 直面奖励作弊问题，提出层次化奖励分解（HRD）")
ev_tritonrl2 = grab(
    "2510.17891", r"credit assignment",
    "TritonRL 的 HRD 用于缓解信用分配问题")

# 反作弊：Dr. Kernel
ev_dr = grab(
    "2602.05885", r"reward hacking and lazy optimization",
    "Dr. Kernel 指出模型会优先选「平凡但正确」而非「快但可能错」")
ev_dr2 = grab(
    "2602.05885", r"trivial correctness over meaningful speedup",
    "Dr. Kernel 具体描述懒惰优化：trivial correctness 压过真实加速")
ev_dr3 = grab(
    "2602.05885", r"Profiling-based Rejection Sampling|PRS",
    "Dr. Kernel 的解法：渐进式奖励 + 基于 profiling 的拒绝采样")

# 稀疏奖励与不稳定：MusaCoder
ev_musa = grab(
    "2606.04847", r"sparse rewards, reward hacking, and training instability",
    "MusaCoder 把三重困难并列：稀疏奖励、奖励作弊、训练不稳定")
ev_musa2 = grab(
    "2606.04847", r"Buffered Dynamic Retry|MirrorPop",
    "MusaCoder 的工程手段：缓冲重试与 off-policy 序列过滤")

# 结构化奖励
ev_mtrl = grab(
    "2607.20908", r"structural code-aware rewards",
    "多轮 RL 引入结构化奖励：并行化特征等代码性质进入奖励")
ev_mtrl2 = grab(
    "2607.20908", r"outcome-based signals",
    "该文批评已有 RLVR 只看正确性与加速比这类结果信号")

# 环境反馈成本：LEAP
ev_leap = grab(
    "2608.01804", r"compilation latencies|signal sparsity",
    "LEAP 指出多轮环境反馈的两个成本：编译延迟与奖励稀释")
ev_leap2 = grab(
    "2608.01804", r"Group Relative Policy Optimization",
    "LEAP 基于无 critic 的 GRPO（省去价值网络的内存开销）")
# GRPO 的具体缺陷：不是「不流行」，而是「有已知偏差」
ev_grpo_bias = grab(
    "2602.05885", r"biased policy gradient",
    "Dr. Kernel 指出 GRPO 的 self-inclusion 导致策略梯度有偏")
ev_grpo_sparse = grab(
    "2610.23950", r"inherently incurs sparse rewards",
    "ATRL 指出 GRPO 依赖终端结果评估，长程任务上奖励天然稀疏")
ev_grpo_token = grab(
    "2608.01804", r"token inefficiency",
    "LEAP 在 GRPO 的相对优势中额外惩罚 token 低效")

# 上下文与长程：Compaction-Aware
ev_compact = grab(
    "2610.23950", r"context window|context accumulation",
    "上下文累积超出窗口，是多轮交互的硬约束")

# 大规模 agentic
ev_agent = grab(
    "2602.24286", r"agentic RL|torch\.compile",
    "CUDA Agent 做大规模 agentic RL，并以 torch.compile 为对照")
ev_agent2 = grab(
    "2602.24286", r"training-free refinement",
    "该文把已有方法分为「免训练精修」与「训练式」两类")

# 合成数据
# ⚠️ 正文写的是 "data synthetic algorithm"，不是 "synthetic data"。
ev_drtriton = grab(
    "2603.21465", r"data synthetic algorithm",
    "DRTriton 用合成算法 CSP-DAG 保证算子空间全覆盖与无偏采样")
ev_drtriton_res = grab(
    "2603.21465", r"92\%",
    "DRTriton-7B 在 KernelBench Level 2 上 92% 超过 PyTorch，"
    "对照 GPT-5.2 的 23%、Claude-Sonnet-4.5 的 19%")

# CUDA-L2
ev_l2 = grab(
    "2512.02551", r"HGEMM|cuBLAS",
    "CUDA-L2 以 cuBLAS 为基线优化 HGEMM")
ev_l2b = grab(
    "2512.02551", r"CUDA execution speed as the RL reward",
    "CUDA-L2 直接用执行速度作奖励")

# 邻接：降低奖励成本
ev_forecast = grab(
    "2605.31464", r"surrogate|forecast",
    "GPU Forecasters 用模型预测 kernel 性能，替代真实测量")
ev_profiling = grab(
    "2606.26453", r"profil",
    "Micro-Profiling 把硬件计数器变成专家级反馈信号")

# 基础设施：评测协议
ev_verified = grab(
    "2607.16241", r"verified|PyTorch",
    "KernelBench-Verified 用更严格协议重测，结论反转")
ev_checker = grab(
    "2609.22220", r"mutation",
    "Measuring the Checker 用变异分析检验评测器本身是否可靠")
ev_kb = grab(
    "2502.10517", r"KernelBench",
    "KernelBench 是该领域的奠基基准")


# ---------------------------------------------------------------- 主张
claims: list[dict] = []


def add_claim(cid: str, statement: str, ctype: str, confidence: str,
              evids: list[str], *, counter: str = "", derivation: str = "",
              notes: str = "") -> None:
    claims.append({
        "claim_id": cid,
        "statement": statement,
        "claim_type": ctype,
        "as_of": AS_OF,
        "confidence": confidence,
        "evidence_ids": ";".join(e for e in evids if e),
        "counter_evidence_ids": counter,
        "derivation": derivation,
        "notes": notes,
    })


add_claim("c-kernel-rl-fit",
          "kernel 生成天然适合强化学习：奖励可验证（能否编译、能否通过正确性检查、相对基线快多少），无需人工偏好标注。",
          "spec", "high", [ev_kevin2, ev_kevin],
          notes="这是该方向在 2025 年集中爆发的结构性原因")

add_claim("c-iterative-nature",
          "kernel 编写本质上是迭代过程——写、跑、看 profiling、改——因此多轮 RL 比单轮生成更贴合任务形态。",
          "spec", "high", [ev_kevin, ev_mtrl],
          notes="Kevin 首次把这一点显式写进训练目标")

add_claim("c-cuasmrl-origin",
          "LLM 之前已存在在 SASS 指令调度层应用深度 RL 的工作，"
          "说明「用学习替代手工调优」的思路早于大模型。",
          "attribution", "medium", [ev_cuasmrl],
          notes="CuAsmRL（2025-01）作为方法谱系的起点")

add_claim("c-reward-hacking",
          "RL 训练 kernel 生成模型时存在系统性奖励作弊：模型倾向于选择「平凡但正确」的实现，而非「更快但可能出错」的实现。",
          "measurement", "high", [ev_dr, ev_dr2, ev_tritonrl],
          notes="Dr. Kernel 与 TritonRL 独立报告同一现象")

add_claim("c-lazy-optimization",
          "懒惰优化是奖励作弊的具体形态：一旦正确性奖励是二值的、速度奖励被正确性一票否决，模型的最优策略就是写出最保险的朴素实现。",
          "spec", "high", [ev_dr2],
          derivation="由奖励结构推出：若 R = 1[correct] * f(speed) 且 correct 难以保证，"
          "则最大化期望奖励的策略是最大化 P(correct)，即退化为朴素实现。",
          notes="这是奖励设计的结构性问题，不是模型能力问题")

add_claim("c-three-difficulties",
          "该方向公认的三重困难是：稀疏奖励、奖励作弊、训练不稳定。",
          "spec", "high", [ev_musa],
          notes="MusaCoder 把三者并列，与 Dr. Kernel、TritonRL 的观察一致")

add_claim("c-hrd-decomposition",
          "层次化奖励分解（把高层推理与底层实现的奖励解耦）是缓解信用分配问题的有效手段。",
          "spec", "medium", [ev_tritonrl2, ev_tritonrl, ev_grpo_bias],
          notes="TritonRL 的 HRD；单篇报告，故 medium")

add_claim("c-structural-reward",
          "奖励设计正从「单一结果标量」转向「结构化信号」：把并行化特征、代码结构等中间性质纳入奖励，而不只看最终正确性与加速比。",
          "spec", "high", [ev_mtrl, ev_mtrl2],
          notes="这是 2026 年方法演进的主线")

add_claim("c-profiling-reward",
          "profiling 反馈（硬件计数器）被用作奖励或环境信号，"
          "把x",
          "spec", "medium", [ev_profiling],
          notes="Micro-Profiling 等工作")

add_claim("c-prs-rejection",
          "基于 profiling 的拒绝采样与渐进式奖励是反作弊的具体工程手段。",
          "spec", "medium", [ev_dr3],
          notes="Dr. Kernel 的 PR/PRS")

add_claim("c-env-cost",
          "多轮环境反馈的主要成本是编译与测速延迟，以及由此带来的奖励稀释"
          "与上下文膨胀。",
          "measurement", "high", [ev_leap, ev_compact],
          notes="LEAP 与 Compaction-Aware 分别从延迟与上下文两侧描述")

add_claim("c-context-limit",
          "上下文窗口是多轮 kernel RL 的硬约束：交互轮数增加会迅速超出"
          "模型的有效上下文，需要压实或摘要机制。",
          "spec", "medium", [ev_compact],
          notes="Ascend 平台上的实证，是否可迁移到 CUDA 未验证")

add_claim("c-grpo-default-but-flawed",
          "无 critic 的 GRPO 已成为该方向的默认算法（省去价值网络的内存开销），"
          "但它有两个与该任务直接冲突的已知缺陷：self-inclusion 导致策略梯度有偏，"
          "依赖终端结果评估导致长程交互中奖励天然稀疏。",
          "spec", "high", [ev_leap2, ev_grpo_bias, ev_grpo_sparse, ev_grpo_token],
          derivation="kernel 生成的两个特性恰好命中 GRPO 的两个弱点："
                     "(1) 一次优化需要多轮编译-测速，属长程任务，"
                     "终端奖励在几十步后才出现，故稀疏；"
                     "(2) 奖励可分解为正确性与速度两部分，"
                     "而 GRPO 的组内相对优势把它们压成一个标量。",
          notes="「是默认」与「为何不合适」同时成立；"
                "后续的 HRD、渐进式奖励、段级目标都是在补这两个洞")

add_claim("c-forecast-surrogate",
          "用模型预测 kernel 性能（代理模型）来替代真实测量，"
          "是降低奖励获取成本的可行方向。",
          "spec", "medium", [ev_forecast],
          notes="GPU Forecasters；尚属早期")

add_claim("c-synthetic-data",
          "大规模合成数据是缓解 kernel 训练数据稀缺的主要手段。",
          "measurement", "high", [ev_drtriton, ev_drtriton_res],
          notes="DRTriton：7B 模型在 Level 2 上达 92%，显著高于通用大模型；说明专用训练的价值")

add_claim("c-baseline-inflation",
          "以「是否快于基线」作奖励时，基线的选择直接决定奖励的真假："
          "基线不开 TF32 等加速，会让作弊行为获得奖励。",
          "measurement", "high", [ev_verified],
          notes="KernelBench-Verified 的受控实验")

add_claim("c-checker-reliability",
          "奖励函数的正确性本身需要被检验：评测器（checker）的漏洞会被"
          "RL 主动发现并利用。",
          "measurement", "high", [ev_checker],
          notes="Measuring the Checker 用变异分析评估评测器")

add_claim("c-agentic-scale",
          "大规模 agentic RL（把 RL 与 agent 环境、数据合成流水线结合）"
          "是该方向当前的前沿形态。",
          "spec", "medium", [ev_agent, ev_agent2],
          notes="CUDA Agent")

add_claim("c-l1-result",
          "CUDA-L1 报告在 KernelBench 250 题上算术平均 3.12x 的加速。",
          "measurement", "high", [ev_l1, ev_l1_res],
          notes="对比式 RL 的代表结果；需与基线口径一并看")

add_claim("c-l2-cublas",
          "CUDA-L2 以 cuBLAS 为基线优化 HGEMM，并直接用执行速度作 RL 奖励。",
          "measurement", "high", [ev_l2, ev_l2b],
          notes="少见的以闭源库为基线的对照")

add_claim("c-benchmark-base",
          "KernelBench 建立了「PyTorch 参考实现 -> CUDA kernel」这一任务范式和"
          "配套的正确性/加速比评测，后续工作大多沿用。",
          "attribution", "high", [ev_kb],
          notes="领域奠基基准")


# ---------------------------------------------------------------- 写出
def write_csv(name: str, rows: list[dict], header: list[str]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    (HERE / name).write_text(buf.getvalue(), encoding="utf-8", newline="\n")


SRC_HEADER = ["source_id", "url", "source_type", "publisher", "title",
              "published_at", "updated_at", "fetched_at", "language",
              "trust_tier", "access", "license", "notes"]
sources = []
for aid in INCLUDED:
    p = papers.get(aid)
    if not p:
        print(f"  [!] 纳入列表里的 {aid} 不在候选池")
        continue
    layer = ("core" if aid in CORE
             else "adjacent" if aid in ADJACENT else "infra")
    sources.append({
        "source_id": src_id(aid),
        "url": f"https://arxiv.org/abs/{aid}",
        "source_type": "academic",
        "publisher": "arXiv",
        "title": p["title"],
        "published_at": p["published"],
        "updated_at": p.get("updated") or p["published"],
        "fetched_at": FETCHED,
        "language": "en",
        "trust_tier": "primary",
        "access": "open",
        "license": "arXiv 非独占许可",
        "notes": f"layer={layer}",
    })

write_csv("sources.csv", sources, SRC_HEADER)

EV_HEADER = ["evidence_id", "document_id", "source_id", "quote", "locator",
             "quote_type", "stance", "fetched_at", "note"]
write_csv("evidence.csv", evidence, EV_HEADER)

CLAIM_HEADER = ["claim_id", "statement", "claim_type", "as_of", "confidence",
                "evidence_ids", "counter_evidence_ids", "derivation", "notes"]
write_csv("claims.csv", claims, CLAIM_HEADER)

# 文档快照：让 E1 有可比对的原件
docdir = HERE / "documents"
docdir.mkdir(exist_ok=True)
DOC_HEADER = ["document_id", "source_id", "content_hash", "parser_version",
              "byte_size", "snapshot"]
import hashlib  # noqa: E402
doc_rows = []
used_aids = {a for a in INCLUDED if a in papers}
for aid in sorted(used_aids):
    p = papers[aid]
    text = p["abstract"]
    did = doc_id(aid)
    (docdir / f"{did}.txt").write_text(text, encoding="utf-8", newline="\n")
    doc_rows.append({
        "document_id": did,
        "source_id": src_id(aid),
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "parser_version": PARSER,
        "byte_size": str(len(text.encode("utf-8"))),
        "snapshot": f"documents/{did}.txt",
    })
write_csv("documents.csv", doc_rows, DOC_HEADER)

print(f"\nsources  {len(sources)}")
print(f"evidence {len(evidence)}")
print(f"claims   {len(claims)}")
print(f"documents {len(doc_rows)}")

# ---------------- 自检：quote 必须是摘要原文子串（E1） ----------------
bad = 0
for e in evidence:
    aid = aid_of(e["source_id"])
    ab = papers.get(aid, {}).get("abstract", "")
    if e["quote"] not in ab:
        print(f"  [!] E1 违反 {e['evidence_id']}: quote 不是 {aid} 摘要子串")
        bad += 1
print(f"\n=== E1 自检：{len(evidence)} 条，失败 {bad} ===")

# ---------------- 自检：prediction 类必须带 derivation（C2） ----------------
for c in claims:
    if c["claim_type"] == "prediction" and not c["derivation"]:
        print(f"  [!] C2 违反 {c['claim_id']}: prediction 无 derivation")
        bad += 1
print(f"=== C2 自检：{len(claims)} 条主张 ===")
