"""导出「速度声明可比性」统计为可审计的证据产物。

⚠️ 为什么需要这一步：
   c-comparability 是本文自己的统计结论（70 条里只有 8 条可比），
   没有任何外部论文能证明它——这正是不变量 C1 卡住它的原因。
   正确的做法不是把 confidence 降级了事，也不是放宽规则，
   而是**让这项统计本身成为可审计的一手证据**：
     - 把逐条判定结果导出为 claims_audit.csv（谁、哪条、判成什么、为什么）
     - 在 sources.csv 里登记为一个 internal 来源，带抓取时间与生成命令
     - 在 evidence.csv 里引其具体行号作为 locator
   这样「可审计」才成立：任何人可以重跑脚本，逐行核对。
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from pathlib import Path

# 从脚本自身位置推导（脚本在 <archive>/ 下，paper/ 是它的子目录）。
DST = Path(__file__).resolve().parent
SRC = DST / 'paper'

claims = json.loads((SRC / 'speed_claims.json').read_text(encoding='utf-8'))

COMPARABLE_KINDS = ('GEOMEAN', 'AVERAGE')
COMPARABLE_BASES = ('PyTorch', 'cuBLAS', 'torch.compile')

rows = []
for i, c in enumerate(claims, 1):
    comparable = (c['kind'] in COMPARABLE_KINDS
                  and c['baseline'] in COMPARABLE_BASES)
    rows.append({
        'row': i,
        'arxiv_id': c['id'],
        'published': c['pub'],
        'value_x': f"{c['value']:.2f}",
        'claim_kind': c['kind'],
        'baseline': c['baseline'],
        'comparable': 'yes' if comparable else 'no',
        'reason': ('' if comparable else
                   ('统计口径非总体平均' if c['kind'] not in COMPARABLE_KINDS
                    else '基线非明确库')),
        'snippet': c['snippet'][:150],
    })

buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator='\n')
w.writeheader()
w.writerows(rows)
out = DST / 'claims_audit.csv'
out.write_text(buf.getvalue(), encoding='utf-8')

# 汇总
n = len(rows)
n_comp = sum(1 for r in rows if r['comparable'] == 'yes')
old = [r for r in rows if r['published'] < '2026-07-01']
new = [r for r in rows if r['published'] >= '2026-07-01']
c_old = sum(1 for r in old if r['comparable'] == 'yes')
c_new = sum(1 for r in new if r['comparable'] == 'yes')
kc = Counter(r['claim_kind'] for r in rows)

summary = {
    'generated_at': '2026-11-03T15:40:00+08:00',
    'generator': 'research/cuda-kernel-gen/build_evidence.py -> export_claim_audit.py',
    'source_data': 'research/cuda-kernel-gen/speed_claims.json',
    'total_claims': n,
    'comparable_claims': n_comp,
    'comparable_ratio': round(n_comp / n, 4),
    'kind_distribution': dict(kc),
    'period_2025_02_to_2026_06': {'total': len(old), 'comparable': c_old},
    'period_2026_07_to_2026_11': {'total': len(new), 'comparable': c_new},
    'criteria': {
        'comparable_kind': list(COMPARABLE_KINDS),
        'comparable_baseline': list(COMPARABLE_BASES),
    },
}
(DST / 'claim_audit_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'写入 {out.name}: {n} 行')
print(f'  可比 {n_comp}/{n} = {n_comp / n * 100:.1f}%')
print(f'  2026-06 前: {c_old}/{len(old)}')
print(f'  2026-07 后: {c_new}/{len(new)}')
print(f'写入 claim_audit_summary.json')
