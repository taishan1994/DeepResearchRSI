"""把新补的证据挂到对应主张上。

## 为什么要单独一步

补了证据 ≠ 主张引用了它。claim 的 evidence_ids 是显式清单，
新证据若没被挂上去，绑定校验仍然不过——这正是「补了材料但没接线」。

## 边界

只**追加** evidence_id，不删任何既有引用，不改 statement。
追加的理由逐条写在 REBIND 的注释里：这个数字靠哪条新证据支撑。
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build_tables.py"

# claim_id -> 要追加的 evidence_id，及理由
REBIND: dict[str, tuple[str, str]] = {
    # 32K 提示 7,196 / 128K 6,853 都在 prefill 段
    "c-prefill-sgl-8x": ("e-40877-32k",
                         "32K 提示 ≈7,196 tok/s 出自该段"),
    # 325K 前缀缓存命中
    "c-prefill-ceiling": ("e-40877-cachehit-325k",
                          "0.34 s / 112K 前缀 ≈ 325K tok/s 出自该段"),
    # DSpark 三档速率
    "c-decode-dspark": ("e-40877-dspark-table;e-40877-block6",
                        "76.5–78.9 / 120.3–120.5 在分档表，237–252 在 block_size=6 段"),
    # 4 卡并发阶梯
    "c-decode-tp4-conc": ("e-40877-conc-table",
                          "115.2 / 220.6 / 322.2 / 468.2 出自并发表"),
    # 1M 冷预填阶梯
    "c-1m-cold-5min": ("e-40877-cold-ladder",
                       "402,625 / 704,582 / 905,885 / 1,006,538 与 310.5 s 出自阶梯表"),
    # 511 GB 权重
    "c-min-4x96": ("e-q-511gb-again", "「ships roughly 511 GB of weights」"),
    # 196B Engram
    "c-engram-dominates": ("e-report-196b", "「552B backbone plus 196B Engram」"),
    # 盈亏平衡
    "c-selfhost-breakeven": ("e-q-511gb-again", "同源补充上下文"),
    # 2×96 装不下
    "c-no-1m-on-2x96": ("e-q-511gb-again", "511 GB vs 2×96 GB"),
}


def main() -> int:
    s = io.open(BUILD, encoding="utf-8").read()
    changed = 0

    for cid, (extra_ids, why) in REBIND.items():
        # 定位该 claim 的 evidence 字符串
        m = re.search(
            r'(\("' + re.escape(cid) + r'",.*?"(?:spec|measurement|derivation|vendor|report|prediction)",\s*"\w+",\s*")([^"]*)(")',
            s, re.S)
        if not m:
            print(f"  [!] 定位失败：{cid}")
            continue
        cur = m.group(2)
        have = [x.strip() for x in cur.split(";") if x.strip()]
        add = [x.strip() for x in extra_ids.split(";") if x.strip()]
        new = have + [x for x in add if x not in have]
        if new == have:
            print(f"  = {cid}：已含，跳过")
            continue
        s = s[:m.start(2)] + ";".join(new) + s[m.end(2):]
        changed += 1
        print(f"  + {cid}  ← {';'.join(a for a in add if a not in have)}  （{why}）")

    io.open(BUILD, "w", encoding="utf-8").write(s)
    print(f"\n已重绑 {changed} 条主张")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
