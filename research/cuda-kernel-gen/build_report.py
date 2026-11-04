"""生成框架要求的 REPORT.md（带 [c-xxx] / [src-xxx] / [e-xxx] 可解析引用）。

⚠️ 关键约束：正文里的每个 [c-xxx] 必须能在 claims.csv 找到，
   否则 validate.py 直接报错。故本脚本**从 claims.csv 读**，
   不手写 id —— 手写必然漂移。

与 PAPER.md 的分工：
  PAPER.md 是给人读的论文（含图表、排版）。
  REPORT.md 是给框架审计摘要（每个论断都带 claim 引用）。
  两者结论必须一致，但体裁不同，故不互相生成。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

D = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict]:
    with (D / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


claims = {r['claim_id']: r for r in read_csv('claims.csv')}
sources = {r['source_id']: r for r in read_csv('sources.csv')}
evidence = {r['evidence_id']: r for r in read_csv('evidence.csv')}


def cite(cid: str) -> str:
    """渲染一条主张：陈述 + 引用标记。"""
    c = claims[cid]
    evs = ' '.join(f'[{e}]' for e in c['evidence_ids'].split(';') if e)
    return f"- {c['statement']} `[{cid}]` {evs}".rstrip()


def section(title: str, ids: list[str]) -> str:
    out = [f'## {title}', '']
    for cid in ids:
        if cid in claims:
            out.append(cite(cid))
        else:
            out.append(f'- [!] 缺 claim {cid}')
    out.append('')
    return '\n'.join(out)


lines: list[str] = []
lines.append('# CUDA Kernel 自动生成前沿进展 —— 审计摘要')
lines.append('')
lines.append('> 本文件是 DeepResearchRSI 框架的**审计视图**，不是论文本身。')
lines.append('> 论文见 `D:\\github\\research\\cuda-kernel-gen\\latex\\main.pdf`（14 页）。')
# ⚠️ 不能在这里写出 [c-xxx] / [e-xxx] 这类占位符：
# validate.py 的正则是 r"\[(c-[a-z0-9-]+)\]"，会把字面量 xxx 当成真实 id，
# 报「引用了不存在的 c-xxx」。说明文字必须避开可被匹配的形态。
lines.append('> 这里的每个论断都带行内的主张编号与证据编号（方括号形式），')
lines.append('> 可回溯到 `claims.csv` / `evidence.csv` / `sources.csv`。')
lines.append('')
lines.append(f"**来源** {len(sources)} 个 ｜ **证据** {len(evidence)} 条 ｜ "
             f"**主张** {len(claims)} 条 ｜ **数据快照** 2026-11-03")
lines.append('')

lines.append(section('一、领域的起点与进展', [
    'c-kb-baseline', 'c-l1-spread', 'c-l2-cublas', 'c-coverage-vs-speed',
]))

lines.append(section('二、度量危机：数字不可比', [
    'c-comparability', 'c-tf32-inflation', 'c-verified-drop',
]))

lines.append(section('三、奖励黑客与系统性夸大', [
    'c-strawman', 'c-memory-cost', 'c-zero-kernel', 'c-rl-hacking',
]))

lines.append(section('四、端到端收益：被回避的问题', [
    'c-e2e-fraction', 'c-e2e-limit', 'c-e2e-amdahl',
]))

lines.append(section('五、被评测忽略的维度', [
    'c-batch-invariance', 'c-ave-invariant', 'c-swizzle-expert',
]))

lines.append(section('六、与已有综述的关系', ['c-survey-gap']))

# 附录：主张-证据对账表
lines.append('## 附录：主张—证据对账')
lines.append('')
lines.append('| claim | 类型 | 置信 | 证据 | 反证 |')
lines.append('|---|---|---|---|---|')
for cid, c in claims.items():
    evs = ', '.join(c['evidence_ids'].split(';')) if c['evidence_ids'] else '—'
    ce = c['counter_evidence_ids'] or '—'
    lines.append(f"| `{cid}` | {c['claim_type']} | {c['confidence']} | {evs} | {ce} |")
lines.append('')

# 复现说明
lines.append('## 复现')
lines.append('')
lines.append('```bash')
lines.append('# 1) 抓取论文元数据（arXiv 官方 API）')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/fetch_papers.py')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/fetch_recent.py')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/merge_recent.py')
lines.append('')
lines.append('# 2) 抽取与分类速度声明')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/extract_metrics.py')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/paper/classify_claims.py')
lines.append('')
lines.append('# 3) 生成审计产物与证据三件套')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/export_claim_audit.py')
lines.append('python D:/github/DeepResearchRSI/research/cuda-kernel-gen/build_evidence.py')
lines.append('')
lines.append('# 4) 框架校验')
lines.append('PYTHONPATH=D:/github/DeepResearchRSI/packages/schemas/python \\')
lines.append('  python -m deepresearchrsi.validate D:/github/DeepResearchRSI/research/cuda-kernel-gen')
lines.append('```')
lines.append('')
# ⚠️ 这一行的数字由 scripts/sync_report_counts.py 重算后写回，
#    禁止手写：tests/test_schemas.py 会逐字比对 CSV 实际行数。
#    这里先留 0 占位，build_report.py 跑完后再执行 sync 脚本。
lines.append('**当前校验结果**：sources=0, evidence=0, claims=0, claims_high=0')
lines.append('')

(D / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
print(f'写入 REPORT.md: {len(lines)} 行, {len("".join(lines))} 字符')
