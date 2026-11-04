"""给 PAPER.md 插入 [c-xxx] 主张引用，补上 P1（引用闭合）。

为什么需要这一步（框架层面）：
    docs/data-model.md 定义 P1「Paper 引用的每个 claim_id 必须存在」，
    由 scripts/audit_paper.py 机器校验。
    但本文 PAPER.md 原本**一个 [c-xxx] 都没有**，
    于是 18 条主张与正文之间没有任何机器可验证的连接，
    audit_paper.py 在这个归档上等于什么都没查（cited 为空集，A 项恒过）。

⚠️ 第一版按「锚点字符串首次出现」批量插入，结果 16 处里至少 4 处语义错位：
     - 摘要「度量危机」段插了 c-verified-drop（该段讲的是 70 条声明统计）
     - 摘要「关键词」行插了 c-rl-hacking（关键词没有主张）
     - 行 28 讲 92% 覆盖率，却插了 c-kb-baseline
   即「同一数字在多个段落出现，机器无法判断哪一处是它的论证位置」。
   故本版改为**逐条人工指定**：每条主张写明 (行号特征串, claim_id)，
   由 (行特征, 插入位置) 精确定位，不靠首次匹配。

做法：
    每项给一个 (行首特征, 结束后推荐引用)，在该行最后一个「。」前插入。
    行特征必须能唯一确定那一行。
"""

from __future__ import annotations

import re
from pathlib import Path

P = Path(__file__).resolve().parent / 'PAPER.md'

# (行内唯一特征串, 要插入的 claim_id 列表)
# 顺序即插入顺序；同一行可插入多条。
PLAN: list[tuple[str, list[str]]] = [
    # 摘要：每段结尾挂该段支撑的主张
    ('我们抽取全部 70 条速度声明并按语义分类', ['c-comparability']),
    ('全文 70 条声明中只有 **8 条（11%）** 可跨论文比较', ['c-comparability']),
    ('KernelBench-Verified 的受控实验显示，开启 TF32 基线', ['c-verified-drop']),
    ('另有 28% 的生成 kernel 增加了峰值显存', ['c-memory-cost']),
    ('可优化空间只占 8.9%–58.2%，端到端收益上限约', ['c-e2e-fraction']),
    # 第 1 章
    ('前沿推理模型在不到 20% 的题目上能达到 PyTorch 的速度', ['c-kb-baseline']),
    ('最强者的几何平均只有 0.88x', ['c-verified-drop']),
    ('同期已有一篇 IJCAI 2026 综述', ['c-survey-gap']),
    # 第 4 章
    ('构建了可扩展的数据合成流水线与带自动验证', ['c-coverage-vs-speed']),
    ('把访存模式、架构规', ['c-swizzle-expert']),
    ('提出「数据流不变量」', ['c-ave-invariant']),
    # 第 5 章
    ('进一步过滤：要求「几何或算术平均」', ['c-comparability']),
    ('同一篇 CUDA-L1，从 1.42x（中位数）到 120x（峰值）', ['c-l1-spread']),
    ('只报成功案例会系统性高估', ['c-memory-cost']),
    # 第 6 章
    ('典型例子就是 TF32', ['c-tf32-inflation']),
    ('对「诚实基线」只有 **2.03x**', ['c-strawman']),
    ('**19 个存在已确认的批量不变性违规**', ['c-batch-invariance']),
    ('60 道 Level-1 题中有 4 道可以被全零张量通过', ['c-zero-kernel']),
    # 第 7 章
    ('**80%–86% 的时间花在 cuBLAS GEMM 与 FlashAttention 里**', ['c-e2e-limit']),
    ('在占比 8.9% 的场景下端到端也只有约 1.07 倍', ['c-e2e-amdahl']),
    # 第 9 章
    ('从「不到 20% 的题目能打平 PyTorch」到「九成快于', ['c-kb-baseline']),
]


def main() -> int:
    text = P.read_text(encoding='utf-8')
    lines = text.split('\n')
    done: list[tuple[int, str]] = []
    failed: list[str] = []

    for needle, cids in PLAN:
        hit = None
        for i, line in enumerate(lines):
            if needle in line:
                hit = i
                break
        if hit is None:
            failed.append(needle)
            continue
        line = lines[hit]
        add = ''.join(f'[{c}]' for c in cids if f'[{c}]' not in line)
        if not add:
            continue
        pos = line.rfind('。')
        lines[hit] = (line[:pos] + add + line[pos:]) if pos >= 0 else line.rstrip() + add
        for c in cids:
            done.append((hit + 1, c))

    P.write_text('\n'.join(lines), encoding='utf-8', newline='\n')

    print(f'插入 {len(done)} 处：')
    for ln, cid in done:
        print(f'  行 {ln:4d}  [{cid}]')
    if failed:
        print(f'\n未命中 {len(failed)} 条：')
        for f in failed:
            print(f'  「{f[:40]}」')

    cited = sorted(set(re.findall(r'\[(c-[a-z0-9-]+)\]', '\n'.join(lines))))
    print(f'\n正文引用 {len(cited)} 条主张')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
