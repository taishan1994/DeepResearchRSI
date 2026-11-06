"""把全文压成可核对的候选句（digest），供人工判定入 evidence.csv。

为什么要有这一步：全文平均 6 万字符，直接读会让注意力漂移，
最后记住的仍然是摘要。这里的规则是「必须含硬数 + 语境信号」，
把 23 篇压到每篇 20–40 条，人工再判定。
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

NUM = re.compile(r"\d")
CTX = re.compile(
    r"ceiling|headroom|controller|promot|reject|lossless|mismatch|token forcing|"
    r"paired|lower bound|confidence|noise|benchmark|goodput|throughput|latency|"
    r"SLO|speedup|geometric|arithmetic|baseline|ablation|proxy|anchor|"
    r"quantiz|tolerance|accuracy|regress|failure|fail|revers|slower|negative",
    re.I)


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\u2020])", text)
    return [p.strip() for p in parts if 40 <= len(p.strip()) <= 700]


def main() -> int:
    out = []
    for p in sorted(DOCS.glob("doc-arxiv-*-full.txt")):
        tag = p.name[len("doc-arxiv-"):-len("-full.txt")]
        aid = tag.replace("-", ".", 1)
        text = p.read_text(encoding="utf-8", errors="replace")
        keep = [s for s in sentences(text) if NUM.search(s) and CTX.search(s)]
        seen, uniq = set(), []
        for s in keep:
            k = s[:80]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(s)
        out.append(f"\n===== {aid} ({len(uniq)} 条) =====")
        out.extend(uniq[:60])
        print(f"  {aid}: {len(uniq)}")
    (HERE / "digest.txt").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("digest 行数", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
