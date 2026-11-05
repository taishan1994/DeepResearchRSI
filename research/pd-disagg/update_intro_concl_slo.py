"""把 SLO 这一层接入引言与结论。

## 引言

贡献列表加一条。位置在「四类之外」之后，因为它是第三次换维度，
逻辑上是递进（成本链 -> 实现平面 -> 目标）。

同时同步计数：85 证 / 10 主张 / 78 -> 85。

## 结论

结论现在说「技术栈分四层」，然后说「四类之外还有三层」。
要再加一层最高的：**先定 SLO 形状，再定技巧方向**。

这是四次切法里唯一能让前面结论反转的维度，故应放在结论的
最后、作为使用顺序的第一步。

## 措辞

不写「本文提出四种切法」——四种切法是分析手段，不是贡献。
写成「同一件事可以从四个角度看，顺序是 SLO -> 平面 -> 手段」。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
INTRO = HERE / "paper" / "sec1_intro.tex"
CONCL = HERE / "paper" / "sec7_discuss.tex"


def main() -> int:
    # ---- 引言 ----
    s = INTRO.read_text(encoding="utf-8")
    if "sec:slo" not in s:
        anchor = "  \\item 主动搜集使分离失效或转负的条件"
        item = (
            "  \\item 指出同一技巧在不同 SLO 下\\textbf{方向相反}——"
            "chunked prefill 的 token 预算调小则 TBT 好、吞吐差，"
            "调大则相反；三组真实应用的 TTFT 跨约 $120$ 倍而 TPOT "
            "几乎不变，故决定配置的是两个 SLO 的相对松紧，"
            "不是「SLO 严不严」（第 \\ref{sec:slo} 节）。\n"
        )
        i = s.find(anchor)
        if i < 0:
            print("[!] 引言锚点未找到")
        else:
            s = s[:i] + item + s[i:]
            print("引言已加 SLO 贡献项")

    reps = [
        ("46 篇论文全文与 24 份官方工程文档快照，共 70 个来源、\n"
         "78 条证据、9 条主张",
         "46 篇论文全文与 24 份官方工程文档快照，共 70 个来源、\n"
         "85 条证据、10 条主张"),
        ("（E1 不变量，\n78/78 全部校验通过，无「未校验」条目）",
         "（E1 不变量，\n85/85 全部校验通过，无「未校验」条目）"),
    ]
    for a, b in reps:
        if a in s:
            s = s.replace(a, b)
            print(f"引言计数已改：{a[:18]}...")
    INTRO.write_text(s, encoding="utf-8", newline="\n")
    print(f"sec1_intro.tex {len(s)} 字符")

    # ---- 结论 ----
    c = CONCL.read_text(encoding="utf-8")
    if "先定 SLO" not in c:
        tail = (
            "还有最后一层，它是使用顺序上的第一步。\n"
            "本文的四次切法里，只有 SLO 那一次能让前面的结论\textbf{反转}:\n"
            "同一个技巧在一个 SLO 下是正收益,在另一个下可能为负。\n"
            "chunked prefill 的 token 预算就是例子——调小则 TBT 好、吞吐差,\n"
            "调大则相反;而三组真实应用的 TTFT 跨约 120 倍、TPOT 几乎不变,\n"
            "说明真正决定配置的是两个 SLO 的相对松紧。\n\n"
            "故使用顺序应当是:\n"
            "\textbf{先定 SLO 形状}(哪个更紧、比值多少、达成率目标),\n"
            "\textbf{再按实现平面查漏}(数据面/执行面/控制面),\n"
            "\textbf{最后按成本链取舍}(四类里每类选一个)。\n"
            "顺序不能颠倒:方向错了,后面做得越细越糟。\n\n"
            "这也意味着全文所有「某技巧提升 X%」的说法都隐含了一个 SLO 形状。\n"
            "把它们当作无条件成立的结论,与把分离当成固有属性,是同一个错误。\n\n"
        )
        anchor = "最后一点值得重复："
        i = c.find(anchor)
        if i < 0:
            c = c + "\n\n" + tail
            print("结论已追加 SLO 段（追加在末尾）")
        else:
            c = c[:i] + tail + c[i:]
            print("结论已加 SLO 段")
    else:
        print("结论已含 SLO 段")

    CONCL.write_text(c, encoding="utf-8", newline="\n")
    print(f"sec7_discuss.tex {len(c)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
