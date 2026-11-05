"""把第 7 节（四类之外）接入引言与结论。

## 引言

贡献列表加一条，并同步计数（70 源 / 78 证 / 9 主张）。
位置放在技巧层那一条之后——两者是「四类」与「四类之外」的递进关系。

## 结论

原文说「技术栈分四层」。现在要修正为：**四层是对的，但只在
「分离这笔账」这个视角下成立**；换实现平面看还有三层，
且最大的单项收益往往不在四层里。

这是一个措辞上的精细活：不能推翻四层（它是站得住的），
也不能让读者以为四层就够了。

## 一个数字上的取舍

结论不重复 2.65x / 93% 这些具体值，只给量级（数量级 / 数十个百分点），
避免结论变成数字堆砌。具体值留给第 7 节。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
INTRO = HERE / "paper" / "sec1_intro.tex"
CONCL = HERE / "paper" / "sec7_discuss.tex"


def main() -> int:
    # ---------------- 引言 ----------------
    s = INTRO.read_text(encoding="utf-8")
    if "sec:plane" not in s:
        anchor = "  \\item 主动搜集使分离失效或转负的条件"
        item = (
            "  \\item 指出上述四类只管「分离引入的额外成本」，"
            "按实现平面重看还有数据面/执行面/控制面三层，"
            "并用三个反例界定这些手段的适用条件"
            "（第 \\ref{sec:plane} 节）。\n"
        )
        i = s.find(anchor)
        if i < 0:
            print("[!] 引言锚点未找到")
        else:
            s = s[:i] + item + s[i:]
            print("引言已加贡献项")

    reps = [
        ("46 篇论文全文与 21 份官方工程文档快照，共 67 个来源、\n"
         "62 条证据、8 条主张",
         "46 篇论文全文与 24 份官方工程文档快照，共 70 个来源、\n"
         "78 条证据、9 条主张"),
        ("（E1 不变量，\n62/62 全部校验通过，无「未校验」条目）",
         "（E1 不变量，\n78/78 全部校验通过，无「未校验」条目）"),
    ]
    for a, b in reps:
        if a in s:
            s = s.replace(a, b)
            print(f"引言计数已改：{a[:20]}...")
    INTRO.write_text(s, encoding="utf-8", newline="\n")
    print(f"sec1_intro.tex {len(s)} 字符")

    # ---------------- 结论 ----------------
    c = CONCL.read_text(encoding="utf-8")
    if "四类之外" not in c:
        anchor = "最后一点值得重复："
        tail = (
            "还有一层必须说清，否则上面的四层会被误读成完整清单。\n"
            "这四层的共同视角是「分离引入的额外成本」。换成按实现平面看,\n"
            "还有数据面、执行面、控制面三层,而生产系统里最大的单项收益\n"
            "往往在这四层之外:并行策略选择可带来数倍差异,\n"
            "一条调度策略的上限可达数十个百分点的吞吐,\n"
            "算子融合是十余个百分点的端到端延迟——都不涉及把 KV 搬得更快。\n"
            "所以判据的用法是:用三平面保证不漏,用四类判断传输那一层怎么取舍。\n\n"
            "同一节里还有三个反例值得记住,因为它们界定了适用条件:\n"
            "流水线并行不适合热轮次(前缀已缓存、新增 token 太少);\n"
            "上下文并行不必然迁移到另一种注意力结构(它只是打平了原来的做法);\n"
            "负载均衡也可能有害——迁移要取 KV,预取的块占容量,\n"
            "结果是队列更均衡但并发更少。\n\n"
            "最后一点值得重复："
        )
        i = c.find(anchor)
        if i < 0:
            print("[!] 结论锚点未找到")
        else:
            c = c[:i] + tail + c[i + len(anchor):]
            print("结论已补四类之外")
    else:
        print("结论已含四类之外")

    CONCL.write_text(c, encoding="utf-8", newline="\n")
    print(f"sec7_discuss.tex {len(c)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
