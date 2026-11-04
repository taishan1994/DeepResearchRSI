"""给 9 张图写实体图注，替换掉「图 N」这种空壳。

问题（用户指出）：
    图片内部标题写着「图 1　本文纳入的 58 篇论文按发表月份分布」，
    PDF 图注又写着「图 1：图 1」——两处编号，两处说明，
    读者无法判断哪个是权威。

修法：
    1. 图内标题去掉「图 N」前缀（fix_figure_titles.py 已做），
       只留自解释的短标题，编号与说明交给 caption。
    2. alt 文本从「图 N」改为完整图注，md_to_tex.py 会把它转成
       \\caption{...}，PDF 里就是「图 N：<图注>」。

图注写法：先说这张图展示什么，再说数据来源，最后说该看什么。
"""

from __future__ import annotations

import re
from pathlib import Path

P = Path(__file__).resolve().parent / 'PAPER.md'

CAPTIONS = {
    1: ('本文纳入的 98 篇论文按发表月份分布。'
        '红色区域为 2025-10 之后，占全部论文的 89%。'
        '数据来自 arXiv 官方 API 的 submittedDate 字段，'
        '可见领域在 2025 年下半年后急剧升温。'),

    2: ('70 条速度声明的语义类型分布。'
        '横轴为条数，括号内为占全部声明的百分比。'
        '绿色区域为口径合格的两类（算术平均与几何平均）。'
        '只有 8 条（11%）同时满足「总体平均 + 明确库基线」，'
        '即真正可跨论文比较。'),

    3: ('同一系统换一个基线，结论就反转。'
        '三组柱子分别是 CUDA-L1、CUDA-L2 与 KernelBench-Verified，'
        '每组从左到右基线依次变严。'
        '最右一组最能说明问题：同一个 GPT-5.5，在默认 PyTorch 协议下是 1.43x，'
        '换成 TF32 基线并加入隐藏测试集后只有 0.88x——'
        '从「超过 PyTorch」变成「打不过 PyTorch」。'
        '这里只画两个端点，因为原始论文只报告了这两个数，'
        '不存在「只换 TF32 而保留原测试集」的中间测量。'),

    4: ('各方法标签的论文数，按半年切分。'
        '同一篇论文可带多个标签。'
        'SFT 路线在 2025 上半年占优，RL 与 Agent 路线自 2025 下半年起快速上升，'
        '2026 年之后纯 SFT 工作已明显减少。'),

    5: ('两个系统在同一基准上报告的量纲不同，故分两栏呈现。'
        '(a) KernelPro 报告的是几何平均加速比（2.42x / 4.69x / 5.30x，对应 Level 1/2/3）；'
        '(b) CUDA Agent 报告的是「快于 torch.compile 的 kernel 占比」（100% / 100% / 92%）。'
        '左栏是「快多少倍」，右栏是「有多少个更快」——'
        '把两者并成一根轴，就会读成「CUDA Agent 快 100 倍」。'),

    6: ('三类泄漏的并列示意，从左至右依次为训练集泄漏、基线泄漏、测试集泄漏，'
        '每格给出其典型表现。底部一行是后果：报告数字与真实能力之间的落差，'
        '以 KernelBench-Verified 实测的 1.43x → 0.88x 为例。'
        '三者性质不同但后果同向——都让「会不会写 kernel」被高估。'),

    7: ('搜索成本与性能回报的收益递减关系。'
        '注意这是一张示意图，纵轴是量级估计而非实测值：'
        '横轴按系统复杂度排序（单轮生成 → 多轮反馈 → Agent 搜索 → 多 Agent → 进化算法），'
        '纵轴给出各路线典型几何平均加速比的大致位置，'
        '成本按相对倍数标注。'
        '要传达的是趋势：成本随复杂度呈指数增长，性能回报趋于饱和，'
        '提示「更多搜索」并非当前瓶颈的解法。'),

    8: ('可比性随时间的变化。'
        '两个时段的分组对比：几何平均占比从 18% 升至 30%，'
        '说明报告几何平均正在成为惯例；'
        '但达到「总体平均 + 明确库基线」双重标准的声明从 16% 降至 0%——'
        '论文数量翻倍，可比数字没有增加。'),

    9: ('kernel 加速与端到端收益的关系。'
        '(a) 真实负载中可优化时间的实测占比，数据来自 arXiv:2609.21058 的剖析；'
        '(b) 按 Amdahl 定律推算的端到端加速比，三条曲线对应不同可优化占比。'
        '在占比 8.9% 的场景下，即使 kernel 本身快 4 倍，端到端也只有 1.07 倍。'),
}


# 图片路径 -> 图号。用路径定位而非「图 N」前缀，
# 因为 alt 一旦被写成图注句子，「图 N」就不存在了，按前缀找会全部失配
# （本脚本第一版就是这样：重跑时 9 张全部报「未找到」）。
FIG_FILE = {
    1: 'fig1_timeline.png',
    2: 'fig2_claim_types.png',
    3: 'fig3_baseline_ladder.png',
    4: 'fig4_method_evolution.png',
    5: 'fig5_difficulty.png',
    6: 'fig6_leakage.png',
    7: 'fig7_tradeoff.png',
    8: 'fig8_comparability.png',
    9: 'fig9_endtoend.png',
}


def main() -> int:
    text = P.read_text(encoding='utf-8')
    n = 0
    for no, cap in CAPTIONS.items():
        fname = FIG_FILE[no]
        # ![...](figures/xxx.png)
        pat = re.compile(r'!\[[^\]]*\]\(((?:\.\./)?figures/' + re.escape(fname) + r')\)')
        if not pat.search(text):
            print(f'  [!] 图 {no}（{fname}）未在正文中找到')
            continue
        safe = cap.replace(']', '］').replace('\n', ' ')
        text = pat.sub('![' + safe + r'](\1)', text, count=1)
        n += 1

    P.write_text(text, encoding='utf-8', newline='\n')
    print(f'已重写 {n} 条图注')

    # 复核
    print('\n当前 alt 文本（即 PDF 图注）：')
    for m in re.finditer(r'!\[([^\]]{4,60})', text):
        print('  -', m.group(1)[:56] + ('…' if len(m.group(1)) > 56 else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
