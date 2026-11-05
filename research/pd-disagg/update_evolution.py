"""给 EVOLUTION.md 加判据八，并更新覆盖率表。

## 为什么这条够格成为判据

现有七条判据的共同点是「**怎么验**已有的东西」（执行路径、分母、
三态、子串、脚本算数、反例测试、两次成规则）。
缺的是「**去哪找**」——检索范围本身可能系统性缺一块。

本轮的翻车正是这一类：46 篇论文、203 篇候选、12 组查询，
E1 覆盖率 100%，所有判据都过了，但**整层内容没在语料里**。
检查再严也检不出「没找」。

故判据八与其余七条正交：其余七条管「验得对不对」，
它管「找得全不全」。

## 同时更新覆盖率表

原表只有 4 个归档，加上 pd-disagg（62/62 = 100%）与 kernel-agent
已列。表里的数字从 validate 输出取，不手写。
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent  # 仓库根
TARGET = HERE / "docs" / "EVOLUTION.md"

CRITERION_8 = """### 判据八：检索的盲区不会被检查发现

前七条都在管「**验得对不对**」。还有一类错误它们全都检不出：
**东西根本没被找进来**。

本仓库的一次实例：一篇 46 篇论文、67 个来源的综述，E1 覆盖率 100%、
数值回溯全通过、审计全绿——但缺了整整一层内容（具体的优化技巧）。
原因是检索只用了学术术语（`disaggregated prefill`、`KV transfer`），
而 `LPLB`、`Waterfill`、`DSpark` 这些**工程术语在 46 篇全文里一次都没出现**：
它们还没有对应的论文，只活在框架文档与工程博客里。

**为什么检查救不了**：所有检查器的输入都来自语料。语料缺一块，
检查器在缺失的子集上依然全绿。`0/0` 与 `0/3000` 都显示为「无失败」。

**怎么用**：检索计划里单独列**来源类别**，不是只列查询词：

| 类别 | 例子 | 缺了会怎样 |
|---|---|---|
| 学术论文 | arXiv、会议 | 缺机制的一手推导 |
| 框架官方文档 | SGLang / vLLM docs | 缺实践者真正在用的开关 |
| 设计文档 | `docs/design/*.md` | 缺实现约束与阈值来源 |
| 工程博客 | 厂商 / 团队博客 | 缺未经论文包装的实测数字 |
| release notes / PR | GitHub | 缺「什么时候引入、什么时候弃用」 |

判据不是「有没有论文」，而是「**本领域的从业者会怎么称呼它**」。
凡是这个问题的答案不在已检索的词汇表里，就再做一轮。

"""


def get_counts() -> dict[str, tuple[int, int]]:
    """从 validate 取每个归档的 (evidence, e1_checked)。"""
    env = {"PYTHONPATH": r"D:\github\DeepResearchRSI\packages\schemas\python"}
    import os
    e = dict(os.environ)
    e.update(env)
    out: dict[str, tuple[int, int]] = {}
    for slug in ("rtx-pro-6000", "cuda-kernel-gen", "cuda-kernel-rl",
                 "kernel-agent", "pd-disagg"):
        try:
            r = subprocess.run(
                [sys.executable, "-m", "deepresearchrsi.validate",
                 f"research/{slug}"],
                capture_output=True, text=True, env=e, timeout=120)
            txt = r.stdout + r.stderr
            ev = chk = None
            import re
            m = re.search(r"evidence=(\d+)", txt)
            if m:
                ev = int(m.group(1))
            m = re.search(r"e1_checked=(\d+)", txt)
            if m:
                chk = int(m.group(1))
            if ev is not None and chk is not None:
                out[slug] = (ev, chk)
        except Exception as ex:  # 不让取数失败阻断文档更新
            print(f"  [!] {slug}: {ex}")
    return out


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")
    orig = len(s)

    # ---- 1) 加判据八 ----
    if "判据八" not in s:
        anchor = "---\n\n## 4. 三次「进化失败」"
        i = s.find(anchor)
        if i < 0:
            print("[!] 找不到第四节锚点")
            return 1
        s = s[:i] + CRITERION_8 + s[i:]
        # 标题里的「七条」改成「八条」
        s = s.replace("## 3. 进化出来的七条判据",
                      "## 3. 进化出来的八条判据")
        s = s.replace("以下七条是这套系统真正学到的东西",
                      "以下八条是这套系统真正学到的东西")
        print("已加判据八")
    else:
        print("判据八已存在")

    # ---- 2) 更新覆盖率表 ----
    counts = get_counts()
    if counts:
        rows = []
        order = ["rtx-pro-6000", "cuda-kernel-gen", "cuda-kernel-rl",
                 "kernel-agent", "pd-disagg"]
        rows.append("| 归档 | 证据数 | E1 已校验 | 覆盖率 |")
        rows.append("|---|---|---|---|")
        for slug in order:
            if slug not in counts:
                continue
            ev, chk = counts[slug]
            pct = f"{chk / ev * 100:.0f}%" if ev else "—"
            bold = "**" if pct == "100%" or pct == "0%" else ""
            rows.append(f"| `{slug}` | {ev} | {chk} | {bold}{pct}{bold} |")
        new_table = "\n".join(rows)

        old_start = s.find("| 归档 | 证据数 | E1 已校验 | 覆盖率 |")
        if old_start >= 0:
            old_end = s.find("\n\n", old_start)
            s = s[:old_start] + new_table + s[old_end:]
            print("已更新覆盖率表")

    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"\nEVOLUTION.md {orig:,} -> {len(s):,} 字符")
    for probe in ("判据八", "八条判据", "框架官方文档", "pd-disagg"):
        print(f"  含 {probe:<14} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
