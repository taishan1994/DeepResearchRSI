"""建立 rsi-infra-feedback 的来源与文档层。

## 这一篇的定位

锚点是智谱官方博客《Toward Recursive Self-Improvement: How GLM Built Its Own
Inference Infrastructure》(z.ai, 2026-09-17)。它没有论文、没有 arXiv id，
事实全在博客正文与随附信息里。故本归档的第一手来源是 `official`。

与站内已有的 `rsi-inference` 的分工：
  rsi-inference        以 **kernel 生成**为主，组织轴是「反馈能证明什么」，
                       结论是只有 kernel 层判据可被廉价判定。
  本篇                  以 **系统级（推理/训练栈）自主优化**为主，组织轴是
                       「反馈如何被构造」——局部性、代价、可验证性三属性。
                       它要检验的正是上一句结论是否成立。

## 快照复用

站内 5 个归档已存有这些论文的全文快照，逐字节复制而非重抓：
既省网络，也保证同一篇论文在站内各归档里是同一份文本（content_hash 可比）。
"""
from __future__ import annotations

import csv
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
FETCHED = datetime.now(TZ).replace(microsecond=0).isoformat()

# 锚点：(source_id 后缀, 本地相对路径, 标题, 发布日, parser, 备注)
ANCHOR = [
    ("blog-en", ("documents/doc-zai-blog-en.txt", None),
     "Toward Recursive Self-Improvement: How GLM Built Its Own Inference Infrastructure",
     "2026-09-17", "raw-copy-v1",
     "layer=anchor｜口径｜正文全文（135 段，21KB），从 z.ai 博客 JS bundle 中抽出的"
     "纯文本。三层密集反馈（正确性 / 系统行为 / 性能）、三个案例、"
     "以及「两周 / 3x 吞吐 / 十万卡」三个数字都只在这里"),
    ("blog-html", ("documents/doc-zai-blog-html.html", None),
     "同上，原始 HTML 外壳（SPA 页面，正文在 JS bundle 内）",
     "2026-09-17", "raw-copy-v1",
     "layer=anchor｜溯源｜这是页面的原始字节。保留它是因为纯文本版经过抽取，"
     "若要争辩「原文究竟怎么写的」，只能回到这一份；同时它记录了 "
     "og:title 与 bundle 路径，可复现抽取过程"),
]

# arXiv：(aid, 标题, 发布日, 复用自哪个归档的相对路径, 层, 标签, 备注)
ARXIV = [
    # ---- A 线：系统级 benchmark 与测量（这一族的「判据」侧）----
    ("2607.20468", "InferenceBench: A Benchmark for Open-Ended LLM Inference Optimization by AI Agents",
     "2026-07-22", "agent-serving-bench/documents/doc-arxiv-2607-20468.txt", "core", "bench-serving",
     "系统级优化 agent 的主基准：开放式改服务栈，三重闸门（质量/完整性/部署一致性）。"
     "关键发现是**简单超参搜索打赢 agent**——这是本篇「反馈构造」论断的最强反例"),
    ("2609.18123", "AutoTuneBench: Trustworthy Measurement for Agent Auto-Tuning of LLM Serving Engines",
     "2026-09-24", "rsi-serving/documents/doc-arxiv-2609-18123-full.txt", "core", "bench-measure",
     "把测量本身当成攻击面：四种失败模式（稻草人基线、绝对耗时不可迁移、饱和任务、"
     "基础设施缺陷冒充科学）。它证明「反馈可验证」不免费，要花工程代价去建"),
    ("2610.07792", "ServeLearnBench: How Well Can Agents Self-Improve from Serving Experience?",
     "2026-10-08", "rsi-serving/documents/doc-arxiv-2610-07792-full.txt", "core", "bench-learn",
     "问「agent 能否从服务经验里自改进」：演化环境流式数据集，区分"
     "Hidden-Dependent 与 Fully Specified 两类，故能测出「适应是否伤害本来会做的题」"),
    ("2601.06288", "AIConfigurator: Lightning-Fast Configuration Optimization for Multi-Framework LLM Serving",
     "2026-01-09", "rsi-serving/documents/doc-arxiv-2601-06288-full.txt", "adjacent", "nonagent-search",
     "非 agent 的数据驱动配置搜索（算子级性能模型 + 幂律修正）。"
     "列入是为了做对照：不用 LLM 也能做系统级调优，故「agent」不是必要条件"),
    # ---- B 线：服务栈 / 运行时自优化 ----
    ("2610.25012", "Conjugate Compilation: Self-Improving Agentic Co-Compilation for Speculative Decoding",
     "2026-10-26", "rsi-serving/documents/doc-arxiv-2610-25012-full.txt", "core", "serve-compile",
     "把投机解码的草稿与验证放进同一次执行联合编译，用 MCTS + LLM 提案搜索计划。"
     "它的判据是「在它改变的那次执行里评判」——反馈局部性的一个正例"),
    ("2610.08993", "Verify Less, Evolve More: Training Idea-Level Critics for Verification-Efficient ML Evolving Agents",
     "2026-10-09", "rsi-serving/documents/doc-arxiv-2610-08993-full.txt", "adjacent", "verifier-cost",
     "直接攻击「验证太贵」：训一个 idea 级 critic 替代执行验证。"
     "它给出反馈三属性里「便宜」这一条的可量化替代方案"),
    # ---- C 线：策略 / 脚手架自演化 ----
    ("2610.22791", "Self-Evolving Coding Agents via Harness-Policy Optimization",
     "2026-10-26", "rsi-serving/documents/doc-arxiv-2610-22791-full.txt", "core", "scaffold-evolve",
     "把「脚手架」与「策略」交替优化，并论证 harness 优化胜过 SFT 蒸馏。"
     "它是「自改进发生在脚手架而非权重」这一判断的直接支持"),
    ("2610.21791", "RSIFlow: Adaptive Self-Improvement Workflows with an Evolving Meta-Agent",
     "2026-10-25", "rsi-inference/documents/doc-arxiv-2610-21791-full.txt", "adjacent", "workflow-evolve",
     "演化的是**工作流**而非代码：meta-agent 自适应编排子任务。"
     "提供「被改进的对象可以再上一层」的第三种答案"),
    ("2603.21321", "Improving Coherence and Persistence in Agentic AI for System Optimization",
     "2026-03-25", "rsi-inference/documents/doc-arxiv-2603-21321-full.txt", "core", "engram",
     "MIT 的 Engram：指出两种失效（演化邻域偏置、连贯性天花板），"
     "用结构化研究笔记本跨跑累积知识。这是本篇「长程累积」的关键对照"),
    # ---- D 线：内核 / 算子层（作为对照层，证明层级差异）----
    ("2602.14293", "KernelBlaster: Continual Cross-Task CUDA Optimization via Memory-Augmented In-Context Reinforcement Learning",
     "2026-02-20", "rsi-inference/documents/doc-arxiv-2602-14293-full.txt", "core", "kernel-memory",
     "跨任务记忆 + 上下文内 RL，回答「每个新 kernel 都从零搜」的浪费。"
     "它是「局部反馈最便宜」这一层的代表作"),
    ("2610.31034", "CANNBot-CAKE: Collaborative Agentic Kernel Evolution for Ascend NPU",
     "2026-10-30", "rsi-inference/documents/doc-arxiv-2610-31034-full.txt", "core", "kernel-npu",
     "国产 NPU 上的协同演化。与锚点最同构：同为国产芯片 + 生态不成熟 + "
     "靠反馈补文档缺失，故可直接对照「密集反馈」是否只在 GPU 上成立"),
    ("2506.20807", "GPU Kernel Scientist: An LLM-Driven Framework for Iterative Kernel Optimization",
     "2025-06-30", "rsi-inference/documents/doc-arxiv-2506-20807-full.txt", "adjacent", "kernel-early",
     "早期形态：把「提出-编译-测速-改」写成固定循环。"
     "列入为时间起点，用来看 18 个月里循环结构变了什么"),
    ("2510.16996", "STARK: Strategic Team of Agents for Refining Kernels",
     "2025-10-18", "kernel-agent/documents/doc-arxiv-2510-16996-full.txt", "adjacent", "kernel-team",
     "多 agent 分工（规划/编码/调试）修 kernel。用来检验「多 agent 是否等于更强反馈」"),
    ("2511.06345", "PRAGMA: A Profiling-Reasoned Multi-Agent Framework for Automatic Kernel Optimization",
     "2025-11-10", "kernel-agent/documents/doc-arxiv-2511-06345-full.txt", "adjacent", "kernel-profiling",
     "把 profiler 读数显式喂进 agent 作为推理依据。"
     "它是「系统行为反馈」在 kernel 层的对应物，可与锚点案例二对读"),
    # ---- E 线：训练侧（同构但对象不同）----
    ("2511.03844", "ASAP: an Agentic Solution to Auto-optimize Performance of Large-Scale LLM Training",
     "2025-11-05", "documents/doc-arxiv-2511-03844-full.txt", "core", "train-sharding",
     "训练侧同构工作：profiler + roofline + 知识库 → 分片配置提案。"
     "它的 limitation 自陈「缺 Evaluator Agent、无闭环」，正好是密集反馈的反面坐标"),
    # ---- F 线：判据侧的反证 ----
    ("2607.16241", "KernelBench-Verified: Do LLM-Generated Kernels Actually Beat PyTorch?",
     "2026-07-19", "agent-serving-bench/documents/doc-arxiv-2607-16241.txt", "core", "judge-strict",
     "收紧测量后同一批模型从 1.43x 掉到 0.88x。"
     "它证明「反馈的可验证性」一变，结论就翻转——本篇 q4 的核心证据"),
    # ---- G 线：第 3 轮补入（此前因检索方法缺陷被整体漏掉）----
    ("2610.04646", "SEIS: Self-Evolving Inference Systems",
     "2026-10-03", "documents/doc-arxiv-2610-04646-full.txt", "core", "engine-evolve",
     "与锚点最直接对标的学术工作：agent 连续 session 改写整个 mini-sglang"
     "（kernel / 算子融合 / runtime / 投机解码），1942 vs 594 tok/s（3.27x）、"
     "295→89 ms。⚠️ 关键区别：它明确自陈「agent 固定、引擎演化」，故不是严格 RSI"),
    ("2611.11558", "InfraRSI: Harnessing Recursive Self-Improvement for Training Infrastructure",
     "2026-11-08", "documents/doc-arxiv-2611-11558-full.txt", "core", "train-rsi",
     "训练侧：两层 RSI（run 内在线修正先验 + 跨集群经验蒸馏），"
     "最高 2.75x、MFU 17.4%→30.0%。⚠️ 仓库极新，尚无独立复现——"
     "本篇把它当作「声明强度 vs 证据强度」的案例"),
    ("2608.25570", "Beyond Scaling: Self-Evolving LLM Agents for Hardware Kernel Optimization via an Experience-Driven Workflow and Experience Graph Memory (KOPE)",
     "2026-08-26", "documents/doc-arxiv-2608-25570-full.txt", "core", "experience-graph",
     "Experience Graph Memory + Active Context Management：把 decision→feedback→"
     "后续决策 存成图，在固定 token 预算下检索。pass 55.2%→84.6%、"
     "token 15.9B→1.113B。⚠️ 本篇第一轮曾打印过它的摘要却漏收，是本归档方法缺陷的物证"),
    ("2610.36848", "Evolving Agent Teams",
     "2026-10-27", "documents/doc-arxiv-2610-36848-full.txt", "core", "org-evolve",
     "NeurIPS'26。被演化的对象是**团队结构**而非代码：supervisor 观察停滞原因后重组角色。"
     "把「可进化对象」推到组织层，是本篇谱系里最靠上的一格"),
    ("2609.26777", "SWE-Serve: Benchmarking Agentic Engineering for Production Inference Serving",
     "2026-09-22", "documents/doc-arxiv-2609-26777-full.txt", "core", "bench-production",
     "NVIDIA：53 个从 SGLang 真实生产变更提炼的任务群。核心发现是"
     "「局部测试通过、端到端服务测试失败」，故它是密集反馈必要性的独立证据"),
    ("2607.05297", "MetaSkill-Evolve: Recursive Self-Improvement of LLM Agents via Two-Timescale Meta-Skill Evolution",
     "2026-07-03", "documents/doc-arxiv-2607-05297-full.txt", "core", "meta-skill",
     "双时间尺度：task skill 快循环、meta-skill 慢循环。形式化最干净的元级 RSI，"
     "但对象是通用 agent 任务、不是推理系统"),
    ("2603.21331", "AutoKernel: Autonomous GPU Kernel Optimization via Iterative Agent-Driven Search",
     "2026-03-22", "documents/doc-arxiv-2603-21331-full.txt", "adjacent", "kernel-mvp",
     "profile→Amdahl 排序→改 kernel→五阶段 harness→keep/revert。单轮约 90 秒。"
     "⚠️ 它不说自己是 self-evolving agent，故在第 3 轮之前的关键词检索里完全不可达"),
    ("2505.22954", "Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents",
     "2025-05-29", "documents/doc-arxiv-2505-22954-full.txt", "core", "rsi-strict",
     "严格 RSI 的参照点：agent 修改自己的源码并用 benchmark 选择后代，"
     "SWE-bench 20→50%、Polyglot 14.2→30.7%。⚠️ 改的是 coding agent，不是推理栈"),
    ("2506.13131", "AlphaEvolve: A coding agent for scientific and algorithmic discovery",
     "2025-06-14", "documents/doc-arxiv-2506-13131-full.txt", "adjacent", "evolution-search",
     "LLM 提案 + 自动评估器 + 进化程序库。它是「evaluator 驱动」的原型，"
     "但属通用算法发现，非推理专用。⚠️ 措辞是 discovery 而非 agent，"
     "需专门一条检索式才可达"),
    ("2609.17391", "FlashVector: Agent for Hierarchical Model Serving Stack Optimization",
     "2026-09-15", "documents/doc-arxiv-2609-17391-full.txt", "core", "stack-hier",
     "跨层：kernel→graph→Triton server→Python feature stack。"
     "对象是推荐系统 serving 而非 LLM token serving，是「同构但异域」的边界案例"),
    ("2611.10719", "No Second Run: Does RSI Stop at Frontier Pre-training?",
     "2026-11-07", "documents/doc-arxiv-2611-10719-full.txt", "core", "rsi-limit",
     "对本篇核心论断的反面证据：质疑 RSI 能否越过前沿预训练这道坎。"
     "列入是为了让 q5（瓶颈在哪）有可被证伪的对立面"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resolve(rel: str) -> Path:
    """先在本文档目录找，再去同级归档找。"""
    local = HERE / rel
    if local.is_file():
        return local
    return ROOT / rel


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    src_rows, doc_rows = [], []

    for suffix, (rel, _), title, pub, parser, note in ANCHOR:
        src = resolve(rel)
        if not src.is_file():
            print(f"[FAIL] 缺快照：{rel}")
            return 1
        sid = f"src-zai-{suffix}"
        did = f"doc-zai-{suffix}"
        ext = src.suffix
        dst = DOCS / f"{did}{ext}"
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        src_rows.append([sid,
                         "https://z.ai/blog/glm-built-its-inference-infrastructure",
                         "official", "Zhipu AI / Z.ai（GLM Team）",
                         title, pub, pub, FETCHED, "en", "primary", "open", "all rights reserved",
                         note])
        doc_rows.append([did, sid, sha(dst), parser,
                         dst.stat().st_size, f"documents/{dst.name}"])

    for aid, title, pub, rel, layer, tag, note in ARXIV:
        src = resolve(rel)
        if not src.is_file():
            print(f"[FAIL] 缺快照：{rel}")
            return 1
        sid = "src-arxiv-" + aid.replace(".", "-")
        did = "doc-arxiv-" + aid.replace(".", "-")
        dst = DOCS / f"{did}-full.txt"
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        src_rows.append([sid, f"https://arxiv.org/abs/{aid}", "academic", "arXiv",
                         title, pub, pub, FETCHED, "en", "primary", "open", "arXiv",
                         f"layer={layer}｜{tag}｜{note}"])
        doc_rows.append([did, sid, sha(dst), "arxiv-html-v1",
                         dst.stat().st_size, f"documents/{dst.name}"])

    with (HERE / "sources.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["source_id", "url", "source_type", "publisher", "title",
                    "published_at", "updated_at", "fetched_at", "language",
                    "trust_tier", "access", "license", "notes"])
        w.writerows(src_rows)

    with (HERE / "documents.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["document_id", "source_id", "content_hash", "parser_version",
                    "byte_size", "snapshot"])
        w.writerows(doc_rows)

    print(f"sources {len(src_rows)}（锚点 {len(ANCHOR)} + arXiv {len(ARXIV)}）"
          f" ／ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
