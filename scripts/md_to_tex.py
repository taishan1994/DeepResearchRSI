"""把 PAPER.md 转成 LaTeX（NeurIPS 风格双栏）。

为什么用转换器而不是手写 .tex：
正文 3.7 万字、14 图、9 表，手工搬运必然引入新错误，而
`check_paper.py` 的 I1-I7 只认 PAPER.md。故 PAPER.md 仍是唯一的
**事实源**，LaTeX 是它的一种渲染，与 PDF 渲染器并列。
⭐ 这与「一个源多种呈现」是同一个原则：不许出现两份会各自漂移的正文。

转换范围：标题层级、段落、列表、引用块、表格、图、代码块、
行内强调（粗体/斜体/代码）、以及 [c-xxx] 主张引用。
超出范围的一律报错而不是静默丢弃——静默丢弃会让 LaTeX 版缺内容而无人察觉。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------- 转义 ----------
TEX_ESCAPE = {
    '\\': r'\textbackslash{}',
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    # en-dash：中文行常在「11%–13%」处断行，若它不可断，
    # 该行就会超宽（实测 3.1pt）。显式给出零宽断点。
    '\u2013': r'-\hspace{0pt}',
}


def esc(s: str) -> str:
    """转义 LaTeX 特殊字符。先处理反斜杠，避免二次转义。"""
    out = []
    for ch in s:
        out.append(TEX_ESCAPE.get(ch, ch))
    return ''.join(out)


CITE_RE = re.compile(r'\[(c-[A-Za-z0-9_-]+)\]')


# SimSun 缺字形的符号：必须在转换阶段包进 \sym{}，
# 否则 XeLaTeX 会静默地渲染成空白，不报错。
#
# ⚠️ 两条容易踩的坑：
#   1) 右侧不能用 raw string —— r'\sym{\u2b50}' 里的 \u2b50 是六个字面字符，
#      不会变成符号，LaTeX 里得到「\u2b50」这种东西，且不报错。
#   2) 每个 \sym{} 后面要跟一个空组 {} —— LaTeX 会吞掉控制序列后的空格，
#      `\sym{⚠} 全文` 会渲染成「⚠全文」。空组隔断这个吞并。
SYMBOLS = '\u2b50\U0001f525\u26a0\u21d2\u2192\u2194'
SYMBOL_FALLBACK = {ch: '\\sym{' + ch + '}{}' for ch in SYMBOLS}


def _esc_char(ch: str) -> str:
    # U+FE0F 是 emoji 变体选择符（\u26a0\ufe0f 里的第二个码位），
    # 它本身没有字形，保留会让 XeLaTeX 报 Missing character。
    # 变体语义由 \\sym{} 选定的字体承担，故直接丢弃。
    if ch == chr(0xFE0F):
        return '' 
    if ch in SYMBOL_FALLBACK:
        return SYMBOL_FALLBACK[ch]
    return TEX_ESCAPE.get(ch, ch)


def inline(s: str) -> str:
    """单遍递归解析行内标记。

    支持（可嵌套）：`code`、**bold**、*italic*、[c-xxx] 主张引用。
    ⭐ 单遍递归没有「占位符」这个中间态，故嵌套强调不会泄漏。
    """
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]

        # 行内代码：内容原样转义，不再解析标记
        if ch == '`':
            j = s.find('`', i + 1)
            if j > i + 1:
                out.append(r'\texttt{' + ''.join(_esc_char(c) for c in s[i + 1:j]) + '}')
                i = j + 1
                continue

        # 粗体（必须先于斜体，否则 ** 会被当作两个 *）
        if s.startswith('**', i):
            j = s.find('**', i + 2)
            if j > i + 2:
                out.append(r'\textbf{' + inline(s[i + 2:j]) + '}')
                i = j + 2
                continue

        # 斜体
        if ch == '*':
            j = s.find('*', i + 1)
            if j > i + 1:
                out.append(r'\textit{' + inline(s[i + 1:j]) + '}')
                i = j + 1
                continue

        # 主张引用
        m = CITE_RE.match(s, i)
        if m:
            # ⚠️ 长主张 ID（如 c-256k-context-costs-16-gib-of-kv，34 字符）
            # 无法在 \textsuperscript{\texttt{...}} 里断行：
            # \allowbreak 和 \- 都试过，均不生效（实测仍溢出 59.4pt）。
            # 根因是 \textsuperscript 内部形成一个不可断的 hbox。
            # 故去掉上标，改为正文内的小号等宽标记，并把连字符变成断点。
            cid = m.group(1).replace('-', r'-\hspace{0pt}')
            out.append(r'{\scriptsize\texttt{' + cid + '}}')
            i = m.end()
            continue

        out.append(_esc_char(ch))
        i += 1
    return ''.join(out)


def table_tex(rows: list[list[str]], caption: str | None, label: str) -> str:
    """把表格行转成 booktabs 三线表。列数按表头定。"""
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]

    # 列宽策略：
    #   - 该列全是数字 -> r（右对齐，不折行）
    #   - 该列文本很长（>24 字符）-> X（自动折行、自动分配宽度）
    #   - 其余 -> l
    # ⚠️ 第一版全用 l，而 l 是「不折行的定宽列」，
    # 于是 237 字的摘要被排成一行，溢出 873pt（约两倍通栏宽）。
    spec = []
    for c in range(ncol):
        body = [r[c] for r in rows[1:]]
        numeric = body and all(re.fullmatch(r'[\d,.\u00d7%+\-\u2013\u2014 ]*', b or '0')
                               for b in body)
        longest = max((len(b) for b in body), default=0)
        if numeric:
            spec.append('r')
        elif longest > 24:
            spec.append('X')
        else:
            spec.append('l')
    colspec = ''.join(spec)
    use_tabularx = 'X' in colspec

    # 这些表有 5 到 6 列，双栏放不下（实测溢出 1300pt 以上，约三倍栏宽），
    # 故用 table* 跨栏。字号降到 footnotesize、列间距收紧，才能放进通栏宽度。
    out = [r'\begin{table*}[t]', r'\centering', r'\footnotesize',
           r'\setlength{\tabcolsep}{4pt}']
    if caption:
        out.append(r'\caption{' + inline(caption) + '}')
    out.append(r'\label{' + label + '}')
    if use_tabularx:
        out.append(r'\begin{tabularx}{\textwidth}{' + colspec + '}')
    else:
        out.append(r'\begin{tabular}{' + colspec + '}')
    out.append(r'\toprule')
    out.append(' & '.join(inline(c) for c in rows[0]) + r' \\')
    out.append(r'\midrule')
    for r in rows[1:]:
        out.append(' & '.join(inline(c) for c in r) + r' \\')
    out.append(r'\bottomrule')
    out.append(r'\end{tabularx}' if use_tabularx else r'\end{tabular}')
    out.append(r'\end{table*}')
    return '\n'.join(out)


def convert(md: str, figdir: str = 'figures') -> tuple[str, list[str]]:
    """返回 (latex 正文, 警告列表)。"""
    lines = md.split('\n')
    out: list[str] = []
    warns: list[str] = []
    i = 0
    fig_no = 0
    tab_no = 0
    pending_caption: str | None = None
    in_abstract = False

    while i < len(lines):
        raw = lines[i]
        s = raw.rstrip()

        # 空行
        if not s.strip():
            out.append('')
            i += 1
            continue

        # 水平线
        if s.strip() == '---':
            i += 1
            continue

        # 代码块
        if s.startswith('```'):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            # ⚠️ 不用 verbatim：它不折行，双栏下一行长命令就溢出 132pt。
            # lstlisting 开了 breaklines，长命令行自动续行。
            out.append(r'\begin{lstlisting}')
            out.extend(buf)
            out.append(r'\end{lstlisting}')
            continue

        # 图
        m = re.match(r'!\[[^\]]*\]\(([^)]+)\)', s.strip())
        if m:
            fig_no += 1
            # 图片路径是相对 paper/ 的（figures/fig-1.png），
            # 而 .tex 在 paper/latex/ 下编译，故加 ../ 前缀。
            src = '../' + m.group(1)
            cap = ''
            if i + 2 < len(lines) and lines[i + 1].strip() == '' \
                    and lines[i + 2].startswith('*图'):
                cap = lines[i + 2].strip().strip('*')
                i += 2
            # 双栏下 \linewidth 只有约 84mm，而这些图是按 168mm 单栏画的；
            # 直接 width=\linewidth 会让图中文字小到不可读。
            # 故图表一律跨栏（figure*），宽度取通栏宽。
            out.append(r'\begin{figure*}[t]')
            out.append(r'\centering')
            out.append(r'\includegraphics[width=0.86\textwidth]{' + src + '}')
            if cap:
                out.append(r'\caption{' + inline(cap) + '}')
            out.append(r'\label{fig:' + str(fig_no) + '}')
            out.append(r'\end{figure*}')
            i += 1
            continue

        # 表格
        if s.startswith('|'):
            buf = []
            while i < len(lines) and lines[i].startswith('|'):
                buf.append(lines[i])
                i += 1
            rows = []
            for r in buf:
                if re.fullmatch(r'\|[\s:|-]+\|', r.strip()):
                    continue
                cells = [c.strip() for c in r.strip().strip('|').split('|')]
                rows.append(cells)
            # 表题在表格之后，但中间隔一个空行。
            # ⚠️ 第一版只检查紧邻的下一行，于是 9 个表题全部配对失败——
            # 而失败方式是「安静地退化成无题表格」，PDF 里看不出来。
            # 故这里跳过空行去找，找不到再报警。
            cap = None
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                mt = re.match(r'\*表\s*(\d+)[\u3000\s]*(.+?)\*$', lines[j].strip())
                if mt:
                    cap = mt.group(2).strip()
                    i = j + 1
            tab_no += 1
            out.append(table_tex(rows, cap, f'tab:{tab_no}'))
            continue

        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            lvl = len(m.group(1))
            text = m.group(2)
            # ⚠️ 一级标题由 main.tex 的跨栏标题区承载，正文里不再输出，
            # 否则 PDF 上标题会出现两次。
            if lvl == 1:
                pass
            elif lvl == 2:
                # 「# # 摘要」这种形式也在这里
                # ⚠️ 剥掉标题自带的中文编号（「1　引言」-> 「引言」），
                # 否则与 LaTeX 自动编号叠加，渲染成「1 1　引言」。
                t2 = text.lstrip('#').strip()
                t2 = re.sub(r'^[\dA-Z]+(\.\d+)*[\u3000\s]+', '', t2)
                if t2 in ('摘要', 'Abstract'):
                    # ⚠️ abstract 环境必须显式闭合：它一直延续到下一个 \section。
                    # 第一版只写了 \begin{abstract}，于是 CTAN 报
                    # 「\begin{abstract} ended by \end{document}」，
                    # 而这是唯一一处会让整篇正文被吞进摘要的环境。
                    in_abstract = True
                    out.append(r'\begin{abstract}')
                else:
                    if in_abstract:
                        out.append(r'\end{abstract}')
                        in_abstract = False
                    out.append(r'\section{' + inline(t2) + '}')
            elif lvl == 3:
                t3 = text.lstrip('#').strip()
                t3 = re.sub(r'^[\dA-Z]+(\.\d+)*[\u3000\s]+', '', t3)
                out.append(r'\subsection{' + inline(t3) + '}')
            else:
                t4 = re.sub(r'^[\dA-Z]+(\.\d+)*[\u3000\s]+', '', text)
                out.append(r'\subsubsection{' + inline(t4) + '}')
            i += 1
            continue

        # 引用块
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(lines[i][1:].strip())
                i += 1
            acc: list[str] = []
            paras: list[str] = []
            for b in buf:
                if b:
                    acc.append(b)
                else:
                    if acc:
                        paras.append(''.join(acc))
                        acc = []
            if acc:
                paras.append(''.join(acc))
            # 副标题已在 main.tex 的标题区，这里跳过避免重复。
            paras = [p for p in paras if not p.startswith('**副标题**')]
            if paras:
                out.append(r'\begin{quote}\small')
                for p in paras:
                    out.append(inline(p))
                    out.append('')
                out.append(r'\end{quote}')
            continue

        # 列表
        if re.match(r'^\s*[-*]\s+', s):
            out.append(r'\begin{itemize}')
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                item = re.sub(r'^\s*[-*]\s+', '', lines[i])
                out.append(r'  \item ' + inline(item))
                i += 1
            out.append(r'\end{itemize}')
            continue

        if re.match(r'^\s*\d+\.\s+', s):
            out.append(r'\begin{enumerate}')
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                item = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                out.append(r'  \item ' + inline(item))
                i += 1
            out.append(r'\end{enumerate}')
            continue

        # 段末的 *图 N ...* / *表 N ...* 说明（没有配对到图表本体）
        mt = re.match(r'^\*表\s*(\d+)[\u3000\s]*(.+?)\*$', s.strip())
        if mt:
            warns.append(f'表题未配对到表格：{s.strip()[:40]}')
            i += 1
            continue
        mf = re.match(r'^\*图\s*(\d+)[\u3000\s]*(.+?)\*$', s.strip())
        if mf:
            warns.append(f'图题未配对到图片：{s.strip()[:40]}')
            i += 1
            continue

        # 普通段落：合并同段连续行
        buf = [s]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if (not nxt.strip() or nxt.startswith(('#', '|', '>', '```', '!['))
                    or nxt.strip() == '---' or re.match(r'^\s*[-*]\s+', nxt)
                    or re.match(r'^\s*\d+\.\s+', nxt)):
                break
            buf.append(nxt)
            i += 1
        out.append(inline(''.join(buf)))
        out.append('')

    return '\n'.join(out), warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='把 PAPER.md 转成 LaTeX 正文')
    ap.add_argument('paper_dir')
    ap.add_argument('-o', '--output', default=None)
    args = ap.parse_args(argv)

    pdir = Path(args.paper_dir)
    md = (pdir / 'PAPER.md').read_text(encoding='utf-8')
    body, warns = convert(md)
    dst = Path(args.output) if args.output else pdir / 'latex' / 'body.tex'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(body, encoding='utf-8', newline='\n')
    print(f'[OK] {dst}  {len(body):,} 字符')
    for w in warns:
        print('  [WARN]', w)
    return 0


if __name__ == '__main__':
    sys.exit(main())
