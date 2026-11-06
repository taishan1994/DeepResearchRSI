"""粗筛：把 1006 篇候选按「与模型训练 RSI 的相关度」分桶，只为缩小人工判读范围。

打分不是结论，是**取材边界的记录**：它决定哪 60 篇会被人工读摘要。
故每条规则都要能说出「为什么这条算相关」。
"""
from __future__ import annotations
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
recs = json.loads((HERE / "candidates_rsi.json").read_text(encoding="utf-8"))

# 硬门槛：2022-01 起（STaR 是这条线的起点）
recs = [r for r in recs if r["published"] >= "2022-01-01"]

RSI = re.compile(r"self-improv|self-evolv|self-reward|recursive self|self-play|self-train|self-teach|"
                 r"self-critiqu|self-refin|self-correct|absolute zero|bootstrapp|model collapse|"
                 r"self-generated|self-distill|self-challeng|self-question|data flywheel|"
                 r"self-synthes|self-instruct|self-verif|self-consisten|rsi\b", re.I)
TRAIN = re.compile(r"\b(rl|reinforcement|training|train|fine-tun|post-train|dpo|grpo|ppo|reward model|"
                   r"verifier|distill|policy|gradient|weights?|checkpoint)\b", re.I)
CONTEXT = re.compile(r"harness|prompt|memory|skill|scaffold|workflow|agent", re.I)
META = re.compile(r"survey|review|position|risk|safety|audit|evaluat|benchmark|theory|theoretic|"
                  r"convergence|collapse|limits?|challenge", re.I)

def bucket(r):
    t, a = r["title"], r["abstract"]
    blob = t + " " + a
    if not RSI.search(blob):
        return None
    if "self-play" in blob.lower() and not TRAIN.search(blob):
        return None
    if META.search(t) and re.search(r"survey|review|position|trustworth|audit|risk", t, re.I):
        return "meta"
    if TRAIN.search(blob) and re.search(r"self-reward|self-train|self-play|rlvr|absolute zero|"
                                        r"bootstrapp|self-improv|recursive self|self-evolv|"
                                        r"data|curriculum|verifier", blob, re.I):
        return "weights"
    if CONTEXT.search(blob):
        return "context"
    return "other"

buckets: dict[str, list] = {}
for r in recs:
    b = bucket(r)
    if b:
        buckets.setdefault(b, []).append(r)

for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
    print(f"{k:8s} {len(v):4d}")

print("\n=== weights 桶里 2022-2026 全部标题（按时间） ===")
for r in sorted(buckets.get("weights", []), key=lambda x: x["published"]):
    print(r["published"], r["id"], r["title"][:105])
