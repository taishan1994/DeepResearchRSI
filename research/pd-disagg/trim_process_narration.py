"""删掉 sec7 里的过程叙述，保留结论。

## 为什么要删

论文正文里出现了「第 1 轮写这篇时」「本轮找到了已做完这件事的工作」——
这是**过程叙述**，属于 REPORT.md，不属于论文。读者不关心作者第几轮
发现了什么，只关心结论与依据。

这类残留是连载式写作的副作用：每一轮都在正文里向前一轮「交代」。
压缩时它该被清掉。

## 保留什么

结论全部保留，包括三个数字（0.48 / 2.10 / 1.27）与窗口形状的描述。
只删「我第几轮想到了什么」。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SEC = HERE / "paper" / "sec7_discuss.tex"
BS = chr(92)

OLD = (
    BS + "subsection{本轮补上的一件事：收益有上界}\n"
    "\n"
    "第 1 轮写这篇时，「收益取决于负载」只是一句定性判断，\n"
    "「测出交叉点」被列为下一步实验。本轮找到了已做完这件事的工作：\n"
    "跨 8 个模型扫 9 个输入输出比" + BS + "texttt{[c-window]}。\n"
    "\n"
    "结果比「一个交叉点」更有信息量，也更不利于简化叙事："
)
NEW = (
    BS + "subsection{收益有上界，且上界会回落}\n"
    "\n"
    "跨 8 个模型扫 9 个输入输出比" + BS + "texttt{[c-window]}，\n"
    "结果比「一个交叉点」更有信息量，也更不利于简化叙事："
)


def main() -> int:
    s = SEC.read_text(encoding="utf-8")
    before = len(s)
    if OLD not in s:
        print("[!] 锚点未找到")
        return 1
    s = s.replace(OLD, NEW, 1)
    SEC.write_text(s, encoding="utf-8", newline="\n")
    print(f"已删过程叙述：{before} -> {len(s)} 字符（-{before - len(s)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
