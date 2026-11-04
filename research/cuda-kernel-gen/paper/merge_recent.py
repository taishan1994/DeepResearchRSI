"""把 2026-07 之后的 40 篇并入主论文库，扩展到 98 篇。

⚠️ 为什么必须并入而不只是「加一句补充说明」：
   本综述的论点是**基于统计**的（「50 条声明中只有 16% 可比」）。
   若时间窗停在 2026-06 而撰写于 2026-11，这个统计就有一个
   5 个月的盲区——恰好是领域变动最快的 5 个月。
   补进去之后，「最新进展」这个要求才真正成立。
"""

from __future__ import annotations

import json
from pathlib import Path

D = Path(__file__).resolve().parent

old = json.loads((D / 'papers.json').read_text(encoding='utf-8'))
new = json.loads((D / 'recent_2026h2.json').read_text(encoding='utf-8'))

# 统一 id 形态（去掉版本号后缀）
def norm(p):
    p = dict(p)
    p['id'] = p['id'].split('v')[0]
    if 'authors' not in p:
        p['authors'] = []
    if 'updated' not in p:
        p['updated'] = p['published']
    return p

merged = {}
for p in old:
    q = norm(p)
    merged[q['id']] = q
before = len(merged)
for p in new:
    q = norm(p)
    merged.setdefault(q['id'], q)

items = sorted(merged.values(), key=lambda x: x['published'])
(D / 'papers.json').write_text(
    json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'原 {before} 篇，新增 {len(merged) - before} 篇，合计 {len(items)} 篇')

by_month: dict[str, int] = {}
for p in items:
    by_month[p['published'][:7]] = by_month.get(p['published'][:7], 0) + 1
for m in sorted(by_month):
    print(f'  {m}: {by_month[m]:2d} {"#" * by_month[m]}')
