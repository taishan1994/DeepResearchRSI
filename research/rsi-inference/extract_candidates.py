"""从快照里挑候选证据句：把「可能值得引用」的句子先捞出来。

## 为什么不让模型直接读全文找句子

全文平均 6 万字符，45 篇就是 270 万字符。逐篇通读既慢，又会漏——
人（和模型）读长文时注意力会漂移，最后往往只记住摘要。
而本文需要的证据高度模式化：数字、口径、迭代轮次、反馈定义。
故先用正则把候选句压缩到每篇 12-20 条，再人工判定哪条进 evidence.csv。

## 输出必须是原文子串

E1 要求 quote 是快照的原文子串。故这里输出的每一句都直接从快照切片，
不做任何归一化（不去多余空格、不改引号）。判定者复制粘贴即可通过校验。

用法：
    python extract_candidates.py                 # 全部 core
    python extract_candidates.py 2611.04998      # 单篇
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

# 六类信号。每一类对应论文里一个必须被核对的东西：
# 增益多大 / 和谁比 / 反馈是什么 / 迭代多少轮 / 代价多少 / 边界在哪
PATTERNS = {
    "speedup": r"(\d+(?:\.\d+)?\s*(?:x|X|\u00d7)\s*(?:faster|speedup|speed-up)?|"
               r"speedup of \d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:x|\u00d7)\s+(?:geomean|geometric))",
    "percent": r"\d+(?:\.\d+)?\s*%",
    "baseline": r"(baseline|compared (?:to|with)|outperform|beat|torch\.compile|cublas|"
                r"PyTorch|cuDNN|Triton)",
    "feedback": r"(feedback|reward|verif|correctness|test case|unit test|profil|"
                r"speed-of-light|roofline|counter)",
    "iteration": r"(iteration|round|step budget|budget of|trials?|rollout|epoch)",
    "cost": r"(cost|token|GPU hour|wall-clock|overhead|latency|expensive)",
}

STRONG = ("speedup", "percent")


def sentences(text: str) -> list[str]:
    # 按句末标点切，保留原样（不 strip 内部空白，切完再 lstrip）
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    return [p.strip() for p in parts if 40 <= len(p.strip()) <= 600]


def pick(text: str, limit: int = 18) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for s in sentences(text):
        if s in seen:
            continue
        hits = [k for k, pat in PATTERNS.items() if re.search(pat, s, re.I)]
        # 至少命中一个强信号，或命中三个弱信号，才值得一看。
        # 只靠 feedback/iteration 这类词命中的句子太多，且多是套话。
        if not (any(h in STRONG for h in hits) or len(hits) >= 3):
            continue
        seen.add(s)
        out.append((s, hits))
    # 优先保留含多个信号的句子：它们通常就是「结论句」
    out.sort(key=lambda x: -len(x[1]))
    return out[:limit]


def main() -> int:
    want = sys.argv[1] if len(sys.argv) > 1 else None
    inc = json.loads((HERE / "included_rsi.json").read_text(encoding="utf-8"))
    for c in inc["core"]:
        aid = c["arxiv_id"]
        if want and aid != want:
            continue
        stem = "doc-arxiv-" + aid.replace(".", "-")
        full = DOCS / f"{stem}-full.txt"
        snap = full if full.is_file() else DOCS / f"{stem}.txt"
        if not snap.is_file():
            continue
        text = snap.read_text(encoding="utf-8")
        kind = "fulltext" if snap is full else "abstract"
        print("=" * 100)
        print(f"{aid} [{kind}, {len(text)} chars] {c['title'][:80]}")
        print(f"  topic={c['topic']}")
        for s, hits in pick(text):
            tag = ",".join(hits)
            print(f"  [{tag}] {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
