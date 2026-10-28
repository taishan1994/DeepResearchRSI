"""审计：同一个 URL 被登记成多个 source_id。

背景（第 198 轮）：
    校验器 `validate_research.py` 只检查 source_id 是否唯一，
    但允许同一个 URL 以不同 source_id 重复登记。
    这类重复不会让任何检查失败，却会让「一个来源」在统计里变成两个，
    并且更危险的是：两份记录的 trust_tier / source_type 往往不一致，
    于是同一条证据的强度取决于「你是从哪个 source_id 数上去的」。

判据（可复现）：
    对 URL 做 strip + 去尾斜杠 + 小写归一化，然后分组。
    组内 >1 即报。

用法：
    python scripts/audit_duplicate_sources.py research/rtx-pro-6000
    python scripts/audit_duplicate_sources.py research/rtx-pro-6000 --plan

退出码：0 无重复；1 有重复。
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

TIER_ORDER = {'tertiary': 0, 'secondary': 1, 'primary': 2}
TYPE_ORDER = {'press': 0, 'community': 1, 'retail': 2, 'academic': 3,
              'independent': 4, 'review': 5, 'vendor-adjacent': 6,
              'vendor': 7, 'official': 8}


def norm(url: str) -> str:
    return url.strip().rstrip('/').lower()


def build_plan(src, ev):
    ev_count = Counter()
    first_seen = {}
    for i, e in enumerate(ev):
        ev_count[e['source_id']] += 1
        first_seen.setdefault(e['source_id'], i)

    by_url = defaultdict(list)
    for s in src:
        by_url[norm(s['url'])].append(s)
    dup = {u: v for u, v in by_url.items() if len(v) > 1}

    plan = []
    for u, v in dup.items():
        # KEEP 规则：登记最早的那个。
        # 理由：行序是真实的登记顺序，后登记的重复 id 应当被吸收。
        v_ord = sorted(v, key=lambda s: first_seen.get(s['source_id'], 10 ** 9))
        keep, drop = v_ord[0], v_ord[1:]

        tier = min((s['trust_tier'] for s in v), key=lambda x: TIER_ORDER.get(x, 0))
        types = {s['source_type'] for s in v}
        stype = (max(types, key=lambda x: TYPE_ORDER.get(x, 0))
                 if len(types) > 1 else keep['source_type'])
        pa = [s['published_at'] for s in v if s['published_at']]
        ua = [s['updated_at'] for s in v if s['updated_at']]

        plan.append({
            'url': u,
            'keep': keep['source_id'],
            'drop': [s['source_id'] for s in drop],
            'moved_evidence': sum(ev_count[s['source_id']] for s in drop),
            'tier_before': {s['source_id']: s['trust_tier'] for s in v},
            'tier_after': tier,
            'type_before': {s['source_id']: s['source_type'] for s in v},
            'type_after': stype,
            'title': max((s['title'] for s in v), key=len),
            'publisher': max((s['publisher'] for s in v), key=len),
            'published_at': pa[0] if pa else '',
            'updated_at': ua[0] if ua else '',
            'published_at_conflict': len(set(pa)) > 1,
            'updated_at_conflict': len(set(ua)) > 1,
        })
    return plan, ev_count


def main(argv) -> int:
    slug = argv[1] if len(argv) > 1 else 'research/rtx-pro-6000'
    want_plan = '--plan' in argv
    root = Path(slug)
    src_p, ev_p = root / 'sources.csv', root / 'evidence.csv'
    if not src_p.exists() or not ev_p.exists():
        print(f'找不到 {src_p} 或 {ev_p}')
        return 2

    src = list(csv.DictReader(src_p.open(encoding='utf-8-sig')))
    ev = list(csv.DictReader(ev_p.open(encoding='utf-8-sig')))
    plan, ev_count = build_plan(src, ev)

    print(f'source 总数: {len(src)}')
    print(f'evidence 总数: {len(ev)}')
    print(f'URL 重复组数: {len(plan)}')
    if not plan:
        print('\n[OK] 无重复来源')
        return 0

    involved = sum(1 + len(p['drop']) for p in plan)
    movable = sum(p['moved_evidence'] for p in plan)
    print(f'涉及 source 行: {involved}')
    print(f'可合并后减少: {involved - len(plan)}')
    print(f'需改归属的 evidence 行: {movable}')

    tier_diff = [p for p in plan if len(set(p['tier_before'].values())) > 1]
    type_diff = [p for p in plan if len(set(p['type_before'].values())) > 1]
    date_diff = [p for p in plan
                 if p['published_at_conflict'] or p['updated_at_conflict']]
    print(f'trust_tier 冲突组: {len(tier_diff)}')
    print(f'source_type 冲突组: {len(type_diff)}')
    print(f'日期冲突组: {len(date_diff)}')

    print('\n分组明细:')
    for p in sorted(plan, key=lambda x: x['keep']):
        drops = ', '.join(f'{d}(ev={ev_count[d]})' for d in p['drop'])
        print(f'  KEEP {p["keep"]:<34} ev={ev_count[p["keep"]]:<4} <- {drops}')
        print(f'       {p["url"][:100]}')
        if len(set(p['tier_before'].values())) > 1:
            print(f'       TIER {p["tier_before"]} -> {p["tier_after"]}')
        if len(set(p['type_before'].values())) > 1:
            print(f'       TYPE {p["type_before"]} -> {p["type_after"]}')

    if want_plan:
        out = root / 'duplicate_sources_plan.json'
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8', newline='\n')
        print(f'\nplan 已写入 {out}')

    print('\n说明：本脚本只报告，不修改任何文件。')
    print('合并需人工确认 KEEP 规则——因为组内两个 id 都被主张引用过，')
    print('任选其一都会改变部分主张的 source 归属。')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
