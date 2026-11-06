"""把全文压成可核对的候选句（digest），供人工判定入 evidence.csv。

为什么要有这一步：量化论文平均 5–8 万字符，且正文大量篇幅在讲量化核的数学，
直接读会让注意力漂移，最后记住的仍然是摘要里的「我们比 AWQ 好」。
这里的规则是「必须含硬数 + 量化语境信号」，把 32 篇压到每篇 20–60 条，人工再判定。

## 与 rsi-serving 的 digest 差别

端到端那篇的语境词是 ceiling/promot/lossless；量化层的语境词完全不同：
bit、calib、perplexity、WikiText、GSM8K、MMLU、outlier、group size、W4A4。
照抄会让九成句子被滤掉。
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

NUM = re.compile(r"\d")
CTX = re.compile(
    r"quantiz|quantis|bit-width|low-bit|mixed-precision|W4A4|W8A8|FP4|FP8|INT4|INT2|ternary|"
    r"calibrat|perplexity|WikiText|GSM8K|MMLU|accuracy|degradation|drop|regress|"
    r"outlier|group size|granularity|scale|zero-point|rotation|Hessian|Fisher|"
    r"sensitiv|budget|allocat|layer|tile|expert|"
    r"fidelity|divergence|KL|agreement|consisten|same request|failure|fail|"
    r"throughput|latency|memory|speedup|tokens per second|"
    r"benchmark|evaluat|baseline|ablation|sweep|sensitivity",
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
