"""一次性维护脚本：把正文里的计数同步到 analysis.json 的当前值。

## 为什么需要它

计数会随证据/主张的增补而变（本轮从 73/31 增到 81/33），而正文里
散落着十几处硬编码的数字。手工改必然漏——`check_numbers.py` 就是
为抓这种漏而写的，但它只查「关键几处」。

本脚本把**已知会漂移的那几处**按数据重写，跑完再跑 `check_numbers.py` 确认。

## 边界

它不试图重写整篇文章（做不到），只处理带有明确模板的句子。
匹配不上就报出原文，让人工决定——**不做模糊替换**。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ana = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    c = ana["counts"]
    layer = ana["evidence_by_layer"]

    p = HERE / "REPORT.md"
    s = p.read_text(encoding="utf-8")
    orig = s

    # (正则, 替换模板) —— 每条都锚定唯一模板，命中数必须为 1
    rules: list[tuple[str, str]] = [
        (r"> 来源数：3（论文 / 仓库 / 项目页）｜ 证据数：\d+ ｜ 主张数：\d+（\d+ 高置信 / \d+ 争议）",
         f"> 来源数：3（论文 / 仓库 / 项目页）｜ 证据数：{c['evidence']} ｜ "
         f"主张数：{c['claims']}（{c['claims_high']} 高置信 / {c['claims_disputed']} 争议）"),
        (r"1\. \*\*E1（原文子串）\*\*：\d+ 条 quote 全部由 `build_specpilot\.py` 的 `grab\(\)` 从快照实取，"
         r"不是手写。校验器逐条比对，结果 `e1_checked=\d+, e1_unverifiable=0`。",
         f"1. **E1（原文子串）**：{c['evidence']} 条 quote 全部由 `build_specpilot.py` 的 `grab()` "
         f"从快照实取，不是手写。校验器逐条比对，结果 "
         f"`e1_checked={c['evidence']}, e1_unverifiable=0`。"),
        (r"2\. \*\*引用闭合\*\*：\d+ 条主张引用的证据全部存在，且 \d+ 条证据\*\*没有一条零引用\*\*（`evidence_dangling=\[\]`）。",
         f"2. **引用闭合**：{c['claims']} 条主张引用的证据全部存在，且 {c['evidence']} "
         f"条证据**没有一条零引用**（`evidence_dangling=[]`）。"),
        (r"\*\*为什么仓库只值 3 个来源、却给了 \d+ 条证据里的 \d+ 条\*\*（paper \d+ / code \d+ / page \d+，"
         r"见 `analysis\.json` 的 `evidence_by_layer`）",
         f"**为什么仓库只值 3 个来源、却给了 {c['evidence']} 条证据里的 {layer['code']} 条**"
         f"（paper {layer['paper']} / code {layer['code']} / page {layer['page']}，"
         f"见 `analysis.json` 的 `evidence_by_layer`）"),
        (r"\| E1 原文子串 \| `e1_checked=\d+`、`e1_unverifiable=0` \|",
         f"| E1 原文子串 | `e1_checked={c['evidence']}`、`e1_unverifiable=0` |"),
        (r"\| 证据零悬空 \| `evidence_dangling=\[\]`（\d+/\d+ 被引用） \|",
         f"| 证据零悬空 | `evidence_dangling=[]`（{c['evidence']}/{c['evidence']} 被引用） |"),
        (r"  documents\.csv +\d+ 份快照（含 content_hash 与 byte_size）",
         f"  documents.csv                 {c['documents']} 份快照（含 content_hash 与 byte_size）"),
        (r"  evidence\.csv +\d+ 条，十维标注",
         f"  evidence.csv                  {c['evidence']} 条，十维标注"),
        (r"  claims\.csv +\d+ 条（\d+ 高置信 / \d+ 中 / \d+ 争议），\d+ 条证据零悬空",
         f"  claims.csv                    {c['claims']} 条（{c['claims_high']} 高置信 / "
         f"{c['claims_medium']} 中 / {c['claims_disputed']} 争议），{c['evidence']} 条证据零悬空"),
        (r"\(sources=3, evidence=\d+, claims=\d+, claims_high=\d+, claims_disputed=\d+, "
         r"c1_violations=0, e1_unverifiable=0\)",
         f"(sources={c['sources']}, evidence={c['evidence']}, claims={c['claims']}, "
         f"claims_high={c['claims_high']}, claims_disputed={c['claims_disputed']}, "
         f"c1_violations=0, e1_unverifiable=0)"),
    ]

    bad = 0
    for pat, rep in rules:
        s, n = re.subn(pat, rep, s)
        if n != 1:
            bad += 1
            print(f"[!] 命中 {n} 次（期望 1）：{pat[:70]}")

    if s != orig:
        p.write_text(s, encoding="utf-8", newline="\n")
        print(f"已重写 REPORT.md（{len(rules) - bad}/{len(rules)} 条规则生效）")
    else:
        print("无需改动")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
