"""生成 analysis.json —— 报告里所有计数与统计的唯一来源。

## 为什么数字必须由脚本产出

docs/LESSONS.md 2.1 记录过一类反复出现的失效：**把某一次的正确答案写进正文
（或检查器），而不是写成从数据推出来的规则**。后果是数据一变，正文悄悄失真，
而所有校验仍然通过。

故本归档里：

  * 报告正文里出现的每个计数（来源数、证据数、主张数、维度分布、
    高置信数、争议数、快照数、仓库规模）都从本文件读；
  * 本文件只做统计，不做判断——判断在 claims.csv；
  * `scripts/validate_research.py` 的输出另存 validation.txt。

用法：python make_analysis.py
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def rows(name: str) -> list[dict]:
    p = HERE / name
    if not p.is_file():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    sources = rows("sources.csv")
    evidence = rows("evidence.csv")
    claims = rows("claims.csv")
    documents = rows("documents.csv")

    # 五维标注写在 evidence.note 的 `dim=xxx｜` 前缀里。
    # 用正则取而不是靠 split，是为了让未标注的证据显式落到 (none) 桶里，
    # 而不是被静默当成某一维。
    dims = Counter()
    for e in evidence:
        m = re.match(r"dim=([a-z0-9-]+)", e.get("note") or "")
        dims[m.group(1) if m else "(none)"] += 1

    # 按「层」分组：paper / code / page。
    # 层由 source_id 决定，而 source 的 layer 写在 sources.csv 的 notes 前缀里
    # （`layer=paper｜...`），这样新增来源时不需要改本文件。
    layer_of = {}
    for s in sources:
        m = re.match(r"layer=([a-z]+)", s.get("notes") or "")
        layer_of[s["source_id"]] = m.group(1) if m else "unknown"
    ev_by_layer = Counter(layer_of.get(e.get("source_id", ""), "unknown") for e in evidence)

    cited = Counter()
    for c in claims:
        for eid in filter(None, (c.get("evidence_ids") or "").split(";")):
            cited[eid] += 1
        for eid in filter(None, (c.get("counter_evidence_ids") or "").split(";")):
            cited[eid] += 1

    # 悬空证据 = 有证据没被任何主张引用。它不违反 C1，
    # 但一个零引用的证据要么是白取的，要么是该补的主张——都要显式报出来。
    dangling = sorted({e["evidence_id"] for e in evidence} - set(cited))

    repo = {}
    rap = HERE / "repo_audit.json"
    if rap.is_file():
        repo = json.loads(rap.read_text(encoding="utf-8"))

    brief = (HERE / "brief.yaml").read_text(encoding="utf-8") \
        if (HERE / "brief.yaml").is_file() else ""
    subq = re.findall(r"^\s*- id: (q\d+)$", brief, re.M)
    status = re.findall(r"^\s+status: (\w+)$", brief, re.M)

    val = ""
    vp = HERE / "validation.txt"
    if vp.is_file():
        val = vp.read_text(encoding="utf-8").strip()
    else:
        try:
            val = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_research.py"),
                 f"research/{HERE.name}"],
                capture_output=True, text=True, cwd=str(ROOT), check=False,
            ).stdout.strip().splitlines()[-3]
        except (OSError, IndexError):
            val = ""

    out = {
        "archive": HERE.name,
        "counts": {
            "sources": len(sources),
            "documents": len(documents),
            "evidence": len(evidence),
            "claims": len(claims),
            "claims_high": sum(1 for c in claims if c["confidence"] == "high"),
            "claims_medium": sum(1 for c in claims if c["confidence"] == "medium"),
            "claims_low": sum(1 for c in claims if c["confidence"] == "low"),
            "claims_disputed": sum(1 for c in claims if c["confidence"] == "disputed"),
        },
        "sources_by_tier": dict(Counter(s["trust_tier"] for s in sources)),
        "sources_by_type": dict(Counter(s["source_type"] for s in sources)),
        "claims_by_type": dict(Counter(c["claim_type"] for c in claims)),
        "evidence_by_dim": dict(dims.most_common()),
        "evidence_by_layer": dict(ev_by_layer.most_common()),
        "evidence_dangling": dangling,
        "evidence_cited_once_or_more": len(cited),
        "subquestions": {"total": len(subq), "ids": subq,
                         "status": dict(Counter(status))},
        "repo": repo,
        "validation": val,
    }
    (HERE / "analysis.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in out.items() if k != "repo"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
