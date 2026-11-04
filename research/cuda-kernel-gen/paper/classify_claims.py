"""把抽取到的速度数字按「语义类型」分类。

这是本综述最核心的一张分析表，因为：

    「up to 16x」  ≠  「geomean 1.43x」

前者是最优个案，后者是总体平均。把两者并列进同一张表，
读者会以为后者才是保守的、前者是典型的——恰好相反。

分类：
  UP_TO       up to Nx / 最高 Nx     —— 最优个案，不可当总体水平
  GEOMEAN     几何平均              —— 最能代表总体
  AVERAGE     average / on average  —— 算术平均，被极值拉高
  PER_CASE    某个具体算子上的 Nx    —— 单点，不可外推
  VS_MODEL    相对某个 LLM 而非库    —— 与「超过 PyTorch」不是一回事
  UNSPECIFIED 未说明                —— 无法归类
"""

from __future__ import annotations

import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent

# 提取「数字 + 倍数 + 上下文窗口」，然后判定类型
NUMX = re.compile(r'(\d+\.?\d*)\s*[x×]')


def classify(window: str) -> str:
    w = window.lower()
    if re.search(r'up\s*to|as\s*much\s*as|max(?:imum)?\s*of|achiev\w*\s*up\s*to', w):
        return 'UP_TO'
    if re.search(r'geometric|geomean|geo-?mean', w):
        return 'GEOMEAN'
    if re.search(r'on\s+average|average\s+(?:of|speedup)|mean\s+speedup', w):
        return 'AVERAGE'
    if re.search(r'over\s+(?:llms?|baseline\s+models?|gpt|claude|qwen|deepseek|sota\s+(?:general|llm))', w):
        return 'VS_MODEL'
    if re.search(r'over\s+(?:\w+\s+){0,3}(?:eager|pytorch|cublas|triton|torch\.compile)', w):
        return 'PER_CASE'
    return 'UNSPECIFIED'


def main() -> int:
    papers = json.loads((D / 'papers.json').read_text(encoding='utf-8'))
    records = []

    for p in papers:
        ab = p['abstract']
        for m in NUMX.finditer(ab):
            val = float(m.group(1))
            # 上下文窗口：前 130 字符，后 110 字符
            w = ab[max(0, m.start() - 130): m.end() + 110]
            kind = classify(w)
            # 判定 baseline
            wl = w.lower()
            if 'cublas' in wl:
                base = 'cuBLAS'
            elif 'torch.compile' in wl or 'torch compile' in wl:
                base = 'torch.compile'
            elif 'pytorch' in wl or 'eager' in wl:
                base = 'PyTorch'
            elif 'triton' in wl:
                base = 'Triton'
            elif re.search(r'llms?|gpt|claude|qwen|deepseek|sota', wl):
                base = 'other LLM'
            else:
                base = '未指明'
            records.append({
                'id': p['id'][:10],
                'title': p['title'],
                'pub': p['published'],
                'value': val,
                'kind': kind,
                'baseline': base,
                'snippet': ' '.join(w.split())[:190],
            })

    # 去重（同一篇同一数值同一类型只留一条）
    seen, uniq = set(), []
    for r in records:
        k = (r['id'], r['value'], r['kind'], r['baseline'])
        if k not in seen:
            seen.add(k)
            uniq.append(r)

    uniq.sort(key=lambda r: (r['pub'], -r['value']))

    print('=' * 116)
    print('全部速度声明（按发表时间）')
    print('=' * 116)
    for r in uniq:
        print(f"{r['pub']} {r['id']:11s} {r['value']:>8.2f}x {r['kind']:12s} vs {r['baseline']:12s}")
        print(f"           {r['snippet'][:150]}")

    from collections import Counter
    print('\n' + '=' * 116)
    print('按语义类型统计')
    print('=' * 116)
    c = Counter(r['kind'] for r in uniq)
    for k, v in c.most_common():
        print(f'  {k:14s} {v:3d}  {"#" * v}')

    print('\n按 baseline 统计')
    c2 = Counter(r['baseline'] for r in uniq)
    for k, v in c2.most_common():
        print(f'  {k:14s} {v:3d}  {"#" * v}')

    # 只保留「可比较」的子集：GEOMEAN/AVERAGE + 明确 baseline
    comparable = [r for r in uniq if r['kind'] in ('GEOMEAN', 'AVERAGE')
                  and r['baseline'] in ('PyTorch', 'cuBLAS', 'torch.compile')]
    print(f'\n✅ 真正可跨论文比较的（几何/算术平均 + 明确库 baseline）: {len(comparable)}/{len(uniq)}')
    for r in comparable:
        print(f"   {r['pub']} {r['id']} {r['value']:.2f}x {r['kind']} vs {r['baseline']}")

    (D / 'speed_claims.json').write_text(
        json.dumps(uniq, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n写入 {D / "speed_claims.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
