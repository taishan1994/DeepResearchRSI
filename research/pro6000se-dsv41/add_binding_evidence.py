"""补 B 类「证据覆盖缺口」：数字在文档里，但没进所引证据的引文窗口。

## 问题

audit_binding.py 发现 27 个数字是「未绑定」的：它们确实存在于文档快照里
（所以 audit_numbers.py 的「档案里有没有」检查全绿），
但**主张所引的那几条证据的引文里没有它们**。

例：c-1m-cold-5min 说「402K→5,065 / 704K→4,022 / 906K→3,478 / 1.006M→3,242」，
但它引的 e-40877-1m-ladder 只框到了 3,242 与 322.0 秒那一段，
**四个上下文档位的速率一个都没进引文**。读者顺着引用去查，查不到 4,022。

这不是数字记错，是**证据不支撑主张**——比数字错更隐蔽，因为
「数字存在」与「数字被引用支持」是两件事，而多数检查只验前者。

## 做法

对每个缺口，从文档里按真实锚点切一条**新证据**（不改旧证据，保持可追溯），
锚点必须是原文连续子串，且窗口要能把主张里的数字框进去。
若某个锚点在原文找不到 → 直接失败，不猜。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCDIR = HERE / "documents"

# (evidence_id, document_id, source_id, anchor, locator)
NEW = [
    # 32K 提示约 7,196（c-prefill-sgl-8x）
    ("e-40877-32k", "doc-sglang-40877", "src-sglang-40877",
     "32K prompt: ≈7,196 tok/s", "prefill 表 / 32K 行"),
    # 前缀缓存 325K（c-prefill-ceiling；也补 C 类 325,000）
    ("e-40877-cachehit-325k", "doc-sglang-40877", "src-sglang-40877",
     "cache-hit prefill", "Radix/prefix cache 段"),
    # DSpark 分档表：76.5–78.9 / 120.3–120.5 / 237–252（c-decode-dspark）
    ("e-40877-dspark-table", "doc-sglang-40877", "src-sglang-40877",
     "Prompt class", "DSPARK A/B 表"),
    ("e-40877-block6", "doc-sglang-40877", "src-sglang-40877",
     "block_size=6", "DSPARK / 生产配置"),
    # 4 卡并发阶梯：115.2 / 220.6 / 322.2 / 468.2（c-decode-tp4-conc）
    ("e-40877-conc-table", "doc-sglang-40877", "src-sglang-40877",
     "Concurrency", "decode vs concurrency 表"),
    # 1M 冷预填阶梯：402K/704K/906K/1.006M（c-1m-cold-5min）
    ("e-40877-cold-ladder", "doc-sglang-40877", "src-sglang-40877",
     "Prompt tokens", "cold prefill 阶梯表"),
    # 511GB 权重（c-min-4x96）
    ("e-q-511gb-again", "doc-qovery-selfhost", "src-qovery-selfhost",
     "ships roughly 511 GB of weights", "Key Points / 权重体积"),
    # 196B Engram（c-engram-dominates）
    ("e-report-196b", "doc-qovery-selfhost", "src-qovery-selfhost",
     "552B backbone parameters plus 196B Engram memory parameters", "Key Points / 参数"),
]


def window(text: str, anchor: str, after: int = 620) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    hi = min(len(text), i + len(anchor) + after)
    # 尽量在句末收尾，避免切断词语
    seg = text[i:hi]
    m = None
    for m in re.finditer(r"(?:[.!?]\s|\n\n)", seg):
        pass
    if m and m.end() > 120:
        hi = i + m.end()
    return " ".join(text[i:hi].split())


def main() -> int:
    extra_path = HERE / "evidence_extra.json"
    extra: list[dict] = []
    if extra_path.is_file():
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
    have = {r["evidence_id"] for r in extra}

    added = 0
    for eid, did, sid, anchor, loc in NEW:
        if eid in have:
            continue
        txt = (DOCDIR / f"{did}.txt").read_text(encoding="utf-8", errors="ignore")
        try:
            q = window(txt, anchor)
        except LookupError:
            print(f"[!] 锚点不在 {did}：{anchor!r}")
            return 1
        extra.append({
            "evidence_id": eid, "document_id": did, "source_id": sid,
            "quote": q, "locator": loc, "stance": "supports",
            "extracted_by": "add_binding_evidence.py/1（锚点扩窗）",
        })
        added += 1

    extra_path.write_text(json.dumps(extra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"evidence_extra.json 现含 {len(extra)} 条（本次新增 {added}）")
    for r in extra[-added:] if added else []:
        print(f"\n{r['evidence_id']}: {r['quote'][:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
