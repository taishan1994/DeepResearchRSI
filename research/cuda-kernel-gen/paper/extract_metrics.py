"""从 58 篇摘要中抽取「可比较的量化结果」。

⚠️ 这一步是本综述的立论基础，也是最容易出错的地方。
   典型陷阱：
   1. 同一个倍数在不同 baseline 下不可比。KernelBench 的「1.43x」是
      对未开 TF32 的 PyTorch，「0.88x」是对开了 TF32 的 PyTorch。
      两者差 1.6 倍，直接并列会得出相反结论。
   2. 「pass@k」「速度提升」「正确率」是三种不同量纲，不能混。
   3. 有些论文报的是「相对某个模型」而非「相对 PyTorch/cuBLAS」。

故本脚本只做**抽取与归类**，不做跨论文合并，并把每个数字的
「相对谁」一并记录下来。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent

# 速度类：x 倍 / 百分比加速
SPEED_PAT = [
    re.compile(r'(\d+\.?\d*)\s*[x×]\s*(?:geo|speedup|faster|on average|geomean)', re.I),
    re.compile(r'(\d+\.?\d*)\s*[x×]\s*(?:speedup|faster)', re.I),
    re.compile(r'speedup\s+of\s+(\d+\.?\d*)\s*[x×]', re.I),
    re.compile(r'(\d+\.?\d*)\s*[x×]\s*(?:over|compared)', re.I),
    re.compile(r'(\d+\.?\d*)%\s*(?:speedup|faster|improvement in speed)', re.I),
    re.compile(r'up to\s+(\d+\.?\d*)\s*[x×]', re.I),
]
# 正确率类
PASS_PAT = [
    re.compile(r'(?:pass@1|pass rate|correctness|accuracy)[^\d%]{0,30}(\d+\.?\d*)\s*%', re.I),
    re.compile(r'(\d+\.?\d*)\s*%\s*(?:pass@1|pass rate|correctness)', re.I),
    re.compile(r'pass@1[^\d]{0,12}(\d+\.?\d*)', re.I),
]
# baseline 关键词（用于标注「相对谁」）
BASE_KW = [
    ('PyTorch', r'pytorch|torch\.'),
    ('cuBLAS', r'cublas'),
    ('Triton', r'triton'),
    ('CUDA', r'\bcuda\b'),
    ('torch.compile', r'torch\.compile'),
    ('TileLang', r'tilelang'),
    ('vendor lib', r'vendor|cutlass|cudnn'),
]

# 方法标签（按综述分类）
TAGS = {
    'SFT': r'supervised fine-?tun|instruction tun|SFT',
    'RL': r'reinforcement learning|\bRL\b|GRPO|PPO|policy gradient|reward',
    'Agent': r'agent|agentic|multi-agent|harness|orchestrat',
    'Profiling': r'profil|nsight|ncu|hardware.?aware|roofline|counter',
    'Memory': r'memory|experience|skill library|retriev|knowledge base',
    'Evolutionary': r'evolution|genetic|beam search|tree search|MCTS',
    'DSL': r'tilelang|triton|cutlass|cute|dsl|cuTe',
    'Benchmark': r'benchmark|evaluat|metric',
}


def first(pat_list, text):
    for p in pat_list:
        m = p.search(text)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None


def baselines(text: str) -> list[str]:
    t = text.lower()
    return [name for name, kw in BASE_KW if re.search(kw, t)]


def main() -> int:
    papers = json.loads((D / 'papers.json').read_text(encoding='utf-8'))
    rows = []
    for p in papers:
        ab = p['abstract']
        speed = first(SPEED_PAT, ab)
        acc = first(PASS_PAT, ab)
        tags = [t for t, kw in TAGS.items() if re.search(kw, ab, re.I)]
        rows.append({
            'id': p['id'][:10],
            'title': p['title'],
            'pub': p['published'],
            'speed': speed,
            'acc': acc,
            'baselines': baselines(ab),
            'tags': tags,
        })

    # ---- 报告 ----
    print('=' * 108)
    print(f'{"id":12s} {"日期":10s} {"速度":>8s} {"准确":>7s}  {"相对":22s} 方法')
    print('=' * 108)
    for r in sorted(rows, key=lambda x: x['pub']):
        sp = f"{r['speed']:.2f}x" if r['speed'] else '-'
        ac = f"{r['acc']:.1f}%" if r['acc'] and r['acc'] <= 100 else '-'
        bl = ','.join(r['baselines'])[:22]
        print(f"{r['id']:12s} {r['pub']:10s} {sp:>8s} {ac:>7s}  {bl:22s} {','.join(r['tags'])[:34]}")

    # ---- 统计 ----
    print('\n' + '=' * 108)
    have_speed = [r for r in rows if r['speed']]
    print(f'能抽出速度数字的: {len(have_speed)}/{len(rows)}')
    vs_pt = [r for r in have_speed if 'PyTorch' in r['baselines']]
    vs_cublas = [r for r in have_speed if 'cuBLAS' in r['baselines']]
    print(f'  其中明确对 PyTorch: {len(vs_pt)}   对 cuBLAS: {len(vs_cublas)}')
    print('\n⚠️ 这就是本领域最严重的问题：')
    print('   同一个「1.5x」在对 PyTorch / 对 cuBLAS / 对未开 TF32 的 PyTorch 之间')
    print('   含义完全不同，而多数摘要不写明 baseline。')

    from collections import Counter
    c = Counter()
    for r in rows:
        for t in r['tags']:
            c[t] += 1
    print('\n方法标签分布:')
    for k, v in c.most_common():
        print(f'  {k:14s} {v:2d}  {"#" * v}')

    # 全部论文按 baseline 可辨识度分档
    print('\nbaseline 可辨识度:')
    clear = sum(1 for r in rows if r['baselines'])
    print(f'  摘要中能认出至少一个 baseline: {clear}/{len(rows)}')
    print(f'  完全认不出: {len(rows) - clear}/{len(rows)}')

    (D / 'extracted.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n写入 {D / "extracted.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
