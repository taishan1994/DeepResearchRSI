"""把负载形态接入引言与结论，并同步计数。

## 引言

贡献列表加一条。位置在 SLO 那一条之后——负载形态是第五次切法，
也是唯一一个「能取消一整类技巧」的维度。

同步计数：92 证 / 11 主张 / 92 of 92。

## 结论

结论末尾的「使用顺序」原本是三步（SLO -> 平面 -> 成本链）。
要补成四步，负载形态排在最前，理由是它能让后面三步失效。

## 措辞

不写「本文提出五种切法」。写成「同一件事可以从五个角度看，
顺序是负载 -> SLO -> 平面 -> 手段」。切法是分析手段，不是贡献。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
INTRO = HERE / "paper" / "sec1_intro.tex"
CONCL = HERE / "paper" / "sec7_discuss.tex"


def main() -> int:
    s = INTRO.read_text(encoding="utf-8")
    if "sec:load" not in s:
        anchor = "  \\item 主动搜集使分离失效或转负的条件"
        item = (
            "  \\item 指出\\textbf{负载形态是前置输入而非决策维度}："
            "真实 agentic 负载的缓存命中率达 $94.2\\%$、输入输出比 $131:1$，"
            "前者把「省传输量」与「隐藏传输」两类挤到边缘，"
            "后者使 P:D 配比极端倾斜；并记录一个测量陷阱——"
            "哈希链未固定种子时跨实例查找会静默全未命中，"
            "却呈现一个看起来合理的零命中率（第 \\ref{sec:load} 节）。\n"
        )
        i = s.find(anchor)
        if i < 0:
            print("[!] 引言锚点未找到")
        else:
            s = s[:i] + item + s[i:]
            print("引言已加负载形态贡献项")

    reps = [
        ("85 条证据、10 条主张", "92 条证据、11 条主张"),
        ("（E1 不变量，\n85/85 全部校验通过，无「未校验」条目）",
         "（E1 不变量，\n92/92 全部校验通过，无「未校验」条目）"),
    ]
    for a, b in reps:
        if a in s:
            s = s.replace(a, b)
            print(f"引言计数已改：{a[:16]}...")
    INTRO.write_text(s, encoding="utf-8", newline="\n")
    print(f"sec1_intro.tex {len(s)} 字符")

    c = CONCL.read_text(encoding="utf-8")
    if "负载形态排在最前" not in c:
        old = ("故使用顺序应当是:\n"
               "\\textbf{先定 SLO 形状}(哪个更紧、比值多少、达成率目标),\n")
        new = ("故使用顺序应当是:\n"
               "\\textbf{先看负载形态}(命中率、I/O 比、轮间隔、长度分布),\n"
               "\\textbf{再定 SLO 形状}(哪个更紧、比值多少、达成率目标),\n")
        if old in c:
            c = c.replace(old, new, 1)
            print("结论已把负载形态排到最前")
        else:
            tail = (
                "\n\n负载形态排在最前,理由是它能\textbf{让后面三步的结论失效},\n"
                "而不是让它们更精确:SLO 只能翻转方向,\n"
                "负载形态能直接取消一整类技巧的用武之地。\n"
                "真实 agentic 负载的缓存命中率达 94.2%,输入输出比 131:1——\n"
                "前者把「省传输量」与「隐藏传输」挤到边缘,后者使 P:D 配比极端倾斜。\n"
                "故当命中率足够高时,\n"
                "最有效的优化不是把 KV 搬得更快,而是让 KV 不必被搬。\n"
            )
            c = c + tail
            print("结论已追加负载形态段")
    else:
        print("结论已含负载形态段")

    CONCL.write_text(c, encoding="utf-8", newline="\n")
    print(f"sec7_discuss.tex {len(c)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
