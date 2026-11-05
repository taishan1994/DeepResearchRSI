"""压缩 sec10 / sec11 里重复的「与前几节的关系」段。

## 问题

三次换维度，每次都写了一段「与前面几节的关系」：
sec9（三平面）、sec10（SLO）、sec11（负载）。
三段结构相同、内容层层叠加。叠加本身是对的（每加一层要重新收拢），
但读到第三次就是重复，且判据页已把六层关系统一收拢。

## 改法

sec9 保留（第一次收拢，读者需要）。
sec10 与 sec11 各压成一小段：保留「本层新增的判断力」，
把重新列举前三节的部分换成指向判据页的交叉引用。

## 实现

不用长字符串拼接（上一版因漏写 + 报了语法错），
改用「找 subsection 标题、切到下一个 subsection」的结构化定位。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"
BS = chr(92)


def slice_subsection(s: str, title_frag: str) -> tuple[int, int] | None:
    """找到以 title_frag 开头的 subsection，返回 [start, end) 边界。"""
    m = re.search(re.escape(BS) + r"subsection\{[^}]*" + re.escape(title_frag)
                  + r"[^}]*\}", s)
    if not m:
        return None
    start = m.start()
    nxt = re.search(re.escape(BS) + r"subsection\{", s[m.end():])
    end = m.end() + nxt.start() if nxt else len(s)
    return start, end


SLO_NEW = (
    BS + "subsection{这一节新增的判断力}\n\n"
    "三平面保证不漏，四类给出取舍，而 SLO 是第一个能让前面结论\n"
    + BS + "textbf{发生方向翻转}的维度——这是它存在的全部理由。\n"
    "六层的完整关系与使用顺序见第 " + BS + "ref{sec:onepage} 节的\n"
    "图 " + BS + "ref{fig:decision} 与表 " + BS + "ref{tab:layers}。\n\n"
)

LOAD_NEW = (
    BS + "subsection{这一节新增的判断力}\n\n"
    "负载形态是唯一一个能" + BS + "textbf{取消一整类技巧}的维度，\n"
    "而 SLO 只能翻转方向——理由已在第 " + BS + "ref{sec:onepage} 节说明。\n"
    "这里只补它带来的正面结论：\n"
    + BS + "textbf{当命中率足够高时，最有效的优化不是把 KV 搬得更快，\n"
    "而是让 KV 不必被搬}。这与本文反复出现的那条主线一致——\n"
    "收益来自「让两阶段不必做同一件事」，而最高效的做法是\n"
    "让某件事根本不发生。分离是这条主线里最贵的一个实例；\n"
    "前缀命中是同一个道理在缓存层的体现，且它比分离便宜得多。\n"
)


def main() -> int:
    for name, frag, new in [
        ("sec10_slo.tex", "这一节与前三节的关系", SLO_NEW),
        ("sec11_load.tex", "这一步在判据里的位置", LOAD_NEW),
    ]:
        p = PAPER / name
        s = p.read_text(encoding="utf-8")
        before = len(s)
        span = slice_subsection(s, frag)
        if not span:
            print(f"[!] {name} 未找到「{frag}」")
            continue
        start, end = span
        print(f"  {name}: 该小节 {end - start} 字符")
        s = s[:start] + new + s[end:]
        p.write_text(s, encoding="utf-8", newline="\n")
        print(f"    {before} -> {len(s)} 字符（-{before - len(s)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
