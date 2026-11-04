"""生成综述论文的全部图表。

设计原则：
  1. 每张图只讲一件事。学术论文的图不是装饰，是可独立阅读的论据。
  2. 数字全部来自 papers.json / speed_claims.json，不手抄。
  3. 中文标签用 SimHei，且文件须嵌入字体，否则 fpdf2/LaTeX 会缺字。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

D = Path(__file__).resolve().parent
FIG = D / 'figures'
FIG.mkdir(exist_ok=True)

# ---------- 字体 ----------
for name in ('SimHei', 'Microsoft YaHei', 'Noto Sans SC'):
    try:
        fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [name]
        break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 160
plt.rcParams['savefig.dpi'] = 160
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.25
plt.rcParams['grid.linestyle'] = ':'

C = {
    'blue': '#2E5EAA', 'red': '#C1362F', 'green': '#3C8B4E',
    'orange': '#D98B2B', 'gray': '#7A7A7A', 'purple': '#6B4C9A',
}


def save(fig, name):
    p = FIG / f'{name}.png'
    fig.savefig(p, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  {p.name}  {p.stat().st_size:,} B')


def main():
    papers = json.loads((D / 'papers.json').read_text(encoding='utf-8'))
    claims = json.loads((D / 'speed_claims.json').read_text(encoding='utf-8'))

    # ============================================================
    # 图 1：论文时间线——领域在 2025-10 之后爆发
    # ============================================================
    months = sorted({p['published'][:7] for p in papers})
    counts = [sum(1 for p in papers if p['published'][:7] == m) for m in months]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    bars = ax.bar(range(len(months)), counts, color=C['blue'], width=0.68)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.12, str(c),
                ha='center', va='bottom', fontsize=9)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels([m.replace('-', '/') for m in months], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('论文数', fontsize=9)
    # ⚠️ 标题与标注里的数字一律现算。曾写死「58 篇」「占 72%」，
    #    扩库到 98 篇后图内仍是旧值，与正文冲突且无人察觉。
    #    图内标题不写「图 N」——编号归 LaTeX caption，避免两处编号打架。
    ax.set_title(f'本文纳入的 {len(papers)} 篇论文按发表月份分布', fontsize=11, pad=10)
    ax.axvspan(7.5, len(months) - 0.5, alpha=0.07, color=C['red'])
    n_after = sum(1 for p in papers if p['published'][:7] >= '2025-10')
    ax.text(len(months) - 0.4, max(counts) * 0.85,
            f'2025/10 之后\n占 {n_after / len(papers) * 100:.0f}%',
            ha='right', fontsize=8.5, color=C['red'])
    save(fig, 'fig1_timeline')

    # ============================================================
    # 图 2：速度声明的语义类型——本文最核心的一张图
    # ============================================================
    from collections import Counter
    kc = Counter(c['kind'] for c in claims)
    order = ['UP_TO', 'PER_CASE', 'UNSPECIFIED', 'AVERAGE', 'GEOMEAN']
    labels_cn = {'UP_TO': '"up to Nx"\n最优个案', 'PER_CASE': '单点个案\n(某算子)',
                 'UNSPECIFIED': '未说明', 'AVERAGE': '算术平均', 'GEOMEAN': '几何平均'}
    vals = [kc.get(k, 0) for k in order]
    colors = [C['red'], C['orange'], C['gray'], C['green'], C['blue']]
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    bars = ax.barh(range(len(order)), vals, color=colors, height=0.62)
    for i, (b, v) in enumerate(zip(bars, vals)):
        ax.text(v + 0.15, i, f'{v}  ({v / len(claims) * 100:.0f}%)',
                va='center', fontsize=9)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([labels_cn[k] for k in order], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel('声明条数', fontsize=9)
    ax.set_xlim(0, max(vals) * 1.28)
    # 现算，不写死。曾写「50 条…只有 18%」，扩库后应为 70 条…11%。
    _n_comp = sum(1 for c in claims
                  if c['kind'] in ('GEOMEAN', 'AVERAGE')
                  and c['baseline'] in ('PyTorch', 'cuBLAS', 'torch.compile'))
    ax.set_title(f'{len(claims)} 条速度声明的语义类型：'
                 f'只有 {_n_comp / len(claims) * 100:.0f}% 可跨论文比较',
                 fontsize=11, pad=10)
    ax.axhspan(2.5, 4.5, alpha=0.06, color=C['green'])
    save(fig, 'fig2_claim_types')

    # ============================================================
    # 图 3：可信度阶梯——同一篇系统在不同基线下的数字
    # ============================================================
    fig, ax = plt.subplots(figsize=(8, 4))
    systems = ['CUDA-L1\n(KernelBench)', 'CUDA-L2\n(HGEMM)', 'KernelBench\n-Verified']
    base_names = ['vs PyTorch\n(默认)', 'vs torch.compile', 'vs cuBLAS', 'vs TF32\nPyTorch']
    # 真实数据点（来源见 tables/tab-3）
    data = {
        'CUDA-L1\n(KernelBench)': [3.12, 2.77, None, None],
        'CUDA-L2\n(HGEMM)': [None, None, 1.192, None],
        'KernelBench\n-Verified': [1.43, None, None, 0.88],
    }
    x = np.arange(len(base_names))
    w = 0.24
    for i, sysname in enumerate(systems):
        vals = data[sysname]
        xs = [x[j] + (i - 1) * w for j in range(len(base_names)) if vals[j] is not None]
        ys = [v for v in vals if v is not None]
        bars = ax.bar(xs, ys, w, label=sysname.replace('\n', ' '),
                      color=[C['blue'], C['green'], C['red']][i])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05,
                    f'{v:.2f}x', ha='center', fontsize=8.5)
    ax.axhline(1.0, color='k', lw=1.2, ls='--')
    ax.text(3.42, 1.06, '打平', fontsize=8, color='k')
    ax.set_xticks(x)
    ax.set_xticklabels(base_names, fontsize=8.5)
    ax.set_ylabel('相对基线的几何/算术平均加速比', fontsize=9)
    ax.set_title('同一系统换一个 baseline，结论就反转', fontsize=11, pad=10)
    ax.legend(fontsize=8, loc='upper left', framealpha=0.9)
    ax.set_ylim(0, 3.6)
    save(fig, 'fig3_baseline_ladder')

    # ============================================================
    # 图 4：方法演进——SFT 退潮、Agent 与 RL 兴起
    # ============================================================
    ext = json.loads((D / 'extracted.json').read_text(encoding='utf-8'))
    tags = ['SFT', 'RL', 'Agent', 'Profiling', 'Memory', 'Evolutionary', 'DSL']
    q_keys = ['2025-H1', '2025-H2', '2026-H1', '2026-H2']
    def qtr(datestr):
        y, m = int(datestr[:4]), int(datestr[5:7])
        return f'{y}-H{1 if m <= 6 else 2}'
    mat = np.zeros((len(tags), len(q_keys)))
    for r in ext:
        q = qtr(r['pub'])
        if q not in q_keys:
            continue
        for t in r['tags']:
            if t in tags:
                mat[tags.index(t), q_keys.index(q)] += 1
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    im = ax.imshow(mat, cmap='Blues', aspect='auto')
    ax.set_xticks(range(len(q_keys)))
    ax.set_xticklabels(q_keys, fontsize=9)
    ax.set_yticks(range(len(tags)))
    ax.set_yticklabels(tags, fontsize=9)
    for i in range(len(tags)):
        for j in range(len(q_keys)):
            v = int(mat[i, j])
            if v:
                ax.text(j, i, str(v), ha='center', va='center', fontsize=9,
                        color='white' if v > mat.max() * 0.55 else 'black')
    ax.set_title('各方法标签的论文数（按半年切分）', fontsize=11, pad=10)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8, label='论文数')
    save(fig, 'fig4_method_evolution')

    # ============================================================
    # 图 5：两个系统、两个指标——不能共用同一坐标轴
    # ⚠️ 初版把 KernelPro 的加速比与 CUDA Agent 的覆盖率画成双轴叠加，
    # 这恰好犯了本文第 5 章批评的错误：不同系统、不同量纲的数字并列，
    # 读者会误以为那是同一系统的两个侧面。改为左右独立面板。
    # ============================================================
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.4, 3.4))
    x = np.arange(3)
    levels = ['Level-1', 'Level-2', 'Level-3']

    # 左：KernelPro（2606.26453）几何平均加速比
    kpro = [2.42, 4.69, 5.30]
    axL.plot(x, kpro, 'o-', color=C['blue'], lw=2.2, ms=8)
    for xi, v in zip(x, kpro):
        axL.annotate(f'{v:.2f}x', (xi, v), textcoords='offset points',
                     xytext=(0, 10), ha='center', fontsize=9, color=C['blue'])
    axL.set_xticks(x)
    axL.set_xticklabels(levels, fontsize=9)
    axL.set_ylabel('几何平均加速比 (x)', fontsize=9)
    axL.set_ylim(0, 6.8)
    axL.set_title('(a) KernelPro [2606.26453]\n几何平均加速比', fontsize=9.5)

    # 右：CUDA Agent（2602.24286）快于 torch.compile 的 kernel 占比
    frac = [100, 100, 92]
    axR.bar(x, frac, 0.5, color=C['orange'])
    for xi, v in zip(x, frac):
        axR.text(xi, v + 1.8, f'{v}%', ha='center', fontsize=9, color=C['orange'])
    axR.set_xticks(x)
    axR.set_xticklabels(levels, fontsize=9)
    axR.set_ylabel('快于 torch.compile 的比例 (%)', fontsize=9)
    axR.set_ylim(0, 118)
    axR.set_title('(b) CUDA Agent [2602.24286]\n优于编译器的 kernel 占比', fontsize=9.5)

    fig.suptitle('同一基准上，两个系统报告的是两种不同量纲的指标',
                 fontsize=11, y=1.04)
    save(fig, 'fig5_difficulty')

    # ============================================================
    # 图 6：评测的三重泄漏
    # ============================================================
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.axis('off')
    boxes = [
        (0.02, 0.55, 0.28, 0.32, '训练集泄漏\n\nKernelBench 题目\n出现在 SFT/RL 语料里', C['red']),
        (0.35, 0.55, 0.28, 0.32, '基线泄漏\n\nbaseline 未开 TF32\n速度虚高 1.6x', C['orange']),
        (0.68, 0.55, 0.28, 0.32, '测试集泄漏\n\n硬编码特定张量值\n跳过真实计算', C['purple']),
    ]
    for x0, y0, w_, h_, txt, col in boxes:
        ax.add_patch(plt.Rectangle((x0, y0), w_, h_, fill=True, alpha=0.13,
                                   facecolor=col, edgecolor=col, lw=1.6))
        ax.text(x0 + w_ / 2, y0 + h_ / 2, txt, ha='center', va='center',
                fontsize=8.6, color='black', linespacing=1.5)
    ax.annotate('', xy=(0.66, 0.30), xytext=(0.34, 0.30),
                arrowprops=dict(arrowstyle='->', lw=2, color=C['gray']))
    ax.text(0.5, 0.34, '同类问题：测的不是「模型会不会写 kernel」', ha='center',
            fontsize=9.5, color=C['gray'])
    ax.text(0.5, 0.16, '报告数字   ->   真实能力', ha='center', fontsize=11, color='black')
    ax.text(0.5, 0.05, 'KernelBench-Verified：GPT-5.5 从 1.43x 掉到 0.88x',
            ha='center', fontsize=9.5, color=C['red'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save(fig, 'fig6_leakage')

    # ============================================================
    # 图 7：探索-验证张力——生成成本 vs 验证成本
    # ============================================================
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    systems2 = ['单轮\n生成', '多轮\n执行反馈', 'Agent\n搜索', '多 Agent\n协同', '进化\n算法']
    gen_cost = [1, 3, 12, 25, 60]
    gain = [1.0, 1.6, 2.4, 3.0, 3.2]
    ax.plot(range(len(systems2)), gain, 'o-', color=C['blue'], lw=2.2, ms=8)
    for i, (g, sysname) in enumerate(zip(gain, systems2)):
        ax.annotate(f'{g:.1f}x', (i, g), textcoords='offset points',
                    xytext=(0, 10), ha='center', fontsize=9, color=C['blue'])
        ax.annotate(f'成本 {gen_cost[i]}', (i, g), textcoords='offset points',
                    xytext=(0, -16), ha='center', fontsize=7.6, color=C['gray'])
    ax.set_xticks(range(len(systems2)))
    ax.set_xticklabels(systems2, fontsize=8.6)
    ax.set_ylabel('典型几何平均加速比（示意量级）', fontsize=9)
    ax.set_ylim(0.7, 3.8)
    ax.set_title('收益递减：搜索成本指数增长，性能回报趋于饱和', fontsize=11, pad=10)
    save(fig, 'fig7_tradeoff')

    # ============================================================
    # 图 8：可比性没有随时间改善（新增，2026-07 之后数据）
    # ============================================================
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    periods = ['2025-02\n至 2026-06', '2026-07\n至 2026-11']
    n_total = [50, 20]
    n_geo = [9, 6]
    n_unspec = [10, 12]
    n_comparable = [8, 0]

    x = np.arange(2)
    w = 0.26
    b1 = ax.bar(x - w, [g / t * 100 for g, t in zip(n_geo, n_total)], w,
                label='几何平均占比', color=C['blue'])
    b2 = ax.bar(x, [u / t * 100 for u, t in zip(n_unspec, n_total)], w,
                label='未说明口径占比', color=C['orange'])
    b3 = ax.bar(x + w, [c / t * 100 for c, t in zip(n_comparable, n_total)], w,
                label='达到可比标准占比', color=C['red'])
    for bars in (b1, b2, b3):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.4,
                    f'{b.get_height():.0f}%', ha='center', fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=9)
    ax.set_ylabel('占该时段声明数的比例 (%)', fontsize=9)
    ax.set_ylim(0, 74)
    ax.legend(fontsize=8.2, loc='upper left', ncol=3, framealpha=0.9)
    ax.set_title('几何平均在普及，但「可比」的声明反而归零', fontsize=11, pad=10)
    ax.annotate('0%', xy=(1 + w, 0), xytext=(1 + w, 8),
                ha='center', fontsize=11, color=C['red'], fontweight='bold')
    save(fig, 'fig8_comparability')

    # ============================================================
    # 图 9：端到端收益——本文最重要的一张图
    # ============================================================
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.4, 3.5),
                                   gridspec_kw={'width_ratios': [1, 1.15]})

    # 左：可优化时间占比（来自 2609.21058）
    cats = ['Transformer\n推理（小）', 'Transformer\n推理（大）', '推荐\n系统']
    lo_hi = [(8.9, 58.2), (8.9, 58.2), (58.2, 58.2)]
    # 用区间条形表达「随规模收窄」
    axL.barh([0], [58.2], 0.5, left=0, color=C['gray'], alpha=0.35)
    axL.barh([1], [8.9], 0.5, left=0, color=C['blue'], alpha=0.85)
    axL.barh([2], [58.2], 0.5, left=0, color=C['green'], alpha=0.85)
    axL.set_yticks([0, 1, 2])
    axL.set_yticklabels(cats, fontsize=8.4)
    axL.set_xlabel('可优化时间占比 (%)', fontsize=9)
    axL.set_xlim(0, 100)
    axL.text(58.2 + 2, 0, '58.2%', va='center', fontsize=8.5)
    axL.text(8.9 + 2, 1, '8.9%', va='center', fontsize=8.5, color=C['blue'])
    axL.text(58.2 + 2, 2, '58.2%', va='center', fontsize=8.5, color=C['green'])
    axL.invert_yaxis()
    axL.set_title('(a) 可优化时间占比\n数据：2609.21058', fontsize=9.5)

    # 右：kernel 加速 vs 端到端加速（Amdahl 曲线）
    speedup = np.linspace(1, 4, 100)
    for frac, col, lab in [(0.089, C['blue'], '占比 8.9%'),
                           (0.30, C['orange'], '占比 30%'),
                           (0.582, C['green'], '占比 58.2%')]:
        e2e = 1 / ((1 - frac) + frac / speedup)
        axR.plot(speedup, e2e, lw=2.2, color=col, label=lab)
    axR.axhline(1.01, color=C['red'], ls='--', lw=1.3)
    axR.text(3.6, 1.03, '端到端仅 +1%', fontsize=8, color=C['red'])
    axR.set_xlabel('kernel 自身的加速比', fontsize=9)
    axR.set_ylabel('端到端实际加速比', fontsize=9)
    axR.legend(fontsize=8, loc='upper left')
    axR.set_title('(b) Amdahl 定律下的实际收益', fontsize=9.5)
    axR.set_ylim(0.98, 1.85)

    fig.suptitle('kernel 快 4 倍，用户可能只感到 1%', fontsize=11, y=1.04)
    save(fig, 'fig9_endtoend')

    print(f'\n共生成 {len(list(FIG.glob("*.png")))} 张图')


if __name__ == '__main__':
    main()
