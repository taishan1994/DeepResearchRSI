"""在 PAPER.md 的指定位置插入 `[c-xxx]` 引用标记。

## 为什么不用锚点自动匹配

`cuda-kernel-gen` 试过：按「第一处匹配的关键句」插入，
16 处里 4 处语义错位——同一个数字在摘要、正文、图注反复出现，
机器无法判断哪一处是它的**论证位置**。

故这里用 (定位片段, claim_id) 的手工配对表。定位片段取该处**独有**的短语，
insert 时校验「片段存在且唯一」，不唯一就报错，绝不猜。
"""

from __future__ import annotations

import sys
from pathlib import Path

P = Path(__file__).resolve().parent / "PAPER.md"

# (定位片段, 要插入的 claim 标记, 插在片段之前还是之后)
# anchor 必须在该处唯一出现，否则脚本拒绝执行。
INSERTS: list[tuple[str, str, str]] = [
    # 1.1 难度落差
    ("前者在 2025 年基本被解决", "c-benchmark-base", "after"),
    # 1.1 RL 适用条件
    ("这正是 RLVR 这一范式的适用条件", "c-kernel-rl-fit", "after"),
    # 2.1 Kevin 的可验证奖励
    ("Kevin 明确指出，kernel 编写是高度迭代的过程",
     "c-iterative-nature", "after"),
    # 2.2 多轮代价
    ("多轮环境反馈的两个主要成本是编译延迟与奖励稀释",
     "c-env-cost", "after"),
    # 2.2 上下文约束
    ("交互轮数增加会让上下文迅速累积",
     "c-context-limit", "after"),
    # 2.3 谱系起点
    ("CuAsmRL（2025-01）在 SASS 指令调度层用 RL agent",
     "c-cuasmrl-origin", "after"),
    # 3.1 无新优化目标
    ("没有一个工作提出新的优化目标", "c-grpo-default-but-flawed", "after"),
    # 3.2 结果型与多轮并列
    ("结果型与多轮交互并列最高（各 9 篇）", "c-structural-reward", "after"),
    # 3.3 结果驱动
    ("代表是 CUDA-L1（对比式 RL）", "c-l1-result", "after"),
    # 3.3 CUDA-L2
    ("以执行速度直接作奖励，以 cuBLAS 为基线", "c-l2-cublas", "after"),
    # 3.3 过程驱动
    ("层次化分解（TritonRL 的 HRD）", "c-hrd-decomposition", "after"),
    # 4.1 反复报告
    ("模型会 hack 训练奖励，优先选「平凡的正确性」",
     "c-reward-hacking", "after"),
    # 4.1 三重困难
    ("把它与稀疏奖励、训练不稳定并列为三重困难",
     "c-three-difficulties", "after"),
    # 4.2 懒惰优化
    ("这就是 Dr. Kernel 说的「懒惰优化」（lazy optimization）",
     "c-lazy-optimization", "after"),
    # 4.3 基线作弊
    ("KernelBench-Verified 用更严格的协议重测，结论反转",
     "c-baseline-inflation", "after"),
    # 4.3 评测器漏洞
    ("Measuring the Checker 用变异分析检验评测器",
     "c-checker-reliability", "after"),
    # 4.4 PRS
    ("Dr. Kernel 用 PR（progressive rewards）与 PRS",
     "c-prs-rejection", "after"),
    # 5.1 梯度有偏
    ("Dr. Kernel 指出 GRPO 存在 self-inclusion 导致的策略梯度偏差",
     "c-grpo-default-but-flawed", "after"),
    # 5.2 长程稀疏
    ("GRPO 依赖终端结果评估，训练长程任务时**固有地**产生稀疏奖励",
     "c-grpo-default-but-flawed", "after"),
    # 5.3 无人报净效果
    ("没有任何工作报告「加了中间奖励之后，最终加速比是否真的提高」的对照实验",
     "c-grpo-default-but-flawed", "after"),
    # 6.3 检索盲区
    ("KernelBench 与 Cold-Start 两篇不在本轮候选池中",
     "c-benchmark-base", "after"),
    # 7.4 消融建议
    ("都应该报告「有中间奖励 vs 无中间奖励」的最终加速比对照",
     "c-grpo-default-but-flawed", "after"),
    # 3.3 环境驱动
    ("CUDA Agent 把 RL 与 agent 环境、数据合成流水线结合",
     "c-agentic-scale", "after"),
    # 3.3 过程驱动 profiling
    ("profiling 计数器（Micro-Profiling）", "c-profiling-reward", "after"),
]


def main() -> int:
    text = P.read_text(encoding="utf-8")
    applied = 0
    skipped: list[str] = []

    # 先检查所有锚点唯一性，全部通过才动手——避免改一半
    for anchor, cid, _pos in INSERTS:
        n = text.count(anchor)
        if n != 1:
            skipped.append(f"{anchor[:36]}… 出现 {n} 次（需恰好 1 次）")
    if skipped:
        print("[!] 锚点不唯一，未做任何修改：")
        for s in skipped:
            print("    " + s)
        return 1

    # 从后往前插，避免前面的插入影响后面的偏移
    for anchor, cid, pos in sorted(INSERTS,
                                   key=lambda x: -text.find(x[0])):
        idx = text.find(anchor)
        insert_at = idx + len(anchor) if pos == "after" else idx
        text = text[:insert_at] + f" [{cid}]" + text[insert_at:]
        applied += 1

    P.write_text(text, encoding="utf-8", newline="\n")
    print(f"已插入 {applied} 处引用标记")

    # 立即自检：所有 c-xxx 都必须在 claims.csv 里存在
    import csv
    claims_csv = P.parent.parent / "claims.csv"
    with claims_csv.open(encoding="utf-8-sig", newline="") as fh:
        valid = {r["claim_id"] for r in csv.DictReader(fh)}
    import re
    used = set(re.findall(r"\[(c-[a-z0-9-]+)\]", text))
    bad = used - valid
    if bad:
        print(f"[!] 引用了不存在的主张：{sorted(bad)}")
        return 1
    print(f"引用自检通过：{len(used)} 个主张被正文引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
