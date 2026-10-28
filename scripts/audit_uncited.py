"""审计：找出「主张已记录但正文没有引用标签」的条目。
背景（第 112 轮）：
    校验器只能检查「正文引用的 id 是否存在」，无法检查
    「已记录的主张是否在正文中被引用」。
    后者一旦缺失，prose 与 CSV 就会脱节，而所有自动检查仍然通过。

用法：
    python scripts/audit_uncited.py research/rtx-pro-6000

判据说明：
    本脚本只统计 `[c-xxx]` 形式的内联标签。
    正文中「内容已写但没打标签」与「内容根本没写」都会被计入，
    需要人工区分——所以它给出的是"待核实清单"，不是"错误清单"。

    第 198 轮修正：
    原来的字符类写成 r'[a-z0-9-]'，会漏掉含大写或下划线的 claim_id
    （实测漏了 2 条：c-default-src1-is-q8_1、c-env-var-GGML_CUDA_MMQ_PREC），
    于是把「已引用」误报成「未引用」。
    现在改为 [A-Za-z0-9_-]，与 claims.csv 里实际出现的字符集一致。

    ⚠️ 这个 bug 的形状值得记住：**一个检查器的字符类比它的数据窄**，
    它的输出不是「错误的」，而是「偏向某一边的」——
    而偏向「多报未引用」这一边特别隐蔽，因为它看起来只是「清单长了一点」。
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

CLAIM_TAG = re.compile(r'\[(c-[A-Za-z0-9_\-]+)\]')


def main(slug_dir: str) -> int:
    root = Path(slug_dir)
    rep_path = root / 'REPORT.md'
    claims_path = root / 'claims.csv'
    if not rep_path.exists() or not claims_path.exists():
        print(f'找不到 {rep_path} 或 {claims_path}')
        return 2

    rep = rep_path.read_text(encoding='utf-8')
    claims = {r['claim_id']: r
              for r in csv.DictReader(claims_path.open(encoding='utf-8-sig'))}
    cited = set(CLAIM_TAG.findall(rep))
    uncited = sorted(set(claims) - cited)

    total = len(claims)
    print(f'主张总数: {total}')
    print(f'正文已引用: {total - len(uncited)}')
    print(f'未引用:     {len(uncited)}  ({len(uncited) / total * 100:.1f}%)')

    if not uncited:
        print('\n[OK] 全部主张均在正文中被引用')
        return 0

    print('\n按置信度:')
    for k, v in sorted(Counter(claims[c]['confidence'] for c in uncited).items()):
        print(f'  {k:<10} {v}')

    print('\n按 as_of:')
    for k, v in sorted(Counter(claims[c]['as_of'] for c in uncited).items()):
        dated = sum(1 for x in claims.values() if x['as_of'] == k)
        print(f'  {k}  {v:>3} / {dated:>4}')

    print('\n待核实清单（需人工判断是「没写」还是「写了没打标签」）:')
    for c in uncited:
        st = claims[c]['statement'].replace('\n', ' ')
        if len(st) > 78:
            st = st[:78] + '…'
        print(f'  {c:<28} [{claims[c]["confidence"]:<7}] {st}')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'research/rtx-pro-6000'))
