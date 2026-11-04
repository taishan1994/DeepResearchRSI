"""核对 PAPER.md 里的每个百分比与计数，是否与 JSON 数据一致。

⚠️ 为什么需要这个：我在正文里手写过「26% 是 up to」，而实测是 20%。
   这类错误在长文里极难靠人眼发现，且它恰好落在全文的核心论据上。
   凡是「数字来自数据」的地方，都应该由脚本核对，而不是靠记忆。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent
md = (D / 'PAPER.md').read_text(encoding='utf-8')

claims = json.loads((D / 'speed_claims.json').read_text(encoding='utf-8'))
papers = json.loads((D / 'papers.json').read_text(encoding='utf-8'))
ext = json.loads((D / 'extracted.json').read_text(encoding='utf-8'))

n_claims = len(claims)
kc = Counter(c['kind'] for c in claims)
bc = Counter(c['baseline'] for c in claims)

# 可跨论文比较的：几何/算术平均 + 明确库基线
comparable = [c for c in claims
              if c['kind'] in ('GEOMEAN', 'AVERAGE')
              and c['baseline'] in ('PyTorch', 'cuBLAS', 'torch.compile')]

checks: list[tuple[str, str, bool]] = []


def chk(label: str, pattern: str, expect: str):
    hit = pattern in md
    checks.append((label, expect + ('  [OK]' if hit else '  [MISSING]'), hit))


print('=' * 88)
print('一、核心计数（期望值从数据源实时计算，不写死）')
print('=' * 88)
# ⚠️ 这里原本写死 '58 篇' / '50 条' / '16%' / '18%' —— 每次扩库都得手改，
#    而手改必然滞后（本轮就因此 7 项全红，纯属假警报）。
#    改为从 papers.json / speed_claims.json 现算，论文里必须出现对应字符串。
N_PAPERS = len(papers)
N_CLAIMS = len(claims)
N_COMP = sum(1 for c in claims
             if c['kind'] in ('GEOMEAN', 'AVERAGE')
             and c['baseline'] in ('PyTorch', 'cuBLAS', 'torch.compile'))
PCT_COMP_ALL = round(N_COMP / N_CLAIMS * 100)

chk('论文总数', f'{N_PAPERS} 篇', f'{N_PAPERS} 篇')
chk('时间跨度', '2025-02 至 2026-11', '2025-02 至 2026-11')
chk('声明总数', f'{N_CLAIMS} 条速度声明', f'{N_CLAIMS} 条')
chk('可比声明', f'{N_COMP} 条（{PCT_COMP_ALL}%）', f'{N_COMP} 条（{PCT_COMP_ALL}%）')

print('\n' + '=' * 88)
print('二、语义分布（正文表格 vs 实测）')
print('=' * 88)
expect_map = {
    'UP_TO': ('「up to Nx」最优个案', kc.get('UP_TO', 0)),
    'PER_CASE': ('单点个案', kc.get('PER_CASE', 0)),
    'UNSPECIFIED': ('未说明口径', kc.get('UNSPECIFIED', 0)),
    'AVERAGE': ('算术平均', kc.get('AVERAGE', 0)),
    'GEOMEAN': ('几何平均', kc.get('GEOMEAN', 0)),
}
for kind, (cn, n) in expect_map.items():
    pct = n / n_claims * 100
    # 在正文表格里找该行
    pat = re.compile(re.escape(cn) + r'\s*\|\s*(\d+)\s*\|\s*(\d+)%')
    m = pat.search(md)
    if m:
        doc_n, doc_pct = int(m.group(1)), int(m.group(2))
        ok = (doc_n == n) and (abs(doc_pct - pct) <= 1)
        checks.append((f'{cn}', f'实测 {n} 条 {pct:.0f}% / 正文 {doc_n} 条 {doc_pct}%'
                       + ('  [OK]' if ok else '  [MISMATCH]'), ok))
    else:
        checks.append((f'{cn}', '正文中未找到该行  [MISSING]', False))

print('\n' + '=' * 88)
print('三、摘要里的一句话统计（百分比从 speed_claims.json 现算）')
print('=' * 88)
# ⚠️ 同上的问题：这里曾写死 20%/24%/20%/18%，扩库后全部失效。
#    现在由 kind 分布现算，并要求论文摘要里出现相同百分比的表述。
_kc = {}
for _c in claims:
    _kc[_c['kind']] = _kc.get(_c['kind'], 0) + 1
_p_up = round(_kc.get('UP_TO', 0) / N_CLAIMS * 100)
_p_pc = round(_kc.get('PER_CASE', 0) / N_CLAIMS * 100)
_p_un = round(_kc.get('UNSPECIFIED', 0) / N_CLAIMS * 100)
_p_geo = round(_kc.get('GEOMEAN', 0) / N_CLAIMS * 100)

chk('摘要 up to', f'{_p_up}% 是「up to Nx」最优个案', f'{_p_up}%')
chk('摘要 单点', f'{_p_pc}% 是单点个案', f'{_p_pc}%')
chk('摘要 未说明', f'{_p_un}% 连统计口径都未说明', f'{_p_un}%')
chk('摘要 几何平均', f'{_p_geo}% 是几何平均', f'{_p_geo}%')

print('\n' + '=' * 88)
print('四、表 3 的关键数值能否在摘要中找到')
print('=' * 88)
key_vals = [
    ('2507.14111', '3.12'), ('2507.14111', '1.42'), ('2507.14111', '120'),
    ('2507.14111', '2.77'), ('2507.14111', '7.72'),
    ('2512.02551', '19.2'), ('2512.02551', '22.0'),
    ('2607.16241', '1.43'), ('2607.16241', '0.88'),
]
pmap = {p['id'][:10]: p for p in papers}
for aid, val in key_vals:
    ab = pmap.get(aid, {}).get('abstract', '')
    ok = val in ab
    checks.append((f'{aid} 的 {val}', '在摘要中' + ('  [OK]' if ok else '  [MISSING]'), ok))

print('\n' + '=' * 88)
print('五、其他关键断言')
print('=' * 88)
chk('TF32 虚高 1.6 倍', '1.6 倍', '1.6')
chk('28% 增加显存', '28% 的生成 kernel 增加了峰值显存', '28%')
chk('跨度 85 倍', '跨度 85 倍', '85')
chk('跨度 3.5 倍', '跨度 3.5 倍', '3.5')

# 输出
for label, msg, ok in checks:
    flag = '  ' if ok else '!!'
    print(f'{flag} {label:34s} {msg}')

bad = [c for c in checks if not c[2]]
print('\n' + '=' * 88)
print(f'核对 {len(checks)} 项，失败 {len(bad)} 项')
if bad:
    for label, msg, _ in bad:
        print(f'  [FAIL] {label}: {msg}')
    raise SystemExit(1)
print('全部通过')
