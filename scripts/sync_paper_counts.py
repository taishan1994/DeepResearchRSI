"""把论文正文里的自述数字与档案同步。

为什么它是常驻脚本而不是一次性的：`check_paper.py` 的 I5 已经从四个不同轮次
抓出同一个错误——「本文引用的 N 条主张」这类描述在每加一节后都会过期。
四轮连续复发说明它是**结构性的**，不是偶发疏忽，故把修法也固化下来。

它做三件事：
  1. 「本文引用的 N 条主张」-> 实际唯一引用数
  2. 「有 N 条是 unspecified」-> 实际数
  3. 重写 1.1.4 的欠账清单表，并同步 data/tab4_sku_debt.csv

用法：
    python scripts/sync_paper_counts.py
    python scripts/sync_paper_counts.py --check   # 只报告，不写文件
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path('research/rtx-pro-6000')
PAPER = ROOT / 'paper' / 'PAPER.md'
D = ROOT / 'paper' / 'data'

TABLE_HEAD = '| claim_id | claim_type | sku | 陈述摘要 |'
TABLE_SEP = '|---|---|---|---|'
TABLE_RE = re.compile(
    r'\| claim_id \| claim_type \| sku \| 陈述摘要 \|\n\|[-|]+\|\n(?:\|.*\n)+')


def compute(text: str) -> tuple[int, list[str], dict]:
    cl = {c['claim_id']: c for c in csv.DictReader(
        (ROOT / 'claims.csv').open(encoding='utf-8-sig'))}
    cited = sorted(set(re.findall(r'\[(c-[A-Za-z0-9_-]+)\]', text)))
    uns = [c for c in cited if c in cl and cl[c]['sku'] == 'unspecified']
    return len(cited), uns, cl


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='同步论文自述数字')
    ap.add_argument('--check', action='store_true', help='只报告不写')
    args = ap.parse_args(argv)

    t = PAPER.read_text(encoding='utf-8')
    uniq, uns, cl = compute(t)
    print(f'唯一主张 {uniq}，其中 unspecified {len(uns)}')

    t2 = re.sub(r'本文引用的 \d+ 条主张', f'本文引用的 {uniq} 条主张', t)
    t2 = re.sub(r'有 \*\*\d+ 条是 `unspecified`\*\*',
                f'有 **{len(uns)} 条是 `unspecified`**', t2)
    t2 = re.sub(r'这 \d+ 条不是「没查」', f'这 {len(uns)} 条不是「没查」', t2)

    # 重写欠账清单
    rows = ['claim_id,claim_type,sku,陈述摘要']
    md = [TABLE_HEAD, TABLE_SEP]
    for cid in uns:
        st = cl[cid]['statement'].replace(',', '；').replace('\n', ' ')[:58]
        rows.append(f"{cid},{cl[cid]['claim_type']},unspecified,{st}")
        md.append(f'| {cid} | {cl[cid]["claim_type"]} | unspecified | {st} |')

    m = TABLE_RE.search(t2)
    if m:
        t2 = t2[:m.start()] + '\n'.join(md) + '\n' + t2[m.end():]
    else:
        print('[WARN] 找不到欠账清单表体，跳过表格重写')

    changed = t2 != t
    if args.check:
        print('需要更新' if changed else '已是最新')
        return 1 if changed else 0

    if not changed:
        print('已是最新，未写文件')
        return 0

    csv_text = '\n'.join(rows) + '\n'
    assert '\ufffd' not in csv_text
    (D / 'tab4_sku_debt.csv').write_text(csv_text, encoding='utf-8', newline='\n')

    assert '\ufffd' not in t2
    PAPER.write_text(t2, encoding='utf-8', newline='\n')
    print(f'已同步，PAPER.md {len(t2)} 字符（原 {len(t)}）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
