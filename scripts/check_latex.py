"""LaTeX 版 PDF 的版式校验。

为什么不能复用 `check_layout.py`：
那个脚本按**单栏 A4、右边距 538.6pt** 写死了判据，而 LaTeX 版是双栏，
栏右边界是 537.2pt，且分左右栏。两套版式的几何完全不同。

检查项：
  X1  逐页字数下限（排除标题页与末页）
  X2  无 U+FFFD、字体已嵌入
  X3  右边界溢出——**排除中文标点悬挂**
  X4  行宽填充率（相对栏宽，双栏要分栏算）
  X5  内容完整性：PAPER.md 的每个段落都能在 PDF 里找到
  X6  图与图注同页

⚠️ X3 的关键：中文排版允许句读标点悬挂到栏外（「行尾标点不占字宽」），
   XeCJK 默认就这么做。若把悬挂也算越界，会得到 50 多处假阳性。
   故只把「以非标点结尾且超出 >2pt」算真溢出。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

PAGE_W = 595.276
MARGIN_MM = 20.5
MARGIN_PT = MARGIN_MM * 72 / 25.4
RIGHT_LIMIT = PAGE_W - MARGIN_PT          # 537.2
COL_GAP_PT = 0.72 * 72 / 25.4 / 2         # 半栏间距
CJK = re.compile(r'[\u4e00-\u9fff]')

# 允许悬挂到栏外的中文标点
HANGING = '。，、：；）」』】》？！…·'

MIN_CHARS = 120          # 双栏单页有效字数下限（图表页会更少）
OVERFLOW_TOL = 2.0       # pt，小于此视为舍入
FILL_MIN = 0.93          # 行宽填充率下限


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='LaTeX 版 PDF 版式校验')
    ap.add_argument('pdf')
    ap.add_argument('--md', default=None, help='PAPER.md 路径（做完整性对账）')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args(argv)

    doc = pymupdf.open(args.pdf)
    n = doc.page_count
    pages = [{'no': i + 1, 'page': doc[i], 'text': doc[i].get_text()} for i in range(n)]
    problems: list[tuple[str, str]] = []

    # ---------- X1 逐页字数 ----------
    short = []
    for pg in pages[1:-1]:                      # 跳过标题页与末页
        c = len(CJK.findall(pg['text']))
        if c < MIN_CHARS:
            short.append((pg['no'], c))
    if short:
        detail = '、'.join(f'p{p}={c}字' for p, c in short[:5])
        problems.append(('FAIL', f'X1 {len(short)} 页字数不足：{detail}'))
    else:
        lo = min(len(CJK.findall(pg['text'])) for pg in pages[1:-1])
        print(f'  X1 逐页字数达标（最少 {lo} 字）')

    # ---------- X2 缺字与字体 ----------
    allt = ''.join(pg['text'] for pg in pages)
    fonts = set()
    for pg in pages:
        for f in pg['page'].get_fonts():
            fonts.add(f[3])
    if '\ufffd' in allt:
        problems.append(('FAIL', f'X2 出现 {allt.count(chr(0xFFFD))} 个 U+FFFD'))
    else:
        names = ', '.join(sorted(f.split('+')[-1] for f in fonts))
        print(f'  X2 无缺字；嵌入字体 {len(fonts)} 种：{names}')

    # ---------- X3 右边界溢出（排除标点悬挂）----------
    real, hanging = [], 0
    for pg in pages:
        for b in pg['page'].get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                x1 = ln['bbox'][2]
                if x1 <= RIGHT_LIMIT + OVERFLOW_TOL:
                    continue
                txt = ''.join(sp['text'] for sp in ln['spans']).rstrip()
                if not txt:
                    continue
                # ⚠️ 判据不能只看「最后一个字符是什么」。
                # 中文行常以「字 + 标点」结尾，标点悬挂出界，
                # 但若标点后还跟着拉丁字符（如 7,346 对 6,267（+17.2%）、），
                # 末字符仍是标点。故改成：**只要该行任意位置含中文，
                # 且末尾 3 个字符里有标点**，就判为悬挂。
                tail = txt[-3:]
                has_cjk = bool(CJK.search(txt))
                if has_cjk and any(c in HANGING for c in tail):
                    hanging += 1
                else:
                    real.append((pg['no'], round(x1 - RIGHT_LIMIT, 1), txt[-30:]))
    if real:
        worst = max(r[1] for r in real)
        sample = '；'.join(f'p{p}+{d}pt' for p, d, _ in real[:4])
        problems.append(('FAIL', f'X3 {len(real)} 处真溢出（最大 {worst}pt）：{sample}'))
    else:
        print(f'  X3 无真溢出（另 {hanging} 处中文标点悬挂，属正常排版）')

    # ---------- X4 行宽填充率（分栏）----------
    fills = []
    for pg in pages:
        rows = []
        for b in pg['page'].get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                txt = ''.join(sp['text'] for sp in ln['spans']).strip()
                if not txt or not ln['spans']:
                    continue
                if abs(ln['spans'][0]['size'] - 10) > 0.8:
                    continue
                rows.append((round(ln['bbox'][1], 1), round(ln['bbox'][0], 1),
                             round(ln['bbox'][2], 1), txt))
        rows.sort()
        for k, (y, x0, x1, txt) in enumerate(rows):
            if len(txt) < 20 or k + 1 >= len(rows):
                continue
            ny, nx0, _nx1, _ = rows[k + 1]
            if abs(nx0 - x0) < 1.5 and 0 < ny - y < 24:
                # 双栏：左栏的右边界是栏中线，右栏才是页右边界。
                # 不分栏会让右栏的行被误判为「只填到一半」。
                col_right = (RIGHT_LIMIT if x0 > PAGE_W / 2
                             else PAGE_W / 2 - COL_GAP_PT)
                fills.append((x1 / col_right, x1))
    if len(fills) >= 20:
        # ⚠️ 双栏必须分栏算：左栏右端到栏中线，右栏到页右边。
        fills.sort()
        ratios = sorted(f[0] for f in fills)
        ratio = ratios[len(ratios) // 2]
        mid_pt = sorted(f[1] for f in fills)[len(fills) // 2]
        msg = (f'同段非末行 {len(fills)} 条，右端中位 {mid_pt:.1f}pt，'
               f'填充率中位 {ratio * 100:.1f}%')
        if ratio < FILL_MIN:
            problems.append(('FAIL', f'X4 行宽填充率过低：{msg}'))
        else:
            print(f'  X4 行宽填充正常：{msg}')
    else:
        print(f'  X4 样本不足（{len(fills)} 条），跳过')

    # ---------- X5 内容完整性 ----------
    if args.md:
        md = Path(args.md).read_text(encoding='utf-8')
        flat = re.sub(r'[^\u4e00-\u9fff]', '', allt)
        paras = [p.strip() for p in md.split('\n')
                 if p.strip() and not p.strip().startswith(
                     ('#', '|', '>', '!', '*表', '*图', '---'))]
        miss = []
        for p in paras:
            core = re.sub(r'[^\u4e00-\u9fff]', '', p)
            if len(core) < 12:
                continue
            wins = [core[i:i + 8] for i in (0, len(core) // 2, max(0, len(core) - 8))]
            if not any(w in flat for w in wins):
                miss.append(core[:24])
        if miss:
            problems.append(('FAIL', f'X5 正文有 {len(miss)} 段在 PDF 中找不到：'
                                     + '；'.join(miss[:4])))
        else:
            print(f'  X5 内容完整：源 {len(paras)} 段全部见于 PDF')

    # ---------- X6 图与图注同页 ----------
    orphan = []
    for pg in pages:
        imgs = pg['page'].get_images()
        if not imgs:
            continue
        txt = pg['text']
        if not re.search(r'图\s*\d+|Figure\s*\d+', txt):
            orphan.append(pg['no'])
    if orphan:
        problems.append(('WARN', f'X6 {len(orphan)} 页有图但无图注：{orphan[:6]}'))
    else:
        print('  X6 有图页面均有图注')

    # ---------- 报告 ----------
    print()
    if args.verbose:
        for pg in pages:
            print(f"      p{pg['no']:>2} {len(CJK.findall(pg['text'])):>4} 字")
        print()
    for lvl, msg in problems:
        print(f'  [{lvl}] {msg}')
    fails = sum(1 for lv, _ in problems if lv == 'FAIL')
    warns = sum(1 for lv, _ in problems if lv == 'WARN')
    print(f'\n共 {n} 页 ｜ FAIL {fails} / WARN {warns}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
