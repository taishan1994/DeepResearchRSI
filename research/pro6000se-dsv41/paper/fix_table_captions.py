"""把「表题在表格之前」改成「表题在表格之后」。

## 为什么要改

仓库既有的两篇论文（rtx-pro-6000、pd-disagg）都把表题放在表格**下方**，
`md_to_tex.py` 也是按这个顺序配对，然后生成 LaTeX 的 `\\caption`。
我写的 PAPER.md 把表题放在表格**上方**（这是排版手册里也常见的做法），
结果是 md_to_tex 吐出 12 条 `[WARN] 表题未配对到表格`。

⚠️ 关键判断：这 12 条 WARN **不是「表题写错了」**，而是「顺序与转换器的约定不一致」。
两种顺序本身都对，但一篇论文里必须统一——若一半在上、一半在下，
渲染出来的 PDF 会出现有些表有标题、有些没有（因为配不上的那条被跳过）。

故这里统一改成「题在下」，跟既有论文与转换器对齐。改的是顺序，不是内容。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"

# 匹配：一段以 *表 N　...* 开头的题注行，紧随其后是空行 + 表格块
PAT = re.compile(
    r"^\*表\s*(\d+)　([^\n]*)\*\n"      # 题注行
    r"\n"                                # 空行
    r"((?:\|[^\n]*\n)+)",                # 表格块（连续的 | 行）
    re.M,
)


def main() -> int:
    text = PAPER.read_text(encoding="utf-8")
    moved = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal moved
        num, cap, table = m.group(1), m.group(2), m.group(3)
        moved += 1
        # 表格 -> 空行 -> 题注
        return f"{table}\n*表 {num}　{cap}*\n"

    new = PAT.sub(repl, text)
    if moved == 0:
        print("没有找到「题注在上」的表——可能已经改过，或格式变了")
        return 1

    PAPER.write_text(new, encoding="utf-8")
    print(f"已把 {moved} 张表的题注移到表格下方")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
