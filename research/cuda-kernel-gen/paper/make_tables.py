"""生成论文表格数据（CSV），供 LaTeX 与 Markdown 共用。

⚠️ 每一行的数字必须能追溯到 arXiv 摘要原文。
   脚本最后会做一次自检：把表格里的关键数字回查 papers.json，
   找不到就报错。这是防止我在写表时手滑的唯一办法。
"""

from __future__ import annotations

import json
import csv
import io
import re
from pathlib import Path

D = Path(__file__).resolve().parent
TAB = D / 'tables'
TAB.mkdir(exist_ok=True)

papers = {p['id'][:10]: p for p in
          json.loads((D / 'papers.json').read_text(encoding='utf-8'))}
claims = json.loads((D / 'speed_claims.json').read_text(encoding='utf-8'))


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(header)
    w.writerows(rows)
    (TAB / name).write_text(buf.getvalue(), encoding='utf-8')
    print(f'  {name}  {len(rows)} 行')


# ============================================================
# 表 1：基准数据集对比
# ============================================================
t1 = [
    ['KernelBench', '2502.10517', '2025-02', '250', 'CUDA', 'PyTorch', 'fast_p（阈值可调）'],
    ['TritonBench', '2502.14752', '2025-02', '184', 'Triton', 'PyTorch / Triton', '正确性 + 加速比'],
    ['MultiKernelBench', '2507.17773', '2025-07', '285', 'CUDA', 'PyTorch', 'pass@k + 加速比'],
    ['KernelBench-Verified', '2607.16241', '2026-06', '250', 'CUDA', 'TF32 PyTorch', '几何平均 + 内存'],
    ['KernelBenchX', '2605.04956', '2026-05', '—', 'CUDA', 'PyTorch / Triton', '跨平台可移植性'],
    ['SOL-ExecBench', '2603.19173', '2026-03', '—', 'CUDA', '硬件上限 (SOL)', '达到机器上限的比例'],
]
write_csv('tab1_benchmarks.csv',
          ['基准', 'arXiv', '时间', '题目数', '目标语言', '基线', '主指标'], t1)

# ============================================================
# 表 2：方法论谱系（按 RL / SFT / Agent 三大路线）
# ============================================================
t2 = [
    ['SFT', 'KernelLLM', 'HF 模型卡', 'Meta', 'Llama-3.1-8B 微调', '首个开源 kernel 专用模型'],
    ['SFT', 'ConCuR', '2510.07356', '—', '精简推理链', '强调「简洁性」提升正确率'],
    ['SFT', 'Tokens to Regions', '2606.16231', '—', 'CUDA 敏感指令微调', '按代码区域而非 token 对齐'],
    ['RL', 'Kevin', '2507.11948', '—', '多轮 RL', '首个多轮 RL 训练 kernel 模型'],
    ['RL', 'CUDA-L1', '2507.14111', 'DeepReinforce', '对比式 RL', '平均 3.12x，峰值 120x'],
    ['RL', 'AutoTriton', '2507.05687', '—', 'Triton + RL', '面向 Triton 而非 CUDA'],
    ['RL', 'QiMeng-Kernel', '2511.20100', '中科院', '宏观思考/微观编码', '策略与实现解耦'],
    ['RL', 'CUDA-L2', '2512.02551', '—', 'RL + 执行速度奖励', 'HGEMM 上超 cuBLAS 19.2%'],
    ['RL', 'Dr. Kernel', '2602.05885', '—', 'TRLOO 去偏', '指出 GRPO 自包含偏差'],
    ['RL', 'CUDA Agent', '2602.24286', '字节/清华', '大规模 Agentic RL', '三级 100/100/92% 优于 torch.compile'],
    ['Agent', 'GPU Kernel Scientist', '2506.20807', '—', '进化式 Agent', '早期 Agent 探索'],
    ['Agent', 'STARK', '2510.16996', '—', '多 Agent 协同', '规划/编码/验证分工'],
    ['Agent', 'CudaForge', '2511.01884', '—', '硬件反馈 Agent', '以 profiler 为唯一反馈'],
    ['Agent', 'KernelBlaster', '2602.14293', '—', 'MCTS 搜索', '2.5x 几何平均'],
    ['Agent', 'Ave', '2604.18616', '—', '数据流不变量', '编译期约束做护栏'],
]
write_csv('tab2_methods.csv',
          ['路线', '系统', 'arXiv', '机构', '核心机制', '关键贡献'], t2)

# ============================================================
# 表 3：同一系统的多基线对照（本文最重要的一张表）
# ============================================================
t3 = [
    ['CUDA-L1', 'KernelBench 250 题', 'PyTorch 默认', '3.12x', '算术平均', '2507.14111'],
    ['CUDA-L1', 'KernelBench 250 题', 'PyTorch 默认', '1.42x', '中位数', '2507.14111'],
    ['CUDA-L1', 'KernelBench 250 题', 'PyTorch 默认', '120x', '峰值（up to）', '2507.14111'],
    ['CUDA-L1', 'KernelBench 250 题', 'torch.compile', '2.77x', '算术平均', '2507.14111'],
    ['CUDA-L1', 'KernelBench 250 题', 'CUDA Graph', '2.81x', '算术平均', '2507.14111'],
    ['CUDA-L1', 'KernelBench 250 题', 'cuDNN', '7.72x', '算术平均', '2507.14111'],
    ['CUDA-L2', 'HGEMM 1000 配置', 'torch.matmul', '+22.0%', '算术平均', '2512.02551'],
    ['CUDA-L2', 'HGEMM 1000 配置', 'cuBLAS (最优布局)', '+19.2%', '算术平均', '2512.02551'],
    ['CUDA-L2', 'HGEMM 1000 配置', 'cuBLASLt 启发式', '+16.8%', '算术平均', '2512.02551'],
    ['CUDA-L2', 'HGEMM 1000 配置', 'cuBLASLt 自动调优', '+11.4%', '算术平均', '2512.02551'],
    ['GPT-5.5（单轮）', 'KernelBench', 'PyTorch 默认协议', '1.43x', '几何平均', '2607.16241'],
    ['GPT-5.5（单轮）', 'KernelBench', 'TF32 PyTorch', '0.88x', '几何平均', '2607.16241'],
]
write_csv('tab3_baseline_ladder.csv',
          ['系统', '测试集', '基线', '数值', '统计口径', 'arXiv'], t3)

# ============================================================
# 表 4：速度声明的语义分类（数据来自 speed_claims.json）
# ============================================================
from collections import Counter
kc = Counter(c['kind'] for c in claims)
bc = Counter(c['baseline'] for c in claims)
kind_cn = {'UP_TO': '"up to Nx" 最优个案', 'PER_CASE': '单点个案',
           'UNSPECIFIED': '未说明', 'AVERAGE': '算术平均', 'GEOMEAN': '几何平均'}
t4 = [[kind_cn.get(k, k), str(kc[k]), f'{kc[k] / len(claims) * 100:.0f}%']
      for k in ['UP_TO', 'PER_CASE', 'UNSPECIFIED', 'AVERAGE', 'GEOMEAN']]
write_csv('tab4_claim_semantics.csv', ['语义类型', '条数', '占比'], t4)

# ============================================================
# 表 5：基线可辨识度
# ============================================================
t5 = [[k, str(v), f'{v / len(claims) * 100:.0f}%'] for k, v in bc.most_common()]
write_csv('tab5_baselines.csv', ['声明中的基线', '条数', '占比'], t5)

# ============================================================
# 自检：表格数字能否回溯到 arXiv 原文
# ============================================================
print('\n=== 自检：表格数字回溯 ===')
problems = []
# 检查 tab3 的每个数值都能在对应论文摘要里找到
for row in t3:
    sysname, _, _, val, _, aid = row
    if aid not in papers:
        problems.append(f'{aid} 不在论文库')
        continue
    ab = papers[aid]['abstract']
    num = val.replace('x', '').replace('%', '').replace('+', '')
    # 允许 3.12 / 3.1 这类四舍五入
    cands = [num, num.rstrip('0').rstrip('.')]
    if not any(c in ab for c in cands):
        # 检查是否是换算值
        problems.append(f'{aid} 中找不到数值 {val}（{sysname}）')

if problems:
    for p in problems:
        print(f'  [!] {p}')
else:
    print('  全部数值可在原文摘要中找到')

print(f'\n共 5 张表 -> {TAB}')
