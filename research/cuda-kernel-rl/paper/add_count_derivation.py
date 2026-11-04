"""给「计数型」主张补上 derivation，让 P2（数值可回溯）能真正校验。

## 问题的性质

本文图里有 `9` 篇用结果型奖励、`4` 篇用 GRPO、`7` 篇未点名算法——
这些数字在任何一篇文献的摘要里**都不存在**，它们是本文对语料的统计。

`audit_paper.py` 的 P2 原本要求：每个数字都能在某条 evidence.quote 里
逐字找到。这个判据对观测值正确（1.43x 就该来自论文原文），
但用于统计值就是错的——统计数据不会长在文献里。

## 解法：像 Amdahl 那样重算

`audit_paper.py` 已为派生值留了 `recompute` 通道：
claim 的 derivation 里写明公式，审计**真的重算一遍**，
吻合才放行。Amdahl 的 1.0715 就是这么过的。

本轮给 `recompute` 加了「计数」分支：
    derivation 里写 `计数 outcome=9`
    审计从语料重新统计 outcome 标签的篇数，等于 9 才通过

这样编造的计数仍然过不了（数出来不是 9），而真实统计能过。

## 为什么 derivation 只写标签，不写"我数了 13 篇里的 9 篇"

如果 derivation 自己写死 9，那审计只是核对「derivation 的数字 == 图中的数字」，
两者可以一起错。故 derivation 只声明**口径**（哪个标签），
篇数由审计独立重算。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
A = json.loads((ROOT / "analysis.json").read_text(encoding="utf-8"))

# claim_id -> 要追加的计数口径说明（tag 必须与 audit_paper.recount 的
# TAG_PATTERNS 键一致，否则审计无法重算）
COUNT_CITES = {
    "c-structural-reward": [
        ("outcome", "结果型奖励"),
        ("multi_turn", "多轮交互"),
        ("structural", "结构化代码奖励"),
    ],
    "c-reward-hacking": [
        ("anti_hack", "反作弊机制"),
    ],
    "c-profiling-reward": [
        ("profiling", "profiling 驱动"),
    ],
    "c-grpo-default-but-flawed": [
        ("grpo", "GRPO"),
        ("ppo", "PPO"),
        ("unnamed", "未点名算法"),
    ],
}


def main() -> int:
    path = ROOT / "claims.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = list(rows[0].keys())

    changed = 0
    for r in rows:
        cid = r["claim_id"]
        if cid not in COUNT_CITES:
            continue
        parts = []
        for tag, label in COUNT_CITES[cid]:
            n = _count(tag)
            parts.append(f"计数 {tag}={n}（{label}）")
        add = "；".join(parts) + "，由审计从语料独立重算"
        cur = (r.get("derivation") or "").strip()
        if "计数 " in cur:
            # 已有则替换，避免重复追加
            r["derivation"] = cur
            continue
        r["derivation"] = (cur + "；" + add) if cur else add
        changed += 1

    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"已为 {changed} 条主张补上计数口径")
    return 0


def _count(tag: str) -> int:
    """本地先算一遍，写进 derivation 供人阅读；审计会独立重算。"""
    papers: dict[str, dict] = {}
    for f in (ROOT / "candidates_rl.json",
              ROOT.parent / "cuda-kernel-gen" / "paper" / "papers.json"):
        if not f.is_file():
            continue
        for p in json.loads(f.read_text(encoding="utf-8")):
            pid = (p.get("id") or "").strip()
            if pid:
                papers.setdefault(pid, p)
    import re
    core = []
    with (ROOT / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if "layer=core" not in (r.get("notes") or ""):
                continue
            m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", r["source_id"])
            if m:
                core.append(f"{m.group(1)}.{m.group(2)}")
    pats = {
        "outcome": r"speedup|execution speed|correctness|pass@",
        "multi_turn": r"multi-turn|iterative|interact",
        "structural": r"structural|parallelization|data-flow|decompos",
        "profiling": r"profil|counter|hardware metric",
        "anti_hack": r"reward hack|cheat|hacking|trivial",
        "grpo": r"GRPO|Group Relative Policy Optimization",
        "ppo": r"\bPPO\b",
    }
    n = 0
    for aid in core:
        ab = (papers.get(aid) or {}).get("abstract") or ""
        if tag == "unnamed":
            if not re.search(r"GRPO|Group Relative Policy Optimization"
                             r"|contrastive|\bPPO\b", ab, re.I):
                n += 1
        elif tag in pats and re.search(pats[tag], ab, re.I):
            n += 1
    return n


if __name__ == "__main__":
    raise SystemExit(main())
