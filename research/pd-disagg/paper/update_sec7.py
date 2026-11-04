"""更新 §7 讨论与结论，纳入本轮的窗口发现。

## 为什么要改

第 1 轮 §7 的「如果要做下一步实验」写的是：
「扫描输入输出长度比，测出收益交叉点」——把它当成未来的工作。

但第 2 轮找到的 HeteroPanacea 已经做了这件事（跨 8 个模型扫 9 个比例），
而且结果比「一个交叉点」更强：是**有上下界的窗口，且非单调**。

如果还写「下一步要测交叉点」，等于忽略已有证据。必须改。

## 同理改局限

第 1 轮局限写「每类模型只取一到两例」。本轮补到 8 个模型
（Llama-3.1-405B、DeepSeek-V4、GPT-OSS、Llama4-Scout、
Llama4-Maverick、Qwen3-235B-A22B、GLM-4.6、DeepSeek-V4-Pro），
但**仍不足以支撑跨硬件平台的断言**——所有 8 个都在同一套
NPU 模拟设计空间里。这个限定要写清楚，否则「8 个模型」听起来
比实际更强。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "sec7_discuss.tex"


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")

    # ---- 1) 在「一个反复出现的模式」之后插入窗口讨论 ----
    anchor = "\\subsection{没做的事}"
    insert = r"""\subsection{本轮补上的一件事：收益有上界}

第 1 轮写这篇时，「收益取决于负载」只是一句定性判断，
「测出交叉点」被列为下一步实验。本轮找到了已做完这件事的工作：
跨 8 个模型扫 9 个输入输出比\texttt{[c-window]}。

结果比「一个交叉点」更有信息量，也更不利于简化叙事：

\begin{itemize}[leftmargin=1.3em,itemsep=1.5pt,topsep=2pt]
  \item 翻转确实存在，而且很陡：$I/O=1$ 时 $0.48\times$、
        $I/O=10$ 时 $2.10\times$，集中在\textbf{一个数量级}内。
  \item 但翻转之后\textbf{不是单调上升}。平台期 $1.5$--$1.8\times$
        延续到 $I/O=500$，$I/O=1000$ 回落到 $1.27\times$。
  \item 回落的原因是 decode 侧硬件开始闲置：prefill 大到成为瓶颈后，
        为 decode 单独配置的算力用不满。
\end{itemize}

这一条改变了我对「最佳实践」的理解。此前我把它想成「在什么条件下
分离划算」——一个单调的门槛。实际是\textbf{一个区间}：太轻不划算，
太重也不划算。而「太重」这一侧此前几乎没人讨论，
因为它不是失败案例，只是收益变薄。

实践含义很具体：如果按「负载越重越该分离」来判断，
会在最重的工作负载上做分离——恰好落在收益回落的区间。

"""
    if "本轮补上的一件事" not in s:
        i = s.find(anchor)
        if i < 0:
            print("[!] 找不到「没做的事」锚点")
            return 1
        s = s[:i] + insert + s[i:]
        print("已插入窗口讨论")
    else:
        print("窗口讨论已存在")

    # ---- 2) 改局限里的模型覆盖条目 ----
    old_cov = (r"  \item \textbf{模型覆盖不全。} MLA 有 DeepSeek 系、GQA 有 "
               r"Llama/Qwen 系、" + "\n"
               r"        MoE 有 ExpertPlex，但每类只取了一到两例，" + "\n"
               r"        不足以支撑「某类模型都该这样做」的断言。")
    new_cov = (r"  \item \textbf{模型覆盖有平台偏差。} 第 5 节引到 8 个模型的"
               r"结果（Llama-3.1-405B、" + "\n"
               r"        DeepSeek-V4、GPT-OSS、Llama4-Scout、Llama4-Maverick、"
               r"Qwen3-235B-A22B、" + "\n"
               r"        GLM-4.6、DeepSeek-V4-Pro），但\textbf{全部来自同一套 "
               r"NPU 模拟设计空间}。" + "\n"
               r"        故「8 个模型」不等于「8 种硬件」，跨真实加速器平台"
               r"（GPU / NPU / CXL 池）" + "\n"
               r"        的结论仍需实测。")
    if old_cov in s:
        s = s.replace(old_cov, new_cov)
        print("已改模型覆盖条目")
    elif "平台偏差" in s:
        print("模型覆盖条目已改过")
    else:
        print("[!] 模型覆盖条目锚点未找到")

    # ---- 3) 改「下一步实验」----
    old_next = (r"若要把判据变成可计算的模型，最小可行的实验是：在同一套硬件上，"
                r"\n固定模型与 SLO，扫描\textbf{输入输出长度比}这一个变量，"
                r"\n测出「分离 vs chunked prefill」的收益交叉点。"
                r"\n这个交叉点的位置，就是判据 1 与判据 3 的联合定量形式。"
                r"\n只需一套硬件、一个模型、一个 SLO，即可得到一条有实用价值的曲线。")
    new_next = (r"上一轮我把「扫描输入输出比、测出交叉点」列为待做，"
                r"本轮发现已有工作做了" + "\n"
                r"（见本节前面）。故剩下的空缺不是交叉点的\textbf{位置}，"
                r"而是它的\textbf{可迁移性}：" + "\n"
                r"已有结果全部来自模拟，且局限在一套 NPU 设计空间内。"
                r"最小可行的真实实验是：" + "\n"
                r"在同一套真实 GPU 上，固定模型与 SLO，扫输入输出比，"
                r"\textbf{测出窗口的上下沿}，" + "\n"
                r"再换一套互联（NVLink vs RDMA）重复一次，看窗口平移多少。"
                r"\n两张表就能回答「窗口位置由负载决定还是由拓扑决定」"
                r"这个本文无法回答的问题。")
    if old_next in s:
        s = s.replace(old_next, new_next)
        print("已改下一步实验")
    elif "可迁移性" in s:
        print("下一步实验已改过")
    else:
        print("[!] 下一步实验锚点未找到")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nsec7_discuss.tex {len(s):,} 字符")
    print("  含 c-window:", s.count("c-window"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
