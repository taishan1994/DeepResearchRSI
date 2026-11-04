"""验证 X8（图号与内容对应）真能抓到错位，而不是永远通过。

⚠️ 判据如果不能失败，就等于没有判据。
   本文件构造已知有病的样本，确认 X8 报错；再用健康样本确认不误报。

约定（与 check_latex.py 一致）：
   期望编号 = 图片在正文中的**出现次序**（1..N），
   不是文件名里的 figN —— 文件名只表示当初第几个画的。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# X8 的判定逻辑（与 check_latex.py 保持一致，此处复刻用于单测）
def x8_find_mismatch(md_text: str, pdf_text: str) -> list[str]:
    expect: list[tuple[int, str]] = []
    for idx, m in enumerate(
            re.finditer(r'!\[([^\]]+)\]\((?:\.\./)?figures/[^)]+\)', md_text), 1):
        alt = m.group(1)
        first = re.split(r'[。；：]', alt)[0][:10]
        expect.append((idx, first))

    found: dict[int, str] = {}
    for m in re.finditer(r'图\s*(\d+)[ \t]*\n([^\n]{0,24})', pdf_text):
        no = int(m.group(1))
        if no not in found:
            found[no] = m.group(2)

    def norm(s: str) -> str:
        return re.sub(r'[\s，。、：；·\-—]', '', s)

    mismatch: list[str] = []
    for no, first in expect:
        got = found.get(no, '')
        if not got:
            mismatch.append(f'图{no}: PDF 中找不到该编号的图注')
            continue
        if norm(got)[:6] != norm(first)[:6]:
            mismatch.append(f'图{no}: 期望「{first}」实得「{got[:12]}」')
    return mismatch


RESULTS: list[str] = []


def check(name: str, cond: bool, detail: str = '') -> None:
    RESULTS.append(('[PASS] ' if cond else '[FAIL] ') + name
                   + (f'\n{detail}' if not cond else ''))


# 两张图：第 1 张是时间分布，第 2 张是方法标签
md_ok = (
    '![本文纳入的 98 篇论文按发表月份分布。红色区域为新增时段。]'
    '(figures/fig1_timeline.png)\n\n'
    '![各方法标签的论文数，按半年切分。](figures/fig4_method_evolution.png)\n'
)

# ---- 用例 1：编号正确，不应误报
pdf_ok = ('图1\n本文纳入的98 篇论文按发表月份分布。红色区域为新增时段。\n'
          '图2\n各方法标签的论文数，按半年切分。\n')
check('正确编号不误报', x8_find_mismatch(md_ok, pdf_ok) == [],
      str(x8_find_mismatch(md_ok, pdf_ok)))

# ---- 用例 2：编号错位（第 2 张图被渲染成「图 1」），必须报出
pdf_bad = ('图1\n各方法标签的论文数，按半年切分。\n'
           '图2\n本文纳入的98 篇论文按发表月份分布。\n')
mm = x8_find_mismatch(md_ok, pdf_bad)
check('错位被 X8 抓到', len(mm) > 0, '未报出任何错位')

# ---- 用例 3：PDF 里缺一张图的图注，必须报出
pdf_missing = '图1\n本文纳入的98 篇论文按发表月份分布。\n'
mm2 = x8_find_mismatch(md_ok, pdf_missing)
check('缺图注被 X8 抓到', len(mm2) > 0, '未报出缺失')

# ---- 用例 4：正文行内引用不得被当成图注
pdf_inline = ('正文里写：图 1 显示了98 篇论文的时间分布。\n'
              '图1\n本文纳入的98 篇论文按发表月份分布。\n'
              '图2\n各方法标签的论文数，按半年切分。\n')
check('行内引用不被误当图注', x8_find_mismatch(md_ok, pdf_inline) == [],
      str(x8_find_mismatch(md_ok, pdf_inline)))

print()
for r in RESULTS:
    print(r)
bad = sum(1 for r in RESULTS if r.startswith('[FAIL]'))
print(f'\n{len(RESULTS) - bad}/{len(RESULTS)} 通过')
raise SystemExit(1 if bad else 0)
