"""按五个维度聚合证据，生成 analysis.json（论文里所有数字都读它）。

## 为什么单独一个分析脚本

论文里的数字若手写，改一处就要改全文，而且必然出现「表里 7 篇、正文 6 篇」。
上一轮（cuda-kernel-rl）在这上面栽过两次：手写的算法表全错、
`1.19x` 无法回溯。故这里所有计数都由脚本从证据/来源算出来。

## 输出

  dims            各维度的证据数与涉及论文数
  dim_sources     每个维度下有证据的论文清单（去重）
  sources_by_layer core / adjacent 计数
  time            按季度的工作数
  claims          主张数与置信度分布
  cross           同时覆盖多个维度的工作（说明系统性）
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> list[dict]:
    with (HERE / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


DIM_RE = re.compile(r"^\[(\w+)\]")


def main() -> int:
    ev = read("evidence.csv")
    src = read("sources.csv")
    cl = read("claims.csv")

    dim_ev: Counter = Counter()
    dim_src: dict[str, set[str]] = defaultdict(set)
    src_dims: dict[str, set[str]] = defaultdict(set)

    for r in ev:
        m = DIM_RE.match(r.get("note") or "")
        if not m:
            continue
        d = m.group(1)
        dim_ev[d] += 1
        sid = r.get("source_id") or ""
        dim_src[d].add(sid)
        src_dims[sid].add(d)

    order = ["observe", "act", "budget", "recover", "eval"]
    dims = {
        "order": order,
        "evidence_count": {d: dim_ev.get(d, 0) for d in order},
        "source_count": {d: len(dim_src.get(d, ())) for d in order},
        "sources": {d: sorted(dim_src.get(d, ())) for d in order},
    }

    layer = Counter()
    for s in src:
        note = s.get("notes") or ""
        m = re.search(r"layer=(\w+)", note)
        layer[m.group(1) if m else "unknown"] += 1

    # 时间分布：按季度
    time_q = Counter()
    for s in src:
        d = (s.get("published_at") or "")[:7]
        if len(d) == 7:
            y, mo = d.split("-")
            q = (int(mo) - 1) // 3 + 1
            time_q[f"{y}-Q{q}"] += 1

    # 跨维度覆盖：一个工作覆盖 ≥3 个维度，说明它是系统级而非单点改进
    multi = {sid: sorted(ds) for sid, ds in src_dims.items() if len(ds) >= 3}

    conf = Counter((c.get("confidence") or "") for c in cl)

    out = {
        "generated_by": "analyze.py",
        "as_of": (src[0]["fetched_at"][:10] if src else ""),
        "total_sources": len(src),
        "total_evidence": len(ev),
        "total_claims": len(cl),
        "sources_by_layer": dict(layer),
        "dims": dims,
        "time_by_quarter": dict(sorted(time_q.items())),
        "multi_dimension_works": len(multi),
        "multi_dimension_detail": multi,
        "claim_confidence": dict(conf),
    }

    txt = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    (HERE / "analysis.json").write_text(txt, encoding="utf-8", newline="\n")
    paper = HERE / "paper"
    if paper.is_dir():
        (paper / "analysis.json").write_text(txt, encoding="utf-8", newline="\n")

    print(f"来源 {len(src)}｜证据 {len(ev)}｜主张 {len(cl)}")
    print("\n各维度：")
    for d in order:
        print(f"  {d:<9} 证据 {dims['evidence_count'][d]:>2} ｜ "
              f"论文 {dims['source_count'][d]:>2}")
    print(f"\n层级：{dict(layer)}")
    print(f"季度：{dict(sorted(time_q.items()))}")
    print(f"跨 ≥3 维度的工作：{len(multi)} 个")
    print(f"置信度：{dict(conf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
