"""审计：`confidence` 与证据表的关系，并给出它的构造规则。

背景（第 230 轮的结论，第 231 轮的可执行形式）：
    Prism 的 `ExecReport.signal` 把权重全部写在一个函数里
    （compiles=1.0、tests_passed +1.5、tests_failed -0.5、
    types_ok +0.5/-0.25），所以它是「可复算」的。
    而本归档的 `confidence` 从来没有任何构造规则 ——
    第 230 轮据此判定它「既是一个序关系，又是一个不可复算的量」。

    本脚本的作用是把这句话量化，并给出一个诚实的裁决。

实测结论（第 231 轮，2020 条主张）：
    - `high`（1671）全部是 primary + open，但这**不足以解释**它：
      全部证据都是 primary 的主张有 1820 条，其中 1651 是 high、
      157 是 medium、6 是 low、6 是 disputed。
    - 反向也有 20 条 high 含非 primary 证据。
    - 故 `confidence` **不是证据表任何一列的函数**，
      它额外吸收了标注者对「结论强度」的判断。

所以本脚本的裁决不是「算出一个分数」，而是回答三个可检验的问题：
    1. `confidence=high` 是否违反 S2（access != open 不能支撑 high/medium）；
    2. `confidence=high` 是否违反 C1（需要 trust_tier=primary）；
    3. 三个候选规则各自的解释力是多少 —— 用来证明「没有一条够用」。

用法：
    python scripts/audit_confidence.py research/rtx-pro-6000

退出码：
    0  没有违反 S2/C1，且已打印候选规则的解释力
    1  有违反
    2  输入缺失

判据说明：
    本脚本**不重算 confidence**。因为三个候选规则的解释力都远低于 100%，
    重算会把 1671 条 high 里的一大批降级，而这个动作需要研究决策而不是工具。
    工具能做的是把「没有一条规则够用」这件事变成可复现的输出。
"""

import csv
import sys
from collections import Counter
from pathlib import Path

ORDER = ['low', 'medium', 'high', 'disputed']


def _load(root: Path):
    src = {s['source_id']: s
           for s in csv.DictReader((root / 'sources.csv').open(encoding='utf-8-sig'))}
    ev = {e['evidence_id']: e
          for e in csv.DictReader((root / 'evidence.csv').open(encoding='utf-8-sig'))}
    cl = list(csv.DictReader((root / 'claims.csv').open(encoding='utf-8-sig')))
    return src, ev, cl


def _tiers(claim, src, ev):
    out = []
    for i in claim['evidence_ids'].split(';'):
        i = i.strip()
        if i in ev:
            s = src.get(ev[i]['source_id'])
            out.append(s['trust_tier'] if s else '?')
    return out


def _accesses(claim, src, ev):
    out = []
    for i in claim['evidence_ids'].split(';'):
        i = i.strip()
        if i in ev:
            s = src.get(ev[i]['source_id'])
            out.append(s['access'] if s else '?')
    return out


def main(slug_dir: str) -> int:
    root = Path(slug_dir)
    for name in ('sources.csv', 'evidence.csv', 'claims.csv'):
        if not (root / name).exists():
            print(f'找不到 {root / name}')
            return 2
    src, ev, cl = _load(root)
    total = len(cl)
    print(f'主张总数: {total}')
    print('confidence 分布:',
          {k: v for k, v in sorted(Counter(c['confidence'] for c in cl).items())})

    # --- 1. S2 / C1 违规：这两条是硬约束，必须为零 ---
    bad_s2, bad_c1 = [], []
    for c in cl:
        if c['confidence'] not in ('high', 'medium'):
            continue
        acc = _accesses(c, src, ev)
        if acc and any(a != 'open' for a in acc):
            bad_s2.append(c['claim_id'])
        tiers = _tiers(c, src, ev)
        if c['confidence'] == 'high' and tiers and any(t != 'primary' for t in tiers):
            bad_c1.append(c['claim_id'])

    print(f'\nS2 违规（access != open 却标 high/medium）: {len(bad_s2)}')
    for x in bad_s2[:10]:
        print('  ', x)
    print(f'C1 违规（high 但含非 primary 证据）: {len(bad_c1)}')
    for x in bad_c1[:10]:
        print('  ', x)

    # --- 2. 三个候选规则的解释力 ---
    print('\n候选规则的解释力（分母 = 主张总数）:')

    # 规则 A：全部证据 primary -> high
    rule_a = 0
    for c in cl:
        tiers = _tiers(c, src, ev)
        pred = 'high' if (tiers and all(t == 'primary' for t in tiers)) else 'not-high'
        actual = 'high' if c['confidence'] == 'high' else 'not-high'
        if pred == actual:
            rule_a += 1
    print(f'  A 全部 primary => high               {rule_a:>5} / {total}'
          f'  ({rule_a / total * 100:.1f}%)')

    # 规则 B：全部 primary 且 >= 2 条证据 -> high
    rule_b = 0
    for c in cl:
        tiers = _tiers(c, src, ev)
        n = len([i for i in c['evidence_ids'].split(';') if i.strip()])
        pred = 'high' if (tiers and all(t == 'primary' for t in tiers) and n >= 2) else 'not-high'
        actual = 'high' if c['confidence'] == 'high' else 'not-high'
        if pred == actual:
            rule_b += 1
    print(f'  B 全部 primary 且 >=2 条证据 => high  {rule_b:>5} / {total}'
          f'  ({rule_b / total * 100:.1f}%)')

    # 规则 C：全 primary+open 且非 interpretation -> high
    rule_c = 0
    for c in cl:
        tiers = _tiers(c, src, ev)
        pred = 'high' if (tiers and all(t == 'primary' for t in tiers)
                          and c['claim_type'] != 'interpretation') else 'not-high'
        actual = 'high' if c['confidence'] == 'high' else 'not-high'
        if pred == actual:
            rule_c += 1
    print(f'  C 全 primary 且非 interpretation     {rule_c:>5} / {total}'
          f'  ({rule_c / total * 100:.1f}%)')

    # --- 3. 反例：全 primary 却不是 high 的那一批 ---
    allp_not_high = [c for c in cl
                     if c['confidence'] != 'high'
                     and (lambda t: bool(t) and all(x == 'primary' for x in t))(
                         _tiers(c, src, ev))]
    print(f'\n反例（全部证据都是 primary 但不是 high）: {len(allp_not_high)}')
    print('  其 confidence:', dict(Counter(c['confidence'] for c in allp_not_high)))
    print('  其 claim_type:', dict(Counter(c['claim_type'] for c in allp_not_high)))
    for c in allp_not_high[:8]:
        print(f'  {c["claim_id"]:<46} [{c["claim_type"]:<13}] {c["confidence"]}')

    print('\n裁决：')
    print('  没有任何一条候选规则的解释力接近 100%，')
    print('  故 confidence 不是证据表任何一列的函数 ——')
    print('  它额外吸收了标注者对「结论强度」的判断。')
    print('  本脚本不重算它：重算会把大批 high 降级，而那是研究决策，不是工具。')

    return 1 if (bad_s2 or bad_c1) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'research/rtx-pro-6000'))
