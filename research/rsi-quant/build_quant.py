"""建立「模型量化 RSI」来源层：included / sources.csv / 摘要快照 / documents.csv。

## 三层的划分标准（与 rsi-serving 同一套骨架，判据换了）

- core：实现了一个「自动决定量化方案 -> 拿到精度/效率反馈 -> 再改」的循环，
  或提出了可被循环直接使用的判定量（敏感度估计、误差归因、位分配准则）。
  这一层的关键词是**可判定**：给出的量必须能被另一个系统拿去当判据。
- adjacent：不实现循环，但提供判据的另一半——量化到底怎么算「坏了」
  （保真度指标、评测协议、校准集敏感性、agent 场景下的失效）。

⚠️ 为什么把「敏感度/归因」也算进 core：量化的循环与传统自动优化不同，
它的瓶颈不是「搜不动」，而是「不知道往哪搜」。一个能给出 per-layer 敏感度
的估计器，实际上就是循环里的 cost model。若只收「完整 agent 系统」，
这一层会只剩两三篇，而恰恰是这些估计器决定了循环能否闭合。
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
PARSER = "fetch_quant.py/1.0"

CORE = {
    # --- 分配：把有限 bit 预算分到层/块/tile 上 ---
    "2611.07217": ("alloc", "TileQuant：把 tile 作为混合精度的分配单元，而不是整个矩阵"),
    "2609.01587": ("alloc", "量化损伤的结构：为什么下一个 bit 应该全局地花"),
    "2608.28003": ("alloc", "在质量退化约束下最大化性能的层位宽分配"),
    "2608.30564": ("alloc", "Q-Strata：MoE LLM 的分层位分配"),
    "2610.09877": ("alloc", "逐层误差归因，用于快速稳健的混合精度 PTQ"),
    "2610.18642": ("alloc", "MultiAlloc：预算感知的 KV cache 精度分配"),
    "2610.07457": ("alloc", "AlignQuant：tile 对齐的混合精度量化"),
    # --- 敏感度：循环里的 cost model ---
    "2607.17733": ("sens", "MXSens：敏感度感知的混合精度量化"),
    "2609.33923": ("sens", "量化误差是谱平坦的：单个随机探针即可标定、无需数据的敏感度估计"),
    "2609.25916": ("sens", "超越标量敏感度：激活感知的混合精度量化 + 跨层精修"),
    "2608.24945": ("sens", "FAMPWQ：Fisher 信息驱动的自适应混合精度权重量化"),
    # --- agent / 自动流水线：循环本体 ---
    "2608.05499": ("agent", "APQF：agentic profiling 引导的剪枝 + 混合精度量化 + 自适应微调"),
    "2610.09183": ("agent", "Q-PACE：QAT 过程中的动态精度分配"),
    "2609.39223": ("agent", "QATFactory：部署对齐的 QAT 与蒸馏框架"),
    "2611.06858": ("agent", "CompressionBench：让编码 agent 去压缩 LLM，比什么"),
    # --- 无校准 / 校准集无关：把「校准集依赖」这条失效模式拿掉 ---
    "2608.11045": ("calib", "ReRound：无校准量化中解决中点歧义"),
    "2606.26650": ("calib", "CAT-Q：低成本高精度的三值量化"),
}

ADJACENT = {
    # --- 判据：量化到底怎么算「坏了」 ---
    "2609.07664": ("eval", "Accuracy is Not Enough：用散度衡量量化 LLM 的保真度损失"),
    "2606.19558": ("eval", "Displacement Is Not Direction：评测量化 LLM 部署的保真度指标"),
    "2607.08734": ("eval", "The Illusion of Equivalency：量化效应的统计刻画"),
    "2607.27275": ("eval", "Flat Score, Amplified Failures：误差预算如何掩盖量化 agent 的损伤"),
    "2607.09999": ("eval", "Silent Failures：量化 LLM 推理的失效模式分类学与空壳收敛"),
    "2610.04403": ("eval", "Saying, Not Knowing：激进 GGUF 量化的小模型仍会写出它已无法定义的罕见词"),
    "2611.02368": ("eval", "Beyond Accuracy：量化如何影响编码 agent"),
    "2609.04748": ("eval", "Same Request, Different Answer：量化放大 serving 中的缓存诱发分歧"),
    "2608.30996": ("eval", "Faithfulness Is Not Free：审计 RAG 中的离线 KV-cache 量化"),
    "2608.03854": ("eval", "校准依赖评分规则：量化生物医学 LLM 分类"),
    # --- 跨对象的一致性：同一位宽不同结果 ---
    "2609.28974": ("boundary", "同一 bit 宽、不同结果：跨架构的 TTS 后训练量化"),
    "2607.21063": ("boundary", "QuantiBias：量化诱发偏差的基准"),
    "2608.18578": ("boundary", "Compress and Forget：bitsandbytes 量化放大了前摄干扰"),
    "2607.25451": ("boundary", "Bits and Memories：跨量化级别的逐字抽取测量"),
    "2610.32417": ("boundary", "量化语言模型 agent 完成任务的实际能耗"),
    "2608.15117": ("boundary", "解剖一个量化 agent：代码合成负载下的显存稳定性"),
    "2608.29667": ("survey", "以目标为中心的 QAT 综述"),
}


def main() -> int:
    rows = {r["arxiv_id"]: r for r in json.loads(
        (HERE / "candidates_quant.json").read_text(encoding="utf-8"))}
    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    DOCS.mkdir(exist_ok=True)

    layers = [("core", CORE), ("adjacent", ADJACENT)]
    src_rows, doc_rows, included = [], [], {}
    missing = []
    for layer, table in layers:
        included[layer] = []
        for aid, (topic, why) in table.items():
            r = rows.get(aid)
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
    (HERE / "included_quant.json").write_text(
        json.dumps(included, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")

    print(f"core {len(included['core'])} 篇，adjacent {len(included['adjacent'])} 篇")
    print(f"sources.csv {len(src_rows)} 行，documents.csv {len(doc_rows)} 行")
    if missing:
        print("[!] 候选池里找不到：", missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
