"""抓取 diffbot EXL3 的完整结果页（recipe/results/RESULTS.md），以及另外两个独立社区来源。

## 为什么必须抓这一页

上一轮我把『2 卡 EXL3 旁路』的数字改错了，原因是**只看了 HF 模型卡的 README**，
而 README 把实测细节放在**链接出去的** `recipe/results/RESULTS.md` 里。
那一页含：

1. **8× RTX PRO 6000 Blackwell Server Edition** 节点的实测
   （EPYC 9B45、1.4 TB RAM、云 VM、TP4+EP4 单副本同时只跑一个）。
   —— 这正是我上一轮断言「空白」的那一格。**我又错了，同一个错法。**
2. 我上一轮判定为「编造」的六个数字，其实全都在这页上：
   `0.0522 / 0.0306 / 0.0111`（"This release, as served" 行）、
   `0.0082`（"Original, second pass (floor)" —— 真的是噪声底）、
   `224.1`（agentic 单会话 **decode tok/s**，不是墙钟秒）、
   `172.8`（46K 单流 decode 中位）、
   `11,157 / 11,467`（40K 冷预填）。

所以上一轮的「更正」本身是错的：我把对的改成了错的，并且自认为找到了编造。
教训不是「要更仔细」，而是：**核对一个数字前，必须先确认自己拿到的是出数字的那份文档。**

## 其余两个来源

- `tacos4me/...Prune-2xRTX6K`：第三种路线（专家剪枝到 224/384，2 卡全驻显存），
  141 tok/s 单流、~9,800 预填、GPQA 92.9%。与 EXL3（量化）是**不同**的取舍。
- `Niko1221/Strata#4816`：单张 **Workstation Edition**、Windows 11、IST-DAS 2.25bpw，
  84 tok/s decode / 1,889 预填 —— 单卡可行性的实证，且**是 WE 不是 SE**。
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = [
    # (document_id, source_id, url, 说明, 类型, 信任层)
    ("doc-diffbot-results", "src-diffbot-results",
     "https://huggingface.co/diffbot/DeepSeek-V4.1-Flash-EXL3-3bpw-2x-RTX-PRO-6000/raw/main/recipe/results/RESULTS.md",
     "EXL3 完整结果页：含 8×Server Edition 节点实测、KL 噪声底 0.0082、agentic 224.1 tok/s",
     "benchmark", "primary"),
    ("doc-tacos4me-prune", "src-tacos4me-prune",
     "https://huggingface.co/tacos4me/DeepSeek-V4.1-Flash-Prune-2xRTX6K/raw/main/README.md",
     "专家剪枝路线：224/384 专家、2 卡全驻显存、141 tok/s 单流、GPQA 92.9%",
     "benchmark", "primary"),
    ("doc-strata-4816", "src-strata-4816",
     "https://api.github.com/repos/Niko1221/Strata/issues/4816",
     "单张 Workstation Edition + Windows 11：84 tok/s decode、1,889 tok/s 预填（16K）",
     "benchmark", "primary"),
]


def main() -> int:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    fetched_at = now.isoformat(timespec="seconds")

    doc_rows = list(csv.DictReader((ROOT / "documents.csv").open(encoding="utf-8-sig")))
    src_rows = list(csv.DictReader((ROOT / "sources.csv").open(encoding="utf-8-sig")))
    have_src = {r["source_id"] for r in src_rows}
    have_doc = {r["document_id"] for r in doc_rows}

    for did, sid, url, why, stype, tier in TARGETS:
        req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
        with urllib.request.urlopen(req, timeout=90) as fh:
            raw = fh.read()
        text = raw.decode("utf-8", errors="replace")
        (ROOT / "documents" / f"{did}.txt").write_bytes(text.encode("utf-8"))
        print(f"[OK] {did}  {len(text):,} 字符")

        if sid not in have_src:
            src_rows.append({
                "source_id": sid,
                "url": url.split("/raw/")[0] if "/raw/" in url else url,
                "source_type": stype,
                "publisher": "diffbot" if "diffbot" in sid else
                             ("tacos4me" if "tacos4me" in sid else "Niko1221/Strata"),
                "title": why,
                "published_at": "", "updated_at": "",
                "fetched_at": fetched_at,
                "language": "en", "trust_tier": tier,
                "access": "open", "license": "unknown",
                "notes": why,
            })
            have_src.add(sid)

        if did not in have_doc:
            doc_rows.append({
                "document_id": did, "source_id": sid,
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "parser_version": "fetch9.py/1",
                "byte_size": len(text.encode("utf-8")),
                "snapshot": f"documents/{did}.txt",
            })
            have_doc.add(did)

    with (ROOT / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(src_rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(src_rows)
    with (ROOT / "documents.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(doc_rows[0].keys()), lineterminator="\n")
        w.writeheader(); w.writerows(doc_rows)

    print(f"\nsources {len(src_rows)} ｜ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
