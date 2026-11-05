"""更新结论：技术栈从三层改为四层，技巧层单列。

## 为什么必须改

结论开头写的是「技术栈可以分成三层：为什么分 / 怎么搬 / 怎么切」。
用户的反馈恰恰是缺了第四层——**具体优化技巧**。
若结论仍是三层，读者从最后一段看不出这一层存在，
等于补的内容没有进入论证结构。

## 改成什么

四层，并把技巧层的性质写进结论：
  · 按作用对象四类（省传输量 / 让传输不可见 / 均衡 / 省 decode 步）
  · 同类替代、异类叠加 —— 这是最实用的一句
  · 有几条是分离的替代品，故判据的用法是「先后顺序」而非「二选一」

## 一个数字上的取舍

不在结论里重复 525% 这类极端值。它来自模拟过载场景，
放在结论会夸大。结论只用区间与量级。

## 实现注意

标题行的 `\\section{结论}` 是单个反斜杠，用 chr(92) 拼，
不手写——此处历史上多次被 PowerShell 吃掉一个反斜杠。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "paper" / "sec7_discuss.tex"

BS = chr(92)

OLD = (
    "PD 分离的技术栈可以分成三层："
    + BS + "textbf{为什么分}（两阶段资源画像相反）、\n"
    + BS + "textbf{怎么搬}（NVLink / RDMA / 存储三档，相差一个数量级以上）、\n"
    + BS + "textbf{怎么切}（chunked prefill、显式分离、弹性调整三条路线）。"
)

NEW = (
    "PD 分离的技术栈可以分成四层："
    + BS + "textbf{为什么分}（两阶段资源画像相反）、\n"
    + BS + "textbf{怎么搬}（NVLink / RDMA / 存储三档，相差一个数量级以上）、\n"
    + BS + "textbf{怎么切}（chunked prefill、显式分离、弹性调整三条路线）、\n"
    + BS + "textbf{怎么优化}（具体技巧，按作用对象分四类）。\n\n"
    "第四层是本文最后补上的一层，也是最容易被一句「部署时调一调」\n"
    "打发掉的一层。它值得单列，因为四类技巧"
    + BS + "textbf{同类互相替代、异类可以叠加}：\n"
    "省传输量（逐层与 chunk 级传输、KV 压缩、前缀缓存）、\n"
    "让传输不可见（TBO、SBO、DBO、piggyback）、\n"
    "均衡负载（Waterfill、LPLB、EPLB）、\n"
    "省 decode 步（DSpark 自适应验证、投机解码）。\n"
    "取舍问题因此不是「选哪个」，而是「每类选一个」。\n\n"
    "各类的幅度差一到两个数量级，且都"
    + BS + "textbf{有前置依赖}：\n"
    "均衡类是个位数百分比（$0.84" + BS + "%$--$7.34" + BS + "%$），\n"
    "且在无冗余副本时只有开销；逐层传输在 KV 太小时因固定开销反而更慢；\n"
    "DBO 在 token 数低于阈值时不拆。"
    + BS + "textbf{前置条件不满足时，开了是负收益。}\n\n"
    "更关键的是：这几类里有几条是分离的"
    + BS + "textbf{替代品}而非补充——\n"
    "chunked prefill 与 piggyback 在不分离架构里就能拿到相当一部分收益。\n"
    "故本文的判据不是「要不要分离」的二选一，而是一个先后顺序：\n"
    "先试便宜的手段（省量、隐藏、准入），再考虑分离——\n"
    "因为分离是这些手段里固定成本最高的一个。"
)


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")
    orig = len(s)

    if "四层" in s:
        print("结论已是四层")
        return 0

    if OLD not in s:
        print("[!] 结论开头未匹配，退化为逐句替换")
        a = "PD 分离的技术栈可以分成三层"
        if a in s:
            s = s.replace(a, "PD 分离的技术栈可以分成四层")
            # 在「三条路线）。」后追加第四层
            b = "弹性调整三条路线）。"
            if b in s:
                s = s.replace(b, b + "\n\n" + NEW.split("\n\n", 1)[1], 1)
                print("已用退化路径改为四层")
            else:
                print("[!] 退化路径也失败")
                return 1
        else:
            return 1
    else:
        s = s.replace(OLD, NEW)
        print("已改为四层")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"sec7_discuss.tex {orig} -> {len(s)} 字符")
    for probe in ("四层", "同类互相替代", "替代品", "前置条件不满足"):
        print(f"  含 {probe:<14} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
