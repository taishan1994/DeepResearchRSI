"""把「一页判据」的流程图改成通栏，并按实测宽度设定框宽。

## 问题

流程图在 figure 里，用 5 个 \\fbox{\\parbox{12.2cm}{...}} 竖向堆叠。
但它是单栏浮动体，单栏只有 8.12cm，而框实占
12.2 + 2×3pt(fboxsep) + 2×0.4pt(fboxrule) = 12.44cm，
超出 4.32cm = 125.7pt。这是全篇最大的一处 Overfull。

上一版我把表改成 table* 时漏了它——它是 **figure** 不是 table。

## 改法

1. figure -> figure*
2. parbox 宽度从 12.2cm 提到 15.0cm：
   通栏 16.96cm，减 fboxsep/fboxrule 后可用约 16.7cm。
   留 1.7cm 余量，避免 TeX 的行内断行容差把它顶出去。
3. 框内的长句保持不变——宽度变大后自然更少折行。

## 为什么不用 resizebox

那会缩小字号。10pt 缩到 8pt 以下，流程图的可读性比省下的空间更重要。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEC = HERE / "paper" / "sec0_onepage.tex"
BS = chr(92)

# 新框宽：通栏 16.96 - 安全余量
BOX_W = 15.0


def main() -> int:
    s = SEC.read_text(encoding="utf-8")

    # 1) figure -> figure*
    i = s.find(BS + "label{fig:decision}")
    if i < 0:
        print("[!] 未找到 fig:decision")
        return 1
    b = s.rfind(BS + "begin{figure}", 0, i)
    if b < 0:
        print("[!] 未找到 begin{figure}")
        return 1
    s = s[:b] + BS + "begin{figure*}" + s[b + len(BS + "begin{figure}"):]
    e = s.find(BS + "end{figure}", i)
    if e < 0:
        print("[!] 未找到 end{figure}")
        return 1
    s = s[:e] + BS + "end{figure*}" + s[e + len(BS + "end{figure}"):]

    # 2) parbox 宽度
    old_ws = set(re.findall(r"parbox\{([\d.]+)cm\}", s))
    s = re.sub(r"parbox\{[\d.]+cm\}", f"parbox{{{BOX_W}cm}}", s)
    print(f"figure -> figure*；parbox 宽度 {sorted(old_ws)} -> {BOX_W}cm")

    SEC.write_text(s, encoding="utf-8", newline="\n")

    # 3) 自检
    occ = BOX_W + 2 * 3 / 28.3465 + 2 * 0.4 / 28.3465
    print(f"框实占 {occ:.2f} cm，通栏上限 16.96 cm -> "
          f"{'OK' if occ < 16.96 else '仍超宽'}")
    n = s.count(f"parbox{{{BOX_W}cm}}")
    print(f"parbox 共 {n} 处")
    return 0 if occ < 16.96 and n == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
