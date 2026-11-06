import csv, re, sys
from pathlib import Path
root = Path(r"D:\github\DeepResearchRSI\research\rsi-model-training")
src = {r["source_id"]: r for r in csv.DictReader((root/"sources.csv").open(encoding="utf-8-sig"))}
ev  = {r["evidence_id"]: r for r in csv.DictReader((root/"evidence.csv").open(encoding="utf-8-sig"))}
cl  = {r["claim_id"]: r for r in csv.DictReader((root/"claims.csv").open(encoding="utf-8-sig"))}
rep = (root/"REPORT.md").read_text(encoding="utf-8")
pap = (root/"paper"/"PAPER.md").read_text(encoding="utf-8")
for name, text in (("REPORT", rep), ("PAPER", pap)):
    cites = set(re.findall(r"\[(c-[a-z0-9-]+)\]", text))
    print(name, "claims cited", len(cites), "of", len(cl), "uncited:", sorted(set(cl)-cites))
    evs = set()
    for c in cites:
        for e in cl[c]["evidence_ids"].split(";"):
            evs.add(e.strip())
    print("  evidence reached", len(evs), "of", len(ev))
print("orphan evidence (never cited by any claim):", sorted(set(ev) - {e.strip() for c in cl.values() for e in c["evidence_ids"].split(";")}))
