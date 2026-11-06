"""补两条 EXL3 的真实测量证据，用于替换此前编造的数字。

## 为什么必须重建而不是「改改文字」

原先的主张 c-quant-quality-cost 写了：

    KL 0.0522（中性文本）/ 0.0306（代码）/ 0.0111（agentic），
    GSM8K-200 98.5%、HumanEval 97.0%，噪声底 0.0082；
    agentic 回放单流 224.1 tok/s、代码 172.8 tok/s、40K 预填 11,157–11,467 tok/s

逐条核对原文后：

| 我写的 | 原文 | 性质 |
|---|---|---|
| KL 0.0522 | 0.0519 / 0.0309 / 0.0109 / 0.0341（short100） | 数字被记串 |
| 0.0306 | 0.0309 | 记错 |
| 0.0082「噪声底」 | **原文无此数**；原文说「stayed within run-to-run noise」但没给数值 | **编造** |
| GSM8K 98.5 / HumanEval 97.0 | 「went from 98.5 / 95.7 to 99.0 / 97.6」 | 取了旧值并串错 |
| 224.1 tok/s | **224.0 秒**（wall clock） | **把秒当 tok/s** |
| 172.8 tok/s | 原文无代码生成吞吐 | **编造** |
| 11,157–11,467 | 11,038–11,306 | 记错区间 |

⚠️ 最该记住的一条：这些数字之所以能通过 audit_paper 的 C 项，
是因为我把它们同时写进了 claim.statement 与 PAPER.md——
**自己写的 claim 给自己的正文背书，闭环了，但闭的是空环**。
新增的 audit_numbers.py 改从 evidence.quote 与文档快照取池，才暴露出来。

故本文件只做两件事：从原文切真实引文，并让 claim 只陈述引文里逐字存在的内容。
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE / "documents" / "doc-diffbot-exl3.txt"

# 新增证据：锚点取自原文，且必须是原文的连续子串
NEW_EVIDENCE = [
    ("e-exl3-kl-noise", "doc-diffbot-exl3", "src-diffbot-exl3",
     "KL 0.0519 / 0.0311 / 0.0110 and 0.0344 on short100",
     "Results on our development build / KL 行"),
    ("e-exl3-prefill-40k", "doc-diffbot-exl3", "src-diffbot-exl3",
     "fresh 40K-token prefill 10,424-10,684 → 11,038-11,306 tok/s",
     "Results on our development build / 40K 预填行"),
    ("e-exl3-wallclock", "doc-diffbot-exl3", "src-diffbot-exl3",
     "agentic wall clock 230.6 → 224.0 s at one session and 185.8 → 170.5 s at four",
     "Results on our development build / agentic wall clock 行"),
    ("e-exl3-agentic-decode", "doc-diffbot-exl3", "src-diffbot-exl3",
     "CPU host experts in decode raised 1-session agentic decode",
     "CPU host experts 段"),
    ("e-exl3-gsm8k", "doc-diffbot-exl3", "src-diffbot-exl3",
     "GSM8K / HumanEval went from 98.5 / 95.7 to 99.0 / 97.6, within run-to-run noise",
     "Prompt encoding / 质量行"),
    ("e-exl3-no-noise-floor", "doc-diffbot-exl3", "src-diffbot-exl3",
     "KL to the original model stayed within",
     "8-bit prefill all-reduce / Accuracy 段"),
]


def window(text: str, anchor: str, before: int = 0, after: int = 340) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    lo = i
    hi = min(len(text), i + len(anchor) + after)
    m = None
    for m in __import__("re").finditer(r"(?:[.!?]\s+|\n\n)", text[i + len(anchor):hi]):
        pass
    if m:
        hi = i + len(anchor) + m.end()
    return " ".join(text[lo:hi].split())


def main() -> int:
    text = DOC.read_text(encoding="utf-8")

    ev_path = HERE / "evidence.csv"
    with ev_path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    have = {r["evidence_id"] for r in rows}

    added = 0
    for eid, did, sid, anchor, loc in NEW_EVIDENCE:
        if eid in have:
            continue
        try:
            q = window(text, anchor)
        except LookupError:
            print(f"  [!] 锚点不在原文：{anchor!r}")
            return 1
        rows.append({
            "evidence_id": eid, "document_id": did, "source_id": sid,
            "quote": q, "locator": loc, "stance": "supports",
            "extracted_by": "add_exl3_evidence.py/1（锚点扩窗）",
        })
        added += 1

    fields = list(rows[0].keys())
    with ev_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"新增 {added} 条证据，evidence.csv 现有 {len(rows)} 条")
    for eid, *_rest in NEW_EVIDENCE:
        q = next(r["quote"] for r in rows if r["evidence_id"] == eid)
        print(f"\n{eid}:\n  {q[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
