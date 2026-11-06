import csv, re
from pathlib import Path
root = Path(r"D:\github\DeepResearchRSI\research\rsi-model-training")
src = list(csv.DictReader((root/"sources.csv").open(encoding="utf-8-sig")))
ev  = list(csv.DictReader((root/"evidence.csv").open(encoding="utf-8-sig")))
cl  = list(csv.DictReader((root/"claims.csv").open(encoding="utf-8-sig")))
print("sources", len(src), "evidence", len(ev), "claims", len(cl))
print("evidence cols", list(ev[0].keys()))
print("sample ev", ev[0])
# source_id of each evidence
sids = {s["source_id"] for s in src}
evsrc = {}
for e in ev:
    sid = e.get("source_id") or ""
    evsrc[e["evidence_id"]] = sid
print("evidence without valid source:", [k for k,v in evsrc.items() if v not in sids])
# claims -> evidence -> source
used = {}
for c in cl:
    for e in (c.get("evidence_ids") or "").split(";"):
        e = e.strip()
        if not e: continue
        s = evsrc.get(e)
        if s: used.setdefault(s, set()).add(c["claim_id"])
print("sources used by claims:", len(used), "of", len(src))
unused = [s["source_id"] for s in src if s["source_id"] not in used]
print("unused sources:", len(unused), unused[:10])
