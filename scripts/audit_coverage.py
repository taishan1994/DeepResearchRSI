"""审计：正文覆盖度的三层判别。

背景（第 114 轮）：
    第 112–113 轮反复在「未引用主张」这个单一指标上打转，
    得出了两个互相矛盾的结论（先是「内容都在」，后是「内容真没写」）。
    根因是指标选错了：报告以「小节」为组织单位，
    一个小节引用 3–5 条主张是常态，某一条主张没有单独标签并不等于内容缺失。

    本脚本改为三个层次分别度量，避免混用：

      层 1  主张级    有多少主张带 c- 标签（受写作粒度影响，仅供参考）
      层 2  小节级    有多少小节至少含一个引用标签（真正反映结构健全度）
      层 3  事实级    正文里含「数字+单位」的外部数据陈述，
                      有多少处在完全无标签的小节里（真正的内容缺口候选）

用法：
    python scripts/audit_coverage.py research/rtx-pro-6000
"""

import csv
import re
import sys
from pathlib import Path

UNIT = r'\d+(?:\.\d+)?\s*(?:%|°C|dBA|W|GB|TB|TFLOPS|TOPS|tok/s|ms|μs|ns/day|美元|USD|\$)'
HEAD = re.compile(r'^#{2,4} .+$', re.M)


def main(slug_dir: str) -> int:
    root = Path(slug_dir)
    rep_path = root / 'REPORT.md'
    if not rep_path.exists():
        print(f'找不到 {rep_path}')
        return 2

    rep = rep_path.read_text(encoding='utf-8')
    m = re.search(r'^## 15\.[^\n]*$', rep, re.M)
    body = rep[:m.start()] if m else rep

    claims = list(csv.DictReader((root / 'claims.csv').open(encoding='utf-8-sig')))
    cited = set(re.findall(r'\[(c-[a-z0-9\-]+)\]', body))
    n_unc = sum(1 for c in claims if c['claim_id'] not in cited)

    print('层 1 · 主张级')
    print(f'  主张 {len(claims)}，带 c- 标签 {len(claims) - n_unc}，'
          f'未带 {n_unc} ({n_unc / len(claims) * 100:.1f}%)')
    print('  ⚠️ 这一层受写作粒度影响：小节引用 3–5 条是常态，'
          '单条未标不等于内容缺失')

    heads = [(mm.start(), mm.group(0)) for mm in HEAD.finditer(body)]
    secs = []
    for i, (s, h) in enumerate(heads):
        e = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        secs.append((h, body[s:e]))

    tagged = [h for h, t in secs if re.search(r'\[(?:c|e|src)-[a-z0-9\-]+\]', t)]
    print('\n层 2 · 小节级')
    print(f'  小节 {len(secs)}，含至少一个引用标签 {len(tagged)} '
          f'({len(tagged) / max(len(secs), 1) * 100:.1f}%)')
    print(f'  完全无标签 {len(secs) - len(tagged)}')

    gaps = []
    for h, t in secs:
        if re.search(r'\[(?:c|e|src)-[a-z0-9\-]+\]', t):
            continue
        txt = HEAD.sub('', t).strip()
        if len(txt) > 150 and re.search(UNIT, txt):
            gaps.append((h, txt))

    print('\n层 3 · 事实级（真正的缺口候选）')
    print(f'  无标签、正文 >150 字、且含「数字+单位」的小节: {len(gaps)}')
    for h, t in gaps:
        print(f'    · {h[:70]}')
        print(f'      {t[:100]}')

    return 0 if not gaps else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'research/rtx-pro-6000'))
