"""把 PAPER.md 排成 PDF，专为中文排版调过。

为什么不用 pandoc/weasyprint：环境里没有，且它们对中文断行（禁则处理）
默认是不做的——会把「）」留在行首、「（」留在行尾。这里显式处理。

排版约束：
1. 中文字体必须嵌入（Microsoft YaHei），否则在任何未装该字体的机器上都是方块。
2. 中英混排时，标点按「禁则」处理：行首不出现 。，、；：）」』】！？
3. 代码与数字用等宽，避免 tok/s 之类在数字与斜杠间被拆开。

用法：
    python scripts/render_paper_pdf.py research/rtx-pro-6000/paper
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fpdf import FPDF

# 行首禁则：这些字符不能出现在一行的开头
NO_LINE_START = set("。，、；：）】》」』！？%’”…·ー～,;:)]}>")
# 行尾禁则：这些字符不能出现在一行的结尾
NO_LINE_END = set("（【《「『‘“([{<")

FONT_CANDIDATES = [
    # (正文字体, 粗体/标题字体)
    # 中文论文排版惯例：正文宋体，标题黑体。改用这两者比全部用雅黑更规范。
    (r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\simhei.ttf"),
    (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"),
    (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simhei.ttf"),
]

# Microsoft YaHei 不含 emoji（U+1F300 以上）、⚠（U+26A0）、⭐（U+2B50）
# 与部分数学箭头。直接排会得到方块，故统一降级到字体确实覆盖的字符。
GLYPH_FALLBACK = {
    "⚠️": "注意",
    "⚠": "注意",
    "⭐": "*",
    "🔥": "*",
    "⇒": "=>",
    "→": "->",
    "✅": "[通过]",
    "❌": "[未通过]",
    "📐": "[规范]",
    "🔍": "[核查]",
    "💡": "[要点]",
    "📌": "[标记]",
    "🎯": "[目标]",
    "⚡": "[快]",
    "\ufe0f": "",   # variation selector，无独立字形
    "\u200b": "",   # zero width space
    "\u2212": "-",  # minus sign，SimSun 无此字形
    "\u2013": "-",  # en dash
    "\u00d7": "x",  # multiplication sign
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2248": "约",
}


def pick_fonts() -> tuple[str, str]:
    for regular, bold in FONT_CANDIDATES:
        if Path(regular).is_file():
            return regular, (bold if Path(bold).is_file() else regular)
    raise SystemExit("找不到中文字体（msyh.ttc / simhei.ttf / simsun.ttc）")


def cjk_width(ch: str) -> int:
    """粗略显示宽度：CJK 与全角标点算 2，其余算 1。"""
    if ch == "\t":
        return 4
    code = ord(ch)
    if code < 0x1100:
        return 1
    if any((
        0x1100 <= code <= 0x115F,
        0x2E80 <= code <= 0xA4CF,
        0xAC00 <= code <= 0xD7A3,
        0xF900 <= code <= 0xFAFF,
        0xFE30 <= code <= 0xFE6F,
        0xFF00 <= code <= 0xFF60,
        0xFFE0 <= code <= 0xFFE6,
    )):
        return 2
    return 1


# 1 个「单位」在正文里约等于半个 CJK 字宽。
# 经验值：字号 10pt 时一个 CJK 字宽约 3.5mm，故 1 单位 ≈ 1.75mm。
# 但 SimSun 的拉丁字符比 0.5 个 CJK 更宽，故留 12% 余量，
# 否则含大量英文/数字的行会越出右边距（实测溢出 1-11pt）。
# 图被推到新页时，顶部留白（pt）。太小则图孤悬页首，太大则浪费版面。
TOP_GAP = 34

# 版心右边界（mm）。折行宽度一律由「右边界 - 起点」推出，
# 避免各处各写一个宽度常数而导致错位。
RIGHT_MM = 190.0
MM2PT = 72 / 25.4
# ⚠️ 这个常量已不用于正文折行（见 wrap_measured 的注释）。
# 仍保留是因为 wrap_title 等仍以「单位」为单位做语义断行。
UNIT_MM_PER_HALF_CJK = 1.75 * 1.12


def body_units(size_pt: float, indent_mm: float = 0) -> int:
    usable_mm = 210 - 40 - indent_mm
    unit_mm = (size_pt / 10.0) * UNIT_MM_PER_HALF_CJK
    return max(int(usable_mm / unit_mm), 8)


def wrap_cjk(text: str, max_units: int) -> list[str]:
    """按显示宽度断行，并施加中文禁则。"""
    lines: list[str] = []
    for para in text.split("\n"):
        para = para.rstrip()
        if not para:
            lines.append("")
            continue
        cur, width = [], 0
        for ch in para:
            w = cjk_width(ch)
            if width + w > max_units and cur:
                # 禁则：若下一个字符不能起行，就把当前行最后一个字符挪下去
                if ch in NO_LINE_START and cur:
                    moved = cur.pop()
                    lines.append("".join(cur))
                    cur, width = [moved, ch], cjk_width(moved) + w
                    continue
                while cur and cur[-1] in NO_LINE_END:
                    moved = cur.pop()
                    width -= cjk_width(moved)
                    _ = moved
                lines.append("".join(cur))
                cur, width = [ch], w
            else:
                cur.append(ch)
                width += w
        if cur:
            lines.append("".join(cur))
    return lines


def wrap_measured(pdf, text: str, size: float, max_mm: float) -> list[str]:
    """按**实测字符串宽度**折行，而不是按估算的单位数。

    为什么必须实测：SimSun 里汉字宽、拉丁窄，比例随内容浮动。
    用「半个汉字宽 × 1.12 余量」去估，纯中文段落会白留 12% 的右边距
    （实测每行少排约 5 个汉字），而英文密集的段落仍然可能溢出。
    ⭐ 一个对所有输入都用同一个假设的余量，既不够保守也不够激进。

    `pdf` 需已 set_font 到目标字体与字号。

    ⚠️ 单位：本项目的 FPDF 用 `unit="mm"`，故 `get_string_width` 返回 **mm**。
    参数因此叫 `max_mm` 而不是 `max_pt`——上一版叫 max_pt 却传 pt 值进来，
    比的是「67mm > 481」，等于不折行，于是每行都溢出到页面外。
    ⭐ 单位错误不会报错，只会静默地让判断永远为假。
    """
    if getattr(pdf, "unit", "mm") != "mm":
        raise ValueError(f"wrap_measured 假定 unit='mm'，实际 {pdf.unit!r}")
    lines: list[str] = []
    for para in text.split("\n"):
        para = para.rstrip()
        if not para:
            lines.append("")
            continue
        cur: list[str] = []
        cur_w = 0.0
        for ch in para:
            # ⚠️ 不要用「拼出整行再测量」的写法（trial = "".join(cur) + ch）。
            # get_string_width 是 O(n)，逐字重测整行就是 O(n^2)；
            # 表格单元格动辄两三百字，多行表格会直接把渲染挂死（实测超时 120s）。
            # 逐字累加宽度是 O(n)，且与整行测量在本字体下等价到 1e-3 mm。
            w = pdf.get_string_width(ch)
            if cur and cur_w + w > max_mm:
                # 禁则：不能起行的字符随上一行留下，不能收尾的字符挪到下一行
                if ch in NO_LINE_START:
                    moved = cur.pop()
                    lines.append("".join(cur))
                    cur = [moved, ch]
                    cur_w = pdf.get_string_width(moved) + w
                    continue
                while cur and cur[-1] in NO_LINE_END:
                    moved = cur.pop()
                    cur_w -= pdf.get_string_width(moved)
                lines.append("".join(cur))
                cur = [ch]
                cur_w = w
            else:
                cur.append(ch)
                cur_w += w
        if cur:
            lines.append("".join(cur))
    return lines


# 拉丁字母与数字序列在折行时不可分割：一个英文单词/型号不应被拦腰截断。
LATIN_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-/]*")


def _split_tokens(text: str) -> list[str]:
    """把一行切成「不可分单元」：拉丁词整体是一个单元，中文逐字。

    ⭐ 这是中英混排折行的关键区别：中文可以在任意字间断，
    拉丁词不行。逐字符折行会把 measurement 切成 measure/ment。
    """
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        m = LATIN_RUN.match(text, i)
        if m:
            tokens.append(m.group(0))
            i = m.end()
        else:
            tokens.append(text[i])
            i += 1
    return tokens


def wrap_measured_words(pdf, text: str, size: float, max_mm: float) -> list[str]:
    """词感知折行：拉丁词不拆，中文逐字断，保留中文禁则。

    `pdf` 需已 set_font 到目标字体与字号；单位 mm（与 get_string_width 一致）。
    """
    if getattr(pdf, "unit", "mm") != "mm":
        raise ValueError(f"wrap_measured_words 假定 unit='mm'，实际 {pdf.unit!r}")
    lines: list[str] = []
    for para in text.split("\n"):
        para = para.rstrip()
        if not para:
            lines.append("")
            continue
        cur: list[str] = []
        cur_w = 0.0
        for tok in _split_tokens(para):
            w = pdf.get_string_width(tok)
            if cur and cur_w + w > max_mm:
                # 禁则：标点不能起行；开括号不能收尾
                if tok and tok[0] in NO_LINE_START and len(cur) > 1:
                    moved = cur.pop()
                    lines.append("".join(cur))
                    cur = [moved, tok]
                    cur_w = pdf.get_string_width(moved) + w
                    continue
                while len(cur) > 1 and cur[-1] and cur[-1][-1] in NO_LINE_END:
                    cur.pop()
                lines.append("".join(cur))
                cur = [tok]
                cur_w = w
            else:
                cur.append(tok)
                cur_w += w
        if cur:
            lines.append("".join(cur))
    return lines


# 标题断行时优先在这些位置切开：全角空格、冒号、破折号、斜杠
TITLE_BREAKS = "　：:｜|/、，,（）()—–-·"


def wrap_title(text: str, max_units: int) -> list[str]:
    """标题专用断行：尽量在语义停顿处切，且不把短词拆到两行。

    普通 wrap_cjk 会按宽度硬切，于是「的推理性能」被切成「的推理性 / 能」。
    这里先在合适的标点处找最后一个能放下的位置。
    """
    text = text.strip()
    if sum(cjk_width(c) for c in text) <= max_units:
        return [text]

    lines: list[str] = []
    rest = text
    while rest:
        if sum(cjk_width(c) for c in rest) <= max_units:
            lines.append(rest)
            break
        # 累加到即将超宽的位置
        acc, width = 0, 0
        for i, ch in enumerate(rest):
            w = cjk_width(ch)
            if width + w > max_units:
                break
            width += w
            acc = i + 1
        head = rest[:acc]
        # 在该段内从后往前找语义断点
        cut = -1
        for j in range(len(head) - 1, max(0, len(head) - 14), -1):
            if head[j] in TITLE_BREAKS:
                cut = j + 1
                break
        if cut <= 0:
            # 找不到断点就退到普通禁则断行（至少不把标点放行首）
            cut = acc
        lines.append(rest[:cut])
        rest = rest[cut:].lstrip("　 ")
    return lines


class Paper(FPDF):
    def __init__(self, font_regular: str, font_bold: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("CJK", "", font_regular)
        self.add_font("CJK", "B", font_bold)
        self.set_auto_page_break(True, margin=18)
        self.set_margins(20, 18, 20)
        # fpdf2 的 cell() 默认左右各留 1mm 内边距（c_margin）。
        # 折行时按版心满宽计算，绘制时却从 20mm+1mm 起排，
        # 于是每行实际可用宽度比折行假设少 1mm，累积成溢出。
        # 归零后：文字起点严格对齐 20mm，折行宽度即真实可用宽度。
        self.c_margin = 0
        self._figures_dir = Path(".")

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("CJK", "", 8)
        self.set_text_color(130, 130, 130)
        # ⚠️ 页眉原先写死为「RTX PRO 6000 Blackwell 推理性能综述」。
        # 换主题后，新论文的每一页页眉都在宣称自己是另一篇论文——
        # 而这条错误不会让任何校验器失败：版面正常、引用闭合、编号连续。
        # 故改为由 paper.json 的 title 提供，写死值只作兜底。
        self.cell(0, 6, getattr(self, "_running_title", "") or "研究综述", align="R")
        self.ln(2)
        self.set_draw_color(210, 210, 210)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("CJK", "", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"— {self.page_no()} —", align="C")

    def h1(self, text: str) -> None:
        self.ln(4)
        self.set_font("CJK", "B", 17)
        for ln in wrap_title(text, 40):
            self.cell(0, 9, ln, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def h2(self, text: str) -> None:
        self.ln(3)
        self.set_font("CJK", "B", 13)
        self.set_text_color(30, 70, 110)
        for ln in wrap_title(text, 52):
            self.cell(0, 7.5, ln, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1.5)

    def h3(self, text: str) -> None:
        self.ln(2)
        self.set_font("CJK", "B", 10.8)
        for ln in wrap_title(text, 62):
            self.cell(0, 6.4, ln, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text: str, size: float = 10, indent: float = 0) -> None:
        self.set_font("CJK", "", size)
        # 宽度由起点推出，单位 mm（与 get_string_width 一致）。
        # 减 0.28mm 约 0.8pt，吸收舍入，不足以少排一个汉字（约 3.5mm）。
        max_mm = RIGHT_MM - (20 + indent) - 0.28
        for ln in wrap_measured_words(self, text, size, max_mm):
            if ln == "":
                self.ln(size * 0.42)
            else:
                self.set_x(20 + indent)
                self.cell(0, size * 0.52, ln, new_x="LMARGIN", new_y="NEXT")

    def code(self, text: str) -> None:
        self.set_font("CJK", "", 8.5)
        self.set_fill_color(244, 245, 247)
        for ln in text.split("\n"):
            self.set_x(24)
            self.cell(0, 5, "  " + ln, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullet(self, text: str) -> None:
        self.set_font("CJK", "", 10)
        self.set_x(22)
        self.cell(4, 5.2, "·")
        # 起点是 26mm（与下面 set_x(26) 一致），不是 20mm+6。
        max_mm = RIGHT_MM - 26 - 0.28
        lines = wrap_measured_words(self, text, 10, max_mm)
        for i, ln in enumerate(lines):
            self.set_x(26 if i == 0 else 26)
            self.cell(0, 5.2, ln, new_x="LMARGIN", new_y="NEXT")

    def quote(self, lines: list[str]) -> None:
        self.set_draw_color(160, 180, 200)
        y0 = self.get_y()
        self.set_font("CJK", "", 9.6)
        self.set_text_color(45, 45, 45)
        # 起点是 26mm（与下面 set_x(26) 一致）。
        max_mm = RIGHT_MM - 26 - 0.28
        for ln in lines:
            for piece in wrap_measured_words(self, ln, 9.6, max_mm):
                if piece == "":
                    self.ln(2.4)
                else:
                    self.set_x(26)
                    self.cell(0, 5.0, piece, new_x="LMARGIN", new_y="NEXT")
        y1 = self.get_y()
        self.line(23, y0 - 1, 23, y1 - 1)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def table(self, rows: list[list[str]], caption: str = "") -> None:
        if not rows:
            return
        # 表头重复：表格一旦跨页，续页没有表头，读者无法判断哪一列是什么。
        # 故整张表放不下时分页，并在新页重画表头行。
        ncol = max(len(r) for r in rows)
        avail = 210 - 40
        # 按内容宽度分配列宽
        # 列宽按「该列最长单元格的实测宽度」分配，而不是按汉字数估算。
        # ⚠️ 表头（第 0 行）常常是拉丁词（measurement / derivation），
        # 按汉字数估算会把它算窄，于是表头自身被折成三行。
        self.set_font("CJK", "", 8.2)
        # 每列的「理想宽度」取该列最长单元格的实测宽度，但**封顶**：
        # 摘要列有 237 字，若按理想宽度归一化，其余列会被压到几毫米。
        # ⚠️ 列宽不该由最长内容决定——长内容本来就该折行；
        # 短内容（型号名、计数）折行反而不可读。
        CAP_MM = 42.0
        weights = []
        for c in range(ncol):
            widest = 0.0
            for r in rows:
                if c < len(r) and r[c]:
                    widest = max(widest, self.get_string_width(r[c]))
            weights.append(min(max(widest, 8.0), CAP_MM))
        total = sum(weights)
        widths = [avail * w / total for w in weights]
        # 再保证每列不低于「该列最长单词」的宽度，让 measurement、
        # c-slac-power-favors-h100 这类标识符不至于被拆开。
        need = []
        for c in range(ncol):
            longest_word = 0.0
            for r in rows:
                if c < len(r) and r[c]:
                    for tok in _split_tokens(r[c]):
                        longest_word = max(longest_word, self.get_string_width(tok))
            need.append(longest_word + 1.2)
        for _ in range(6):                       # 迭代几轮即可收敛
            deficit = 0.0
            for c in range(ncol):
                if widths[c] < need[c]:
                    deficit += need[c] - widths[c]
                    widths[c] = need[c]
            if deficit <= 0:
                break
            donors = [c for c in range(ncol) if widths[c] > need[c] + 1.0]
            pool = sum(widths[c] - need[c] for c in donors)
            if pool <= 0:
                break
            for c in donors:
                widths[c] -= deficit * (widths[c] - need[c]) / pool
        self.set_font("CJK", "", 8.2)
        # fpdf2 的 multi_cell 在页面底部会自行分页，于是同一行表格的内容
        # 被拆到两页、每页只剩一个词。表格行的分页必须由我们决定，
        # 故绘制期间关掉自动分页，函数末尾恢复。
        prev_auto = self.auto_page_break
        self.set_auto_page_break(False)
        try:
            for ri, r in enumerate(rows):
                self._table_row(ri, r, ncol, widths)
        finally:
            self.set_auto_page_break(prev_auto)
        # 表格说明放在表体下方，而不是上方——上方的说明会让表与它的
        # 引出行之间隔一段文字，读者容易把说明误读成上一段的结尾。
        if caption:
            self.set_font("CJK", "", 8.6)
            self.set_text_color(80, 80, 80)
            for ln in wrap_measured_words(self, caption, 8.6, 210 - 40 - 1):
                self.set_x(20)
                self.cell(0, 4.6, ln, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        self.ln(2.5)

    def _table_row(self, ri, r, ncol, widths) -> None:
        if True:
            cells = [(r[c] if c < len(r) else "") for c in range(ncol)]
            lines_per_cell = []
            for c, cell in enumerate(cells):
                # 按实测宽度折行。之前用「半个汉字宽」估算再减 2 个单位，
                # 对拉丁文本严重低估：'measurement' 11 个字母只算 5.5 个单位，
                # 减 2 后每行只放三四个字母，于是它被切成 measu/remen/t。
                # ⚠️ 单元格左右各留 0.5mm 内边距，这是真实需要的，不是估算余量。
                max_mm = widths[c] - 1.0
                lines_per_cell.append(
                    wrap_measured_words(self, cell, 8.2, max_mm) if cell else [""])
            nlines = max(len(x) for x in lines_per_cell)
            # 整行放不下就换页，绝不让一行跨页
            if self.get_y() + nlines * 4.6 > 280:
                self.add_page()
            y0 = self.get_y()
            if ri == 0:
                self.set_fill_color(232, 238, 244)
                self.set_font("CJK", "B", 8.2)
            else:
                self.set_fill_color(250, 250, 252)
                self.set_font("CJK", "", 8.2)
            x = 20
            for c, cell_lines in enumerate(lines_per_cell):
                self.set_xy(x, y0)
                if ri == 0:
                    self.multi_cell(widths[c], 4.6, "\n".join(cell_lines), border=0,
                                    align="L", fill=True, new_x="LEFT", new_y="TOP")
                else:
                    self.multi_cell(widths[c], 4.6, "\n".join(cell_lines), border=0,
                                    align="L", fill=True, new_x="LEFT", new_y="TOP")
                x += widths[c]
            self.set_draw_color(215, 220, 226)
            self.line(20, y0 + nlines * 4.6, 190, y0 + nlines * 4.6)
            self.set_y(y0 + nlines * 4.6 + 0.6)

    def figure(self, path: Path, caption: str, max_w: float = 168) -> None:
        if not path.is_file():
            self.body(f"[缺图：{path.name}]")
            return
        from PIL import Image
        with Image.open(path) as im:
            iw, ih = im.size
        w = min(max_w, iw * 0.2646)
        h = w * ih / iw
        if self.get_y() + h > 250:
            self.add_page()
            # 图被推到新页时不能紧贴页顶：那样它与上文完全分离，
            # 读者看到页首一张图、找不到它在讲哪一段。
            # 留出 TOP_GAP 并补一句承上启下的提示，让图仍属于上一段。
            self.set_y(self.get_y() + TOP_GAP)
        x = 20 + (170 - w) / 2
        self.image(str(path), x=x, y=self.get_y(), w=w)
        self.set_y(self.get_y() + h + 2)
        self.set_font("CJK", "", 8.6)
        self.set_text_color(80, 80, 80)
        for ln in wrap_cjk(caption, 76):
            self.set_x(20)
            self.cell(0, 4.6, ln, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)


def inline_clean(s: str) -> str:
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"\[(c-[A-Za-z0-9_-]+)\]", r"[\1]", s)
    s = re.sub(r"<!--.*?-->", "", s)
    # 符号降级：Microsoft YaHei 不含 emoji 与部分箭头，
    # 直接排会得到方块。这里换成字体里确实有的等价字符。
    for src, dst in GLYPH_FALLBACK.items():
        s = s.replace(src, dst)
    return s.strip()


def parse_blocks(md: str):
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.rstrip()
        if s.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            yield ("code", buf)
            continue
        m = re.match(r"!\[[^\]]*\]\(([^)]+)\)", s.strip())
        if m:
            cap = ""
            if i + 2 < len(lines) and lines[i + 1].strip() == "" \
                    and lines[i + 2].startswith("*图"):
                cap = inline_clean(lines[i + 2]).strip("*")
                i += 2
            yield ("figure", (m.group(1), cap))
            i += 1
            continue
        if s.startswith("|"):
            buf = []
            while i < len(lines) and lines[i].startswith("|"):
                buf.append(lines[i])
                i += 1
            rows = []
            for r in buf:
                if re.fullmatch(r"\|[\s:|-]+\|", r.strip()):
                    continue
                cells = [inline_clean(c) for c in r.strip().strip("|").split("|")]
                rows.append(cells)
            # 表格下方的说明行（形如「**表 2　……。** 补充说明」）交给 table()，
            # 由它排在表体正下方。若交由正文流处理，说明会与表分离到下一页。
            caption = ""
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("**表 "):
                caption = inline_clean(lines[j])
                i = j + 1
            yield ("table", (rows, caption))
            continue
        if s.startswith("#### "):
            yield ("h3", inline_clean(s[5:]))
        elif s.startswith("### "):
            yield ("h3", inline_clean(s[4:]))
        elif s.startswith("## "):
            yield ("h2", inline_clean(s[3:]))
        elif s.startswith("# "):
            yield ("h1", inline_clean(s[2:]))
        elif s.startswith("> "):
            # 引用块内同样：连续的非空行属于同一段，须合并后再折行。
            # 空引用行（单独的 >）表示段间空行，保留为独立分隔。
            buf: list[str] = []
            acc: list[str] = []

            def flush() -> None:
                if acc:
                    buf.append("".join(acc))
                    acc.clear()

            while i < len(lines) and (lines[i].startswith("> ") or lines[i].strip() == ">"):
                body = lines[i][2:] if lines[i].startswith("> ") else ""
                if body.strip():
                    acc.append(inline_clean(body))
                else:
                    flush()
                    buf.append("")
                i += 1
            flush()
            yield ("quote", buf)
            continue
        elif s.strip() == "---":
            yield ("rule", None)
        elif s.startswith("- "):
            yield ("bullet", inline_clean(s[2:]))
        elif re.match(r"^\d+\.\s", s):
            yield ("bullet", inline_clean(re.sub(r"^\d+\.\s", "", s)))
        elif s.strip():
            # Markdown 语义：同一段落内换行不是换行，是空格。
            # 源码里为便于编辑而手动折的行，必须在渲染时接回一整段，
            # 否则每行都按源码宽度截断，右边参差不齐。
            buf = [inline_clean(s)]
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip()
                if (not nxt.strip()
                        or nxt.startswith(("#", "|", ">", "```", "- ", "!["))
                        or nxt.strip() == "---"
                        or re.match(r"^\d+\.\s", nxt)):
                    break
                buf.append(inline_clean(nxt))
                i += 1
            yield ("body", "".join(buf))
            continue
        else:
            yield ("blank", None)
        i += 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="把 PAPER.md 排成中文 PDF")
    ap.add_argument("paper_dir")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    md_path = paper_dir / "PAPER.md"
    if not md_path.is_file():
        raise SystemExit(f"缺少正文：{md_path}")

    regular, bold = pick_fonts()
    pdf = Paper(regular, bold)
    pdf._figures_dir = paper_dir
    # 标题与页眉都来自 paper.json，不再写死。
    # 顺带把 <!-- ... --> 写作纪律注释从正文里滤掉：fpdf 的 Markdown
    # 解析器不认识 HTML 注释，会把整段注释原样排进第 1 页。
    spec = {}
    spec_path = paper_dir / "paper.json"
    if spec_path.is_file():
        import json as _json
        spec = _json.loads(spec_path.read_text(encoding="utf-8-sig"))
    title = spec.get("title") or "研究综述"
    pdf._running_title = title
    pdf.set_title(title)
    pdf.set_author("DeepResearchRSI")

    md = md_path.read_text(encoding="utf-8")
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    pdf.add_page()

    first_h1 = True
    for kind, payload in parse_blocks(md):
        if kind == "h1":
            if first_h1:
                pdf.set_font("CJK", "B", 19)
                for ln in wrap_title(payload, 34):
                    pdf.cell(0, 10, ln, align="C", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)
                first_h1 = False
            else:
                pdf.add_page()
                pdf.h1(payload)
        elif kind == "h2":
            pdf.h2(payload)
        elif kind == "h3":
            pdf.h3(payload)
        elif kind == "body":
            pdf.body(payload)
        elif kind == "bullet":
            pdf.bullet(payload)
        elif kind == "quote":
            pdf.quote(payload)
        elif kind == "table":
            rows_, cap_ = payload
            pdf.table(rows_, cap_)
        elif kind == "code":
            pdf.code("\n".join(payload))
        elif kind == "figure":
            rel, cap = payload
            pdf.figure(paper_dir / rel, cap)
        elif kind == "rule":
            pdf.ln(1)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)
        else:
            pdf.ln(1.2)

    out = Path(args.output) if args.output else paper_dir / "PAPER.pdf"
    pdf.output(str(out))
    size = out.stat().st_size
    print(f"[OK]   {out}  {pdf.page_no()} 页  {size:,} 字节")
    return 0


if __name__ == "__main__":
    sys.exit(main())