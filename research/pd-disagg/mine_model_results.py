"""挖「按模型族」的实测结果：模型名 + 分离动作 + 数字，同句。

## 为什么再挖一轮

第 1 轮建证据时按 5 个维度各抓 4-7 条，`model` 维度只有 5 条，
每类模型 1 条。而用户要的核心是「不同模型的最佳实践（最好的效果）」——
只有「做法」没有「效果」，回答不了「最好的」。

44 篇全文里，Llama 出现 34 篇、Qwen 26 篇、DeepSeek 26 篇。
这些论文必然报告了具体模型上的数字，只是第 1 轮的 anchor 关键词
（「expert sharing」之类抽象表述）没覆盖到。

## 判据

一句话要同时命中三样才收：
  ① 一个模型族名（Llama / Qwen / DeepSeek / Mixtral / ...）
  ② 一个分离或阶段词（prefill / decode / disaggregat / split / chunk）
  ③ 一个带单位的数字（×、x faster、GB/s、ms、tokens/s、%）

## 为什么要 ③

只命中 ①② 的句子多是「我们在 Llama-70B 上评测」这类陈述，
不含效果。加 ③ 才留下真正报告结果的句子。

## 与 grabber.py 的关系

grabber 用「关键词锚点扩窗」，适合按主题找定性表述。
本脚本用「三类硬条件同句」，适合按模型找定量结果。
两者互补，不互相替代。
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

MODELS = {
    "Llama": r"Llama[\s\-]?\d?(?:\.\d)?",
    "Qwen": r"Qwen[\d\.\-]*",
    "DeepSeek": r"DeepSeek[\w\.\-]*",
    "Mixtral": r"Mixtral[\w\.\-]*",
    "Mistral": r"Mistral[\w\.\-]*",
    "Gemma": r"Gemma[\w\.\-]*",
    "Yi": r"Yi[\-\s]?\d+B",
    "Phi": r"Phi[\-\s]?\d",
    "OPT": r"OPT[\-\s]?\d+B",
    "LLaVA": r"LLaVA[\w\.\-]*",
    "InternVL": r"InternVL[\w\.\-]*",
    "GPT": r"GPT[\-\s]?\d",
}

PHASE = re.compile(
    r"(prefill|pre-fill|decode|disagg|dis-aggreg|phase split|"
    r"chunked|separate (?:the )?(?:two )?phas)", re.I)

# 带单位的数字：3.2x / 2.1 × / 15.3 GB/s / 12 ms / 1,200 tokens/s / 45%
NUM = re.compile(
    r"(\d+(?:[.,]\d+)?\s*(?:×|x\b|X\b|GB/s|Gbps|MB/s|ms\b|us\b|µs|s\b|%|"
    r"tokens?/s|tok/s|TPS|RPS|req/s))")


def sentences(text: str) -> list[str]:
    # 先按段落切，再按句号切：PDF 转文本后常有断行，
    # 直接按 \n 切会把一句话拆散。
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        flat = " ".join(para.split())
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", flat):
            if 40 <= len(s) <= 700:
                out.append(s)
    return out


def main() -> int:
    hits: dict[str, list[dict[str, str]]] = defaultdict(list)
    n_sent = 0

    for p in sorted(DOCS.glob("*-full.txt")):
        text = p.read_text(encoding="utf-8", errors="replace")
        # 跳过参考文献段：那里模型名与年份密度高、但没有实测结果
        cut = re.search(r"\n\s*References\s*\n", text)
        if cut:
            text = text[:cut.start()]
        for s in sentences(text):
            n_sent += 1
            if not PHASE.search(s):
                continue
            nums = NUM.findall(s)
            if not nums:
                continue
            for fam, pat in MODELS.items():
                m = re.search(pat, s)
                if not m:
                    continue
                hits[fam].append({
                    "source": p.name.replace("-full.txt", ""),
                    "model": m.group(0).strip(),
                    "numbers": nums[:4],
                    "sentence": s,
                })

    print(f"扫描 {n_sent:,} 句，命中 {sum(len(v) for v in hits.values())} 条")
    print()
    for fam in sorted(hits, key=lambda k: -len(hits[k])):
        rows = hits[fam]
        # 同一 source 只留最长的两条，避免单篇论文刷屏
        by_src: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_src[r["source"]].append(r)
        keep = []
        for src, rs in by_src.items():
            rs.sort(key=lambda r: -len(r["sentence"]))
            keep.extend(rs[:2])
        print(f"=== {fam}（{len(rows)} 条，展示 {len(keep)}）===")
        for r in keep[:6]:
            print(f"  [{r['model']}] {r['source']}")
            print(f"    {r['sentence'][:190]}")
        print()

    out = {k: v for k, v in hits.items()}
    (HERE / "model_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print("-> model_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
