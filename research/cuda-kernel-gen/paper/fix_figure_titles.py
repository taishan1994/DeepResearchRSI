"""去掉图片内部标题里的「图 N　」前缀，消除与 LaTeX 图注的重复编号。

问题（用户指出）：
    图片内部画着  「图 1　本文纳入的 58 篇论文按发表月份分布」
    PDF 图注又写着 「图 1：图 1」
    两处都在编号，读者不知道该信哪个。而且图内标题的数据还停在 58 篇/50 条，
    与正文的 98 篇/70 条不一致 —— 双重错误。

修法（学术惯例）：
    编号与说明只放在 LaTeX caption；图内只保留「自解释的短标题」，
    并以 (a)/(b) 标注子图。这样 caption 是唯一权威，图内不与它争。

幂等：已无前缀的标题不会被二次处理。
"""

from __future__ import annotations

import re
from pathlib import Path

P = Path(__file__).resolve().parent / 'make_figures.py'

text = P.read_text(encoding='utf-8')

# 只替换字符串字面量里的「图 N　」前缀（全角空格分隔）
pattern = re.compile(r"'图 \d+\u3000")
new_text, n = pattern.subn("'", text)

if n == 0:
    print('无需改动：图内标题已无「图 N　」前缀')
    raise SystemExit(0)

P.write_text(new_text, encoding='utf-8', newline='\n')
print(f'已去掉 {n} 处图内编号前缀')

# 复核：列出剩余的 set_title / suptitle 文本
print('\n当前图内标题：')
for m in re.finditer(r"(?:set_title|suptitle)\(\s*'([^']+)'", new_text):
    print('  -', m.group(1)[:60])
