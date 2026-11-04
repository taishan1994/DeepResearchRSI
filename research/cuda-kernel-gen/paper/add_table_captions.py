"""给 PAPER.md 的每个 Markdown 表格补一行题注。

格式约定（与 md_to_tex.py 对齐）：题注写在**表格之后**，隔一个空行，形如

    *表 3　同一系统的多基线对照*

⚠️ 为什么题注放在表格后面而不是前面：
   md_to_tex.py 已经按「表后找题注」实现，且 Markdown 渲染器（GitHub、
   Typora）在表后加题注不会被吞进表格。放前面反而会被某些解析器
   当作表头的一部分。这是与现有转换器保持一致的选择。

本脚本可重复执行（幂等）：已有题注的表会被跳过并打上标记。
"""

from __future__ import annotations

import re
from pathlib import Path

D = Path(__file__).resolve().parent
MD = D / 'PAPER.md'

# 按表格出现顺序给出题注。顺序必须与正文中表格的先后完全一致，
# 因为脚本按「第 N 个表」配对，不做语义匹配。
# ⚠️ 增加新表后必须同步本清单，否则新表会没有题注（且不报错）。
CAPTIONS = [
    '两组实验的四个维度对照',            # 1
    '写一个可用 kernel 的三层门槛',       # 2
    '三条技术路线的对比',                # 3
    '速度声明的语义类型判定标准',          # 4
    '70 条速度声明的语义分布',            # 5
    '可比性随时间的变化',                # 6
    '同一系统的多基线对照',              # 7
    'RL 奖励的作弊方式与检测手段',         # 8
    'AutoTuneBench 归纳的四种失败模式',    # 9
    '对报告数字的折价建议',              # 10
    '真实负载中可优化时间的占比',          # 11
    '方法谱系中的 15 篇核心工作',         # 12
    '主流基准对比',                     # 13
]


def main() -> int:
    lines = MD.read_text(encoding='utf-8').split('\n')
    out: list[str] = []
    i = 0
    tab = 0
    added = 0
    skipped = 0

    while i < len(lines):
        ln = lines[i]
        if not ln.startswith('|'):
            out.append(ln)
            i += 1
            continue

        # 收集完整表格
        start = i
        while i < len(lines) and lines[i].startswith('|'):
            out.append(lines[i])
            i += 1
        tab += 1

        # 看表后是否已有题注（跳过空行）
        j = i
        while j < len(lines) and not lines[j].strip():
            j += 1
        has_cap = (j < len(lines)
                   and re.match(r'\*表\s*\d+\u3000', lines[j].strip()))

        if has_cap:
            skipped += 1
            print(f'  表{tab}: 已有题注，跳过')
            continue

        if tab > len(CAPTIONS):
            print(f'  表{tab}: [!] 没有预置题注，请补充 CAPTIONS')
            continue

        # 插入：空行 + 题注
        out.append('')
        out.append(f'*表 {tab}　{CAPTIONS[tab - 1]}*')
        added += 1
        print(f'  表{tab}: 已加题注「{CAPTIONS[tab - 1]}」')

    MD.write_text('\n'.join(out), encoding='utf-8', newline='\n')
    print(f'\n共 {tab} 个表，新增题注 {added}，跳过 {skipped}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
