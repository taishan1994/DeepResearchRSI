"""重排章节编号：按出现顺序重新编号，并修正正文里的「第 N 章」引用。

⚠️ 为什么需要单独一步：手工插入新章节后，编号必然错位。
   本文件曾出现「5.5 出现两次」「7.3 出现在第 8 章下面」这类问题，
   而 Markdown 不报错、LaTeX 也不报错——只有人眼能发现。
   故用脚本按物理顺序重排，保证唯一且连续。

约定：
  - 「## 摘要」与「## 附录 X」不参与编号
  - 「# 7 ...」这种一级标题视为章，统一改成「##」
  - 章内小节编号为 N.M
"""

from __future__ import annotations

import re
from pathlib import Path

D = Path(__file__).resolve().parent
MD = D / 'PAPER.md'
lines = MD.read_text(encoding='utf-8').split('\n')

# 识别标题行
HEAD = re.compile(r'^(#{1,2})\s+(.*)$')
# 提取可能的既有编号前缀
NUM = re.compile(r'^(\d+(?:\.\d+)?)\u3000(.*)$')

out: list[str] = []
chap = 0
sec = 0
numbered = False   # 是否已进入正文编号区（摘要之前是标题）
# 记录「旧编号 -> 新编号」，用于改写正文引用
remap: dict[str, str] = {}

for ln in lines:
    m = HEAD.match(ln)
    if not m:
        out.append(ln)
        continue

    level, text = m.group(1), m.group(2).strip()

    # 跳过：摘要、附录
    if text.startswith('摘要') or text.startswith('附录'):
        out.append(f'## {text}')
        continue

    # ⚠️ 全篇大标题：出现在「摘要」之前、且原本是一级标题。
    # 它不应被编号，否则整篇章号会从 2 开始（本文件踩过这个坑）。
    if not numbered and text and not NUM.match(text):
        out.append(f'# {text}')
        continue

    nm = NUM.match(text)
    old_num = nm.group(1) if nm else None
    title = nm.group(2) if nm else text
    numbered = True

    if old_num is None:
        # 无编号的二级标题：视为新的一章（如「7　端到端收益」丢了数字）
        chap += 1
        sec = 0
        out.append(f'## {chap}　{title}')
        continue

    if '.' in old_num:
        # 小节
        sec += 1
        new = f'{chap}.{sec}'
        remap[old_num] = new
        out.append(f'## {new}　{title}')
    else:
        # 章
        chap += 1
        sec = 0
        remap[old_num] = str(chap)
        out.append(f'## {chap}　{title}')

body = '\n'.join(out)

# 改写正文里的「第 N 章」引用
def fix_ref(m: re.Match) -> str:
    old = m.group(1)
    return f'第 {remap.get(old, old)} 章'

body2 = re.sub(r'第\s*(\d+)\s*章', fix_ref, body)

MD.write_text(body2, encoding='utf-8', newline='\n')

print(f'章节重排完成：共 {chap} 章')
print('编号映射（仅列出发生变化的）:')
for k, v in remap.items():
    if k != v:
        print(f'  {k} -> {v}')
