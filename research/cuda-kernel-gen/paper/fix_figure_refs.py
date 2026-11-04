"""把正文里的「图 N」引用改成按出现顺序的自然编号。

背景：
    图片在正文中的出现顺序是 fig1, fig4, fig5, fig2, fig8, fig3, fig6, fig9, fig7，
    这是由论证逻辑决定的（每张图跟着它所属的节）。

    学术惯例是图号按出现顺序递增（1..N）。故：
      - LaTeX 用自然编号（不干预计数器）
      - 正文里的「图 N」必须改成新号，否则引用指向错误的图

    旧号（= 文件名编号） -> 新号（= 出现次序）
      1 -> 1    4 -> 2    5 -> 3
      2 -> 4    8 -> 5    3 -> 6
      6 -> 7    9 -> 8    7 -> 9

⚠️ 改写必须两步走：先把所有「图 N」换成占位符，再换成新号。
   否则 1->1, 2->4, 4->2 这种互换会在第一遍就互相覆盖
   （2 先变 4，然后 4 又变 2，原来的 2 就丢了）。
"""

from __future__ import annotations

import re
from pathlib import Path

P = Path(__file__).resolve().parent / 'PAPER.md'

# 旧号 -> 新号（按出现次序）
MAP = {1: 1, 4: 2, 5: 3, 2: 4, 8: 5, 3: 6, 6: 7, 9: 8, 7: 9}


def main() -> int:
    text = P.read_text(encoding='utf-8')

    # 只改正文（不动 ![alt](path) 里的 alt 与路径）
    parts = re.split(r'(!\[[^\]]*\]\([^)]*\))', text)
    changed = 0
    for i, seg in enumerate(parts):
        if seg.startswith('!['):
            continue

        # 第一步：图 N -> 占位符
        def to_ph(m: re.Match) -> str:
            n = int(m.group(1))
            return f'\x00{n}\x00'

        tmp = re.sub(r'图 (\d+)', to_ph, seg)

        # 第二步：占位符 -> 新号
        def to_new(m: re.Match) -> str:
            n = int(m.group(1))
            return f'图 {MAP.get(n, n)}'

        new = re.sub(r'\x00(\d+)\x00', to_new, tmp)
        if new != seg:
            changed += len(re.findall(r'图 (\d+)', seg))
            parts[i] = new

    text = ''.join(parts)
    P.write_text(text, encoding='utf-8', newline='\n')
    print(f'改写了 {changed} 处正文图号引用')
    print(f'映射: {MAP}')

    # 复核
    print('\n现在的正文引用：')
    for m in re.finditer(r'[^\n]{0,14}图 \d+[^\n]{0,34}', text):
        if m.group(0).strip().startswith('!['):
            continue
        print('  ', m.group(0).strip()[:58])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
