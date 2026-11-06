"""加入 Server Edition 的真实实测证据，并修正「SE 无实测」这个假否定。

## 这一批证据为什么必须存在

初稿的 c-gap-no-se-measurement 写的是「没有任何来源在 SE 上实测过」。
原文核对后，这句话**是错的**：

  「aristokratic.eth reported, with Engrams on RAM on 4× RTX 6000 Blackwell
   Server Edition at a 450W power limit, single-stream decode at 183 tok/s,
   16-stream aggregate at 695 tok/s, and prefill at 18,400–19,200 tok/s.」

以及 8 卡整机：
  「Festr -- Dual Turin Server (8x Server Edition)」+ NCCL 实测 37.6 GB/s。

所以正确的主张不是「无 SE 实测」，而是：
**SE 有实测，但只有两组，且都不是本课题关心的「全精度 + 8 卡」配置**
（4 卡/Engram-on-RAM/450W 一例；8 卡整机只有 NCCL 与拓扑数据，无 DS4.1 吞吐）。
这个区别很重要：前者是「查漏了」，后者是「证据确实稀薄」——
两者的可信度与写法完全不同。

## 顺带修正另一个偏差

初稿把 `6,853 tok/s`（SGLang 8×Max-Q）当作预填上限的代表。
社区服务页另有 Karmic Kraken 在 4×Max-Q 上的 32K 预填 **17,982 tok/s**，
是它的 2.6 倍——因为 8 卡 PCIe 无 NVLink 的通信开销更大。
把两者并列，读者才能看出「卡多不等于快」。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

# (evidence_id, document_id, source_id, anchor, locator, after)
NEW = [
    # —— Server Edition 4 卡实测（核心） ——
    ("e-se-4x-measured", "doc-r6k-daily-2026-10-25", "src-r6k-daily",
     "aristokratic.eth reported, with Engrams on RAM on 4× RTX 6000 Blackwell Server Edition",
     "Daily Summary 2026-10-24 / Key highlights", 300),
    # —— Server Edition 8 卡整机 ——
    ("e-se-8x-rig", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "Festr -- Dual Turin Server (8x Server Edition)",
     "Community Rig Builds / Festr", 700),
    # —— SE 不支持的显存超频 ——
    ("e-se-no-mem-oc", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "MaxQ cards accept memory clock offset. Server Edition cards return an error",
     "GPU Variants / Memory Overclocking", 260),
    # —— 变体功耗对照 ——
    ("e-variant-tdp", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "RTX PRO 6000 Blackwell Variants", "GPU Variants 表", 320),
    # —— MaxQ vs Workstation 实测差 ——
    ("e-maxq-vs-ws-delta", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "MaxQ vs Workstation Edition Performance", "GPU Variants / 性能对照表", 420),
    # —— TP 必须是 2 的幂 ——
    ("e-tp-power-of-2", "doc-r6k-gpu-configs", "src-r6k-gpu-configs",
     "TP must be power-of-2 for vLLM/SGLang", "Tensor Parallel Constraints", 300),
    # —— 8×SE 的 NCCL 总线带宽 ——
    ("e-se-nccl", "doc-r6k-bench-results", "src-r6k-bench",
     "Festr (8x Server, dual Turin)", "NCCL AllReduce / 32M-2G", 260),
    # —— 4×Max-Q 的 32K 预填 17,982（比 8 卡高） ——
    ("e-kk-32k-prefill", "doc-r6k-model-dsv41-2026-11", "src-r6k-model",
     "32K prefill", "Measured performance / Karmic Kraken 表", 260),
    # —— 4 卡 Max-Q 的 C1/C8 ——
    ("e-kk-c1c8", "doc-r6k-model-dsv41-2026-11", "src-r6k-model",
     "C1 output", "Measured performance 表", 320),
    # —— RAM Engram 188.83 GiB 账目 ——
    ("e-engram-188-83", "doc-r6k-model-dsv41-2026-11", "src-r6k-model",
     "188.83 GiB", "RAM versus SSD ngrams 表", 220),
]


def window(text: str, anchor: str, after: int) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    hi = min(len(text), i + len(anchor) + after)
    seg = text[i:hi]
    m = None
    for m in re.finditer(r"(?:[.!?]\s|\n\n|\(\d\)|\]\(http)", seg):
        pass
    if m and m.end() > 100:
        hi = i + m.end()
    return " ".join(text[i:hi].split())


def main() -> int:
    extra_path = HERE / "evidence_extra.json"
    extra: list[dict] = []
    if extra_path.is_file():
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
    have = {r["evidence_id"] for r in extra}

    added = 0
    for eid, did, sid, anchor, loc, after in NEW:
        if eid in have:
            continue
        txt = (DOCS / f"{did}.txt").read_text(encoding="utf-8", errors="ignore")
        try:
            q = window(txt, anchor, after)
        except LookupError:
            print(f"[!] 锚点不在 {did}：{anchor!r}")
            return 1
        extra.append({
            "evidence_id": eid, "document_id": did, "source_id": sid,
            "quote": q, "locator": loc, "stance": "supports",
            "extracted_by": "add_se_evidence.py/1（锚点扩窗）",
        })
        added += 1

    extra_path.write_text(json.dumps(extra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"evidence_extra.json 现含 {len(extra)} 条（新增 {added}）")
    for r in extra[-added:] if added else []:
        print(f"\n{r['evidence_id']}: {r['quote'][:240]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
