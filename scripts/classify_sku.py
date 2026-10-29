"""给 claims.csv 的 sku 列做分类。用法：python scripts/classify_sku.py

规则的核心是**作用域**：一个 SKU 名称只修饰它附近的那个产品名。
这条规则是被四次失败逼出来的，每一版都在修一个具体的误判：

  v1  只看 statement，用功耗（300W/600W）当 SKU 证据
      -> 把「整机功耗」「电源上限」判成了 MQ。改为只用显式 SKU 名称。

  v2  把「产品身份」和「SKU 判定」混在一起，两者都用 statement + 全部证据原文
      -> 「RTX PRO 5000 72GB 版规格……」因其证据顺带提到 PRO 6000 而被判成
         「提到该产品但未写明 SKU」。改为：产品身份只看 statement。

  v3  SKU 名称在全文任意位置都算
      -> 证据里的「RTX PRO 4500 Workstation Edition」让 `c-lora-ddp` 被判成 ws，
         可那是 PRO 4500 的 Workstation 版。改为：只在产品名附近取。

  v4  单一窗口宽度
      -> 60 太宽（「WS<->5090 比值」这种对照标注被当成 SKU），
         42 太窄（「RTX PRO 6000 WS 的 16-pin」里的 WS 紧邻却漏掉）。
         改为双窗口：完整 SKU 名用 60，多义缩写用 12。

用法上的两个纪律：
  1. `unspecified` 是正式取值，不是失败。它表示「来源确实没写」。
     把 unspecified 硬填成某个 SKU 会制造不存在的精度。
  2. RTX 6000D 是中国特供的**独立产品**（削减计算单元、84GB、448-bit），
     不是本产品的第四个 SKU。只提它的主张判 `na`。
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path('research/rtx-pro-6000')

PRODUCT_RE = re.compile(r'RTX\s*PRO\s*6000|PRO\s*6000\b', re.I)
CHINA_D_RE = re.compile(r'RTX\s*6000D|6000D\b', re.I)

# 两级模式：
#   强模式（Workstation Edition / Server Edition / Max-Q）是完整 SKU 名，
#     在 60 字符内即可认为修饰本产品。
#   弱模式（WS 版 / WS 卡 / SE 版 / 单独的 SE）是多义缩写，
#     档案里也用作「Workstation 侧」的对照标注，故要求极近（12 字符）。
STRONG_WINDOW = 60
WEAK_WINDOW = 12

# 档案里的 WS 写法有四种：Workstation Edition / Blackwell Workstation /
# Workstation 上的 / 工作站版。都算强模式，但只在产品名附近才生效。
WS_STRONG = re.compile(r'Workstation\s*Edition|Blackwell\s+Workstation|Workstation\s*上的|Workstation\s*版|工作站版', re.I)
# 排除「Pro WS WRX90E」「vWS」这类把 WS 用作型号片段或产品名的情况。
WS_WEAK = re.compile(r'(?<![A-Za-z])(?<!Pro )(?<!v)WS(?![A-Za-z0-9])', re.I)
MQ_STRONG = re.compile(r'Max-?Q', re.I)
MQ_WEAK = re.compile(r'(?<![A-Za-z])MQ(?![A-Za-z])')
SE_STRONG = re.compile(r'Server\s*Edition|Server\s*版', re.I)
SE_WEAK = re.compile(r'(?<![A-Za-z])SE(?![A-Za-z0-9])', re.I)

ALL_PAT = re.compile(
    r'三(?:个|款)\s*(?:SKU|版本|卡)|全部\s*SKU|所有\s*SKU|三个版本|三款\s*RTX\s*PRO\s*6000', re.I)


def windows(text: str, width: int) -> str:
    spans = [(m.start(), m.end()) for m in PRODUCT_RE.finditer(text)]
    if not spans:
        return ''
    return ' || '.join(text[max(0, a - width): min(len(text), b + width)]
                       for a, b in spans)


def classify(statement: str, evidence_text: str) -> tuple[str, str]:
    if not PRODUCT_RE.search(statement):
        if CHINA_D_RE.search(statement):
            return 'na', 'RTX 6000D 是独立产品'
        return 'na', '陈述未提及该产品'

    blob = statement + ' ' + evidence_text
    wide = windows(blob, STRONG_WINDOW)
    narrow = windows(blob, WEAK_WINDOW)
    if not wide:
        return 'unspecified', '无邻近上下文'

    if ALL_PAT.search(wide):
        return 'all', '显式说三个 SKU'

    hits = []
    if WS_STRONG.search(wide) or WS_WEAK.search(narrow):
        hits.append('ws')
    if MQ_STRONG.search(wide) or MQ_WEAK.search(narrow):
        hits.append('mq')
    if SE_STRONG.search(wide) or SE_WEAK.search(narrow):
        hits.append('se')

    if not hits:
        return 'unspecified', '邻近窗口内无 SKU 名称'
    if len(hits) == 1:
        return hits[0], '单一 SKU 名称'
    return '+'.join(sorted(hits)), '多个 SKU 名称'


def main() -> int:
    p = ROOT / 'claims.csv'
    with p.open(encoding='utf-8-sig', newline='') as fh:
        r = csv.reader(fh)
        header = next(r)
        rows = [x for x in r if x]
    assert len(header) == 10, header

    i_cid = header.index('claim_id')
    i_stmt = header.index('statement')
    i_sku = header.index('sku')
    i_ev = header.index('evidence_ids')
    i_der = header.index('derivation')
    i_note = header.index('notes')

    ev = {e['evidence_id']: e['quote'] for e in csv.DictReader(
        (ROOT / 'evidence.csv').open(encoding='utf-8-sig'))}

    old = {r[i_cid]: r[i_sku] for r in rows}
    dist: Counter[str] = Counter()
    changes = []

    for row in rows:
        extra = ''
        for eid in (row[i_ev] or '').split(';'):
            eid = eid.strip()
            if eid in ev:
                extra += ' ' + ev[eid]
        if row[i_der]:
            extra += ' ' + row[i_der]
        if row[i_note]:
            extra += ' ' + row[i_note]

        sku, why = classify(row[i_stmt], extra)
        row[i_sku] = sku
        dist[sku] += 1
        if old[row[i_cid]] != sku:
            changes.append((row[i_cid], old[row[i_cid]], sku, why, row[i_stmt][:66]))

    with p.open('w', encoding='utf-8-sig', newline='\n') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator='\n')
        w.writerow(header)
        for row in rows:
            w.writerow(row)

    print(f'总计 {len(rows)} 条，变更 {len(changes)} 条\n')
    for k, v in dist.most_common():
        print(f'  {k:<14} {v:>5}')
    print('\n变更明细：')
    for cid, a, b, why, st in changes:
        print(f'  {cid:<46} {a:<12} -> {b:<12} {why}')
        print(f'      {st}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
