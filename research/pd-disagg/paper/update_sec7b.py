"""改 §7 的「下一步实验」与「结论」，用精确切片。

## 为什么单独写

上一个脚本（update_sec7.py）用整段字符串做锚点，`\\n` 与实际
换行位置差一个字符就匹配不上。改为先定位起止标记、再切片替换，
对换行不敏感。

## 内容上要改三处

1. 「下一步实验」：第 1 轮把「测收益交叉点」列为待做，
   第 2 轮发现已有工作做了。故改为「剩下的问题是窗口的可迁移性」。

2. 结论里的「五个变量」：加了 FFN 轴之后是六个。

3. 结论里的判据第三条：「负载足够重」→「负载落在窗口内」。
   旧表述与第 6 节已不一致。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "sec7_discuss.tex"

NEW_NEXT = r"""上一轮我把「扫描输入输出比、测出交叉点」列为待做，本轮发现已有工作
做了这件事（见本节前面）。故剩下的空缺不是交叉点的\textbf{位置}，
而是它的\textbf{可迁移性}：已有结果全部来自模拟，且局限在一套
NPU 设计空间内。

最小可行的真实实验是：在同一套真实 GPU 上，固定模型与 SLO，
扫输入输出比，\textbf{测出窗口的上下沿}；再换一套互联
（NVLink vs RDMA）重复一次，看窗口平移多少。两张表就能回答
「窗口位置由负载决定还是由拓扑决定」——这是本文无法回答的问题。"""

NEW_CONCL = r"""不同模型的最佳实践不能被表述为一套配置，因为最优做法取决于
六个变量（KV 每 token 大小、FFN 结构、上下文长度、输入输出比、
互联拓扑、SLO），其中只有前两个是模型属性。可迁移的结论是判据而非配置：
两阶段最优配置显著不同、存在高带宽 KV 通路、\textbf{负载落在窗口内}、
KV 规模足够大——四项全满足时分离才划算。

第三条的措辞在本轮被改过，值得单独说明：原先是「负载足够重」，
现在是「负载落在窗口内」。差别在于收益有\textbf{上界}——
$I/O$ 从 10 涨到 1000 时，相对收益从 $2.10\times$ 回落到 $1.27\times$。
按「越重越好」判断，会在最重的工作负载上做分离，恰好是收益变薄的区间。"""


def replace_block(s: str, start: str, end: str, new: str) -> tuple[str, bool]:
    i = s.find(start)
    if i < 0:
        return s, False
    j = s.find(end, i)
    if j < 0:
        return s, False
    return s[:i] + new + "\n" + s[j:], True


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")

    # ---- 1) 下一步实验 ----
    if "可迁移性" not in s:
        s, ok = replace_block(
            s,
            "若要把判据变成可计算的模型",
            "\n\n\\section{结论}",
            NEW_NEXT,
        )
        print("下一步实验:", "已改" if ok else "[!] 未找到")
    else:
        print("下一步实验: 已改过")

    # ---- 2) 结论段 ----
    if "六个变量" not in s:
        s, ok = replace_block(
            s,
            "不同模型的最佳实践不能被表述为一套配置",
            "\n\n最后一点值得重复",
            NEW_CONCL,
        )
        print("结论段:", "已改" if ok else "[!] 未找到")
    else:
        print("结论段: 已改过")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nsec7_discuss.tex {len(s):,} 字符")
    for probe in ("六个变量", "窗口内", "可迁移性", "2.10"):
        print(f"  含 {probe:<8} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
