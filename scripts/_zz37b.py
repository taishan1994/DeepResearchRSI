"""证据密度必须用「体量」做分母，而不是用「来源」做分母。

上一版脚本（_zz37a.py）的指标是「每个来源几条证据」，
它把 156 字节的 .cuh 与 60,100 字节的 .py 当成同一个单位。
本脚本从 title 里解析字节数，重算「每 10 KB 几条证据」。
"""
import csv
import re
from collections import Counter
from pathlib import Path

root = Path('research/rtx-pro-6000')
S = list(csv.DictReader((root / 'sources.csv').open(encoding='utf-8-sig')))
E = list(csv.DictReader((root / 'evidence.csv').open(encoding='utf-8-sig')))

per = Counter(e['source_id'] for e in E)

# title 里的体量线索：'（7,070 字节）' / '（8,998 字节，238 行）' / '（60,100 字节）'
BYTES = re.compile(r'([\d,]{3,})\s*字节')
LINES = re.compile(r'(\d[\d,]*)\s*行')

rows = []
for s in S:
    n = per.get(s['source_id'], 0)
    m = BYTES.search(s['title'])
    if not m:
        continue
    b = int(m.group(1).replace(',', ''))
    if b <= 0:
        continue
    rows.append((s['source_id'], s['source_type'], b, n, s['title']))

print('=' * 80)
print('一、能解析出字节数的来源共 %d 个（占 %d 的 %.1f%%）'
      % (len(rows), len(S), 100 * len(rows) / len(S)))
print('=' * 80)

# 按字节区间分组
buckets = [
    ('< 1 KB', 0, 1024),
    ('1 - 4 KB', 1024, 4096),
    ('4 - 16 KB', 4096, 16384),
    ('16 - 64 KB', 16384, 65536),
    ('64 KB - 256 KB', 65536, 262144),
    ('>= 256 KB', 262144, 10 ** 12),
]
print('%-16s %6s %9s %10s %14s' % ('字节区间', '文件数', '证据数', '每 10KB 证据', '平均每条证据覆盖'))
print('-' * 80)
for label, lo, hi in buckets:
    sub = [r for r in rows if lo <= r[2] < hi]
    if not sub:
        continue
    nb = sum(r[2] for r in sub)
    ne = sum(r[3] for r in sub)
    per10k = ne / (nb / 10240) if nb else 0
    cover = (nb / ne) if ne else 0
    print('%-16s %6d %9d %10.3f %13.0f B' % (label, len(sub), ne, per10k, cover))

print()
print('=' * 80)
print('二、被读得最浅的 15 个大文件（>= 16 KB，按每 10KB 证据数升序）')
print('=' * 80)
big = sorted([r for r in rows if r[2] >= 16384],
             key=lambda r: (r[3] / (r[2] / 10240), -r[2]))
print('%-40s %9s %5s %10s' % ('source_id', '字节', '证据', '每10KB'))
print('-' * 80)
for r in big[:15]:
    print('%-40s %9d %5d %10.3f'
          % (r[0][:40], r[2], r[3], r[3] / (r[2] / 10240)))

print()
print('=' * 80)
print('三、同样算法下，被读得最深的 10 个（>= 16 KB）')
print('=' * 80)
print('%-40s %9s %5s %10s' % ('source_id', '字节', '证据', '每10KB'))
print('-' * 80)
for r in reversed(big[-10:]):
    print('%-40s %9d %5d %10.3f'
          % (r[0][:40], r[2], r[3], r[3] / (r[2] / 10240)))

print()
print('=' * 80)
print('四、结论：分母换了，排名就换了')
print('=' * 80)
smallest = sorted(rows, key=lambda r: r[2])[:6]
print('按「每个来源证据数」排，垫底的是这些（体量都很小）：')
for r in smallest:
    print('  %-38s %6d B  证据%d' % (r[0][:38], r[2], r[3]))
print()
print('按「每 10KB 证据数」排，垫底的是这些（体量都很大）：')
for r in big[:6]:
    print('  %-38s %6d B  证据%d  每10KB %.3f'
          % (r[0][:38], r[2], r[3], r[3] / (r[2] / 10240)))
print()
overlap = {r[0] for r in smallest} & {r[0] for r in big[:6]}
print('两个榜单的交集大小:', len(overlap), overlap or '（空）')
