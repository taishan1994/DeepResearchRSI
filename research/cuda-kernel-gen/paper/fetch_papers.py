"""批量抓取 arXiv 元数据，建立可核查的论文库。

为什么不用网页搜索的摘要拼凑：
  ⚠️ 二手转述会丢精度。这个领域里「加速比」是小数值（0.88x / 1.43x），
     一个数字记错，整篇结论就反了。故一律取 arXiv 官方 API 的原始 abstract。

输出 papers.json：
  {id, title, authors, published, updated, abs, arxiv_url, code_url}

arXiv API 用法：http://export.arxiv.org/api/query?id_list=2402.19173,2502.10517
一次最多建议 20 个 id，否则会被限流。
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'paper' if False else Path(__file__).resolve().parent

# 本综述要覆盖的论文。按「时间线 + 方法论」两个维度挑选，
# 不含仅作工具的项目（那些放在表格里，不进论文库）。
PAPER_IDS = [
    # ---------- 基线 / 基准 ----------
    '2502.10517',   # KernelBench
    '2502.14752',   # TritonBench
    '2507.17773',   # MultiKernelBench
    '2607.16241',   # KernelBench-Verified（批判评测）
    '2605.04956',   # KernelBenchX
    '2603.19173',   # SOL-ExecBench
    '2603.08721',   # KernelCraft
    '2601.00227',   # FlashInfer-Bench
    '2602.19594',   # ISO-Bench
    # ---------- SFT ----------
    '2510.07356',   # ConCuR
    '2606.16231',   # Tokens to Regions
    '2603.16790',   # InCoder-32B
    # ---------- RL ----------
    '2507.05687',   # AutoTriton
    '2507.14111',   # CUDA-L1
    '2507.11948',   # Kevin
    '2510.17891',   # TritonRL
    '2511.20100',   # QiMeng-Kernel
    '2512.02551',   # CUDA-L2
    '2602.05885',   # Dr. Kernel
    '2602.24286',   # CUDA Agent
    '2601.07160',   # AscendKernelGen
    # ---------- Agent 框架 ----------
    '2506.20807',   # GPU Kernel Scientist
    '2509.14279',   # Robust agentic benchmarking
    '2510.03760',   # EvoEngineer
    '2510.26144',   # FM Agent
    '2511.01884',   # CudaForge
    '2511.06345',   # PRAGMA
    '2511.18868',   # KernelBand
    '2512.19018',   # PEAK
    '2512.22147',   # minimal executable programs
    '2602.14293',   # KernelBlaster
    '2602.19128',   # K-Search
    '2603.21331',   # AutoKernel
    '2603.28342',   # Kernel-Smith
    '2604.01489',   # CuTeGen
    '2605.26720',   # Feedback-to-Plan
    '2606.26453',   # Micro-profiling
    '2606.26758',   # EGG
    # ---------- 硬件 / 剖面 ----------
    '2506.09092',   # CUDA-LLM
    '2508.20258',   # SwizzlePerf
    '2510.17158',   # Performance tools in reasoning
    '2512.09196',   # TritonForge
    '2605.04467',   # KEET
    # ---------- 多智能体 ----------
    '2509.07506',   # Astra
    '2510.16996',   # STARK
    '2511.13274',   # KForge
    '2512.23236',   # KernelEvolve (Meta)
    # ---------- 综述（对标对象） ----------
    '2601.15727',   # Towards Automated Kernel Generation in the Era of LLMs
    # ---------- 相邻：DSL / 编译器路径 ----------
    '2510.19873',   # From Large to Small (reasoning graph)
    '2603.10846',   # Cold-start drafting / value-driven memory
    '2604.18616',   # ARGUS
    '2606.16497',   # daVinci-kernel
    '2603.07169',   # Multi-scenario CUDA
    '2604.16625',   # AdaExplore
    '2604.26666',   # FACT
    '2605.05023',   # CuBridge
    '2606.04847',   # MusaCoder
    '2601.12698',   # Two-stage tuner
]

NS = {
    'a': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom',
}


def fetch_batch(ids: list[str]) -> list[dict]:
    url = ('http://export.arxiv.org/api/query?id_list=' + ','.join(ids)
           + '&max_results=' + str(len(ids)))
    req = urllib.request.Request(url, headers={'User-Agent': 'cuda-kernel-survey/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode('utf-8', 'replace')

    root = ET.fromstring(raw)
    out = []
    for e in root.findall('a:entry', NS):
        aid = e.find('a:id', NS).text.rsplit('/', 1)[-1]
        title = ' '.join((e.find('a:title', NS).text or '').split())
        summ = ' '.join((e.find('a:summary', NS).text or '').split())
        pub = (e.find('a:published', NS).text or '')[:10]
        upd = (e.find('a:updated', NS).text or '')[:10]
        authors = [x.find('a:name', NS).text for x in e.findall('a:author', NS)]
        out.append({
            'id': aid,
            'title': title,
            'authors': authors,
            'published': pub,
            'updated': upd,
            'abstract': summ,
            'arxiv_url': f'https://arxiv.org/abs/{aid}',
        })
    return out


def main() -> int:
    papers: list[dict] = []
    B = 15
    for i in range(0, len(PAPER_IDS), B):
        batch = PAPER_IDS[i:i + B]
        print(f'  抓取 {i + 1}-{i + len(batch)} / {len(PAPER_IDS)} ...', flush=True)
        try:
            papers.extend(fetch_batch(batch))
        except Exception as e:
            print(f'    批次失败: {e}')
        time.sleep(3)          # arXiv 要求请求间隔，太快会被 429

    # 去重（同一篇可能因 id 重复出现）
    seen, uniq = set(), []
    for p in papers:
        if p['id'] not in seen:
            seen.add(p['id'])
            uniq.append(p)

    uniq.sort(key=lambda p: p['published'])
    out = OUT / 'papers.json'
    out.write_text(json.dumps(uniq, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'\n入库 {len(uniq)} 篇 / 请求 {len(PAPER_IDS)} 篇')
    missing = set(PAPER_IDS) - seen
    if missing:
        print(f'未取到 {len(missing)} 篇: {sorted(missing)[:10]}')

    by_month: dict[str, int] = {}
    for p in uniq:
        by_month[p['published'][:7]] = by_month.get(p['published'][:7], 0) + 1
    print('\n按月份分布:')
    for m in sorted(by_month):
        print(f'  {m}  {"#" * by_month[m]:22s} {by_month[m]}')
    print(f'\n写入 {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
