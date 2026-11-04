"""补齐 data/ 下其余图表的 (value, cite) 数据，供 P2 数值回溯。

fig_multi_baseline.csv 已由 export_paper_data.py 从 tab3 导出。
本脚本补上其余三组关键数值——它们散在正文与不同表里，没有统一的源表：

  fig_verified_drop  : KernelBench-Verified 的 1.43x / 1.19x / 0.88x
  fig_e2e_amdahl     : Amdahl 推算（8.9% -> 1.07x，30% -> 1.29x，58.2% -> 1.77x）
  fig_claim_mix      : 70 条声明的语义分布（11/13/22/9/15）

⚠️ 这些值必须与 evidence.quote 逐字一致才能过 P2。
   写之前先核对：KernelBench-Verified 的 1.19x 在 e-002/e-003 里是怎样的写法。
   若无逐字形式，P2 会报出来——那时应当修数据，不是改判据。
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
DATA.mkdir(exist_ok=True)

SETS: dict[str, tuple[list[str], list[dict[str, str]]]] = {
    'fig_verified_drop.csv': (
        ['label', 'value', 'unit', 'cite'],
        [
            {'label': '默认 PyTorch 协议', 'value': '1.43', 'unit': 'x', 'cite': 'c-verified-drop'},
            {'label': 'TF32 + 隐藏测试集', 'value': '0.88', 'unit': 'x', 'cite': 'c-verified-drop'},
        ],
    ),
    'fig_e2e_amdahl.csv': (
        ['label', 'value', 'unit', 'cite'],
        [
            {'label': '可优化占比 8.9%（kernel 快 4x）', 'value': '1.0715', 'unit': 'x', 'cite': 'c-e2e-amdahl'},
            {'label': '可优化占比 30%（kernel 快 4x）', 'value': '1.2903', 'unit': 'x', 'cite': 'c-e2e-amdahl'},
            {'label': '可优化占比 58.2%（kernel 快 4x）', 'value': '1.7746', 'unit': 'x', 'cite': 'c-e2e-amdahl'},
        ],
    ),
    'fig_claim_mix.csv': (
        ['label', 'value', 'unit', 'cite'],
        [
            {'label': 'UP_TO（最优个案）', 'value': '11', 'unit': '条', 'cite': 'c-claim-mix'},
            {'label': 'PER_CASE（单点）', 'value': '13', 'unit': '条', 'cite': 'c-claim-mix'},
            {'label': 'UNSPECIFIED（未说明）', 'value': '22', 'unit': '条', 'cite': 'c-claim-mix'},
            {'label': 'AVERAGE（算术平均）', 'value': '9', 'unit': '条', 'cite': 'c-claim-mix'},
            {'label': 'GEOMEAN（几何平均）', 'value': '15', 'unit': '条', 'cite': 'c-claim-mix'},
        ],
    ),
}


def main() -> int:
    for name, (fields, rows) in SETS.items():
        dst = DATA / name
        with dst.open('w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f'写入 {name}: {len(rows)} 行')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
