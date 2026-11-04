"""诊断为何某些关键词取不到引文。

## 为什么需要

9 处失败里至少 3 处显然是**文件名/判据问题**而非文本问题：
`--disaggregation-mode` 我在 sglang-pd.txt 里亲眼见过 38 次。
这类「明明有却取不到」的失败最危险：若直接写进论文，
就变成「SGLang 没有明确配置项」这种错误论断。

## 做法

对每个失败项，打印：
  · 文本是否存在、长度
  · 每个关键词在文本中的出现次数
  · 第一个命中位置的扩窗结果（原样，不截断）
  · 该窗口被哪条判据拒绝
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grabber  # noqa: E402

DOCS = HERE / "documents"

CASES = [
    ("doc", "sglang-pd", ["--disaggregation-mode"]),
    ("doc", "nvidia-nixl", ["RDMA", "NVLink", "GPUDirect", "transport"]),
    ("paper", "2403.02310", ["memory-bound", "bandwidth", "decode phase"]),
    ("paper", "2407.00079", ["KV cache transfer", "KV cache", "transfer"]),
    ("paper", "2610.06917", ["elastic", "scale", "in-place"]),
    ("paper", "2404.09526", ["long-context", "long context", "long sequences"]),
    ("paper", "2608.03741", ["pays for itself", "pay", "worth"]),
    ("paper", "2605.28302", ["how far", "design space", "limit"]),
]


def text_of(kind: str, ident: str) -> tuple[str, str]:
    if kind == "doc":
        p = DOCS / f"{ident}.txt"
    else:
        p = DOCS / f"doc-arxiv-{ident.replace('.', '-')}-full.txt"
    if not p.is_file():
        return "", str(p.name)
    return p.read_text(encoding="utf-8", errors="replace"), p.name


def main() -> int:
    for kind, ident, kws in CASES:
        t, name = text_of(kind, ident)
        print(f"\n{'=' * 74}\n{ident}  ({name}, {len(t):,} 字符)")
        if not t:
            print("  [!] 文件不存在")
            continue
        for kw in kws:
            n = t.lower().count(kw.lower())
            print(f"  关键词 {kw!r}: {n} 次")
            if n == 0:
                continue
            pos = t.lower().find(kw.lower())
            w = grabber._window(t, pos)
            print(f"    窗口({len(w)} 字符): {w[:300]!r}")
            if len(w) < 60:
                print("    -> 拒：窗口过短")
            elif not grabber.SUBSTANCE.search(w):
                print("    -> 拒：无实义词")
            elif not grabber.NUMBER.search(w):
                print("    -> 窗口无数字（need_number=True 时会拒）")
            elif not grabber.ok_quote(w, ""):
                print("    -> 拒：ok_quote（FRONT 或长度）")
            else:
                print("    -> 应可通过")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
