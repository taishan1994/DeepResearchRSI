"""检查 PDF 里有没有 Markdown 残留、结构是否完整。

⚠️ 为什么单独写文件而不是 python -c：
   PowerShell 的 here-string 会吃掉反引号（`）和反斜杠，
   而本检查恰好要匹配这些字符。写成 .py 文件是唯一可靠的方式。
   这是本项目反复踩到的坑，值得记一笔。
"""

import re
import sys
from pathlib import Path

import pymupdf

D = Path(__file__).resolve().parent
pdf = D / 'latex' / 'main.pdf'

doc = pymupdf.open(pdf)
allt = ''.join(pg.get_text() for pg in doc)

print('=' * 74)
print('一、Markdown 残留')
print('=' * 74)
patterns = [
    ('双星号 **', r'\*\*'),
    ('竖线 |', r'\|'),
    ('井号标题 ##', r'#{2,}'),
    ('反引号 `', '`'),
    ('链接 [](', r'\]\('),
    ('图片 ![', r'!\['),
]
# ⚠️ 「[arXiv:2502.10517]」不是 Markdown 残留，是本综述**有意采用**的
# 引用格式（比 footnote 更紧凑，双栏里不会撑破行）。不能计入残留。
# 但要防止真正的 Markdown 链接语法漏网，故单独检查「[](url)」形式。
bad = 0
for name, pat in patterns:
    n = len(re.findall(pat, allt))
    flag = '[OK]' if n == 0 else '[!]'
    if n:
        bad += 1
    print(f'  {name:22s} {n:4d}  {flag}')
    if n:
        m = re.search(pat, allt)
        print(f'      示例: {allt[max(0, m.start() - 30):m.start() + 30]!r}')

# 单独的合理性检查：引用格式是否统一
n_ref = len(re.findall(r'\[arXiv:\d{4}\.\d{4,5}\]', allt))
print(f'  {"[arXiv:...] 引用（保留）":22s} {n_ref:4d}  [OK] 属预期的引用格式')

print()
print('=' * 74)
print('二、章节完整性')
print('=' * 74)
sections = ['摘要', '引言', '背景', '三层能力框架', '方法谱系',
            '度量危机', '奖励黑客', '开放问题', '结论', '附录']
miss = []
for s in sections:
    hit = s in allt
    print(f'  {s:14s} {"[OK]" if hit else "[MISSING]"}')
    if not hit:
        miss.append(s)

print()
print('=' * 74)
print('三、图表编号')
print('=' * 74)
figs = sorted({int(m.group(1)) for m in re.finditer(r'图\s*(\d+)\s', allt)})
tabs = sorted({int(m.group(1)) for m in re.finditer(r'表\s*(\d+)\s', allt)})
print(f'  正文提到的图: {figs}')
print(f'  正文提到的表: {tabs}')
print(f'  PDF 实际页数: {doc.page_count}')
print(f'  总字符数: {len(allt):,}')

print()
print('=' * 74)
ok = (bad == 0 and not miss)
print('结论:', '通过' if ok else f'失败（残留 {bad} 类，缺章节 {miss}）')
sys.exit(0 if ok else 1)
