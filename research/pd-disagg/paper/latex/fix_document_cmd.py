"""把 `\\\\begin{document}` 改成 `\\begin{document}`（真实字节：2 个反斜杠 -> 1 个）。

## 为什么会搞错两轮

我用 PowerShell here-string 生成 main.tex，写了 `\\\\begin{document}`。
落到文件里的**真实字节**是两个反斜杠 + "begin"。
Python 的 repr 显示成 `'\\\\begin{document}'`，我把它误读成「四个反斜杠」，
于是上一版 fix_escapes.py 做了 FOUR -> TWO，方向反了。

核对方法：看码点。`0x5c 0x5c 0x62` = 两个反斜杠 + 'b'，即 LaTeX 的
`\\`（换行命令）紧跟 `begin{document}` —— TeX 在垂直模式下执行 `\\`，
报 `There's no line here to end`。

正确字节应是 `0x5c 0x62`：一个反斜杠 + 'b'。

## 只改这两行

其它位置的 `\\` 是合法的 LaTeX 换行（如 `\\\\[2pt]`），不能动。
故只针对 begin/end document 两处。
"""

from pathlib import Path

BS = chr(92)


def main() -> int:
    p = Path(__file__).resolve().parent / "main.tex"
    s = p.read_text(encoding="utf-8")

    for word in ("begin{document}", "end{document}"):
        bad = BS + BS + word      # 两个反斜杠（错）
        good = BS + word          # 一个反斜杠（对）
        n = s.count(bad)
        if n:
            s = s.replace(bad, good)
        print(f"{word}: 修正 {n} 处")

    p.write_text(s, encoding="utf-8", newline="\n")

    # 校验：逐行看关键两行的前两个码点
    lines = s.split("\n")
    for i, L in enumerate(lines):
        if "begin{document}" in L or "end{document}" in L:
            cps = [hex(ord(c)) for c in L[:3]]
            print(f"  line {i + 1}: {cps}  {L!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
