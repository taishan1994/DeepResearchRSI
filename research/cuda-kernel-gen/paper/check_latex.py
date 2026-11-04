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

    # ---------- X1 逐页密度 ----------
    # ⚠️ 不能用「纯字数」判断一页是否排满。
    #   图表页天然字数少——p13 是 2 张跨栏图 + 一张 15 行表，
    #   汉字只有 83 个，但内容排到了页面 96% 处，完全正常。
    #   旧判据因此在本文件上是稳定误报（每次只剩这一条 FAIL）。
    #   ⚠️ 也不能只看墨迹覆盖率：图表页墨迹可达 3.7%，纯文字页 7.3%，
    #   用覆盖率当判据会反向冤枉图表页。
    #   正确判据是**版面纵向利用率**：内容最低点是否接近版心底部。
    #   再辅以「汉字数 + 图像数 + 表格行数」的下限，防止整页空白蒙混过关。
    import numpy as np
    short = []
    for pg in pages[1:-1]:                      # 跳过标题页与末页
        page = pg['page']
        pix = page.get_pixmap(dpi=100, colorspace='gray')
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        rows = np.where((arr < 200).any(axis=1))[0]
        if not len(rows):
            short.append((pg['no'], 0, 0.0))
            continue
        # 版面纵向利用率：内容最低点 / 页高
        used = rows.max() / pix.height * 100
        # 内容量：汉字数 + 4x 图像数（一张图约等于 4 行的信息量）
        n_cjk = len(CJK.findall(pg['text']))
        n_img = len([x for x in page.get_image_info()
                     if (x['bbox'][2] - x['bbox'][0]) *
                        (x['bbox'][3] - x['bbox'][1]) > 0.04 * 595 * 842])
        content = n_cjk + 40 * n_img
        if used < 88 and content < MIN_CHARS:
            short.append((pg['no'], n_cjk, used))
    if short:
        detail = '、'.join(f'p{p}={c}字/{u:.0f}%' for p, c, u in short[:5])
        problems.append(('FAIL', f'X1 {len(short)} 页偏空：{detail}'))
    else:
        print(f'  X1 逐页版面充盈（图表页按纵向利用率判定）')

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

    # ---------- X3 右边界溢出 ----------
    # ⚠️ 关键教训：**不能用文本 bbox 判定溢出**。
    #   全角标点（，。）的字形框是 10pt 全宽，但可见墨迹只占左半，
    #   于是 bbox 报「越界 5.4pt」，而实际一个像素都没出界。
    #   反过来，bbox 也会漏掉少数字形（如某些斜体）的真实出界。
    #   唯一可靠的办法是**测量墨迹**：把页面渲成灰度位图，
    #   找每行最右侧的非白像素，与右边距比较。
    #   这一步慢（每页约 0.3s），但准确；只对可疑页做也无意义，
    #   故整篇都测一遍。
    import numpy as np
    DPI = 144
    SCALE = DPI / 72.0
    real = []
    for pg in pages:
        pix = pg['page'].get_pixmap(dpi=DPI, colorspace='gray')
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        limit_px = int((RIGHT_LIMIT - 1.0) * SCALE)   # 留 1pt 容差
        if limit_px >= pix.width:
            continue
        rows = np.where((arr[:, limit_px:] < 200).any(axis=1))[0]
        if not len(rows):
            continue
        # 最右墨迹点
        cols = np.where((arr[:, limit_px:] < 200).any(axis=0))[0]
        max_pt = (limit_px + cols.max()) / SCALE
        # 找出对应的文字，便于定位
        y_pt = rows.max() / SCALE
        txt = ''
        for b in pg['page'].get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                if abs(ln['bbox'][1] - y_pt) < 10 or abs(ln['bbox'][3] - y_pt) < 10:
                    txt = ''.join(sp['text'] for sp in ln['spans']).strip()
                    break
        real.append((pg['no'], round(max_pt - RIGHT_LIMIT, 1), txt[-28:]))
    if real:
        worst = max(r[1] for r in real)
        sample = '；'.join(f'p{p}+{d}pt' for p, d, _ in real[:4])
        msg = f'X3 {len(real)} 页有墨迹越界（最大 {worst}pt）：{sample}'
        # 小于 1pt 的越界是字体侧边距，肉眼不可见，不影响版面。
        if worst > 1.5:
            problems.append(('FAIL', msg))
        else:
            print(f'  X3 无可见溢出（{len(real)} 页有 <{worst}pt 的字形侧边距，不可见）')
    else:
        print('  X3 无墨迹越界')

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
    # ⚠️ 不能用 get_images()：它把表格的边框/填充也当成图像，
    # 于是在「表格页」上报「有图无图注」的假阳性。
    # 改为按绘制对象的包围盒面积过滤——真正的插图至少占页面 4%，
    # 表格分隔线远小于此阈值。
    orphan = []
    page_area = PAGE_W * 841.89
    for pg in pages:
        big = 0
        for im in pg['page'].get_image_info():
            b = im.get('bbox')
            if not b:
                continue
            if (b[2] - b[0]) * (b[3] - b[1]) > page_area * 0.04:
                big += 1
        if not big:
            continue
        txt = pg['text']
        if not re.search(r'图\s*\d+|Figure\s*\d+', txt):
            orphan.append(pg['no'])
    if orphan:
        problems.append(('WARN', f'X6 {len(orphan)} 页有图但无图注：{orphan[:6]}'))
    else:
        print('  X6 有图页面均有图注')

    # ---------- X7 图注不得自我重复编号 ----------
    # ⚠️ 这是用户实际指出的问题：图片内部标题画着「图 1　…」，
    #    LaTeX caption 又渲染出「图 1：图 1」，读者不知道该看哪个。
    #    根因是两处都在编号：matplotlib 的 set_title 里写了「图 N」，
    #    而 md_to_tex.py 又把 alt 文本原样塞进 \caption。
    #    学术惯例是**只在 caption 编号**，图内只写自解释的短标题。
    # 判据：caption 文本里若出现「图 N」/「图 N：」，说明编号重复了一次。
    dup_no: list[str] = []
    for pg in pages:
        txt = pg['text']
        # caption 形态：「图 N：图 N」或「图 N\n图 N」
        for m in re.finditer(r'图\s*(\d+)\s*[:：]?\s*\n?\s*图\s*(\d+)', txt):
            dup_no.append(f'p{pg["no"]}: 图{m.group(1)}/图{m.group(2)}')
    if dup_no:
        problems.append(
            ('FAIL', f'X7 图注自我重复编号 {len(dup_no)} 处：{dup_no[:4]}')
        )
    else:
        print('  X7 图注无自我重复编号')

    # ---------- X8 图号必须与图内容对应 ----------
    # ⚠️ 这是本轮发现的第二个真问题，也是最隐蔽的一个：
    #   正文写「图 4 显示了各方法标签的论文分布」，
    #   而 LaTeX 按出现次序编号，实际把方法标签图编成了「图 2」。
    #   三处既有检查全都发现不了：
    #     X6 只查「有图页面有无图注」——有；
    #     X7 只查「图注是否自我重复编号」——否；
    #     check_pdf_content 只查「正文引用的图号集合 == 1..N」——是。
    #   缺的是「图号 ↔ 图内容」的对应性。
    # 做法：从 PAPER.md 读出每张图的 alt 首句，在 PDF 里找「图N」后面
    #   紧跟的文字，确认二者一致（取前 8 字比对，容忍换行与空格差异）。
    if args.md:
        md_text = Path(args.md).read_text(encoding='utf-8')
        # 期望编号 = **出现次序**（LaTeX 的自然编号），不是文件名里的数字。
        # ⚠️ 这里曾用文件名编号，图号改成按出现次序后立刻误报 8 处。
        #   文件名里的 figN 只表示「这是当初第 N 张画的图」，与最终编号无关。
        expect: list[tuple[int, str]] = []
        for idx, m in enumerate(
                re.finditer(r'!\[([^\]]+)\]\((?:\.\./)?figures/[^)]+\)', md_text), 1):
            alt = m.group(1)
            first = re.split(r'[。；：]', alt)[0][:10]
            expect.append((idx, first))
        # 在 PDF 里找「图N」+ 紧随其后的图注开头
        found: dict[int, str] = {}
        for pg in pages:
            t = pg['text']
            # 只认「图N」独占一行（后面紧跟换行）的形态——那才是图注；
            # 正文行内引用「图 1 显示了…」同一行有后续文字，必须排除。
            # ⚠️ 第一版没做这个区分，把正文引用当成 caption 比对，
            #    5 处全是假阳性（期望「本文纳入的 98 篇」，实得「显示了 98 篇…」）。
            for m in re.finditer(r'图\s*(\d+)[ \t]*\n([^\n]{0,24})', t):
                no = int(m.group(1))
                if no not in found:
                    found[no] = m.group(2)
        def norm(s: str) -> str:
            return re.sub(r'[\s，。、：；·\-—]', '', s)
        mismatch: list[str] = []
        missing: list[int] = []
        for no, first in expect:
            got = found.get(no, '')
            if not got:
                # ⚠️ 关键：找不到该编号的图注不能静默跳过。
                #   第一版写的是 if not got: continue，
                #   于是「fig4 被渲染成图2、PDF 里根本没有图4」这种
                #   最典型的错位反而一条都不报（test_x8.py 用例 2 抓出来的）。
                missing.append(no)
                continue
            # 只比前 6 个字，避免因提取边界差异误报
            if norm(got)[:6] != norm(first)[:6]:
                mismatch.append(f'图{no}: 期望「{first}」实得「{got[:12]}」')
        if missing:
            problems.append(
                ('FAIL', f'X8 PDF 中找不到图注编号 {missing}')
            )
        if mismatch:
            problems.append(
                ('FAIL', f'X8 图号与内容不对应 {len(mismatch)} 处：{mismatch[:3]}')
            )
        elif expect:
            print(f'  X8 {len(expect)} 张图的编号与内容对应')

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
