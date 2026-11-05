"""检查 .tex 文件里的反斜杠是否被破坏（不用正则后顾断言）。

## 为什么需要这个检查

2026-11-05 这一轮踩了两次同类问题：在 Python 字符串里写 LaTeX 命令时，
`\\textbf` 被误写成 `\textbf`，Python 把 `\t` 解释成 TAB 字符，
于是文件里出现 `	extbf`。LaTeX 不会报错——它把 `extbf` 当成普通文字，
PDF 里悄悄少了一个粗体，肉眼几乎看不出。

静默失败的典型：不报错、不告警、渲染正常，只有逐字比对能发现。

## 判据

  · 文件里不应有 TAB 字符
  · 命令名（textbf/ref/label 等）前面必须有反斜杠

## 两次自我修正

第一版把反斜杠写成普通字符串里的 `\x5c`——那是四个字符，不是反斜杠，
于是全部文件被误判，报了 275 处假问题。
第二版用正则字符类拼反斜杠，触发 `bad escape \A`。

改用**逐字符扫描**：不用正则，就不会有转义问题。
检查器本身必须先被验证——这是 LESSONS 1.6 的教训。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
BS = chr(92)
TAB = chr(9)
ALPHA = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

COMMANDS = [
    "textbf", "textit", "emph", "texttt", "textrm", "textsc",
    "ref", "label", "cite", "section", "subsection", "paragraph",
    "begin", "end", "item", "caption", "centering", "small",
    "toprule", "midrule", "bottomrule", "frac", "times",
]


def scan(path: Path) -> list[str]:
    s = path.read_text(encoding="utf-8")
    problems: list[str] = []

    for i, line in enumerate(s.split(chr(10)), 1):
        if TAB in line:
            problems.append(f"  第 {i} 行含 TAB 字符")

    # 逐字符扫描：找到每个命令名，检查前一个字符是不是反斜杠
    n = len(s)
    for cmd in COMMANDS:
        start = 0
        while True:
            j = s.find(cmd, start)
            if j < 0:
                break
            start = j + 1
            prev = s[j - 1] if j > 0 else ""
            nxt = s[j + len(cmd)] if j + len(cmd) < n else ""
            if prev == BS:
                continue                    # 正常
            if prev in ALPHA:
                continue                    # 是更长单词的一部分
            if nxt in ALPHA:
                continue                    # 命令名后面还接字母
            line = s.count(chr(10), 0, j) + 1
            problems.append(f"  第 {line} 行 {cmd} 缺反斜杠（前为 "
                            f"{prev!r}）")
    return problems


def main() -> int:
    files = sorted(HERE.glob("paper/sec*.tex"))
    total = 0
    for p in files:
        probs = scan(p)
        if probs:
            total += len(probs)
            print(f"[!] {p.name}")
            for x in probs[:6]:
                print(x)
            if len(probs) > 6:
                print(f"  ...共 {len(probs)} 处")
    print(f"\n检查 {len(files)} 个文件，问题 {total} 处")

    # 反例自测：造一个坏样本，确认能抓到
    probe = Path("_probe_escape.tex")
    probe.write_text("bad " + TAB + "extbf{x} here" + chr(10),
                     encoding="utf-8", newline="\n")
    caught = scan(probe) != []
    probe.unlink()
    print(f"反例自测：{'抓到' if caught else '未抓到（检查器失效）'}")
    if not caught:
        return 2
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
