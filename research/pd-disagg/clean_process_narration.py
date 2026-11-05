"""清理论文正文里的「写作过程叙述」。

## 判定标准

「本轮」「上一轮」「第 N 轮」在正文里分两种：

  · **会话的轮**（agentic turn）—— 指多轮对话的下一轮，正确，保留。
    例：sec9「agentic 会话的轮次间隔很短, 下一轮到达时」
        sec11「路由器可能不会把会话的下一轮调度到同一个实例上」

  · **写作的轮**（第几轮修改这篇论文）—— 属于 REPORT，不属于论文。删。

## 改法

不删结论，只把「本轮发现 X」改成「X」。删掉的是
「我第几轮知道了什么」这层元信息。

有几处改写成直接的陈述句，因为原句的论证结构依赖「此前以为 / 现在知道」
这个对比。改成「A 表面上像 X，实际是 Y」——对比保留，过程删掉。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"

REPLACEMENTS = {
    "sec5_model.tex": [
        ("\\noindent\\textbf{翻转是突变的，而且之后非单调。} "
         "这是本轮最值得记的",
         "\\noindent\\textbf{翻转是突变的，而且之后非单调。} "
         "这是最值得记的一条"),
        ("更关键的是，本轮新增的证据表明\\textbf{收益随负载是窗口而非单调}，",
         "更关键的是，证据表明\\textbf{收益随负载是窗口而非单调}，"),
    ],
    "sec6_boundary.tex": [
        ("上一句还只是说「取决于比率」。本轮的证据把它量化了，而且结论比",
         "上一句只是说「取决于比率」。证据可以把它量化，而且结论比"),
    ],
    "sec7_discuss.tex": [
        ("上一轮我把「扫描输入输出比、测出交叉点」列为待做，本轮发现已有工作",
         "「扫描输入输出比、测出交叉点」曾是明显的空缺，而已有工作"),
        ("第三条的措辞在本轮被改过，值得单独说明：原先是「负载足够重」，",
         "第三条的措辞值得单独说明：容易写成「负载足够重」，"),
    ],
}

# 这些位置的「下一轮」指会话轮次，必须保留——只做记录，不改
KEEP = [
    ("sec11_load.tex", "路由器可能不会把会话的下一轮调度到同一个实例上"),
    ("sec9_plane.tex", "agentic 会话的轮次间隔很短，下一轮到达时"),
]


def main() -> int:
    total = 0
    for name, pairs in REPLACEMENTS.items():
        p = PAPER / name
        s = p.read_text(encoding="utf-8")
        before = len(s)
        hit = 0
        for old, new in pairs:
            if old in s:
                s = s.replace(old, new, 1)
                hit += 1
            else:
                print(f"  [!] {name} 锚点未找到: {old[:32]}")
        if hit:
            p.write_text(s, encoding="utf-8", newline="\n")
            total += hit
            print(f"  {name}: 改 {hit} 处，{before} -> {len(s)} 字符")

    print(f"\n共改 {total} 处")
    print("\n保留的「下一轮」（指会话轮次）：")
    for name, frag in KEEP:
        s = (PAPER / name).read_text(encoding="utf-8")
        ok = frag in s
        print(f"  {name}: {'在' if ok else '不见了'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
