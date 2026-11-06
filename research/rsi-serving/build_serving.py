"""建立「端到端推理 RSI」来源层：included / sources.csv / 摘要快照 / documents.csv。

## 三层的划分标准（与 rsi-inference 保持同一套，但判据换了）

- core：实现了一个「agent 改动端到端推理链路 -> 拿到端到端反馈 -> 再改」的循环，
  且给出可核对的实验。这里的关键词是**端到端**：判据必须是吞吐 / 延迟 / SLO /
  端到端准确率，而不是某个 kernel 的加速比。
- adjacent：不实现循环，但提供判据的一半——或者是评测方法论（怎么知道测量可信），
  或者是成本模型（怎么在没跑之前估算），或者是边界证据（什么问题一定会反号）。
- ceilling：给出端到端天花板的工作（模拟器、控制面综述），用来判断 core 的数字能不能信。
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
PARSER = "fetch_serving.py/1.0"

CORE = {
    # --- 端点：端到端自主优化循环 ---
    "2611.02501": ("loop", "SpecPilot：成本模型定位缺口、控制器判定晋级、token forcing 判定无损"),
    "2610.04646": ("loop", "SEIS：对整台 mini-sglang 引擎做 agentic 自演化"),
    "2605.06068": ("loop", "VibeServe：外层规划 + 内层实现的双层循环，直接合成 serving 栈"),
    "2610.25012": ("loop", "Conjugate Compilation：把投机解码当跨模型编译问题做自改进"),
    "2607.12875": ("loop", "MetaInfer：把推理适配写成带代价的执行适配图上的路由搜索"),
    # --- 配置与容量规划：不跑也能判 ---
    "2601.06288": ("config", "AIConfigurator：性能模型替代 GPU profiling 做配置搜索"),
    "2611.04032": ("config", "ROCm InferaSim：少量 anchor 测量 + 解析定律外推到新部署"),
    # --- 量化与压缩：端到端代价最直接的层 ---
    "2601.03484": ("quant", "HAQA：LLM 驱动的硬件感知量化与部署 agent"),
    "2603.20492": ("quant", "AE-LLM：按部署场景自动选择并组合效率技术"),
    # --- 批处理与运行时：机制会反号的地方 ---
    "2605.11581": ("runtime", "Ada-MK：DAG 搜索驱动的 megakernel 自适应"),
    "2604.26039": ("runtime", "RaMP：MoE 的运行时感知 megakernel 多态，autotune 假设失效"),
    # --- 循环本身作为研究对象 ---
    "2610.16491": ("loop", "SpecRSI：把 draft-verify 搬到 agent 改进上，预算分配给验证"),
    "2610.08993": ("loop", "Verify Less, Evolve More：用 critic 预筛降低验证成本"),
    "2610.22791": ("loop", "Self-HPO：harness 与 policy 交替优化的递归自改进"),
    "2610.34938": ("loop", "编码 agent 的 harness 如何自演化：125 条提议的实证"),
}

ADJACENT = {
    "2607.20468": ("benchmark", "InferenceBench：开放式推理优化的 agent 基准，暴露「背配方」问题"),
    "2609.18123": ("benchmark", "AutoTuneBench：把「测量可信」做成架构的四种失效模式"),
    "2610.07792": ("benchmark", "ServeLearnBench：agent 能否从 serving 经验里自改进"),
    "2606.30560": ("benchmark", "TraceLab：4300 个编码 agent 会话的真实负载画像"),
    "2605.21312": ("ceiling", "Frontier：分离式 serving 的离散事件模拟器"),
    "2609.23130": ("ceiling", "从推理引擎到推理控制面：vLLM / llm-d 的演化"),
    "2503.04253": ("ceiling", "ADOR：serving 的设计空间探索框架"),
    "2602.13692": ("ceiling", "ThunderAgent：程序感知的 agentic 推理系统"),
}


def main() -> int:
    rows = {r["arxiv_id"]: r for r in json.loads(
        (HERE / "candidates_serving.json").read_text(encoding="utf-8"))}
    # 补齐两条：它们出现在 rsi-inference 的检索里，本轮的检索式没覆盖到
    extra = {r["arxiv_id"]: r for r in json.loads(
        (HERE.parent / "rsi-inference" / "candidates_rsi.json").read_text(encoding="utf-8"))}
    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    DOCS.mkdir(exist_ok=True)

    layers = [("core", CORE), ("adjacent", ADJACENT)]
    src_rows, doc_rows, included = [], [], {}
    missing = []
    for layer, table in layers:
        included[layer] = []
        for aid, (topic, why) in table.items():
            r = rows.get(aid) or extra.get(aid)
            if r is None:
                missing.append(aid)
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
                "notes": f"layer={layer}\uFF5C{topic}\uFF5C{why}",
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
    (HERE / "included_serving.json").write_text(
        json.dumps(included, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")

    print(f"core {len(included['core'])} 篇，adjacent {len(included['adjacent'])} 篇")
    print(f"sources.csv {len(src_rows)} 行，documents.csv {len(doc_rows)} 行")
    if missing:
        print("[!] 候选池里找不到：", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
