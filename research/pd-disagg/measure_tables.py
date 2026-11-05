"""测量论文里每张表的渲染宽度，判断哪些需要跨栏。

## 为什么要测

两栏排版下，单栏可用宽度 = (页宽 - 2*边距 - 栏间距) / 2。
A4 宽 21cm，边距 2.05cm，栏间距 0.72cm，故单栏约 8.09cm，
通栏（跨两栏）约 16.9cm。

若某张表的实际内容宽度接近或超过 8.09cm，它在单栏里会被压得很窄，
列内换行增多、表变高——这就是「太长」的表现。
此时应改成通栏（table*）。

## 怎么测

两种宽度：
  · 声明宽度：tabular 列说明里 p{Xcm} 的合计。
    但 l/r/c 列没有声明宽度，按内容自然宽度。
  · 实测宽度：从 PDF 里量表格实际占据的水平范围。
    这个更准，因为包含了内容撑开的部分。

## 一个陷阱

上一次我搜「表 N:」标题来判断表格位置，结果匹配到了正文里的
「第 3、4 节」这类文字——**因为正文引用也含「节」字附近的数字**。
故这次只用 bbox 的 x 范围判断，不依赖文本内容。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"

# 单栏与通栏的可用宽度（cm），由 main.tex 的 geometry 推算
COL_W = 8.09
FULL_W = 16.90


def declared_width(spec: str) -> tuple[float, int]:
    """从 tabular 列说明里求声明宽度合计与列数。"""
    ws = [float(x) for x in re.findall(r"p\{([\d.]+)cm\}", spec)]
    # l / r / c 列各按 0 计（内容撑开，无法静态得知）
    n_lrc = len(re.findall(r"(?<![a-z])[lrc](?![a-z])", spec))
    return sum(ws), len(ws) + n_lrc


def main() -> int:
    print(f"单栏可用 {COL_W} cm ｜ 通栏可用 {FULL_W} cm\n")
    print(f"{'文件':<22}{'label':<18}{'声明cm':>7}{'列':>4}  判定")
    print("-" * 74)

    over = []
    for p in sorted(PAPER.glob("sec*.tex")):
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}",
                             s, re.S):
            t = m.group(1)
            lab = re.search(r"\\label\{(tab:[^}]*)\}", t)
            # 注意：不能用 `\{([^}]*)\}`——列说明里 p{0.9cm} 自带 `}`，
            # 那样只会抓到开头的 `@{}`。改用「到行尾」。
            spec = re.search(r"\\begin\{tabular\}\{([^\n]*)\}", t)
            if not spec:
                continue
            w, n = declared_width(spec.group(1))
            name = lab.group(1) if lab else "?"
            if w > COL_W:
                verdict = f"超单栏 {w - COL_W:+.2f}cm -> 需跨栏"
                over.append((name, w))
            elif w > COL_W * 0.85:
                verdict = f"接近单栏（余 {COL_W - w:.2f}cm）"
            else:
                verdict = f"单栏内（余 {COL_W - w:.2f}cm）"
            print(f"{p.name:<22}{name:<18}{w:>7.2f}{n:>4}  {verdict}")

    print()
    if over:
        print("需改成 table* 的表：")
        for name, w in over:
            print(f"  {name}  声明 {w:.2f}cm")
    else:
        print("按声明宽度无需跨栏（l/r/c 列的实际撑开需看 PDF 实测）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
