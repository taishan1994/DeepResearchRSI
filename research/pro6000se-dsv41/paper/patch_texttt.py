"""给 \\texttt{} 里的长参数串加断点。

## 为什么需要这一步

本文有十几处形如

    \\texttt{--kv-cache-dtype fp8 --block-size 128 --gpu-memory-utilization 0.85}

的命令行片段。\\texttt 默认**不在连字符处断行**（等宽字体没有连字断点），
于是一串 60+ 字符的参数被当成一个不可断的 token，
双栏窄栏下只能越出右边界——实测 5 处溢出，最大 2.7pt。

## 为什么不是「把版面参数再放宽」

已经试过：emergencystretch 5em、tolerance 5000、标点悬挂。
溢出没减少，因为缺的**不是弹性，是断行点**（与 LESSONS 里那条标点溢出同源）。
唯一有效的做法是显式告诉 TeX「这里可以断」：在 `-` 后和空格后插入 \\allowbreak。

## 边界

只改 \\texttt 的内容，不加字、不删字、不改语义；
插入的 \\allowbreak 是零宽且不产生连字符的。故不影响任何事实与引用。

⚠️ body.tex 是 md_to_tex.py 生成的。本脚本必须**在它之后**跑；
重跑 md_to_tex 会覆盖掉这些断点，需要再跑一次本脚本（见附录 C 的构建顺序）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BODY = HERE / "latex" / "body.tex"

TT = re.compile(r"\\texttt\{([^{}]*)\}")


def breakable(content: str) -> str:
    """在 - 后与空格后插入零宽断点。

    ⚠️ 阈值不能设太高。第一版写的是 `len < 28 就跳过`，
    结果 `--mem-fraction-static 0.72`（26 字符）恰好被放过，
    而它正是 p7 那处 2.7pt 溢出的元凶——短串一样会溢出，
    因为双栏栏宽只有约 287pt，26 个等宽字符已经接近一栏。
    故只跳过真正很短的串（如 `fp8`、`TP=8`），其余一律加断点。
    """
    if len(content) < 12:
        return content
    out = content.replace("-", "-\\allowbreak{}")
    # 空格后给一个断点；用 \allowbreak 而非换行符，避免吞掉空格。
    out = out.replace(" ", "\\allowbreak{} ")
    return out


def main() -> int:
    if not BODY.is_file():
        print(f"缺 {BODY}，请先跑 md_to_tex.py")
        return 1
    text = BODY.read_bytes().decode("utf-8")

    # ⚠️ 必须幂等：第一版是「见到 \allowbreak 就整体跳过」，
    # 于是我调低阈值后重跑，它直接跳过、旧的短串仍无断点，
    # 表现为「改了代码但 PDF 没变」——最难发现的一类失效。
    # 正确做法是**先剥掉旧断点再重新加**，这样每次都是按当前阈值重算。
    before = text.count("\\allowbreak")
    text = text.replace("-\\allowbreak{}", "-").replace("\\allowbreak{} ", " ")

    n = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal n
        n += 1
        return "\\texttt{" + breakable(m.group(1)) + "}"

    text = TT.sub(repl, text)
    BODY.write_bytes(text.encode("utf-8"))
    print(f"已处理 {n} 处 \\texttt{{}}（先剥离旧断点 {before} 个，再按当前阈值重算）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
