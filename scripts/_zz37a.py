"""按来源的证据密度审计。

问的不是「每个来源有没有证据」，而是「哪一类来源被读得最浅」。

依据：sources.csv 的 source_type 与 title 里的体量线索，
加上 evidence.csv 的条数。
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

root = Path('research/rtx-pro-6000')
S = list(csv.DictReader((root / 'sources.csv').open(encoding='utf-8-sig')))
E = list(csv.DictReader((root / 'evidence.csv').open(encoding='utf-8-sig')))
C = list(csv.DictReader((root / 'claims.csv').open(encoding='utf-8-sig')))

per = Counter(e['source_id'] for e in E)

# 每个来源被多少条主张引用（经由 evidence）
ev2src = {e['evidence_id']: e['source_id'] for e in E}
cited = Counter()
for c in C:
    for eid in (c['evidence_ids'] or '').split(';'):
        eid = eid.strip()
        if eid in ev2src:
            cited[ev2src[eid]] += 1

print('=' * 78)
print('一、按 source_type 的证据密度')
print('=' * 78)
by_type = defaultdict(list)
for s in S:
    by_type[s['source_type']].append(per.get(s['source_id'], 0))

print('%-18s %6s %8s %8s %8s %8s' % ('source_type', '来源数', '证据数', '均值', '中位', '零证据'))
print('-' * 78)
rows = []
for t, v in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
    v2 = sorted(v)
    n = len(v2)
    med = v2[n // 2] if n % 2 else (v2[n // 2 - 1] + v2[n // 2]) / 2
    zero = sum(1 for x in v2 if x == 0)
    rows.append((t, n, sum(v2), sum(v2) / n, med, zero))
    print('%-18s %6d %8d %8.2f %8.1f %8d' % (t, n, sum(v2), sum(v2) / n, med, zero))

print()
print('=' * 78)
print('二、证据最少的 20 个来源（排除零证据）')
print('=' * 78)
low = sorted([s for s in S if per.get(s['source_id'], 0) > 0],
             key=lambda s: (per.get(s['source_id'], 0), s['source_id']))[:20]
print('%-42s %6s %-18s' % ('source_id', '证据', 'source_type'))
print('-' * 78)
for s in low:
    print('%-42s %6d %-18s' % (s['source_id'][:42], per[s['source_id']], s['source_type']))

print()
print('=' * 78)
print('三、只有一个证据的来源，按类型分布')
print('=' * 78)
single = [s for s in S if per.get(s['source_id'], 0) == 1]
print('单证据来源总数:', len(single))
print('类型分布:', dict(Counter(s['source_type'] for s in single)))
print()
print('样本（前 25 个）:')
for s in single[:25]:
    print('  %-44s %s' % (s['source_id'][:44], s['title'][:52]))

print()
print('=' * 78)
print('四、标题里带「亚文化/论坛/帖」标记的来源，证据密度是否更低')
print('=' * 78)
thread = [s for s in S if re.search(r'帖|thread|forum|discussion|reddit|hn|news\.ycombinator',
                                    s['title'] + s['url'], re.I)]
other = [s for s in S if s not in thread]
tm = [per.get(s['source_id'], 0) for s in thread]
om = [per.get(s['source_id'], 0) for s in other]
print('论坛/帖类:   %3d 个，证据共 %4d，均值 %.2f' % (len(tm), sum(tm), sum(tm) / max(1, len(tm))))
print('其余来源:    %3d 个，证据共 %4d，均值 %.2f' % (len(om), sum(om), sum(om) / max(1, len(om))))
print()
print('单证据比例：')
print('  论坛/帖类: %.1f%%' % (100 * sum(1 for x in tm if x == 1) / max(1, len(tm))))
print('  其余来源:  %.1f%%' % (100 * sum(1 for x in om if x == 1) / max(1, len(om))))

print()
print('=' * 78)
print('五、被主张引用次数为 0 但证据 > 0 的来源')
print('=' * 78)
unused = [s for s in S if per.get(s['source_id'], 0) > 0 and cited.get(s['source_id'], 0) == 0]
print('数量:', len(unused))
for s in unused[:20]:
    print('  %-44s 证据%d 被引0  %s' % (s['source_id'][:44], per[s['source_id']],
                                        s['title'][:44]))
