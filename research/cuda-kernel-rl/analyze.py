"""从证据与主张生成论文需要的统计，输出 `analysis.json`。

## 为什么不让论文直接写数字

上一份综述（`cuda-kernel-gen`）踩过这个坑：图注里写了 `1.19x`，
而那个数在 papers.json / evidence.csv / 表格里**都不存在**——
是写的时候顺手编的。审计脚本查出来才知道。

故本文件的原则是：**论文里的每个数字都从 claim/evidence 算出来**，
先落盘到 analysis.json，再让正文引用这个文件里的键。
人工写死的只允许是「引用编号」和「定性判断」。

## 输出内容

  timeline          按季度统计的 RL 方法论文数
  reward_shift      奖励形态随时间的演化（outcome / structural / multi-turn ...）
  algo_mix          算法提及分布
  quantified        有量化结果的论文及其数字
  coverage          E1 覆盖、证据类型分布
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "candidates_rl.json"
OLD = HERE.parent / "cuda-kernel-gen" / "paper" / "papers.json"

papers: dict[str, dict] = {}
for p in json.loads(CANDS.read_text(encoding="utf-8")):
    papers[p["id"]] = p
if OLD.is_file():
    for p in json.loads(OLD.read_text(encoding="utf-8")):
        papers.setdefault(p["id"], p)


def aid_of(source_id: str) -> str:
    m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", source_id)
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def quarter(date_str: str) -> str:
    y, m = date_str[:4], int(date_str[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


with (HERE / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
    sources = list(csv.DictReader(fh))
with (HERE / "evidence.csv").open(encoding="utf-8-sig", newline="") as fh:
    evidence = list(csv.DictReader(fh))
with (HERE / "claims.csv").open(encoding="utf-8-sig", newline="") as fh:
    claims = list(csv.DictReader(fh))

layer = {}
for r in sources:
    m = re.search(r"layer=(\w+)", r.get("notes") or "")
    layer[r["source_id"]] = m.group(1) if m else "?"

core = [r for r in sources if layer.get(r["source_id"]) == "core"]

# ---------------------------------------------------------------- 时间线
by_q = Counter(quarter(r["published_at"]) for r in core)
timeline = [{"quarter": q, "count": n} for q, n in sorted(by_q.items())]

# ---------------------------------------------------------------- 奖励形态
# 判定依据：摘要里的措辞。每个标签的判定词写在这里，可复核。
REWARD_TAGS = {
    "outcome": r"speedup|execution speed|correctness|pass@",
    "multi_turn": r"multi-turn|iterative|interact",
    "structural": r"structural|parallelization|data-flow|decompos",
    "profiling": r"profil|counter|hardware metric",
    "anti_hack": r"reward hack|cheat|hacking|trivial",
    "curriculum": r"curriculum",
    "contrastive": r"contrastive",
    "synthetic": r"synthetic|data synthes",
}
rew = defaultdict(list)
for r in core:
    aid = aid_of(r["source_id"])
    ab = papers.get(aid, {}).get("abstract", "")
    for tag, pat in REWARD_TAGS.items():
        if re.search(pat, ab, re.I):
            rew[tag].append({"arxiv_id": aid, "published": r["published_at"]})
reward_shift = {k: len(v) for k, v in sorted(rew.items(), key=lambda kv: -len(kv[1]))}

# ---------------------------------------------------------------- 算法分布
# 判定词按优先级排：先 GRPO，再 PPO，再对比式，都不中则「未点名」。
# 顺序重要——一篇论文可能同时提到 GRPO 与 PPO（做对比），
# 这时按它**实际使用**的那个归类，而 GRPO 在摘要里通常是被采用的。
ALGO_RULES: list[tuple[str, str]] = [
    ("GRPO", r"GRPO|Group Relative Policy Optimization"),
    ("对比式", r"contrastive"),
    ("PPO", r"\bPPO\b"),
]
algo_mix: dict[str, int] = {}
algo_which: dict[str, list[str]] = {}
for r in core:
    aid = aid_of(r["source_id"])
    ab = papers.get(aid, {}).get("abstract", "")
    hit = None
    for name, pat in ALGO_RULES:
        if re.search(pat, ab, re.I):
            hit = name
            break
    hit = hit or "未点名"
    algo_mix[hit] = algo_mix.get(hit, 0) + 1
    algo_which.setdefault(hit, []).append(aid)

# ---------------------------------------------------------------- 量化结果
# 只抽「摘要里明确给出数字」的句子，逐条留原文，便于核对
NUM_RE = re.compile(
    r"[^.]*?(?:\d+\.?\d*\s*(?:x|×|%|percent))[^.]*\."
)
quantified: list[dict] = []
for r in core:
    aid = aid_of(r["source_id"])
    ab = papers.get(aid, {}).get("abstract", "")
    for m in NUM_RE.finditer(ab):
        sent = m.group(0).strip()
        # 只要含性能量纲的
        if not re.search(r"speedup|faster|improv|surpass|exceed|beat|achiev",
                         sent, re.I):
            continue
        quantified.append({
            "arxiv_id": aid,
            "published": r["published_at"],
            "title": r["title"],
            "sentence": sent,
            "numbers": re.findall(r"\d+\.?\d*\s*(?:x|×|%)", sent),
        })

# ---------------------------------------------------------------- 覆盖
ev_by_source = Counter(e["source_id"] for e in evidence)
ev_by_type = Counter(e.get("quote_type") or "quote" for e in evidence)
claims_by_conf = Counter(c["confidence"] for c in claims)
claims_by_type = Counter(c["claim_type"] for c in claims)

# 引用闭合：每条 high 主张是否都有 primary 证据
src_tier = {r["source_id"]: r["trust_tier"] for r in sources}
high_no_primary = []
for c in claims:
    if c["confidence"] != "high":
        continue
    evids = (c["evidence_ids"] or "").split(";")
    evmap = {e["evidence_id"]: e for e in evidence}
    ok = any(src_tier.get(evmap.get(x, {}).get("source_id", ""), "") == "primary"
             for x in evids)
    if not ok:
        high_no_primary.append(c["claim_id"])

out = {
    "generated_from": ["sources.csv", "evidence.csv", "claims.csv"],
    "counts": {
        "sources": len(sources),
        "sources_core": len(core),
        "sources_adjacent": sum(1 for r in sources
                                if layer.get(r["source_id"]) == "adjacent"),
        "sources_infra": sum(1 for r in sources
                             if layer.get(r["source_id"]) == "infra"),
        "evidence": len(evidence),
        "claims": len(claims),
        "claims_high": sum(1 for c in claims if c["confidence"] == "high"),
        "papers_in_candidates": len(papers),
    },
    "date_range": {
        "earliest": min(r["published_at"] for r in core),
        "latest": max(r["published_at"] for r in core),
    },
    "timeline": timeline,
    "reward_shift": reward_shift,
    "algo_mix": algo_mix,
    "algo_which": algo_which,
    "quantified": quantified,
    "evidence_per_source": dict(ev_by_source),
    "evidence_by_type": dict(ev_by_type),
    "claims_by_confidence": dict(claims_by_conf),
    "claims_by_type": dict(claims_by_type),
    "high_claims_without_primary": high_no_primary,
}

payload = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
# 同时写两处：归档根目录（给校验/审计用）与 paper/（给画图用）。
# 先前只写根目录，再手动 Copy-Item 到 paper/，结果忘同步一次，
# fig3 就静默跳过了——两份副本必然漂移，故在此一处写全。
(HERE / "analysis.json").write_text(payload, encoding="utf-8", newline="\n")
_paper = HERE / "paper"
if _paper.is_dir():
    (_paper / "analysis.json").write_text(
        payload, encoding="utf-8", newline="\n")
    # papers.json 同理：画图与审计都要最新的候选池
    _src = HERE / "candidates_rl.json"
    if _src.is_file():
        (_paper / "papers.json").write_text(
            _src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

print("analysis.json 已生成（根目录 + paper/）")
print(f"  core {out['counts']['sources_core']} 篇，"
      f"{out['date_range']['earliest']} → {out['date_range']['latest']}")
print(f"  时间线: {timeline}")
print(f"  奖励形态: {reward_shift}")
print(f"  算法: {algo_mix}")
print(f"  含数字句子: {len(quantified)} 条")
print(f"  high 但无 primary: {high_no_primary or '无'}")
