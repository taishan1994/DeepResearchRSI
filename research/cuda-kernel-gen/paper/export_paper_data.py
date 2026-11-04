"""从已有数据导出 P2 需要的 data/*.csv（value + cite 列）。

背景（框架层面）：
    docs/data-model.md 的 P2 规定：paper/data/*.csv 里每个数值，
    必须能在对应 claim 的 statement / derivation / 其 evidence.quote 里找到。
    scripts/audit_paper.py 实现该检查，但它只读 paper/data/*.csv，
    且要求每行有 value 与 cite 两列。

    本归档原先没有 data/ 目录（数值都内嵌在 tables/*.csv 和正文里），
    于是 P2 在这个归档上从未运行过——这也是"契约有、数据无、检查静默通过"。

做法：
    把 tab3（多基线阶梯，含「数值」列）里每个可解析为数值的单元格，
    导出为 (value, cite) 行；cite 按 (系统, 基线) 人工映射到 claim。
    不做自动推断：数值归属哪条主张是语义判断，机器猜不准
    （本轮 earlier 已吃过自动匹配插错引用的亏）。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
DATA.mkdir(exist_ok=True)

# 系统 -> claim_id。这些主张的 statement 里含该系统的核心数值。
SYS_CLAIM = {
    'CUDA-L1':   'c-l1-spread',
    'CUDA-L2':   'c-l2-cublas',
    'KernelBench-Verified': 'c-verified-drop',
}


def main() -> int:
    src = HERE / 'tables' / 'tab3_baseline_ladder.csv'
    rows: list[dict[str, str]] = []
    with src.open(encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            rows.append(r)

    out: list[dict[str, str]] = []
    for r in rows:
        sysname = (r.get('系统') or '').strip()
        baseline = (r.get('基线') or '').strip()
        stat = (r.get('统计口径') or '').strip()
        raw = (r.get('数值') or '').strip()
        # 只取纯数值或 Nx 形式
        m = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)\s*x?', raw)
        if not m:
            continue
        cid = SYS_CLAIM.get(sysname)
        if not cid:
            continue
        # ⚠️ 标签必须带统计口径。同一系统的 3.12x（算术平均）与
        #    1.42x（中位数）都对着「PyTorch 默认」这个基线，
        #    不写口径就会看着像两个互相矛盾的数字。
        label = f'{sysname} / {baseline}'
        if stat:
            label += f'（{stat}）'
        out.append({
            'label': label,
            'value': m.group(1),
            'unit': 'x',
            'cite': cid,
        })

    dst = DATA / 'fig_multi_baseline.csv'
    with dst.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['label', 'value', 'unit', 'cite'])
        w.writeheader()
        w.writerows(out)

    print(f'写入 {dst.relative_to(HERE)}：{len(out)} 行')
    for r in out:
        print(f"  {r['value']:>7} {r['unit']:<2} [{r['cite']}]  {r['label']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
