"""检查 LaTeX 正文里的 caption 是否有重复或空壳。

用途：确认「图 N：图 N」这种事不再出现，且图注与表注不撞车。
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

TEX = Path(__file__).resolve().parent / 'latex' / 'body.tex'
text = TEX.read_text(encoding='utf-8')

# caption 内容里可能有嵌套花括号（\textbf{}），故做简单配对扫描
caps: list[str] = []
i = 0
while True:
    j = text.find(r'\caption{', i)
    if j < 0:
        break
    k = j + len(r'\caption{')
    depth = 1
    while k < len(text) and depth:
        if text[k] == '{':
            depth += 1
        elif text[k] == '}':
            depth -= 1
        k += 1
    caps.append(text[j + len(r'\caption{'):k - 1])
    i = k

print(f'caption 总数 {len(caps)}，去重后 {len(set(caps))}')

dups = [c for c, n in Counter(caps).items() if n > 1]
print('完全重复:', dups if dups else '无')

# 空壳：只有「图 N」/「表 N」或极短
hollow = [c for c in caps if re.fullmatch(r'[图表]\s*\d+', c.strip())]
print('空壳（仅编号）:', hollow if hollow else '无')

# 过短（少于 8 字）的题注，通常说明信息量不足
short = [c for c in caps if len(c.strip()) < 8]
print('过短（<8 字）:', short if short else '无')

# 图注是否都含数据来源或解读（启发式：长度 > 30 视为实体图注）
long_caps = [c for c in caps if len(c) > 30]
print(f'\n实体题注（>30 字）: {len(long_caps)} / {len(caps)}')
for c in caps:
    flag = 'ok ' if len(c) > 30 else 'SHORT'
    print(f'  [{flag}] {c[:70]}')
