"""检索 2026-07 之后的新论文，补齐综述的时间缺口。

⚠️ 背景：初版论文覆盖到 2026-06，但撰写时间是 2026-11。
   对「最新进展」这类要求，5 个月的空白是实质缺陷，不是小节。
   本脚本用 arXiv 的**全文检索**（search_query）而非 id_list，
   以发现尚未进入任何索引的新工作。

检索式设计：
  abs:"CUDA kernel" AND abs:(generat OR optimiz)  -> 生成与优化
  再按 submittedDate 限定 202607010000 TO 202611302359
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

D = Path(__file__).resolve().parent
NS = {'a': 'http://www.w3.org/2005/Atom'}

QUERIES = [
    'abs:"CUDA kernel" AND abs:generat',
    'abs:"GPU kernel" AND abs:(generat OR optimiz)',
    'abs:KernelBench',
    'abs:"kernel generation" AND abs:LLM',
    'abs:(Triton OR CUDA) AND abs:"reinforcement learning" AND abs:kernel',
]

DATE = 'submittedDate:[202607010000 TO 202611302359]'


def search(q: str, maxr: int = 100) -> list[dict]:
    full = f'({q}) AND {DATE}'
    url = ('http://export.arxiv.org/api/query?search_query='
           + urllib.parse.quote(full)
           + f'&start=0&max_results={maxr}&sortBy=submittedDate&sortOrder=descending')
    req = urllib.request.Request(url, headers={'User-Agent': 'survey-gap/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode('utf-8', 'replace')
    root = ET.fromstring(raw)
    out = []
    for e in root.findall('a:entry', NS):
        aid = e.find('a:id', NS).text.rsplit('/', 1)[-1]
        out.append({
            'id': aid.split('v')[0],
            'title': ' '.join((e.find('a:title', NS).text or '').split()),
            'published': (e.find('a:published', NS).text or '')[:10],
            'abstract': ' '.join((e.find('a:summary', NS).text or '').split()),
            'arxiv_url': 'https://arxiv.org/abs/' + aid.split('v')[0],
        })
    return out


def main() -> int:
    seen: dict[str, dict] = {}
    for q in QUERIES:
        print(f'检索: {q}')
        try:
            res = search(q)
            new = sum(1 for r in res if r['id'] not in seen)
            for r in res:
                seen.setdefault(r['id'], r)
            print(f'  返回 {len(res)} 篇，新增 {new}')
        except Exception as e:
            print(f'  失败: {e}')
        time.sleep(3)

    items = sorted(seen.values(), key=lambda x: x['published'], reverse=True)
    # 只要 2026-07 之后的
    items = [x for x in items if x['published'] >= '2026-07-01']

    print(f'\n2026-07 之后共 {len(items)} 篇')
    by_month: dict[str, int] = {}
    for x in items:
        by_month[x['published'][:7]] = by_month.get(x['published'][:7], 0) + 1
    for m in sorted(by_month):
        print(f'  {m}: {by_month[m]} 篇')

    (D / 'recent_2026h2.json').write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    print('\n最新 20 篇:')
    for x in items[:20]:
        print(f"  {x['published']}  {x['id']:12s} {x['title'][:66]}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
