"""为 CUDA kernel 综述生成 DeepResearchRSI 契约要求的证据三件套。

    sources.csv   —— 来源（含 fetched_at / published_at / trust_tier）
    evidence.csv  —— 证据（含可定位的 quote 片段）
    claims.csv    —— 主张（含 claim_type / confidence / as_of / evidence_ids）

⚠️ 设计要点（这几条决定了这些东西有没有用）：

1. **evidence 的 quote 必须是摘要原文的子串**，不是我的转述。
   否则「可审计」就退化成「作者说他说过」。脚本最后会逐条回查。

2. **claim_type 要分清 measurement / spec / prediction**。
   实测值（0.88x）是 measurement；Amdahl 推算（1.07x）是 prediction，
   schema 规定 prediction 必须带 derivation 字段。
   把推算写成实测，是这类综述最常见的错误。

3. **counter_evidence 必须真的挂上去**。
   「端到端只有 1%」这类证据是削弱本领域价值的，
   它应当显式挂在「kernel 加速显著」类主张的对立面，而不是藏在正文里。

4. **fetched_at 用真实抓取时刻**。
   本目录的 papers.json 里没有存抓取时间，
   故此处取本次会话的抓取窗口（2026-11-03 14:52 UTC+8 起）。
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 从脚本自身位置推导，而不是写死本机路径——这样任何人 clone 后都能直接跑。
SRC = Path(__file__).resolve().parent
OUT = SRC / 'paper'

papers = {p['id'][:10]: p for p in
          json.loads((OUT / 'papers.json').read_text(encoding='utf-8'))}
claims_raw = json.loads((OUT / 'speed_claims.json').read_text(encoding='utf-8'))

TZ = timezone(timedelta(hours=8))
FETCHED = '2026-11-03T14:52:00+08:00'

# ---------------------------------------------------------------- sources
# 只纳入正文实际引用的 arXiv 来源 + 2 个非 arXiv 来源
ARXIV_USED = [
    '2502.10517',   # KernelBench
    '2502.14752',   # TritonBench
    '2507.05687',   # AutoTriton
    '2507.11948',   # Kevin
    '2507.14111',   # CUDA-L1
    '2507.17773',   # MultiKernelBench
    '2508.20258',   # SwizzlePerf
    '2510.03760',   # EvoEngineer
    '2510.07356',   # ConCuR
    '2510.16996',   # STARK
    '2510.17891',   # TritonRL
    '2511.01884',   # CudaForge
    '2511.20100',   # QiMeng-Kernel
    '2512.02551',   # CUDA-L2
    '2601.00227',   # FlashInfer-Bench
    '2601.15727',   # 对标综述
    '2602.05885',   # Dr. Kernel
    '2602.14293',   # KernelBlaster
    '2602.19128',   # K-Search
    '2602.24286',   # CUDA Agent
    '2603.19173',   # SOL-ExecBench
    '2604.18616',   # Ave
    '2605.04956',   # KernelBenchX
    '2606.16231',   # Tokens to Regions
    '2606.26453',   # KernelPro
    '2606.26758',   # EGG
    '2607.16241',   # KernelBench-Verified
    '2609.18123',   # AutoTuneBench
    '2609.21058',   # 端到端收益
    '2610.03226',   # D2K-Bench
    '2610.24648',   # EdgeKernelBench
    '2610.36576',   # 学习 profile 什么
    '2610.36623',   # 批量不变性
]

sources: list[dict] = []
for aid in ARXIV_USED:
    p = papers.get(aid)
    if not p:
        print(f'  [!] 论文库缺 {aid}')
        continue
    sources.append({
        'source_id': f'src-arxiv-{aid.replace(".", "-")}',
        'url': f'https://arxiv.org/abs/{aid}',
        'doi': f'10.48550/arXiv.{aid}',
        'source_type': 'academic',
        'publisher': 'arXiv',
        'title': p['title'],
        'published_at': p['published'],
        'updated_at': p.get('updated', p['published']),
        'fetched_at': FETCHED,
        'language': 'en',
        'trust_tier': 'primary',
        'access': 'open',
        'license': 'arXiv (varies)',
        'notes': '经 arXiv 官方 API (export.arxiv.org/api/query) 获取元数据与摘要',
    })

# 补充两个 arXiv 之外、但正文直接使用的来源
sources.append({
    'source_id': 'src-internal-claim-audit',
    'url': 'file:///D:/github/DeepResearchRSI/research/cuda-kernel-gen/claims_audit.csv',
    'doi': '',
    'source_type': 'independent',
    'publisher': '本研究（自建审计产物）',
    'title': '70 条速度声明的逐条可比性判定审计表',
    'published_at': '2026-11-03',
    'updated_at': '',
    'fetched_at': FETCHED,
    'language': 'zh-en',
    'trust_tier': 'primary',
    'access': 'open',
    'license': 'internal',
    'notes': '由 export_claim_audit.py 从 speed_claims.json 生成；'
             '每行含判定理由，可重跑脚本逐行核对。这是本文自统计结论的一手证据。',
})

sources.append({
    'source_id': 'src-hf-kernelllm',
    'url': 'https://huggingface.co/facebook/KernelLLM',
    'doi': '',
    'source_type': 'official',
    'publisher': 'Meta / Hugging Face',
    'title': 'facebook/KernelLLM model card',
    'published_at': '2025-06-30',
    'updated_at': '',
    'fetched_at': FETCHED,
    'language': 'en',
    'trust_tier': 'primary',
    'access': 'open',
    'license': 'other',
    'notes': 'KernelLLM 无 arXiv 编号，正文以其模型卡为引用源',
})
sources.append({
    'source_id': 'src-awesome-kernel',
    'url': 'https://github.com/flagos-ai/awesome-LLM-driven-kernel-generation',
    'doi': '',
    'source_type': 'community',
    'publisher': 'GitHub',
    'title': 'Awesome LLM-Driven Kernel Generation',
    'published_at': '2026-01-22',
    'updated_at': '',
    'fetched_at': FETCHED,
    'language': 'en',
    'trust_tier': 'secondary',
    'access': 'open',
    'license': 'unknown',
    'notes': '用于发现论文清单，不作为事实来源',
})

# ---------------------------------------------------------------- evidence
evidence: list[dict] = []
EID = 0

def add_ev(src_id: str, quote: str, locator: str, note: str,
           quote_type: str = 'quote', stance: str = 'supports') -> str:
    global EID
    EID += 1
    eid = f'e-{EID:03d}'
    evidence.append({
        'evidence_id': eid,
        'source_id': src_id,
        'locator': locator,
        'quote': quote,
        'quote_type': quote_type,
        'stance': stance,
        'fetched_at': FETCHED,
        'note': note,
    })
    return eid


def grab(aid: str, pattern: str, group: int = 0) -> tuple[str, str] | None:
    """从摘要中截取一段**原文**（保证是子串），返回 (quote, locator)。"""
    p = papers.get(aid)
    if not p:
        return None
    ab = p['abstract']
    m = re.search(pattern, ab)
    if not m:
        return None
    s, e = m.span(group)
    # 扩展到句子边界，但保证仍是原文子串
    left = ab.rfind('. ', 0, s)
    left = 0 if left < 0 else left + 2
    right = ab.find('. ', e)
    right = len(ab) if right < 0 else right + 1
    quote = ab[left:right].strip()
    return quote, f'abstract, char {left}-{right}'


# ---- E: KernelBench 的基线成果（领域起点）
r = grab('2502.10517', r'matching the PyTorch baseline in less than (\d+)% of the cases')
if r:
    ev_kb_20 = add_ev('src-arxiv-2502-10517', r[0], r[1],
                      'KernelBench 原始结论：前沿模型在不到 20% 的题目上达到 PyTorch 速度')

# ---- E: KernelBench-Verified 的双基线数字
r = grab('2607.16241', r'achieves a 0\.88x geometric mean speedup[^.]*')
ev_ver_088 = add_ev('src-arxiv-2607-16241', r[0] if r else '', r[1] if r else '',
                    '开启 TF32 基线 + 四分布隐藏测试后的几何平均') if r else ''

r = grab('2607.16241', r'1\.43x speedup observed under the standard evaluation protocol')
ev_ver_143 = add_ev('src-arxiv-2607-16241', r[0], r[1],
                    '同一模型在标准协议下的几何平均') if r else ''

r = grab('2607.16241', r'28\\?% of GPU kernels generated by the best model increase peak GPU memory')
ev_ver_mem = add_ev('src-arxiv-2607-16241', r[0], r[1],
                    '速度之外的代价：28% 的 kernel 增加峰值显存') if r else ''

# ---- E: AutoTuneBench 的诚实基线
r = grab('2609.18123', r'our best kernel reads 10\.6x against a naive baseline but 2\.03x against the honest one')
ev_atb = add_ev('src-arxiv-2609-18123', r[0], r[1],
                '独立复现：稻草人基线 vs 诚实基线，差 5.2 倍') if r else ''

# ---- E: 端到端收益（本文最重要的证据）
r = grab('2609.21058', r'the addressable fraction ranges from [\d.]+\\?% to [\d.]+\\?%')
ev_e2e_frac = add_ev('src-arxiv-2609-21058', r[0], r[1],
                     '真实负载中可优化时间占比的实测范围') if r else ''

r = grab('2609.21058', r'80-86\\?% of runtime is spent in cuBLAS GEMM and FlashAttention')
ev_e2e_80 = add_ev('src-arxiv-2609-21058', r[0], r[1],
                   'Transformer 上 80-86% 时间在 cuBLAS/FlashAttention，端到端上限约 1%') if r else ''

r = grab('2609.21058', r'a tensor of zeros on (\d+) of (\d+) level-1 problems')
ev_e2e_zero = add_ev('src-arxiv-2609-21058', r[0], r[1],
                     'KernelBench 正确性检查可被全零张量通过') if r else ''

# ---- E: 批量不变性
r = grab('2610.36623', r'(\d+) confirmed BI violations among (\d+) batch-applicable released artifacts')
ev_bi = add_ev('src-arxiv-2610-36623', r[0], r[1],
               '83 个可批量化产物中 19 个存在批量不变性违规') if r else ''

# ---- E: CUDA-L1 的多口径数字
r = grab('2507.14111', r'average speedup of x[\d.]+ with a median speedup of x[\d.]+')
ev_l1 = add_ev('src-arxiv-2507-14111', r[0], r[1],
               '同一系统的算术平均与中位数：3.12x vs 1.42x') if r else ''

r = grab('2507.14111', r'peak speedups reaching x(\d+)')
ev_l1_peak = add_ev('src-arxiv-2507-14111', r[0], r[1],
                    '峰值 120x：同一系统内的最长尾') if r else ''

# ---- E2: CUDA-L1 在多个外部基线下的数字
# 补这条的原因：P2 数值回溯要求 paper/data 里每个数值都能在
# 某条 evidence.quote 里逐字找到。原先 2.77 / 2.81 / 7.72 只在摘要里，
# 没有建成 evidence，于是 audit_paper 报「在主张及其全部证据里都找不到」。
# 那不是脚本误报，是证据缺口——数据有，引用链没接上。
r = grab('2507.14111',
         r'x[\d.]+ over Torch Compile.{0,120}?x[\d.]+ over cuDNN libraries')
ev_l1_baselines = add_ev(
    'src-arxiv-2507-14111', r[0], r[1],
    '同一系统对 torch.compile / CUDA Graph / cuDNN 的倍数：2.77 / 2.81 / 7.72'
) if r else ''

# ---- E: CUDA-L2 的四组对照
r = grab('2512.02551', r'\+19\.2\\?% over cuBLAS using the optimal layout configuration')
ev_l2 = add_ev('src-arxiv-2512-02551', r[0], r[1],
               'HGEMM 上相对 cuBLAS 最优布局的增益') if r else ''

# ---- E: CUDA Agent 的覆盖率口径
r = grab('2602.24286', r'100\\?%, 100\\?%, and 92\\?% faster rate over')
ev_agent = add_ev('src-arxiv-2602-24286', r[0], r[1],
                  '「faster rate」是覆盖率而非加速比，与加速比不可混用') if r else ''

# ---- E: Dr. Kernel 的奖励黑客
r = grab('2602.05885', r'models may hack training rewards[^.]*')
ev_drk = add_ev('src-arxiv-2602-05885', r[0], r[1],
                'RL 训练中「懒惰优化」与奖励黑客的明确定义') if r else ''

# ---- E: Ave 的数据流不变量
r = grab('2604.18616', r'data-flow invariants as compile-time guardrails')
ev_ave = add_ev('src-arxiv-2604-18616', r[0], r[1],
               '把正确性从「事后测试」前移到「编译期约束」') if r else ''

# ---- E: 对标综述的范围
r = grab('2601.15727', r'the field remains fragmented and lacks a systematic perspective')
ev_survey = add_ev('src-arxiv-2601-15727', r[0], r[1],
                   '同期 IJCAI 2026 综述对领域现状的判断，本文与其差异化') if r else ''

# ---- E: SwizzlePerf 的专家对比
r = grab('2508.20258', r'less than (\d+) minutes to generate the same hardware-specific optimal swizzling pattern that took expert performance engineers (\d+) weeks')
ev_swz = add_ev('src-arxiv-2508-20258', r[0], r[1],
                '专家 2 周 vs 系统 5 分钟：硬件感知优化的效率对比') if r else ''

# ---- E: 学习 profile 什么
r = grab('2610.36576', r'[Ll]ess is more[^.]*') or grab('2610.36576', r'learn[^.]*profile[^.]*')
if r:
    add_ev('src-arxiv-2610-36576', r[0], r[1],
           '诊断难题的新方向：连「该 profile 什么」都需要学习')

# ---- E: 本文自统计的审计产物（可重跑核对）
# quote 必须逐字等于生成器写出的内容。原先只写了「8 条 / 0 条」，
# 后来图 4 需要引用五个语义类别的计数，而那个计数不在 quote 里，
# P2 因此报「找不到」。修法是把 quote 扩成完整汇总，
# 而不是把数字改成 scripts 认得的写法。
ev_audit = add_ev(
    'src-internal-claim-audit',
    'comparable=yes 的行共 8 条；2026-07-01 之后的 20 行中 comparable=yes 为 0 条。'
    '语义类型计数：UP_TO=11, PER_CASE=13, UNSPECIFIED=22, AVERAGE=9, GEOMEAN=15。',
    'claims_audit.csv 第 2-71 行（comparable 列）；汇总见 claim_audit_summary.json',
    '由 export_claim_audit.py 从 speed_claims.json 生成，判定理由逐行可见',
    quote_type='derived',
    stance='supports',
)

# ---------------------------------------------------------------- claims
claims: list[dict] = []

def add_claim(cid, statement, ctype, as_of, conf, evs, derivation='',
              counter='', notes=''):
    claims.append({
        'claim_id': cid,
        'statement': statement,
        'claim_type': ctype,
        'as_of': as_of,
        'confidence': conf,
        'evidence_ids': ';'.join(evs),
        'counter_evidence_ids': counter,
        'derivation': derivation,
        'notes': notes,
    })


AS_OF = '2026-11-03'

add_claim('c-kb-baseline',
          'KernelBench 发布时，前沿推理模型在不到 20% 的题目上能达到 PyTorch 的速度。',
          'measurement', AS_OF, 'high', [ev_kb_20],
          notes='领域起点的基准数字')

add_claim('c-verified-drop',
          'KernelBench-Verified 在开启 TF32 基线并加入四分布隐藏测试后，最强模型（GPT-5.5）'
          '的几何平均加速比从 1.43x 跌至 0.88x，即打不过 PyTorch。',
          'measurement', AS_OF, 'high', [ev_ver_088, ev_ver_143],
          notes='同一系统的双基线对照，是本文判定「基线泄漏」的核心证据')

add_claim('c-tf32-inflation',
          'TF32 基线配置造成的性能虚高约为 1.6 倍（1.43x / 0.88x）。',
          'prediction', AS_OF, 'medium', [ev_ver_088, ev_ver_143],
          derivation='由同文报告的两个几何平均相除得到：1.43 / 0.88 ≈ 1.625。'
                     '该比值未在原文直接给出，属本文推算。',
          notes='推算值，非原文明示')

add_claim('c-strawman',
          'AutoTuneBench 独立复现了同一现象：某 kernel 相对朴素基线为 10.6x，'
          '相对诚实基线只有 2.03x，相差 5.2 倍。',
          'measurement', AS_OF, 'high', [ev_atb],
          notes='与 c-tf32-inflation 同向，量级更大')

add_claim('c-memory-cost',
          'KernelBench-Verified 发现 28% 的生成 kernel 增加了峰值显存占用。',
          'measurement', AS_OF, 'high', [ev_ver_mem],
          notes='速度之外的隐性代价')

add_claim('c-l1-spread',
          'CUDA-L1 在 KernelBench 250 题上，算术平均 3.12x、中位数 1.42x、峰值 120x，'
          '三个口径跨度达 85 倍；相对 torch.compile / CUDA Graph / cuDNN 分别为 '
          '2.77x / 2.81x / 7.72x。',
          'measurement', AS_OF, 'high', [ev_l1, ev_l1_peak, ev_l1_baselines],
          counter='e-009',
          notes='说明单一统计口径无法描述分布；反证 e-009 指出该类加速比的端到端意义有限')

add_claim('c-l2-cublas',
          'CUDA-L2 在 HGEMM 上相对 cuBLAS 最优布局取得 +19.2% 的平均增益。',
          'measurement', AS_OF, 'high', [ev_l2],
          notes='少见的以闭源库为基线的严谨对照')

add_claim('c-coverage-vs-speed',
          'CUDA Agent 报告的「100%/100%/92% faster rate」是「快于 torch.compile 的 '
          'kernel 占比」（覆盖率），不是加速比；两者量纲不同，不可混用。',
          'spec', AS_OF, 'high', [ev_agent],
          notes='本领域最常见的口径误读之一')

add_claim('c-e2e-fraction',
          '真实负载中可被 kernel 优化影响的时间占比为 8.9% 至 58.2%。',
          'measurement', AS_OF, 'high', [ev_e2e_frac],
          notes='来自三个领域七个负载的剖析')

add_claim('c-e2e-limit',
          'Transformer 推理中 80-86% 的运行时花在 cuBLAS GEMM 与 FlashAttention 上，'
          '因此端到端收益的实际上限约为 1%。',
          'measurement', AS_OF, 'high', [ev_e2e_80],
          counter='',
          notes='本综述认为最需要被广泛知晓的一条；它削弱了 benchmark 加速比的意义')

add_claim('c-e2e-amdahl',
          '在可优化占比 8.9% 的场景下，kernel 本身快 4 倍对应的端到端加速比约为 1.07 倍。'
          '同一公式在占比 30% 与 58.2% 下分别给出 1.29 倍与 1.77 倍。',
          'prediction', AS_OF, 'high', [ev_e2e_frac],
          derivation='Amdahl 定律：S = 1 / ((1 - p) + p / k)，取 k = 4 倍。'
                     'p = 8.9% 时 S ≈ 1.0715；p = 30% 时 S ≈ 1.2903；'
                     'p = 58.2% 时 S ≈ 1.7746。'
                     '三个占比均来自 c-e2e-fraction 的实测区间（8.9%–58.2%）。',
          notes='推算值')

add_claim('c-zero-kernel',
          'KernelBench 的正确性检查（torch.allclose 带绝对容差）在 60 道 Level-1 题中'
          '有 4 道可以被全零张量通过。',
          'measurement', AS_OF, 'high', [ev_e2e_zero],
          notes='基准本身的正确性判据存在漏洞')

add_claim('c-batch-invariance',
          '83 个可批量化的已发布产物中，19 个存在已确认的批量不变性违规（约 23%）。',
          'measurement', AS_OF, 'high', [ev_bi],
          notes='该维度不在任何主流基准的覆盖范围内')

add_claim('c-rl-hacking',
          'RL 训练存在系统性的奖励黑客风险，模型会优先选择「平凡但正确」而非'
          '「快但可能错」的 kernel。',
          'measurement', AS_OF, 'high', [ev_drk],
          notes='Dr. Kernel 将其命名为 lazy optimization')

add_claim('c-ave-invariant',
          'Ave 用数据流不变量把正确性从「事后测试」前移到「编译期约束」，'
          '是提升保证强度的可行方向。',
          'spec', AS_OF, 'medium', [ev_ave],
          notes='方向性判断，效果尚待更大规模验证')

add_claim('c-swizzle-expert',
          'SwizzlePerf 在 5 分钟内生成专家需要 2 周才能找到的 swizzling 模式。',
          'measurement', AS_OF, 'medium', [ev_swz],
          notes='单一 GEMM 案例，不可外推为通用效率')

add_claim('c-comparability',
          '本文统计的 70 条速度声明中，只有 8 条（11%）同时满足「几何/算术平均」'
          '与「明确库基线」，即可跨论文比较；2026-07 之后新增的 20 条中达到该标准的为 0 条。',
          'measurement', AS_OF, 'high', [ev_audit],
          notes='证据为本研究自建的逐条审计表（src-internal-claim-audit），'
                '由 export_claim_audit.py 从 speed_claims.json 生成，可重跑核对')

add_claim('c-survey-gap',
          '同期 IJCAI 2026 综述按四条技术流分类，未对速度声明做统计层面的可比性分析。',
          'attribution', AS_OF, 'medium', [ev_survey],
          notes='本文的差异化定位，基于对该综述及其索引仓库的阅读')

# 补这条的原因：图 4（速度声明语义分布）的数据是 11/13/22/9/15，
# 原先借 c-comparability 作 cite，但那条主张只说「8 条可比」，
# 并不含这五个计数。audit_paper 的 P2 因此报「找不到」——
# 判据没错，是把一组数挂到了不陈述它的主张上。
# 正确做法是让这组数有自己的主张，指向内部审计汇总。
add_claim('c-claim-mix',
          '70 条速度声明的语义类型分布为：UP_TO（最优个案）11 条、'
          'PER_CASE（单点个案）13 条、UNSPECIFIED（未说明口径）22 条、'
          'AVERAGE（算术平均）9 条、GEOMEAN（几何平均）15 条。',
          'measurement', AS_OF, 'high', [ev_audit],
          derivation='由 export_claim_audit.py 对 speed_claims.json 逐条判定后'
                     '汇总得到，计数见 claim_audit_summary.json 的 kind_distribution。',
          notes='这是本文自建的统计产物，不是外部观测；'
                '输入（70 条声明）来自各论文摘要')

# ---------------------------------------------------------------- 写出
def write_csv(path: Path, rows: list[dict], header: list[str]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator='\n',
                       extrasaction='ignore')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    path.write_text(buf.getvalue(), encoding='utf-8')
    print(f'  {path.name}: {len(rows)} 行')


SRC.mkdir(parents=True, exist_ok=True)
write_csv(SRC / 'sources.csv', sources,
          ['source_id', 'url', 'doi', 'source_type', 'publisher', 'title',
           'published_at', 'updated_at', 'fetched_at', 'language',
           'trust_tier', 'access', 'license', 'notes'])
write_csv(SRC / 'evidence.csv', evidence,
          ['evidence_id', 'source_id', 'locator', 'quote', 'quote_type',
           'stance', 'fetched_at', 'note'])
write_csv(SRC / 'claims.csv', claims,
          ['claim_id', 'statement', 'claim_type', 'as_of', 'confidence',
           'evidence_ids', 'counter_evidence_ids', 'derivation', 'notes'])

# ---------------------------------------------------------------- 自检
print('\n=== 自检：evidence.quote 是否为摘要原文子串 ===')
bad = 0
for ev in evidence:
    sid = ev['source_id']
    if not sid.startswith('src-arxiv-'):
        continue
    aid = sid.replace('src-arxiv-', '').replace('-', '.')
    p = papers.get(aid)
    if not p:
        print(f'  [!] {ev["evidence_id"]}: 找不到 {aid}')
        bad += 1
        continue
    if ev['quote'] not in p['abstract']:
        print(f'  [!] {ev["evidence_id"]}: quote 不是 {aid} 摘要的子串')
        print(f'      quote={ev["quote"][:100]!r}')
        bad += 1
print(f'  检查 {len(evidence)} 条，失败 {bad} 条')

print('\n=== 自检：prediction 类必须带 derivation ===')
for c in claims:
    if c['claim_type'] == 'prediction' and not c['derivation']:
        print(f'  [!] {c["claim_id"]} 缺 derivation')
        bad += 1
print(f'  claims {len(claims)} 条')

raise SystemExit(0 if bad == 0 else 1)
