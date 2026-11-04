"""直接测 find_quotes：打印每个失败项的实际候选。

## 为什么之前的诊断误导了我

diag_grab.py 直接调 `grabber.SUBSTANCE` / `NUMBER` / `ok_quote` 判断，
但 v2 的通过条件在 `find_quotes` **内部**（用 REGIME、CONFIG、_title_like），
诊断脚本没反映这些。于是它说「拒：无实义词」，而 find_quotes 其实会跳过
标题继续找下一条——两边的结论不一致，我据此改错了两轮。

教训：诊断必须调用**真正的判定函数**，不能复制一份近似逻辑。
复制出来的那条路会随时间漂移，然后骗人。

## 本脚本的做法

只调 find_quotes，打印：
  · 各关键词命中次数
  · find_quotes 返回的前 2 条候选原文
  · 若为空，逐关键词打印第一个窗口 + 它在 find_quotes 里的三道闸门结果
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grabber  # noqa: E402

DOCS = HERE / "documents"

# (kind, id, keywords, need_number, title)  —— 与 build_pd.py 一致
CASES = [
    ("paper", "2407.00079", ["bottleneck", "both prefill and decode",
                             "prefill and decode"], False,
     "Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving"),
    ("paper", "2407.00079", ["KV cache transfer", "KV cache", "transfer"],
     True, "Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving"),
    ("paper", "2610.06917", ["elastic", "scale", "in-place"], True,
     "FluidPD: In-Place Elasticity for SLO-Aware Prefill-Decode Disaggregated LLM Serving"),
    ("paper", "2404.09526", ["long-context", "long context", "long sequences"],
     True, "LoongServe: Efficiently Serving Long-context Large Language Models with Elastic Sequence Parallelism"),
    ("paper", "2608.03741", ["pays for itself", "pay", "worth"], True,
     "When Does Disaggregation Pay? Simulating Prefill-Decode-Attention-FFN Disaggregation"),
    ("paper", "2605.28302", ["how far", "design space", "limit"], True,
     "How Far Can Disaggregation Go?"),
    ("doc", "nvidia-nixl", ["abstraction over various types of memory",
                            "point to point communications",
                            "plug-in architecture"], False, ""),
]


def text_of(kind: str, ident: str) -> str:
    p = (DOCS / f"{ident}.txt" if kind == "doc"
         else DOCS / f"doc-arxiv-{ident.replace('.', '-')}-full.txt")
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def main() -> int:
    for kind, ident, kws, need, title in CASES:
        t = text_of(kind, ident)
        print(f"\n{'=' * 76}\n{ident}  need_number={need}")
        print(f"  标题: {title[:66]}")
        for kw in kws:
            print(f"  关键词 {kw!r}: {len(__import__('re').findall(kw, t, __import__('re').I))} 次")

        got = grabber.find_quotes(t, kws, need_number=need, title=title)
        print(f"  find_quotes 返回 {len(got)} 条")
        for q in got[:2]:
            print(f"    >> {q[:240]}")

        if not got:
            # 逐关键词看第一道闸门
            import re
            for kw in kws:
                m = re.search(kw, t, re.I)
                if not m:
                    continue
                w = grabber._window(t, m.start())
                print(f"    [{kw}] 窗口 {len(w)} 字符：{w[:200]!r}")
                print(f"         长度>=60: {len(w) >= 60}"
                      f"  标题化: {grabber._title_like(w, title)}"
                      f"  实义/配置: {bool(grabber.SUBSTANCE.search(w) or grabber.CONFIG.search(w))}"
                      f"  数字: {bool(grabber.NUMBER.search(w))}"
                      f"  受限型: {bool(grabber.REGIME.search(w))}"
                      f"  FRONT: {bool(grabber.FRONT.search(w))}")
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
