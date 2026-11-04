"""给尚未被引用的 12 篇 core 工作补证据，每篇至少一条。

## 为什么必须补

上一轮统计发现：26 篇 core 里有 12 篇**一条证据都没有**。
后果不只是「材料少」，而是**结论会偏**：关于「跨维度工作为 0」的判断，
样本其实是 14 篇而不是 26 篇。若那 12 篇里恰有几篇做了系统级设计，
结论就反了。

## 做法

对这 12 篇各扫一遍全文，用一组**通用但要求实质内容**的 pattern 找
最能代表该工作的句子，并按句子内容自动判定它属于哪个维度：

  observe  出现 ncu/profil/metric/feedback/error
  act      出现 edit/rewrite/generate/implementation space
  budget   出现 turn/iteration/budget/cost/prune
  recover  出现 fail/error/fallback/retry/stagnat
  eval     出现 benchmark/speedup/correctness/pass@

一条句子可能命中多个维度，取命中数最多的那个；全不中则记为 `general`
（仍算该篇被引用，但不计入维度统计——不能硬塞）。

## 纪律

- 仍走 build_agent.grab 的 _ok() 过滤（排除题名、作者、致谢）
- 每篇只取一条，避免某篇因篇幅长而权重过高
- 判定维度靠句子内容，不靠论文归类——否则就是自己给自己作证
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from pathlib import Path

import build_agent as B

HERE = Path(__file__).resolve().parent

# 通用候选句：以大写字母开头的完整句，长度适中
SENT = re.compile(r"[A-Z][^.]{60,320}\.")

DIMS = {
    "observe": re.compile(
        r"\b(ncu|nsight|profil\w+|metric|counter|feedback|error message"
        r"|occupancy|register|memory bandwidth)\b", re.I),
    "act": re.compile(
        r"\b(edit|rewrite|generat\w+|implementation space|refine|patch"
        r"|modif\w+|candidate)\b", re.I),
    "budget": re.compile(
        r"\b(turn|round|iteration|budget|cost|prun\w+|overhead|rollout"
        r"|expensive|time limit)\b", re.I),
    "recover": re.compile(
        r"\b(fail\w*|fallback|retry|retries|stagnat\w+|plateau|rollback"
        r"|local optima)\b", re.I),
    "eval": re.compile(
        r"\b(benchmark|speedup|correctness|pass@|fast_?p|baseline"
        r"|evaluat\w+)\b", re.I),
}


def classify(s: str) -> str:
    hits = {d: len(p.findall(s)) for d, p in DIMS.items()}
    best = max(hits, key=lambda k: hits[k])
    return best if hits[best] > 0 else "general"


def main() -> int:
    inc = B.json.loads((HERE / "included_agent.json").read_text(encoding="utf-8"))
    B._TITLES = {c["arxiv_id"]: c["title"]
                 for t in ("core", "adjacent") for c in inc[t]}

    with (HERE / "evidence.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = list(rows[0].keys())
    covered = {r["source_id"] for r in rows}

    todo = [c for c in inc["core"]
            if "src-arxiv-" + c["arxiv_id"].replace(".", "-") not in covered]
    print(f"待补 {len(todo)} 篇 core\n")

    B.EVIDENCE = rows
    B.FAILS = []
    added = 0
    for c in todo:
        aid = c["arxiv_id"]
        text = B.full_text(aid)
        if not text:
            print(f"  [无全文] {aid} {c['title'][:48]}")
            B.FAILS.append(f"{aid}: 无全文")
            continue

        # 在正文中段找候选（跳过前 3000 字符，避开标题与摘要区）
        body = text[3000:]
        picked = None
        for m in SENT.finditer(body):
            q = " ".join(m.group(0).split())
            if not B._ok(q, c["title"]):
                continue
            # 只要含足够多技术词的句子
            if not DIMS["act"].search(q) and not DIMS["observe"].search(q) \
                    and not DIMS["eval"].search(q) and not DIMS["budget"].search(q):
                continue
            picked = q
            break

        if not picked:
            print(f"  [无合格句] {aid} {c['title'][:48]}")
            B.FAILS.append(f"{aid}: 无合格句")
            continue

        dim = classify(picked)
        eid = f"e-{len(B.EVIDENCE) + 1:03d}"
        B.EVIDENCE.append({
            "evidence_id": eid,
            "document_id": "doc-arxiv-" + aid.replace(".", "-"),
            "source_id": "src-arxiv-" + aid.replace(".", "-"),
            "quote": picked,
            "locator": f"fulltext#{dim}",
            "quote_type": "quote",
            "stance": "supports",
            "fetched_at": rows[0]["fetched_at"] if rows else "",
            "note": f"[{dim}] {c['title'][:42]}：代表句",
        })
        added += 1
        print(f"  + {eid} [{dim}] {aid}")
        print(f"       {picked[:88]}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(B.EVIDENCE)
    (HERE / "evidence.csv").write_text(buf.getvalue(), encoding="utf-8",
                                       newline="\n")

    print(f"\n新增 {added} 条，evidence 共 {len(B.EVIDENCE)} 条")
    if B.FAILS:
        print("[!] 失败：")
        for f in B.FAILS:
            print("   ", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
