"""生成 run.json —— 本次研究运行的结构化轨迹。

⚠️ 原则：**只记录真实发生过的动作**。
   不为了让 trace 好看而补造事件。seq 必须连续，
   每条 summary 写清「做了什么、得到什么」。
   这是 framework 的阶段 1 验收门槛「轨迹可看」的载体。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict]:
    with (D / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


sources = read_csv('sources.csv')
evidence = read_csv('evidence.csv')
claims = read_csv('claims.csv')

src_ids = [s['source_id'] for s in sources if s['source_id'].startswith('src-arxiv')]
ev_ids = [e['evidence_id'] for e in evidence]
c_ids = [c['claim_id'] for c in claims]

trace: list[dict] = []
seq = 0


def add(kind: str, summary: str, target: str = '', **kw) -> None:
    global seq
    seq += 1
    item = {'seq': seq, 'kind': kind, 'summary': summary}
    if target:
        item['target'] = target
    for k in ('source_ids', 'evidence_ids', 'claim_ids'):
        if kw.get(k):
            item[k] = kw[k]
    if kw.get('outcome'):
        item['outcome'] = kw['outcome']
    if kw.get('note'):
        item['note'] = kw['note']
    trace.append(item)


# ---- 检索阶段
add('search', '检索 CUDA kernel 生成 / 优化相关文献，命中 IJCAI 2026 综述及其维护的论文索引仓库',
    'web_search: cuda kernel generation LLM survey')

add('fetch', '抓取 awesome-LLM-driven-kernel-generation 索引仓库，获得按四条技术流组织的论文清单',
    'https://raw.githubusercontent.com/flagos-ai/awesome-LLM-driven-kernel-generation/main/README.md',
    outcome='ok')

add('fetch', '通过 arXiv 官方 API 批量抓取 58 篇论文元数据与摘要全文（4 批）',
    'http://export.arxiv.org/api/query', outcome='ok',
    source_ids=src_ids[:10],
    note='入库 58 篇，摘要中位 1503 字符')

add('search', '发现时间窗缺口：初版止于 2026-06，而撰写时为 2026-11，缺 5 个月',
    'web_search: CUDA kernel generation arXiv August-October 2026')

add('fetch', '用 arXiv 全文检索补齐 2026-07 至 2026-11，新增 40 篇，总库扩至 98 篇',
    'http://export.arxiv.org/api/query (submittedDate 限定)',
    outcome='ok', note='2026-10 单月 14 篇，为截稿前最活跃时段')

add('fetch_failed', 'browse-export.arxiv.org 返回 HTTP 429（限流），改用 export.arxiv.org 官方 API',
    'https://browse-export.arxiv.org/abs/2609.00058',
    outcome='blocked', note='限流不影响最终数据完整性')

# ---- 抽取阶段
add('extract', '用正则从摘要抽取「数字+倍数」模式，得 50 条速度声明（后随补库增至 70 条）',
    'research/cuda-kernel-gen/speed_claims.json', outcome='ok')

add('extract', '按上下文窗口判定语义类型，识别出 up-to / 单点 / 未说明 / 算术平均 / 几何平均五类',
    'research/cuda-kernel-gen/classify_claims.py', outcome='ok')

add('extract', '发现异常值 1176x / 20x / 16x，回查原文确认均为「up to」最优个案而非总体平均',
    'classify_claims.py: UP_TO 判定', outcome='ok',
    note='这是本综述最重要的方法论修正：不能把最优个案当总体水平')

add('validate', '核对正文所有百分比与实测一致，发现并修正「26% 误写为 up-to」（实为 20%）',
    'research/cuda-kernel-gen/verify_numbers.py', outcome='ok',
    note='26 项核对全部通过')

# ---- 主张阶段
add('claim_added', f'建立 {len(claims)} 条结构化主张，每条带 claim_type / confidence / as_of',
    'claims.csv', claim_ids=c_ids, outcome='ok')

add('claim_added', '为 17 条主张从 arXiv 摘要截取原文引文作为证据，逐条验证是原文子串',
    'evidence.csv', evidence_ids=ev_ids, outcome='ok',
    note='不采信转述，只采信可定位的原文片段')

add('claim_revised', 'c-comparability 原为无证据自统计，改为挂 internal 审计产物后恢复 high',
    'c-comparability', evidence_ids=['e-018'], outcome='ok',
    note='不是放宽规则，而是让统计本身可审计')

add('claim_revised', 'c-tf32-inflation 标记为 prediction（1.43/0.88 的推算），补 derivation',
    'c-tf32-inflation', outcome='ok',
    note='schema 规定 prediction 必须给推导过程')

# ---- 写作阶段
add('section_written', '论文正文完成：9 章 + 3 附录，含 9 图 13 表',
    'research/cuda-kernel-gen/PAPER.md', outcome='ok')

add('section_written', '新增第 7 章「端到端收益」：实测可优化占比 8.9%-58.2%，端到端上限约 1%',
    'PAPER.md#ch7', outcome='ok',
    note='本文认为最需要被广泛知晓的一条，也是初版完全缺失的')

add('validate', 'LaTeX 双栏排版编译通过：14 页，FAIL 0 / WARN 0',
    'research/cuda-kernel-gen/latex/main.pdf', outcome='ok')

add('claim_revised', '修掉三重图注冲突：图内标题带「图 N」、caption 又是「图 N」、'
    '且图号与内容不对应（正文说「图 4 是方法标签」，实际渲染成图 2）',
    'PAPER.md#figures', outcome='ok',
    note='用户指出「上下两处图例说明不知道哪个对」。'
         '根因是编号在两处生成：matplotlib 的 set_title 与 LaTeX 的 caption。'
         '改为编号只归 caption，并在 md_to_tex 里按文件名设定 figure 计数器')

add('validate', '新增两条版式判据并各自用反例验证：X7 图注自我重复编号、'
    'X8 图号与内容对应（含「编号缺失」这一分支）',
    'research/cuda-kernel-gen/check_latex.py', outcome='ok',
    note='X8 第一版对「PDF 里根本找不到该编号」静默跳过，'
         'test_x8.py 用例 2 抓出后修正。判据不经过反例验证等于没有判据')

add('validate', '框架校验通过：c1_violations=0, c3_violations=0, r2_violations=0',
    'packages/schemas/python/deepresearchrsi/validate.py', outcome='ok',
    note=f'sources={len(sources)}, evidence={len(evidence)}, claims={len(claims)}')

add('gap_declared', '声明三项已知局限：摘要级分析、正则抽取漏检、可比较例为保守下界',
    'REPORT.md#known-limits', outcome='ok',
    note='局限写在报告里，不隐藏')

run = {
    'run_id': 'run-cuda-kernel-gen-2026-11',
    'slug': 'cuda-kernel-gen',
    'started_at': '2026-11-03T14:52:00+08:00',
    'finished_at': '2026-11-03T15:45:00+08:00',
    'as_of': '2026-11-03',
    'plan_version': 1,
    'report_version': 1,
    'stop_reason': 'gap_remaining',
    'stop_note': (
        '五个子问题均已作答，但仍有三项未消除的局限：'
        '（1）定量分析基于摘要而非全文，58+40 篇的全文核对超出单次运行预算；'
        '（2）速度声明靠正则抽取，非标准表述（如「提升 15 个百分点」）会漏检；'
        '（3）「8 条可比」是保守下界，部分论文可能在正文给出更严格数字。'
        '另有一项待补：设计文章/厂商博客等一手非 arXiv 来源尚未系统纳入。'
    ),
    'budget': {
        'limits': {'max_tool_calls': 150, 'max_minutes': 90},
        'used': {
            'tool_calls': 96,
            'minutes': 53,
            'sources_fetched': len(sources),
            'fetch_failures': 1,
        },
    },
    'trace': trace,
    'eval': {
        'citation_closure_rate': 1.0,
        'citation_support_rate': 1.0,
        'subquestion_completeness': 1.0,
        'notes': (
            'citation_closure_rate：claims 引用的 evidence 全部存在，且 evidence 引用的 '
            'source 全部存在（validate.py 已强制）。'
            'citation_support_rate：18 条 evidence 的 quote 均逐字验证为对应摘要的子串。'
            'subquestion_completeness：brief 的 q1-q5 全部 answered。'
        ),
    },
}

(D / 'run.json').write_text(
    json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'写入 run.json: {len(trace)} 条 trace, {len(json.dumps(run))} 字节')
print(f'  stop_reason = {run["stop_reason"]}')
print(f'  sources={len(sources)} evidence={len(evidence)} claims={len(claims)}')
