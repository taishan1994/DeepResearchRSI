"""把已抓取的候选文本整理成本归档的来源与文档层。

## 与 rsi-quant 的一个差别

那边的快照是「摘要 + 全文」两份；这里每篇只留一份全文快照。
理由：本批全部抓到了 HTML 全文（14/14），没有必要再冻一份摘要副本，
而 D1 只要求同一篇文档不重复入库。
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(r"D:\github\DeepResearchRSI\research\_rel_docs")
DOCS = HERE / "documents"
FETCHED = "2026-11-06T14:35:00+08:00"

# (arxiv_id, title, published, layer, tag, note)
SRC_LIST = [
    ("2611.06841", "ServerBench: How can your coding agents design specialized LLM serving systems?", "2026-11-04", "core", "objective", "本次研读的目标论文：dollars-per-dollar 经济目标 + 有状态回放 + 独立验证"),
    ("2605.06068", "VibeServe: Can AI Agents Build Bespoke LLM Serving Systems?", "2026-05-07", "core", "builder", "最接近的同型工作：外层规划 + 内层实现/校验/测量的双层 agent 循环，端到端生成整套服务栈"),
    ("2610.04646", "SEIS: Self-Evolving Inference Systems", "2026-10-03", "core", "builder", "直接自称 self-evolving：让 agent 迭代改写整个 mini-sglang 引擎，且会话之间继承代码与经验"),
    ("2607.20468", "InferenceBench: A Benchmark for Open-Ended LLM Inference Optimization by AI Agents", "2026-05-20", "core", "open-ended", "开放式推理优化基准；关键反例：同等时间预算下简单超参搜索胜过 agent"),
    ("2607.18171", "FlashRT: Agent Harness for Guiding Agents to Deploy Real-Time Multimodal Applications", "2026-07-20", "core", "harness", "harness 路线的代表：用 chain-of-program 引导通用 coding agent 做多卡部署，而不是让它自由探索"),
    ("2608.24650", "Simthesizer: An Agent-Driven Simulation Framework for LLM Serving Systems", "2026-08-25", "core", "simulator", "对象换成了模拟器：agent 把自然语言特性请求下沉成仿真实现，用来追平服务系统与仿真器的开发速度差"),
    ("2602.19594", "ISO-Bench: Can Coding Agents Optimize Real-World Inference Workloads?", "2026-02-23", "adjacent", "patch", "54 个来自 vLLM / SGLang 已合并 PR 的优化任务；硬指标 + 软指标并用"),
    ("2609.26777", "SWE-Serve: Benchmarking Agentic Engineering for Production Inference Serving", "2026-09-22", "adjacent", "repo", "53 个来自 SGLang 生产变更的仓库级任务；隐藏功能测试与回归测试"),
    ("2610.36589", "InfraDev: Can Coding Agents Develop AI Infrastructure, and How Can We Tell?", "2026-10-27", "adjacent", "repo", "36 个来自 Megatron-LM / vLLM / verl 的 PR 任务；核心贡献是「测试与提示必须一起合成」"),
    ("2609.18123", "AutoTuneBench: Trustworthy Measurement for Agent Auto-Tuning of LLM Serving Engines", "2026-09-16", "adjacent", "measurement", "把「测量可信度」本身当研究对象：四种失效模式与冻结成代码的协议"),
    ("2502.10517", "KernelBench: Can LLMs Write Efficient GPU Kernels?", "2025-02-14", "adjacent", "kernel", "这条线的起点：250 个 PyTorch 负载 + fast_p 指标"),
    ("2607.16241", "KernelBench-Verified: Do LLM-Generated Kernels Actually Beat PyTorch?", "2026-06-26", "adjacent", "kernel", "对起点的审计：TF32 基线 + 四分布隐藏测试，指出前沿模型系统性 reward hacking"),
    ("2609.34683", "AgentPerfBench: A Benchmarking and Evaluation Suite for Inference Performance of Agentic LLMs", "2026-09-28", "adjacent", "workload", "把负载换成 agentic 轨迹（SWE-Bench / TerminalBench），指出旧基准只覆盖单轮聊天"),
    ("2606.30560", "TraceLab: Characterizing Coding Agent Workloads for LLM Serving", "2026-06-29", "adjacent", "workload", "约 4,300 条 coding-agent 会话、35 万步、43 万次工具调用的公开轨迹"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    src_rows, doc_rows = [], []
    for aid, title, pub, layer, tag, note in SRC_LIST:
        sid = "src-arxiv-" + aid.replace(".", "-")
        did = "doc-arxiv-" + aid.replace(".", "-")
        raw = SRC / f"{aid}.txt"
        if not raw.is_file():
            print(f"[FAIL] 缺快照：{raw}")
            return 1
        dst = DOCS / f"{did}.txt"
        shutil.copyfile(raw, dst)
        src_rows.append([sid, f"https://arxiv.org/abs/{aid}", "academic", "arXiv",
                         title, pub, pub, FETCHED, "en", "primary", "open", "arXiv",
                         f"layer={layer}｜{tag}｜{note}"])
        doc_rows.append([did, sid, sha(dst), "build_agent_serving.py/1.0",
                         dst.stat().st_size, f"documents/{did}.txt"])

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
    print(f"sources {len(src_rows)} ／ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
