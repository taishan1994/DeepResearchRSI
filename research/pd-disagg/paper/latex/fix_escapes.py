"""修正 main.tex 里被过度转义的 LaTeX 命令。

## 问题

用 PowerShell here-string 生成 main.tex 时，`\\begin{document}` 被写成了
`\\\\begin{document}`（四个反斜杠）。XeLaTeX 把 `\\\\` 读成换行，
于是 `\\\\begin{document}` 变成「换行 + begin{document}」，
报错 `There's no line here to end`。

## 为什么不在 PowerShell 里改

试过两次，都被 here-string 的反斜杠层数问题绕住：
Python 字符串里的 `\\\\` -> PowerShell 解析一次 -> Python 再解析一次，
难以预测最终落到文件里的字节。

故写成独立文件，用 chr(92) 拼反斜杠，完全绕开转义。
"""

from pathlib import Path

BS = chr(92)          # 单个反斜杠
TWO = BS + BS         # LaTeX 的换行/命令前缀
FOUR = TWO + TWO


def main() -> int:
    p = Path(__file__).resolve().parent / "main.tex"
    s = p.read_text(encoding="utf-8")
    before = s.count(FOUR)
    s = s.replace(FOUR + "begin{document}", TWO + "begin{document}")
    s = s.replace(FOUR, TWO)      # 其它位置的四反斜杠一并归一
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"四反斜杠 {before} 处 -> 归一为两反斜杠")

    # 校验：文档里不应再有四反斜杠，且 begin{document} 恰一处
    now = p.read_text(encoding="utf-8")
    print("剩余四反斜杠:", now.count(FOUR))
    print("begin{document} 次数:", now.count("begin{document}"))
    print("end{document} 次数:", now.count("end{document}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
