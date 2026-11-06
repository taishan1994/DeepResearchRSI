"""为 c-prune-route 补证据（tacos4me 剪枝路线的吞吐与质量）。"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

NEW = [
    ("e-prune-2x", "doc-tacos4me-prune", "src-tacos4me-prune",
     "**Decode** | **141 tok/s** single stream", "总表 / Decode 与 Prefill 行", 420),
    ("e-prune-quality", "doc-tacos4me-prune", "src-tacos4me-prune",
     "GSM8K 198/200", "总表 / Quality 行", 320),
    ("e-prune-stream", "doc-tacos4me-prune", "src-tacos4me-prune",
     "Streaming the experts from NVMe with zero CPU compute", "What this is / 对照路线", 340),
]


def window(text: str, anchor: str, after: int) -> str:
    i = text.find(anchor)
    if i < 0:
        raise LookupError(anchor)
    hi = min(len(text), i + len(anchor) + after)
    seg = text[i:hi]
    m = None
    for m in re.finditer(r"(?:\n\n|\n---)", seg):
        pass
    if m and m.end() > 100:
        hi = i + m.end()
    return " ".join(text[i:hi].split())


def main() -> int:
    p = HERE / "evidence_extra.json"
    extra = json.loads(p.read_text(encoding="utf-8"))
    have = {r["evidence_id"] for r in extra}
    added = 0
    for eid, did, sid, anchor, loc, after in NEW:
        if eid in have:
            continue
        txt = (HERE / "documents" / f"{did}.txt").read_text(encoding="utf-8", errors="ignore")
        try:
            q = window(txt, anchor, after)
        except LookupError:
            print(f"[!] 锚点未找到 {anchor[:40]!r}")
            return 1
        extra.append({"evidence_id": eid, "document_id": did, "source_id": sid,
                      "quote": q, "locator": loc, "stance": "supports",
                      "extracted_by": "add_prune_evidence.py/1"})
        added += 1
    p.write_text(json.dumps(extra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"evidence_extra.json 现有 {len(extra)} 条（新增 {added}）")
    for r in extra[-added:] if added else []:
        print(f"\n{r['evidence_id']}: {r['quote'][:250]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
