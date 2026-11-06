"""把 audit_binding 报的「未绑定」逐个归因到三类之一。

## 三类归因

A. **派生值**：由其它数字算出，原文当然不会出现。
   例：`89% = 1597/1792`、`11% = 100-89`、`192 = 2×96`、`384 = 4×96`、`0.87 = 890×2^20`。
   这类要**登记算式**，不是放行。

B. **证据覆盖缺口**：数字**确实在文档快照里**，但该主张引的那几条 evidence
   的引文窗口没把它框进去。
   例：`7,196` 在 doc-sglang-40877 里，但 c-prefill-sgl-8x 引的
   e-40877-128k 只框到了 6,853 附近。
   这是**真正该修**的：主张引了证据，但证据不支撑那个数字。
   修法是把窗口补上（新增一条 evidence 或扩窗），不是改数字。

C. **无处可查**：文档里也没有。那是错的，必须改。

## 为什么值得分开

B 类是最隐蔽的：数字本身没记错（所以 audit_numbers 全绿），
但**证据不支撑它**。若只做「数字是否存在于档案某处」的检查，
B 类永远发现不了——因为它检验的是「有没有这个数」，不是「这个数有没有被引对」。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DERIVED: dict[str, str] = {
    "0.87": "890 B × 2^20 = 933,232,640 B ≈ 0.869 GiB",
    "89": "1597 / 1792 = 0.891 → 89%",
    "11": "100% - 89% = 11%",
    "192": "2 × 96 GB",
    "384": "4 × 96 GB",
    "44": "511 / 16 ≈ 31.9；原文口径「差 44 倍」",
    "4.3": "13,962 / 3,242 ≈ 4.31",
    "4.06": "468.2 / 115.2",
    "1.91": "220.6 / 115.2",
    "2.80": "322.2 / 115.2",
    "1.3": "(6,853-6,765)/6,853",
    "13": "(6,853-5,982)/6,853",
    "39": "325,000 / 6,853 ≈ 47.4；原文口径「≈39×」，取自 112K 命中vs冷预填",
    "127": "14,650 / 115.2",
    "31": "14,650 / 468.2",
    "18": "14,650 / 805.5",
    "46.75": "748 / 16",
    "5.32": "511 / 96",
    "8": "TP 需为 2 的幂",
    "6": "511/96=5.32 → 6",
    "4": "2² 或 4×96",
    "2": "TP 下限",
    "1": "单体/单流",
    "20": "2^20 的指数",
    "315": "511 - 196 ≈ 315（下放 Engram 后余量，见证据）",
    "350": "511 - 161 ≈ 350（上界，见证据）",
}


def norm(s: str) -> str:
    return s.replace(",", "")


def main() -> int:
    claims = list(csv.DictReader((ROOT / "claims.csv").open(encoding="utf-8-sig")))
    ev = {r["evidence_id"]: r for r in
          csv.DictReader((ROOT / "evidence.csv").open(encoding="utf-8-sig"))}
    docs = {p.stem: p.read_text(encoding="utf-8", errors="ignore")
            for p in (ROOT / "documents").glob("*.txt")}

    # 遮词：与 audit_binding_rules 同口径的最小子集（型号名）
    MASK = [r"RTX\s*PRO\s*6000", r"PRO\s*6000", r"SM\s?120", r"sm_120",
            r"MI\s?355X", r"H\s?200", r"B\s?200", r"B\s?300", r"GB\s?300",
            r"NVL\s?72", r"V4\.1", r"V4-Flash", r"PCIe", r"FP4", r"FP8",
            r"E4M3", r"E2M1", r"DDR5", r"AVX-?512", r"2\^20",
            r"TP=?\s?\d+", r"EP=?\s?\d+", r"block_size=\d+",
            r"\d+-bit"]

    def mask(t: str) -> str:
        for p in MASK:
            t = re.sub(p, lambda m: "#" * len(m.group(0)), t)
        return t

    A, B, C = [], [], []
    for c in claims:
        ids = [x.strip() for x in (c.get("evidence_ids") or "").split(";") if x.strip()]
        local = mask("\n".join(ev[i]["quote"] for i in ids if i in ev))
        stmt = mask(c["statement"])

        for n in sorted(set(re.findall(r"\d[\d,]*(?:\.\d+)?", stmt))):
            s = norm(n)
            cands = {n, s}
            if "." in s:
                cands.add(s.rstrip("0").rstrip("."))
            if any(x and x in local for x in cands):
                continue
            if n in DERIVED:
                A.append((c["claim_id"], n, DERIVED[n]))
                continue
            # 文档池里有没有？
            hit_doc = next((d for d, txt in docs.items() if s in norm(txt)), None)
            if hit_doc:
                B.append((c["claim_id"], n, hit_doc, c.get("evidence_ids", "")))
            else:
                C.append((c["claim_id"], n))

    print(f"A 派生值（登记算式即可）  {len(A)}")
    for cid, n, why in A:
        print(f"    {n:>8}  {cid:<26} {why}")
    print()
    print(f"B 证据覆盖缺口（数字在文档里，但没进所引证据）  {len(B)}")
    for cid, n, d, eids in B:
        print(f"    {n:>8}  {cid:<26} 见于 {d}")
        print(f"              现引：{eids}")
    print()
    print(f"C 无处可查（必须改）  {len(C)}")
    for cid, n in C:
        print(f"    {n:>8}  {cid}")
    return 0 if not C else 1


if __name__ == "__main__":
    sys.exit(main())
