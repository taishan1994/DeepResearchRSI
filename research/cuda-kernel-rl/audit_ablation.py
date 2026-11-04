"""在全文里查证「上一轮论文的头号空白」：中间奖励到底有没有被消融。

## 起因

上一轮（只读摘要）的论文里我写了这样一句：

    「没有任何工作报告『加了中间奖励之后，最终加速比是否真的提高』
      的对照实验。」

然后把它列为「本方向最重要的空白」。

**这是把自己的无知写成了别人的缺陷。** 摘要不报消融，不等于正文没做。

## 本轮做法

在 12 篇全文里搜三类证据：
  A. 出现 ablation 章节 / 表格
  B. 出现 w/o、without、remove 等消融标记
  C. 中间奖励各组件（HRD / profiling / PRS / 结构化奖励）的开关对照

逐篇统计命中，并把命中的上下文打出来供人工判读——
统计只能定位，不能代替阅读。

## 输出

`ablation_audit.json`：逐篇的命中情况与原文片段。
论文的第 5、6 节将据它改写。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"

# 消融的典型表达。中英文都要覆盖：这些论文是英文，但表格标题可能是缩写。
ABLATION_PAT = re.compile(
    r"\b(ablation|ablate|ablated)\b"
    r"|\bw/o\b|\bwithout\b|\bremove[sd]?\b|\bdisable[sd]?\b"
    r"|\bvanilla\b|\bbaseline variant\b"
    r"|\bcomponent analysis\b|\bimportance of\b",
    re.I,
)

# 中间奖励的组件名：这些词出现在消融句附近，说明消融的是奖励而非超参
REWARD_COMPONENT_PAT = re.compile(
    r"\b(HRD|hierarchical reward|profiling[- ]based|PRS|progressive reward"
    r"|structural reward|decompos\w*|reward decompos\w*|curriculum"
    r"|rejection sampling|compaction)\b",
    re.I,
)

# 结果量纲：消融若报告了效果，附近应有速度/正确性数字
METRIC_PAT = re.compile(r"\d+\.?\d*\s*(?:x|×|%|percent)", re.I)


def snippets(text: str, pat: re.Pattern, *, window: int = 260,
             limit: int = 6) -> list[str]:
    out: list[str] = []
    for m in pat.finditer(text):
        s = max(0, m.start() - window // 2)
        e = min(len(text), m.end() + window // 2)
        frag = " ".join(text[s:e].split())
        out.append(frag)
        if len(out) >= limit:
            break
    return out


def main() -> int:
    files = sorted(DOCS.glob("*-full.txt"))
    if not files:
        print("没有全文快照，先跑 fetch_fulltext.py")
        return 1

    report: dict[str, dict] = {}
    for f in files:
        aid = f.stem.replace("doc-arxiv-", "").replace("-full", "")
        aid = re.sub(r"^(\d{4})-(\d{4,5})$", r"\1.\2", aid)
        text = f.read_text(encoding="utf-8", errors="replace")

        abl = list(ABLATION_PAT.finditer(text))
        # 只有「消融」与「奖励组件」同时出现在一个窗口内，才算与奖励有关
        reward_abl = 0
        for m in abl:
            s = max(0, m.start() - 300)
            e = min(len(text), m.end() + 300)
            if REWARD_COMPONENT_PAT.search(text[s:e]):
                reward_abl += 1

        # 是否有明确的 Table 标题带 ablation
        tab_abl = len(re.findall(
            r"(?:Table|TABLE)\s*\d+[^\n]{0,90}(?:ablation|Ablation)", text))
        # 是否有「加/去某组件」的对照数字
        onoff = len(re.findall(
            r"(?:w/o|without|w\.o\.|remove)\s+[\w\- ]{2,30}"
            r"[^.]{0,120}?\d+\.?\d*\s*(?:x|×|%)", text, re.I))

        report[aid] = {
            "chars": len(text),
            "ablation_mentions": len(abl),
            "reward_ablation_mentions": reward_abl,
            "ablation_table_titles": tab_abl,
            "onoff_with_numbers": onoff,
            "has_ablation_section": bool(re.search(
                r"\bAblation\b", text)),
            "samples": snippets(text, ABLATION_PAT, limit=3),
        }

    OUT = HERE / "ablation_audit.json"
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    print(f"{'arxiv':<11} {'字符':>8} {'消融':>5} {'奖励相关':>8} "
          f"{'表标题':>6} {'带数字':>6}")
    print("-" * 56)
    n_with = 0
    for aid, r in sorted(report.items()):
        print(f"{aid:<11} {r['chars']:>8,} {r['ablation_mentions']:>5} "
              f"{r['reward_ablation_mentions']:>8} "
              f"{r['ablation_table_titles']:>6} {r['onoff_with_numbers']:>6}")
        if r["reward_ablation_mentions"] or r["onoff_with_numbers"]:
            n_with += 1

    print(f"\n有奖励相关消融迹象的论文：{n_with}/{len(report)}")
    print(f"明细写入 {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
