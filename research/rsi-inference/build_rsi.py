"""建立「推理优化 RSI」来源层：included / sources.csv / 摘要快照 / documents.csv。

## 三层的划分标准

- core：本身就实现了一个「LLM/agent 改动推理栈 -> 拿到反馈 -> 再改」的循环，
  且给出了可核对的实验。这是本文的主体。
- adjacent：不实现循环，但提供了判据的一半——要么给出性能上限（分母），
  要么给出验证/评测方法，要么给出失败模式的证据。
- ceiling：端到端占比、加速比口径、隐藏测试集这类「横向参照」，
  用来判断 core 里的数字能不能信。

这个划分不是按引用量，而是按「它在本文的论证里占哪个位置」。
同一个位置有第三篇时，取证据更硬的那篇——因为本文的论点是判据，
不是文献普查。
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
PARSER = "fetch_rsi.py/1.0"

CORE = {
    # --- 迭代式 agent 写/调 kernel ---
    "2506.20807": ("kernel-agent", "GPU Kernel Scientist：迭代式 kernel 优化的早期代表"),
    "2509.07506": ("kernel-agent", "Astra：多智能体 kernel 性能优化"),
    "2510.16996": ("kernel-agent", "STARK：多智能体精炼 kernel"),
    "2511.06345": ("kernel-agent", "PRAGMA：profiling 推理驱动的多智能体 kernel 优化"),
    "2512.16465": ("kernel-agent", "cuPilot：策略协同的多智能体 CUDA kernel 演化"),
    "2512.23236": ("kernel-agent", "KernelEvolve：Meta 的异构加速器 kernel 规模化"),
    "2602.24286": ("rl", "CUDA Agent：大规模 agentic RL 做 kernel 生成"),
    "2603.21331": ("kernel-agent", "AutoKernel：迭代式 agent 驱动搜索"),
    "2603.28342": ("evolve", "Kernel-Smith：进化的 kernel 优化统一配方"),
    "2603.12440": ("evolve", "KernelFoundry：硬件感知的进化式 kernel 优化"),
    "2604.01489": ("kernel-agent", "CuTeGen：agentic 生成与优化"),
    "2604.16625": ("evolve", "AdaExplore：失败驱动的自适应与多样性保持搜索"),
    "2604.18616": ("agent", "Ave：用数据流不变量引导 agent 优化"),
    "2606.17518": ("agent", "SpecGen：投机生成加速 agentic kernel 优化"),
    "2607.20501": ("kernel-agent", "MKEvolve：模块化多智能体 kernel 生成"),
    "2608.02611": ("agent", "KernelBrain：由粗到细、预算感知的搜索"),
    "2608.25570": ("evolve", "Beyond Scaling：经验驱动的自进化 kernel agent"),
    "2609.30059": ("agent", "KernelOPT：dispatch 感知的 agentic 搜索"),
    "2611.03517": ("agent", "Ask, Don't Equip：提问式编码 agent 做深度 kernel 优化"),
    "2611.04998": ("evolve", "ForgeKernel：自进化 kernel 超过专家与 agent"),
    "2606.26453": ("agent", "Optimizing CUDA like a Human：用微基准工具做专家替身"),
    "2603.29010": ("agent", "DSL + speed-of-light 引导提升 kernel agent 效率"),
    "2608.02712": ("agent", "Don't Regenerate, Debug：修复 near-miss kernel"),
    "2608.20711": ("evolve", "AsmEvo：AMD GPU 汇编级优化，带功能等价验证"),
    "2610.31034": ("evolve", "CANNBot-CAKE：昇腾 NPU 的协同 agentic kernel 演化"),
    "2607.26661": ("evolve", "AgenticCANN：知识增强的 Ascend C 算子演化"),
    "2609.04523": ("agent", "MaxKernel：TPU 的 agentic kernel 生成"),
    "2606.02963": ("kernel-agent", "KForge：跨平台 kernel 生成"),
    "2610.38329": ("agent", "多智能体 kernel 优化循环学习新加速器（案例研究）"),
    # --- RL / 奖励设计 ---
    "2607.20908": ("rl", "多轮 RL：结构与性能双奖励做 CUDA kernel"),
    "2602.14293": ("rl", "KernelBlaster：记忆增强的上下文内 RL，跨任务持续优化"),
    "2606.16497": ("rl", "daVinci-kernel：RL 协同进化技能选择与总结"),
    "2505.23387": ("rl", "Afterburner：RL 驱动的代码效率自改进"),
    # --- 服务系统层的自我改进 ---
    "2610.07792": ("serving", "ServeLearnBench：agent 能否从 serving 经验中自改进"),
    "2610.25012": ("serving", "Conjugate Compilation：投机解码的自改进协同编译"),
    "2605.11581": ("serving", "Ada-MK：DAG 搜索驱动 megakernel 自适应"),
    "2604.26039": ("serving", "RaMP：MoE 的运行时感知 megakernel 多态"),
    "2601.06288": ("serving", "AIConfigurator：多框架 serving 配置优化"),
    # --- 通用循环（方法学来源）---
    "2510.14150": ("loop", "CodeEvolve：开源进化式编码 agent"),
    "2603.21321": ("loop", "系统优化 agent 的一致性与持久性"),
    "2610.21791": ("loop", "RSIFlow：带演化 meta-agent 的自改进工作流"),
    "2610.08993": ("loop", "Verify Less, Evolve More：验证成本与演化效率"),
    "2610.22791": ("loop", "Self-Evolving Coding Agents via Harness-Policy Optimization"),
    "2610.34938": ("loop", "编码 agent 的 harness 如何自演化（实证研究）"),
    "2609.34069": ("loop", "证书驱动的自改进 agentic harness"),
}

ADJACENT = {
    "2502.10517": ("benchmark", "KernelBench：把 kernel 生成变成可测问题"),
    "2607.16241": ("benchmark", "KernelBench-Verified：严格协议下重测，负结果"),
    "2605.16819": ("benchmark", "AgentKernelArena：泛化感知的 kernel agent 评测"),
    "2607.14541": ("benchmark", "LLM 生成的 kernel 是否生产可用：trace 驱动基准"),
    "2509.14279": ("benchmark", "稳健的 agentic kernel 基准、验证与优化"),
    "2609.18123": ("benchmark", "AutoTuneBench：agent 自动调 serving 的可信测量"),
    "2607.20468": ("benchmark", "InferenceBench：开放式推理优化 agent 基准"),
    "2509.09505": ("ceiling", "长上下文 agentic 推理的内存墙与优化路径"),
    "2602.13692": ("serving", "ThunderAgent：程序感知的 agentic 推理系统"),
    "2609.23130": ("serving", "从推理引擎到推理控制面：vLLM/llm-d 的演化"),
    "2605.11732": ("loop", "AgentDisCo：开放式深度研究 agent 的解耦与协作"),
    "2511.03844": ("serving", "ASAP：大规模 LLM 训练性能的 agentic 自动优化"),
}


def short_title(t: str, n: int = 60) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1] + "\u2026"


def main() -> int:
    rows = {r["arxiv_id"]: r for r in json.loads(
        (HERE / "candidates_rsi.json").read_text(encoding="utf-8"))}
    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    DOCS.mkdir(exist_ok=True)

    layers = [("core", CORE), ("adjacent", ADJACENT)]
    src_rows, doc_rows, included = [], [], {}
    for layer, table in layers:
        included[layer] = []
        for aid, (topic, why) in table.items():
            r = rows.get(aid)
            if r is None:
                print(f"  [!] 候选里没有 {aid}")
                continue
            sid = "src-arxiv-" + aid.replace(".", "-")
            did = "doc-arxiv-" + aid.replace(".", "-")
            abstract = r["summary"]
            snap = DOCS / f"{did}.txt"
            snap.write_text(abstract + "\n", encoding="utf-8", newline="\n")
            h = hashlib.sha256(abstract.encode("utf-8")).hexdigest()
            src_rows.append({
                "source_id": sid,
                "url": r["url"],
                "source_type": "academic",
                "publisher": "arXiv",
                "title": r["title"],
                "published_at": r["published"],
                "updated_at": r.get("updated") or r["published"],
                "fetched_at": now,
                "language": "en",
                "trust_tier": "primary",
                "access": "open",
                "license": "arXiv",
                "notes": f"layer={layer}｜{topic}｜{why}",
            })
            doc_rows.append({
                "document_id": did,
                "source_id": sid,
                "content_hash": h,
                "parser_version": PARSER,
                "byte_size": str(len(abstract.encode("utf-8"))),
                "snapshot": f"documents/{did}.txt",
            })
            included[layer].append({
                "arxiv_id": aid,
                "title": r["title"],
                "published": r["published"],
                "topic": topic,
                "why": why,
                "summary": abstract,
                "url": r["url"],
            })

    def write_csv(path: Path, fieldnames: list[str], data: list[dict]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_ALL,
                               lineterminator="\n")
            w.writeheader()
            for row in data:
                w.writerow(row)

    write_csv(HERE / "sources.csv",
              ["source_id", "url", "source_type", "publisher", "title",
               "published_at", "updated_at", "fetched_at", "language",
               "trust_tier", "access", "license", "notes"], src_rows)
    write_csv(HERE / "documents.csv",
              ["document_id", "source_id", "content_hash", "parser_version",
               "byte_size", "snapshot"], doc_rows)
    (HERE / "included_rsi.json").write_text(
        json.dumps(included, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")

    print(f"core {len(included['core'])} 篇，adjacent {len(included['adjacent'])} 篇")
    print(f"sources.csv {len(src_rows)} 行，documents.csv {len(doc_rows)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
