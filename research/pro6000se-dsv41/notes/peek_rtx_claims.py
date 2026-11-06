"""列出 rtx-pro-6000 归档里与 DeepSeek-V4 相关的主张与证据，供本归档复用。"""
import csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "rtx-pro-6000"
claims = list(csv.DictReader((ROOT / "claims.csv").open(encoding="utf-8-sig")))
evid = {r["evidence_id"]: r for r in csv.DictReader((ROOT / "evidence.csv").open(encoding="utf-8-sig"))}

pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r"V4|Flash|deepseek", re.I)
hits = [c for c in claims if pat.search(c["statement"]) or pat.search(c.get("notes") or "")]
print(f"命中主张 {len(hits)} / {len(claims)}")
for c in hits:
    print(f"\n[{c['claim_id']}] {c['claim_type']} / {c['confidence']} / sku={c.get('sku','-')}")
    print("  " + c["statement"][:400])
    for eid in (c.get("evidence_ids") or "").split(";"):
        eid = eid.strip()
        e = evid.get(eid)
        if e:
            print(f"    <{eid}> {e.get('source_id')} :: {e['quote'][:300]}")
