"""把 arXiv 摘要导出为文档快照，供 E1（quote 必须是原文子串）校验。

## 为什么要做这件事

ADR-0002 规定 `Document` 必须存 `raw_uri`（快照路径）与 `content_hash`，
`Evidence.quote` 必须是该快照的原文子串。

但 cuda-kernel-gen 归档里 **一条快照都没有**：19 条证据全部指向 arXiv 摘要，
而摘要文本只存在 `paper/papers.json` 里，不在归档的结构化位置。
结果是 E1 无法校验——不是没实现，是**没有可比对的原件**。

`build_evidence.py` 里有一份自检（`quote in abstract`），
但它只在生成时跑一次，且不产生可留档的快照：
换个人拿到这个归档，无法重跑同一检查。

## 做法

从 `paper/papers.json` 读出每篇论文的摘要，按论文建立快照，
再用 `invariants.write_snapshot` 登记 content_hash。
一篇论文一个 document_id：`doc-arxiv-<id>`。

只导出**被证据引用到的**论文，不导出全部 98 篇——
快照的意义是支撑证据，不是囤积全文。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repo root
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi.invariants import write_snapshot  # noqa: E402

SLUG_DIR = HERE
PAPERS = HERE / "paper" / "papers.json"
PARSER_VERSION = "arxiv-abstract-v1"


def doc_id_for(arxiv_id: str) -> str:
    return "doc-arxiv-" + arxiv_id.replace(".", "-")


def main() -> int:
    papers = json.loads(PAPERS.read_text(encoding="utf-8"))
    by_id: dict[str, dict] = {}
    for p in papers:
        aid = (p.get("arxiv_id") or p.get("id") or "").strip()
        if not aid:
            m = re.search(r"(\d{4}\.\d{4,5})", json.dumps(p))
            aid = m.group(1) if m else ""
        if aid:
            by_id[aid] = p

    # 哪些 source 是 arXiv，且被证据引用
    with (SLUG_DIR / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
        sources = list(csv.DictReader(fh))
    with (SLUG_DIR / "evidence.csv").open(encoding="utf-8-sig", newline="") as fh:
        evid = list(csv.DictReader(fh))
    used = {e["source_id"] for e in evid if e.get("source_id")}

    # source_id -> arxiv id（约定 src-arxiv-2507-14111 -> 2507.14111）
    written = 0
    missing: list[str] = []
    for s in sources:
        sid = s["source_id"]
        if sid not in used:
            continue
        m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", sid)
        if not m:
            continue
        aid = f"{m.group(1)}.{m.group(2)}"
        p = by_id.get(aid)
        if not p:
            missing.append(f"{sid} -> arXiv:{aid} 不在 papers.json")
            continue
        abstract = (p.get("abstract") or p.get("summary") or "").strip()
        if not abstract:
            missing.append(f"{sid} 的摘要为空")
            continue
        write_snapshot(SLUG_DIR, doc_id_for(aid), abstract,
                       source_id=sid, parser_version=PARSER_VERSION)
        written += 1

    print(f"写入 {written} 份摘要快照 -> documents/")
    if missing:
        print(f"未导出 {len(missing)} 条：")
        for m in missing:
            print("  " + m)

    # 让 evidence 能定位到快照：补 document_id 列
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
