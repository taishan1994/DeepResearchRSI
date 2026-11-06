"""去掉图表标题里手写的编号，交给 LaTeX 的 \\caption 自动编号。

## 症状（用户报的「图例上下都有，重复了且不对」）

PDF 里每条图注开头都出现两次编号：

    图1
    图1　装下 V4.1-Flash 需要几张 96 GB 卡。……

## 两个独立的原因，叠在一起

1. **图片自身烧了标题**：`make_figures.py` 里 `ax.set_title("图 1　…")`
   把标题画进了 PNG，于是图的上方有编号+题目。（已在本轮去掉。）

2. **\\caption 里又手写了编号**：`md_to_tex.py` 把
   `*图 1　装下…*` 原样转成 `\\caption{图 1　装下…}`，
   而 LaTeX 的 figure 环境**自己会**在 \\caption 前加上「图 1」。
   于是变成「图1」+「图1　装下…」两行。

第 2 条是根本原因，且它会**在所有版式下重犯**——只要源写法带编号，
转出来就重复。所以修在转换层，而不是修 PDF。

## 做法

`md_to_tex.py` 已经把 caption 包进 `\\caption{}`。
本脚本在生成的 body.tex 上把 `\\caption{图 N　` 改成 `\\caption{`
（表同理：`\\caption{表 N　`）。

⚠️ 必须幂等：重复跑不能把正文里正常的「图 1」也吃掉。
故只匹配 `\\caption{图 <数字>　` 这一种精确形态。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BODY = Path(__file__).resolve().parent / "latex" / "body.tex"

# \caption{图 1　标题}  ->  \caption{标题}
CAP_FIG = re.compile(r"(\\caption\{)图\s*\d+\s*[\u3000\s]\s*")
CAP_TAB = re.compile(r"(\\caption\{)表\s*\d+\s*[\u3000\s]\s*")


def main() -> int:
    if not BODY.is_file():
        print(f"缺 {BODY}")
        return 1
    s = BODY.read_bytes().decode("utf-8")
    n1 = len(CAP_FIG.findall(s))
    n2 = len(CAP_TAB.findall(s))
    s = CAP_FIG.sub(r"\1", s)
    s = CAP_TAB.sub(r"\1", s)
    BODY.write_bytes(s.encode("utf-8"))
    print(f"已去掉手写编号：图 {n1} 处、表 {n2} 处（编号交给 \\caption 自动生成）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
