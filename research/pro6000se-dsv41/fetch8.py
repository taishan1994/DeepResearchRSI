"""补抓社区来源——重点是**Server Edition 的实测**。

## 为什么要补这一批

本文初稿的核心发现是「公开证据里没有任何一组来自 Server Edition」。
这个结论**是错的**。社区 wiki（local-inference-lab/rtx6kpro）里至少有：

1. `daily-summaries/2026-10/2026-10-25.md` 记载 aristokratic.eth
   在 **4× RTX 6000 Blackwell Server Edition**、Engram 放 RAM、450W 限功耗下实测：
   单流解码 183 tok/s、16 流聚合 695 tok/s、预填 18,400–19,200 tok/s。
2. `hardware/gpu-configs.md` 记载 Festr 的 **8× Server Edition** 整机
   （双路 EPYC 9575F、2.2 TB DDR5-6400、3× xGMI），以及 NCCL 实测。

也就是说：**SE 不仅有实测，还有两种规模的整机（4 卡与 8 卡）。**
初稿把「SE 无实测」当成一项发现来写，属于检索覆盖不足导致的**假否定**——
不是「查了没有」，而是「没查到就说没有」。这比数字错更严重，
因为它让整篇文章的骨架（可迁移 / 不可迁移的分层）建立在错误前提上。

## 教训

否定性断言（「没有」「无一例」「不存在」）需要**穷尽性证据**，
而穷尽性无法用「我搜了几个关键词」来支撑。做法上应当：
- 先找**索引页/目录页**（本仓库的 INDEX.md、daily-summaries/ 目录），
  沿着结构走一遍，而不是只搜关键词；
- 明确写出「检索了哪些位置」，让读者能判断覆盖范围。

本文件按官方 raw URL 抓取，存为 documents/*.txt，并登记到 documents.csv。
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "documents"

BASE = ("https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/"
        "dc552294e0bb850af1eb0e33f566bd37c240c7fa/")

# (document_id, source_id, 相对路径, 说明)
TARGETS = [
    ("doc-r6k-daily-2026-10-25", "src-r6k-daily",
     "daily-summaries/2026-10/2026-10-25.md",
     "社区日更：aristokratic.eth 的 4×SE 实测"),
    ("doc-r6k-bench-results", "src-r6k-bench",
     "benchmarks/results.md",
     "社区汇总基准：NCCL/功耗/跨模型对比"),
    ("doc-r6k-model-dsv41-2026-11", "src-r6k-model",
     "models/deepseek-v4.1-flash.md",
     "DS4.1-Flash 服务页：Karmic Kraken R38 实测"),
]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    fetched_at = now.isoformat(timespec="seconds")

    doc_rows = list(csv.DictReader((ROOT / "documents.csv").open(encoding="utf-8-sig")))
    src_rows = list(csv.DictReader((ROOT / "sources.csv").open(encoding="utf-8-sig")))
    have_src = {r["source_id"] for r in src_rows}
    have_doc = {r["document_id"] for r in doc_rows}

    for did, sid, rel, why in TARGETS:
        url = BASE + rel
        req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
        with urllib.request.urlopen(req, timeout=60) as fh:
            raw = fh.read()
        text = raw.decode("utf-8", errors="replace")
        (DOCS / f"{did}.txt").write_bytes(text.encode("utf-8"))
        print(f"[OK] {did}  {len(text):,} 字符  ({why})")

        if sid not in have_src:
            src_rows.append({
                "source_id": sid,
                "source_type": "primary" if "daily" in sid else "primary",
                "trust_tier": "community-measured",
                "title": why,
                "url": url,
                "publisher": "local-inference-lab/rtx6kpro",
                "published_at": "",
                "fetched_at": fetched_at,
                "notes": "社区一手现场记录；含 Server Edition 实测",
            })
            have_src.add(sid)

        if did not in have_doc:
            # documents.csv 的真实表头是 6 列（无 fetched_at/url/notes）——
            # 推断表头就会写成 9 列而崩在 writerows。
            doc_rows.append({
                "document_id": did,
                "source_id": sid,
                "content_hash": sha256(text.encode("utf-8")),
                "parser_version": "fetch8.py/1",
                "byte_size": len(text.encode("utf-8")),
                "snapshot": f"documents/{did}.txt",
            })
            have_doc.add(did)

    with (ROOT / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(src_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(src_rows)
    with (ROOT / "documents.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(doc_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(doc_rows)

    print(f"\nsources {len(src_rows)} ｜ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
