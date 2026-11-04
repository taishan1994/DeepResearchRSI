"""修缺字形：圈码 ①②③④ 在 Times New Roman 里不存在。

## 现象

编译日志有 7 条 `Missing character: There is no ① (U+2460) in font
Times New Roman Bold`。这不会报错，只在 PDF 上留空白——
是典型的「静默失效」：文档看起来编译成功，但内容缺了。

## 为什么会出现

正文用 `\\textbf{① KV 每 token 大小。}` 这样的写法。`\\textbf` 走的是
西文粗体，即 Times New Roman Bold，而它不含 U+2460 区段。
圈码属于 CJK 兼容字符集，SimSun / SimHei 有。

## 修法

把圈码包进 CJK 字体：`\\textcjkc{①}`。本文件在导言区加一个命令，
正文里统一替换。

## 为什么不用 \\sym{}（模板已有的符号回退字体）

模板的 `\\symfont` 是 Segoe UI Symbol，确实也有圈码。但那是为
⭐🔥⚠️ 这类强调符号准备的，字号与基线是按符号调的。
圈码用在正文小标题里，走 CJK 字体视觉更一致。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LATEX = HERE / "latex"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def main() -> int:
    # 1) 在 main.tex 导言区末尾（\begin{document} 之前）加命令
    mp = LATEX / "main.tex"
    s = mp.read_text(encoding="utf-8")
    BS = chr(92)
    cmd = (
        f"\n%% ---------- 圈码：西文字体没有这些字形 ----------\n"
        f"%% 实测 Times New Roman 里 U+2460 区段缺失，编译只报\n"
        f"%% \"Missing character\" 而不报错，PDF 上留空白。\n"
        f"%% 用 CJK 字体渲染，SimSun 有完整圈码。\n"
        f"{BS}newcommand{{{BS}textcjkc}}[1]{{{{\\CJKfamily{{}}#1}}}}\n"
    )
    if "textcjkc" not in s:
        i = s.index(BS + "begin{document}")
        s = s[:i] + cmd + "\n" + s[i:]
        mp.write_text(s, encoding="utf-8", newline="\n")
        print("main.tex：已加 \\textcjkc 命令")
    else:
        print("main.tex：\\textcjkc 已存在")

    # 2) 在 body.tex 里把圈码包起来（只包正文里独立出现的圈码）
    bp = LATEX / "body.tex"
    b = bp.read_text(encoding="utf-8")
    n = 0

    def wrap(m: re.Match) -> str:
        nonlocal n
        n += 1
        return BS + "textcjkc{" + m.group(0) + "}"

    # 避免重复包裹：先跳过已在 \textcjkc{...} 里的
    parts = re.split(r"(" + BS + r"textcjkc\{[" + CIRCLED + r"]\})", b)
    out = []
    for part in parts:
        if part.startswith(BS + "textcjkc{"):
            out.append(part)
        else:
            out.append(re.sub("[" + CIRCLED + "]", wrap, part))
    b2 = "".join(out)
    bp.write_text(b2, encoding="utf-8", newline="\n")
    print(f"body.tex：包裹 {n} 处圈码")

    # 3) 校验
    left = len(re.findall("(?<!" + BS + "textcjkc\\{)(?<!\\{)" +
                          "[" + CIRCLED + "]", b2))
    print(f"仍裸露的圈码（估算）：{left}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
