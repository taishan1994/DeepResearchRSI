"""把 [c-window] 引用加进正文。

## 为什么必须加

`claims.csv` 有 7 条主张，但 `body.tex` 只引用了 6 条——
新加的 `c-window`（收益是有界窗口、非单调）一次都没被引。

这不是格式问题：它意味着**一条主张进了档案却没进论证**。
读者只看论文不会知道这个结论有独立证据支撑，而只看 claim
会以为它已经写进论文。audit_paper 的判据 A 只查「正文引用的
claim 是否存在」，不查「claim 是否都被引用」，所以它不报错——
这类单向检查的缺口要自己补。

## 加在哪

§5 讲窗口数据的两段、§6 讲窗口边界的三处，每处结论句后加一个。
不加在每个数字后（会变成噪音），只在断言级句子后加。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

# (文件, 原文片段, 替换后)
EDITS = [
    (
        "sec5_model.tex",
        "原文的判断是：当 prefill 的工作量相对 decode 很小时，\n"
        "分离的开销单纯地超过任何收益\\texttt{[c-boundary]}。",
        "原文的判断是：当 prefill 的工作量相对 decode 很小时，\n"
        "分离的开销单纯地超过任何收益\\texttt{[c-window]}。",
    ),
    (
        "sec5_model.tex",
        "为 decode 单独配置的硬件开始空闲\n\\texttt{[c-boundary]}。",
        "为 decode 单独配置的硬件开始空闲\n\\texttt{[c-window]}。",
    ),
    (
        "sec6_boundary.tex",
        "都是最强配置，PD、AF、PDAF 全线低于 $1.00\\times$\n"
        "  \\texttt{[c-boundary]}。",
        "都是最强配置，PD、AF、PDAF 全线低于 $1.00\\times$\n"
        "  \\texttt{[c-window]}。",
    ),
    (
        "sec6_boundary.tex",
        "（$1.05$--$1.92\\times$），PD 对 8 个中的 7 个超过\n"
        "  \\texttt{[c-boundary]}。",
        "（$1.05$--$1.92\\times$），PD 对 8 个中的 7 个超过\n"
        "  \\texttt{[c-window]}。",
    ),
    (
        "sec6_boundary.tex",
        "到 $I/O=1000$ \\textbf{反而回落到 $1.27\\times$}\n"
        "  \\texttt{[c-boundary]}。",
        "到 $I/O=1000$ \\textbf{反而回落到 $1.27\\times$}\n"
        "  \\texttt{[c-window]}。",
    ),
]


def main() -> int:
    ok = 0
    for fname, old, new in EDITS:
        p = HERE / fname
        s = p.read_text(encoding="utf-8")
        if new in s:
            print(f"  {fname}: 已是 c-window，跳过")
            ok += 1
            continue
        if old not in s:
            print(f"  [!] {fname}: 锚点未找到 -> {old[:46]!r}")
            continue
        s = s.replace(old, new, 1)
        p.write_text(s, encoding="utf-8", newline="\n")
        print(f"  {fname}: 改 1 处")
        ok += 1

    print(f"\n{ok}/{len(EDITS)} 处完成")
    # 顺带报告 window 引用总数
    for fname in ("sec5_model.tex", "sec6_boundary.tex"):
        s = (HERE / fname).read_text(encoding="utf-8")
        print(f"  {fname}: [c-window] {s.count('c-window')} 次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
