"""修 `\\[2pt]` 被误改成 `\\[2pt]` 的问题。

## 出了什么

fix_document_cmd.py 里我替换了 `\\\\` -> `\\`（真实字节 2 个反斜杠 -> 1 个）。
但 `\\[2pt]` 本来就是**合法**的 LaTeX：换行并加 2pt 垂直间距。
替换后变成 `\\[2pt]`，而 `\\[` 是「进入行间公式」，
于是 TeX 报 `Missing $ inserted`。

## 教训

我的替换范围太大了。正确做法是**只改 begin/end document 那两行**，
而不是全局把双反斜杠换成单反斜杠——后者会破坏所有合法的换行命令。

这与本文件同目录 fix_document_cmd.py 的注释里说的相反：那份注释声称
「其它位置的 `\\\\` 是合法换行，不能动」，但代码里 still 做了全局替换
（`s.replace(bad, good)` 对每处 `\\\\begin{document}` 直接替换是对的，
真正的问题是更早那一版 fix_escapes.py 做了 `FOUR -> TWO` 全局替换，
把 `\\\\[2pt]` 也改了）。

## 修法

把 `\\[数字pt]` 还原成 `\\\\[数字pt]`，其余不动。
"""

from __future__ import annotations

import re
from pathlib import Path

BS = chr(92)
ONE = BS
TWO = BS + BS


def main() -> int:
    p = Path(__file__).resolve().parent / "main.tex"
    s = p.read_text(encoding="utf-8")

    # 单反斜杠 + [数字pt] -> 双反斜杠 + [数字pt]
    # 注意只匹配 \[ 后紧跟数字+pt]，避免碰到真正的 \[ ... 公式
    pat = re.compile(re.escape(ONE) + r"\[(\d+(?:\.\d+)?(?:pt|em|mm|cm))\]")
    n = len(pat.findall(s))
    s = pat.sub(lambda m: TWO + "[" + m.group(1) + "]", s)
    print(f"还原 {n} 处 \\[Npt] -> \\\\[Npt]")

    p.write_text(s, encoding="utf-8", newline="\n")

    # 校验：不应再有孤立的 \[ 后接数字
    left = len(pat.findall(s))
    print("剩余异常:", left)
    for i, L in enumerate(s.split("\n")):
        if "LARGE" in L or "large" in L.split(BS)[0][:20]:
            print(f"  line {i + 1}: {L[:80]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
