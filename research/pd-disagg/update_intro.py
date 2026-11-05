"""更新引言：加入技巧层，并同步计数。

## 为什么必须改引言

用户指出第 1 轮缺「优化技巧」这一层。若只在正文补一节而不动引言，
读者从开篇的贡献列表里看不出有这一层——那等于没补。

## 改动

1. 贡献列表插入一条独立项（技巧层单列，不塞进模型那一条）
2. 方法说明的计数同步：63->67 源、27->62 证、6->8 主张
3. E1 的表述从「27/27」改为「62/62」，并说明为何强调全通过
4. 补一句：技巧里有几条是分离的**替代品**，这改变了判据的用法

## 一个措辞选择

不写「本文首次提出四类划分」。这个划分是从证据里归纳的，
但我没有把握说它是新的——技巧分类在工程博客里零散出现过。
写成「本文按作用对象归为四类」更诚实。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "paper" / "sec1_intro.tex"


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")
    orig = len(s)

    # ---- 1) 贡献列表：在「主动搜集…失效条件」之前插一条 ----
    anchor = "  \\item 主动搜集使分离失效或转负的条件"
    item = (
        "  \\item 把分散在框架文档与工程博客里的\\textbf{具体优化技巧}按\n"
        "        「作用于哪个环节」归为四类，逐条给实测幅度与前置依赖，\n"
        "        并指出其中几条其实是分离的\\textbf{替代品}而非补充\n"
        "        （第 \\ref{sec:technique} 节）。\n"
    )
    if "具体优化技巧" not in s:
        i = s.find(anchor)
        if i < 0:
            print("[!] 贡献列表锚点未找到")
        else:
            s = s[:i] + item + s[i:]
            print("已插入技巧层贡献项")
    else:
        print("技巧层贡献项已存在")

    # ---- 2) 计数 ----
    reps = [
        ("46 篇论文全文与 17 份官方工程文档快照，共 63 个来源、\n"
         "27 条证据、6 条主张",
         "46 篇论文全文与 21 份官方工程文档快照，共 67 个来源、\n"
         "62 条证据、8 条主张"),
        ("（E1 不变量，\n27/27 全部校验通过，无「未校验」条目）",
         "（E1 不变量，\n62/62 全部校验通过，无「未校验」条目）"),
        ("63 个来源、\n27 条证据、6 条主张",
         "67 个来源、\n62 条证据、8 条主张"),
    ]
    for a, b in reps:
        if a in s:
            s = s.replace(a, b)
            print(f"已改计数：{a[:22]}...")

    # ---- 3) 补一句替代品性质 ----
    tail_anchor = "对已发表结果的整理与再计算，不是新的测量。"
    extra = (
        "\n\n最后一点值得前置说明：本文列出的技巧里有几条是分离的\n"
        "\\textbf{替代品}而非补充——chunked prefill 与 piggyback 在不分离的\n"
        "架构里就能拿到相当一部分收益。这意味着第 \\ref{sec:boundary} 节\n"
        "的判据不是「要不要分离」的二选一，而是「先试便宜的手段、\n"
        "再考虑分离」的顺序问题。"
    )
    if "替代品" not in s.split(tail_anchor)[-1]:
        i = s.find(tail_anchor)
        if i > 0:
            j = i + len(tail_anchor)
            s = s[:j] + extra + s[j:]
            print("已补『替代品』说明")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nsec1_intro.tex {orig} -> {len(s)} 字符")
    for probe in ("sec:technique", "62", "67", "替代品"):
        print(f"  含 {probe:<16} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
