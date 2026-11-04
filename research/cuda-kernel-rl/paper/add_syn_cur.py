"""补齐 synthetic / curriculum 的计数口径，并让 audit 支持这两个标签。

## 剩余的两个失败

`fig2_reward_forms.csv` 里有 synthetic=3、curriculum=1，挂着
`c-structural-reward`，但该主张的 derivation 没声明这两个口径，
audit 因此无法重算。

## 顺带一个判断上的修正

`c-synthetic-data` 这条主张本来就是讲合成数据的，
把 synthetic 行挂到它上面比挂 `c-structural-reward` 更准确。
curriculum 没有专门主张，仍挂 `c-structural-reward`（同为「奖励形态」维度）。

故本脚本做两件事：
  1. 让 audit 的 TAG_PATTERNS 认识 synthetic / curriculum（已有，确认）
  2. 把 CSV 里 synthetic 行的 cite 改为 c-synthetic-data，
     并给 c-synthetic-data 补 `计数 synthetic=3`
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def count_tag(tag: str, pat: str, core: list[str],
              papers: dict[str, dict]) -> int:
    return sum(1 for a in core
               if re.search(pat, (papers.get(a) or {}).get("abstract", ""), re.I))


def main() -> int:
    papers: dict[str, dict] = {}
    for f in (ROOT / "candidates_rl.json",
              ROOT.parent / "cuda-kernel-gen" / "paper" / "papers.json"):
        if not f.is_file():
            continue
        for p in json.loads(f.read_text(encoding="utf-8")):
            if p.get("id"):
                papers.setdefault(p["id"], p)

    core: list[str] = []
    with (ROOT / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if "layer=core" not in (r.get("notes") or ""):
                continue
            m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", r["source_id"])
            if m:
                core.append(f"{m.group(1)}.{m.group(2)}")

    n_syn = count_tag("synthetic", r"synthetic|data synthes", core, papers)
    n_cur = count_tag("curriculum", r"curriculum", core, papers)
    print(f"synthetic={n_syn}  curriculum={n_cur}")

    # ---- 改 CSV 的 cite：synthetic -> c-synthetic-data ----
    csv_path = HERE / "data" / "fig2_reward_forms.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = list(rows[0].keys())
    key = header[0]
    for r in rows:
        if r[key] == "synthetic":
            r["cite"] = "c-synthetic-data"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("fig2: synthetic 行改挂 c-synthetic-data")

    # ---- 给两条主张补口径 ----
    claims_path = ROOT / "claims.csv"
    with claims_path.open(encoding="utf-8-sig", newline="") as fh:
        claims = list(csv.DictReader(fh))
    ch = list(claims[0].keys())
    for c in claims:
        cur = (c.get("derivation") or "").strip()
        if c["claim_id"] == "c-synthetic-data" and "计数 synthetic" not in cur:
            add = f"计数 synthetic={n_syn}（合成数据）"
            c["derivation"] = (cur + "；" + add) if cur else add
        if c["claim_id"] == "c-structural-reward" and "计数 curriculum" not in cur:
            add = f"计数 curriculum={n_cur}（课程学习）"
            c["derivation"] = (cur + "；" + add) if cur else add
    with claims_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ch, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(claims)
    print("已补 c-synthetic-data / c-structural-reward 的计数口径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
