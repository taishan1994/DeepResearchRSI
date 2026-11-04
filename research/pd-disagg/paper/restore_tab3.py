"""把 tab3 模型侧变量表插回 sec5（重写 §5 时误删）。

## 为什么是「插回」而不是「新增」

第 1 轮的 sec5_model.tex 里有一张 `tab:model-vars` 表，登记在
paper.json 的 tables 里。第 2 轮我整体重写了 §5，把这张表去掉了，
但 paper.json 仍声明着它——audit_paper 的判据 B 于是报
「正文可能没有引用表：tab3」。

两个选择：删掉 paper.json 里的登记，或把表插回去。
选插回：表里的内容（上下文长度、输入输出比、互联拓扑、SLO）
在重写后的正文里散落在不同段落，成表更便于查。
同时按新的「两个正交轴」框架加一列「轴」，
让表本身也说清新框架。

## 用 write 而不是 here-string

PowerShell here-string 对反斜杠的层数处理不可预测，
同一个 `\\subsection` 在不同轮次被解析成不同结果。
本文件用 chr(92) 拼 LaTeX 命令，彻底绕开。
"""

from __future__ import annotations

from pathlib import Path

BS = chr(92)       # 文件里就是单个反斜杠 + 命令名

HERE = Path(__file__).resolve().parent
TARGET = HERE / "sec5_model.tex"


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")

    if "tab:model-vars" in s:
        print("tab3 已存在，无需插入")
        return 0

    b = BS  # 简写

    table = (
        b + "begin{table}[t]\n"
        + b + "centering\n"
        + b + "caption{决定分离做法的六个变量，只有前两个是模型属性。"
        + "「轴」一列标出该变量影响的是传输成本侧还是并行策略侧——"
        + "这是本文区分注意力轴与 FFN 轴的依据。}\n"
        + b + "label{tab:model-vars}\n"
        + b + "small\n"
        + b + "begin{tabular}{@{}p{1.55cm}p{0.85cm}p{2.35cm}p{1.55cm}@{}}\n"
        + b + "toprule\n"
        + "变量 & 轴 & 影响 & 是否模型属性 " + b + b + "\n"
        + b + "midrule\n"
        + "KV 每 token 大小 & 注意力 & MLA $<$ GQA $<$ MHA，差一个量级 & 是 "
        + b + b + "\n"
        + "FFN 结构 & FFN & dense vs MoE，决定专家放置 & 是 " + b + b + "\n"
        + "上下文长度 & --- & 线性放大 KV，兼有容量问题 & 否（业务） "
        + b + b + "\n"
        + "输入输出比 & --- & 决定 P:D 配比，且收益有窗口 & 否（业务） "
        + b + b + "\n"
        + "互联拓扑 & 成本 & 决定传输带宽档位 & 否（部署） " + b + b + "\n"
        + "SLO & --- & 决定 goodput 定义与最优配比 & 否（业务） "
        + b + b + "\n"
        + b + "bottomrule\n"
        + b + "end{tabular}\n"
        + b + "end{table}\n\n"
    )

    # 插在最后一节之前，让它在「六个变量」的论述附近
    anchor = b + "subsection{为什么仍然不存在统一配置}"
    i = s.find(anchor)
    if i < 0:
        print("[!] 锚点未找到")
        return 1

    s = s[:i] + table + s[i:]
    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"tab3 已插入（{TARGET.name}，{len(s):,} 字符）")

    # 校验
    t = TARGET.read_text(encoding="utf-8")
    print("  tab:model-vars 出现", t.count("tab:model-vars"), "次")
    print("  begin{table}", t.count(b + "begin{table}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
