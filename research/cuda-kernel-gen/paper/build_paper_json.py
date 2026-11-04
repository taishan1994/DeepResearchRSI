"""生成 paper/paper.json —— 论文的结构化规格。

为什么需要它（框架层面）：
    docs/data-model.md 的 P1–P3 全部由 scripts/audit_paper.py 读取
    paper.json 来校验：
      P1 引用闭合  -> 读 sections/figures/tables 的 cites
      P3 无凭空图表 -> 读 figures/tables 声明的产物路径
    而 paper.json 文件根本不存在，audit_paper.py 直接 raise SystemExit。
    也就是说 P1–P3 在本归档上从来没跑过。

⚠️ 本脚本的 cites 必须由**人工判定**，不能自动从正文反推：
    同一个数字（0.88x）在摘要、正文、图注里反复出现，
    机器无法判断哪一处是它的论证位置。
   earlier 用锚点自动插入时，16 处里 4 处语义错位（把 c-verified-drop
   插到了讲 70 条声明统计的句子上）。这里改为手工编排。

figures 的 output 字段对应 figures/ 下的真实文件名；
tables 的 table_id 对应 tables/ 下的真实文件名（本文用 CSV，不是 .md）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / 'PAPER.md'
OUT = HERE / 'paper.json'


def sections() -> list[dict]:
    """按 PAPER.md 的实际章节生成 sections，cites 由正文实际引用反推。"""
    text = PAPER.read_text(encoding='utf-8')
    lines = text.split('\n')
    # 收集每个 H2 起始行
    heads: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith('## '):
            title = line[3:].strip()
            heads.append((i, title))

    out: list[dict] = []
    num = 0
    for idx, (start, title) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = '\n'.join(lines[start:end])
        cites = sorted(set(re.findall(r'\[(c-[a-z0-9-]+)\]', body)))
        # 摘要与附录不参与章节编号
        is_chapter = bool(re.match(r'^\d', title))
        if is_chapter:
            num = int(re.match(r'^(\d+)', title).group(1))
        else:
            num = 0
        out.append({
            'section_id': f'sec-{num}' if num else f'sec-{title[:12]}',
            'number': num,
            'title': re.sub(r'^\d+　?', '', title),
            'file': 'PAPER.md',
            'cites': cites,
        })
    return out


FIGURES = [
    ('fig1', 'timeline', '论文时间分布', 'fig1_timeline.png',
     ['c-kb-baseline']),
    ('fig2', 'bar', '方法标签分布', 'fig4_method_evolution.png',
     ['c-survey-gap']),
    ('fig3', 'comparison', '两个系统的量纲差异', 'fig5_difficulty.png',
     ['c-coverage-vs-speed']),
    ('fig4', 'bar', '速度声明语义分布', 'fig2_claim_types.png',
     ['c-comparability']),
    ('fig5', 'trend', '可比性随时间变化', 'fig8_comparability.png',
     ['c-comparability']),
    ('fig6', 'comparison', '多基线阶梯', 'fig3_baseline_ladder.png',
     ['c-l1-spread', 'c-verified-drop']),
    ('fig7', 'schematic', '三类泄漏', 'fig6_leakage.png',
     ['c-rl-hacking']),
    ('fig8', 'comparison', '端到端收益', 'fig9_endtoend.png',
     ['c-e2e-limit', 'c-e2e-amdahl', 'c-e2e-fraction']),
    ('fig9', 'schematic', '成本收益边界', 'fig7_tradeoff.png',
     ['c-coverage-vs-speed']),
]

TABLES = [
    ('tab1', '两组实验的四个维度对照', ['c-verified-drop', 'c-kb-baseline']),
    ('tab2', '写一个可用 kernel 的三层门槛', ['c-e2e-limit']),
    ('tab3', '三条技术路线的对比', ['c-survey-gap']),
    ('tab4', '速度声明的语义类型判定标准', ['c-comparability']),
    ('tab5', '70 条速度声明的语义分布', ['c-comparability']),
]


def main() -> int:
    # 图注从 PAPER.md 的 alt 文本里取，保证 paper.json 与正文一致
    text = PAPER.read_text(encoding='utf-8')
    cap_by_file: dict[str, str] = {}
    for m in re.finditer(r'!\[([^\]]+)\]\((?:\.\./)?figures/([^)]+)\)', text):
        cap_by_file[m.group(2)] = m.group(1)

    figures = []
    for fid, kind, title, fname, cites in FIGURES:
        if not (HERE / 'figures' / fname).is_file():
            print(f'  [!] 图文件不存在：{fname}')
            continue
        figures.append({
            'figure_id': fid,
            'kind': kind,
            'title': title,
            'caption': cap_by_file.get(fname, title),
            'cites': cites,
            'data_file': f'data/{fid}.csv',
            'output': fname,
        })

    tables = []
    for tid, title, cites in TABLES:
        # 本文用 CSV 而非 .md，路径留给 audit_paper 的兼容分支
        cand = list((HERE / 'tables').glob(f'{tid}_*.csv')) or \
               list((HERE / 'tables').glob(f'{tid}*.csv'))
        tables.append({
            'table_id': tid,
            'title': title,
            'caption': title,
            'cites': cites,
            'data_file': f'tables/{cand[0].name}' if cand else f'tables/{tid}.csv',
        })

    spec = {
        'paper_id': 'paper-cuda-kernel-gen',
        'slug': 'cuda-kernel-gen',
        'title': 'CUDA Kernel 自动生成：从代码生成到性能工程的方法论迁移',
        'subtitle': '一个数字能证明什么',
        'as_of': '2026-11-03',
        'language': 'zh',
        'abstract': _abstract(text),
        'keywords': ['CUDA kernel', '大语言模型', '强化学习', '智能体',
                     '基准评测', '奖励黑客', '端到端收益', 'Amdahl 定律'],
        'sections': sections(),
        'figures': figures,
        'tables': tables,
    }

    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n',
                   encoding='utf-8', newline='\n')
    print(f'写入 paper.json：{len(spec["sections"])} 节 / '
          f'{len(figures)} 图 / {len(tables)} 表')
    return 0


def _abstract(text: str) -> str:
    m = re.search(r'## 摘要\n\n(.+?)\n\n', text, re.S)
    return re.sub(r'\[c-[a-z0-9-]+\]', '', m.group(1)).strip() if m else ''


if __name__ == '__main__':
    raise SystemExit(main())
