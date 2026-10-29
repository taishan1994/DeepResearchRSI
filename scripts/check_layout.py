"""排版健康度检查：查 PDF 的物理形态，而不是内容。

前三个校验器各有分工：

  validate_research.py  档案层：引用闭合、证据等级、主张完整性
  audit_paper.py        论文与档案是否一致（防造假）
  check_paper.py        论文与它自己是否一致（防自相矛盾）
  check_layout.py       论文排出来好不好看（防「能读但没法看」）      <- 本脚本

为什么需要第四个：r261 那份 29 页的 PDF 里有 7 页只有 40-97 个字
（一个表格行被拆到两页、每页只剩一个词），而三个校验器都没报。
它们查引用、查数值、查编号，但**没人查「这一页是不是空的」**。

检查项：

  L1  逐页字数下限（排除首页与末页）
  L2  图片不与它所在的段落分离（图上方必须有正文）
  L3  表格行不跨页（表现为某页字数异常少且以表格碎片开头）
  L4  越界：任何文字不得超出页面右边界
  L5  字体嵌入与缺字

用法：
    python scripts/check_layout.py research/rtx-pro-6000/paper/PAPER.pdf
    python scripts/check_layout.py research/rtx-pro-6000/paper/PAPER.pdf --verbose

退出码非 0 表示有 FAIL。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

# A4 上本项目用的版心：左右各 20 mm，故右边界约 190 mm = 538.6 pt
PAGE_W_PT = 595.276
MARGIN_PT = 20 * 72 / 25.4          # 20 mm
RIGHT_LIMIT = PAGE_W_PT - MARGIN_PT

MIN_CHARS = 300                     # 一页少于这么多字几乎一定是排版问题
CJK = re.compile(r'[\u4e00-\u9fff]')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='PDF 排版健康度检查')
    ap.add_argument('pdf')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args(argv)

    path = Path(args.pdf)
    if not path.is_file():
        print(f'[FAIL] 找不到 {path}')
        return 1

    doc = pymupdf.open(path)
    n = doc.page_count
    problems: list[tuple[str, str]] = []

    pages = []
    for i in range(n):
        p = doc[i]
        txt = p.get_text()
        body = len(txt.replace(' ', '').replace('\n', ''))
        pages.append({
            'no': i + 1,
            'chars': body,
            'imgs': len(p.get_images()),
            'text': txt,
            'page': p,
        })

    # ---------- L1 逐页字数 ----------
    # 首页有标题与摘要块，末页是收尾，两者天然字少。
    thin = [pg for pg in pages[1:-1] if pg['chars'] < MIN_CHARS]
    if thin:
        for pg in thin:
            head = pg['text'].strip().split('\n')
            head = head[1][:40] if len(head) > 1 else '(空)'
            problems.append(
                ('FAIL', f"L1 第 {pg['no']} 页只有 {pg['chars']} 字（下限 {MIN_CHARS}）："
                         f"「{head}」"))
    else:
        lo = min(pg['chars'] for pg in pages[1:-1]) if n > 2 else 0
        print(f'  L1 逐页字数均达标（正文页最少 {lo} 字）')

    # ---------- L2 图与图注必须同页，且正文必须引用 ----------
    # 第一版把「图在页首、上方无正文」判为缺陷。这是错的：
    # 图浮到页首是 LaTeX 的标准做法（[t] 浮动体），不是排版错误。
    # 真正的缺陷只有两种：
    #   (a) 图的图注被挤到下一页，读者看到图找不到它在讲什么；
    #   (b) 正文里根本没有引用这张图。
    all_text = '\n'.join(pg['text'] for pg in pages)
    for pg in pages:
        if not pg['imgs']:
            continue
        p = pg['page']
        txt = pg['text']
        for b in p.get_text('dict')['blocks']:
            if b['type'] != 1:
                continue
            img_bottom = b['bbox'][3]
            # 图下方 110 pt 内应有「图 N」形式的图注
            clip = pymupdf.Rect(MARGIN_PT, img_bottom,
                                RIGHT_LIMIT, min(p.rect.height, img_bottom + 110))
            below = p.get_text('text', clip=clip) if clip.height > 1 else ''
            m = re.search(r'图\s*(\d+)', below)
            if not m:
                problems.append(
                    ('FAIL', f"L2 第 {pg['no']} 页的图下方无图注"
                             f"（图注与图分离，或图注缺失）"))
                continue
            no = m.group(1)
            # 正文（图注以外）必须提到这张图
            refs = len(re.findall(rf'图\s*{no}(?!\d)', all_text))
            if refs < 2:      # 1 次是图注本身，正文里还要有一次
                problems.append(
                    ('WARN', f"L2 图 {no} 在正文中几乎未被引用"
                             f"（全篇出现 {refs} 次，含图注）"))
    if not any(m.startswith('L2') for _, m in problems):
        print('  L2 图与图注同页，且正文均有引用')

    # ---------- L3 表格行不跨页 ----------
    # 特征：某页字数骤降，且首行是一个极短的片段（表格单元格被拆开）
    for pg in pages[1:-1]:
        if pg['chars'] >= MIN_CHARS:
            continue
        lines = [l for l in pg['text'].split('\n') if l.strip()]
        # 去掉页眉页脚
        lines = [l for l in lines
                 if '推理性能综述' not in l and not re.fullmatch(r'—\s*\d+\s*—', l.strip())]
        if lines and max(len(l) for l in lines) <= 24:
            problems.append(
                ('FAIL', f"L3 第 {pg['no']} 页疑似表格行跨页："
                         f"整页最长一行仅 {max(len(l) for l in lines)} 字"))
    if not any(m.startswith('L3') for _, m in problems):
        print('  L3 无表格行跨页迹象')

    # ---------- L4 越界 ----------
    over = 0
    worst = 0.0
    for pg in pages:
        for w in pg['page'].get_text('words'):
            if w[2] > RIGHT_LIMIT + 2:
                over += 1
                worst = max(worst, w[2])
    if over:
        problems.append(
            ('FAIL', f'L4 {over} 处文字超出右边界（最远 {worst:.1f} pt，'
                     f'边界 {RIGHT_LIMIT:.1f} pt）'))
    else:
        print(f'  L4 无越界（右边界 {RIGHT_LIMIT:.1f} pt）')

    # ---------- L5 字体与缺字 ----------
    fonts = set()
    for pg in pages:
        for f in pg['page'].get_fonts():
            fonts.add(f[3])
    allt = ''.join(pg['text'] for pg in pages)
    if '\ufffd' in allt:
        cnt = allt.count('\ufffd')
        problems.append(('FAIL', f'L5 出现 {cnt} 个 U+FFFD（缺字符号）'))
    else:
        print(f'  L5 无缺字；嵌入字体 {len(fonts)} 种：'
              f'{", ".join(sorted(f.split("+")[-1] for f in fonts))}')

    # ---------- 报告 ----------
    print()
    if args.verbose:
        for pg in pages:
            print(f"      p{pg['no']:>2} {pg['chars']:>5} 字  图{pg['imgs']}")
        print()

    for lvl, msg in problems:
        print(f'  [{lvl}] {msg}')

    fails = sum(1 for lv, _ in problems if lv == 'FAIL')
    warns = sum(1 for lv, _ in problems if lv == 'WARN')
    print(f'\n共 {n} 页 ｜ FAIL {fails} / WARN {warns}')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
