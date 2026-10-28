"""审计：找出「同一个 source_id 被写成多个 document_id」的命名漂移。

背景（第 229 轮）：
    第 229 轮跑「双向孤儿检查」时顺带发现，5 个 source_id 各对应两个
    document_id（doc-6k-power / doc-rtx6kpro 等）。核对后确认每一对都是
    同一份文档被写了两个名字——不是真的有两份文档。
    故 `distinct(document_id)` 这个数被高估了。

    这个缺陷之所以长期没被发现，是因为检查器只朝一个方向看：
      - validate.py 的 C1 从 claim 往 evidence 看；
      - 孤儿检查从 source 往 evidence 看。
    两个方向都不是「同一来源内的 document_id 是否唯一」。

判据（第 229 轮的结论，本脚本是它的可执行形式）：
    任何「有多少个 X」的计数，都必须先问「X 的 id 是生成的还是手写的」。
    手写的 id 会漂移，而「分类数」会把两次手误读成两个对象。

用法：
    python scripts/audit_id_drift.py research/rtx-pro-6000
    python scripts/audit_id_drift.py research/*

退出码：
    0  没有漂移
    1  有漂移（打印清单）
    2  输入缺失

判据说明：
    本脚本**不自动归一**。原因是归一需要一条前置规则（取多数派？取报告
    引用多的那个？取与 source_id 更接近的那个？），而三种规则在本归档里
    会给出不同答案：
      - `doc-6k-power`(10) 与 `doc-rtx6kpro`(10) 打平，多数派规则失效；
      - `doc-blender`(3) 与 `doc-blenderartists`(2) 多数派指向短名，
        但 `doc-<source stem>` 规则指向长名；
      - 而 `doc-<source stem>` 规则整体只覆盖 349/440 组，
        故它不是一个可以推广的归档惯例。
    所以本脚本只报事实与三种候选规则各自的结论，把裁决留给人。
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPORT_DOC = re.compile(r'doc-[A-Za-z0-9_.\-]+')


def main(slug_dir: str) -> int:
    root = Path(slug_dir)
    ev_path = root / 'evidence.csv'
    if not ev_path.exists():
        print(f'找不到 {ev_path}')
        return 2
    rows = list(csv.DictReader(ev_path.open(encoding='utf-8-sig')))

    by_source = defaultdict(Counter)
    for r in rows:
        by_source[r['source_id']][r['document_id']] += 1

    total_sources = len(by_source)
    all_docs = {r['document_id'] for r in rows}
    drift = {s: c for s, c in by_source.items() if len(c) > 1}

    print(f'证据行数:            {len(rows)}')
    print(f'来源数（distinct）:  {total_sources}')
    print(f'document_id（distinct）: {len(all_docs)}')
    print(f'  若全部一对一，应为 {total_sources}')

    # 归档层的 naming 惯例覆盖率，只作为候选规则之一报告
    stem_match = sum(1 for s, c in by_source.items()
                     if set(c) == {('doc-' + s[4:])})

    if not drift:
        print('\n[OK] 没有 document_id 漂移')
        return 0

    est = len(all_docs) - sum(len(c) - 1 for c in drift.values())
    print(f'  实测 {len(all_docs)}，扣除 {len(drift)} 组漂移后为 {est}')
    print(f'\ndocument_id 漂移: {len(drift)} 组')
    print(f'（参考：doc-<source stem> 惯例覆盖 {stem_match}/{total_sources} 组，'
          f'故它不是一个可推广的归档惯例）')

    rep_text = ''
    rep_path = root / 'REPORT.md'
    if rep_path.exists():
        rep_text = rep_path.read_text(encoding='utf-8')
    rep_docs = Counter(REPORT_DOC.findall(rep_text))

    for s, c in sorted(drift.items()):
        print(f'\n  {s}')
        for d, n in c.most_common():
            marks = []
            marks.append(f'{n} 条证据')
            marks.append(f'正文出现 {rep_docs.get(d, 0)} 次')
            stem = 'doc-' + s[4:]
            marks.append('等于 stem' if d == stem else '不等于 stem')
            print(f'    {d:<44} {" | ".join(marks)}')
        # 三种候选规则各自的结论
        top = c.most_common()
        majority = top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else '(打平，失效)'
        by_stem = 'doc-' + s[4:]
        stem_ok = by_stem if by_stem in c else '(不在候选中)'
        by_rep = max(c, key=lambda d: rep_docs.get(d, 0))
        print(f'    候选规则: 多数派={majority} | '
              f'stem={stem_ok} | 正文引用最多={by_rep}')

    print('\n判据：归一需要一条前置规则，而三种规则在本归档里会给出不同答案。')
    print('      故本脚本只报事实，把裁决留给人。')
    return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(main('research/rtx-pro-6000'))
    if sys.argv[1].endswith('*'):
        base = Path(sys.argv[1].rstrip('*'))
        rc = 0
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            print(f'=== {d} ===')
            rc = max(rc, main(str(d)))
            print()
        sys.exit(rc)
    sys.exit(main(sys.argv[1]))
