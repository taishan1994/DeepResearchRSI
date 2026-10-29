"""论文内部一致性自检：查 audit_paper.py 不覆盖的那一类问题。

两个脚本的分工：

  audit_paper.py  查「论文与档案是否一致」
                  引用闭合、数值可回溯到证据、图表文件存在且被插入正文
  check_paper.py  查「论文与它自己是否一致」
                  章节编号、图表编号、自述数字、术语、交叉引用

前者防造假，后者防自相矛盾。两者都过，才算论文可交付。

用法：
    python scripts/check_paper.py

退出码非 0 表示有 FAIL 级问题（WARN 不影响退出码）。

已发现的真实缺陷（本脚本上线时抓到）：
  I5  正文写着「本文引用的 29 条主张」，而实际已是 36 条。
      这类数字在每次加章节后都会过期，靠人读发现不了。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path('research/rtx-pro-6000')
PAPER = ROOT / 'paper' / 'PAPER.md'

problems: list[tuple[str, str]] = []   # (等级, 描述)


def fail(code: str, msg: str) -> None:
    problems.append(('FAIL', f'{code} {msg}'))


def warn(code: str, msg: str) -> None:
    problems.append(('WARN', f'{code} {msg}'))


def main() -> int:
    text = PAPER.read_text(encoding='utf-8')
    lines = text.split('\n')

    # ---------- I1 章节编号 ----------
    chaps = [(int(m.group(1)), m.group(2))
             for m in re.finditer(r'^## (\d+)　(.+)$', text, re.M)]
    nums = [n for n, _ in chaps]
    if nums != list(range(1, len(nums) + 1)):
        fail('I1', f'章号不连续：{nums}')
    else:
        print(f'  I1 章号 1..{len(nums)} 连续')

    # ---------- I2 小节归属 ----------
    cur = 0
    bad2 = []
    for ln in lines:
        m2 = re.match(r'^## (\d+)　', ln)
        if m2:
            cur = int(m2.group(1))
            continue
        m3 = re.match(r'^#{3,4} (\d+)\.(\d+)', ln)
        if m3:
            if int(m3.group(1)) != cur:
                bad2.append((ln.strip()[:40], cur))
    if bad2:
        for b, c in bad2:
            fail('I2', f'小节 {b} 出现在第 {c} 章内')
    else:
        print('  I2 小节归属正确')

    # ---------- I3 图表编号与引用 ----------
    figs = sorted(int(m.group(1)) for m in re.finditer(r'\*图 (\d+)　', text))
    tabs = sorted(int(m.group(1)) for m in re.finditer(r'\*表 (\d+)　', text))
    for name, seq in (('图', figs), ('表', tabs)):
        if seq != list(range(1, len(seq) + 1)):
            fail('I3', f'{name}编号不连续：{seq}')
        else:
            print(f'  I3 {name}编号 1..{len(seq)} 连续')

    fig_refs = sorted(int(m.group(1)) for m in re.finditer(r'!\[图 (\d+)\]', text))
    if sorted(set(fig_refs)) != figs:
        fail('I3', f'图引用 {sorted(set(fig_refs))} 与图标题 {figs} 不匹配')
    else:
        print('  I3 图引用与图标题一一对应')

    # ---------- I4 标题编号 vs 引用编号 ----------
    # 每张图/表的标题里写的编号，与它 data_file/output 的序号一致
    for m in re.finditer(r'!\[图 (\d+)\]\(figures/fig-(\d+)\.png\)', text):
        if m.group(1) != m.group(2):
            fail('I4', f'图引用编号 {m.group(1)} 与图片文件 fig-{m.group(2)} 不一致')

    # ---------- I5 自述数字 ----------
    n_claims = len(re.findall(r'\[c-[A-Za-z0-9_-]+\]', text))
    uniq = len(set(re.findall(r'\[(c-[A-Za-z0-9_-]+)\]', text)))
    m = re.search(r'本文引用的 (\d+) 条主张', text)
    if m and int(m.group(1)) != uniq:
        fail('I5', f'正文说「本文引用的 {m.group(1)} 条主张」，实际唯一主张 {uniq} 条')
    else:
        print(f'  I5 自述主张数与实际一致（{uniq} 条唯一 / {n_claims} 处引用）')

    # 正文里若有「N 条是 unspecified」，核对与实际一致
    import csv
    cl = {c['claim_id']: c for c in csv.DictReader(
        (ROOT / 'claims.csv').open(encoding='utf-8-sig'))}
    real_uns = sum(1 for c in set(re.findall(r'\[(c-[A-Za-z0-9_-]+)\]', text))
                   if c in cl and cl[c]['sku'] == 'unspecified')
    m5 = re.search(r'有 \*\*(\d+) 条是 `unspecified`\*\*', text)
    if m5 and int(m5.group(1)) != real_uns:
        fail('I5', f'正文说「{m5.group(1)} 条是 unspecified」，实际 {real_uns} 条')
    elif m5:
        print(f'  I5 unspecified 自述数一致（{real_uns} 条）')

    # ---------- I6 术语统一 ----------
    # 「预填（prefill）」这种括号内的英文对照是刻意并列，不算不统一。
    # 先把所有「中文（english）」形式剥掉，再查残留。
    stripped = re.sub(r'[\u4e00-\u9fff]{1,6}[（(][A-Za-z0-9 \-]{1,20}[）)]', '', text)

    # 只查真会导致歧义的混用：同一概念在正文里出现两种中文写法。
    #
    # ⚠️ 不要把「X阶段」列进变体表。「预填阶段 / 解码阶段」是在说**阶段**，
    # 与「预填 / 解码」指的是同一件事的两个侧面，不是两种写法。
    # 这一条曾经误报过一次：§3.5 写「收益集中在解码阶段而非预填阶段」，
    # 那是对举，语义完全正确。
    TERMS = [
        ('预填', ['预填充', '前填充']),
        ('解码', ['逐字生成', '逐 token 输出']),
        ('显存带宽', ['内存带宽']),
        ('上下文长度', ['上下文窗口长度']),
    ]
    for prefer, variants in TERMS:
        for v in variants:
            if v in stripped:
                warn('I6', f'术语不统一：正文出现「{v}」，建议统一为「{prefer}」')

    # ---------- I7 交叉引用 ----------
    secs = set()
    for m in re.finditer(r'^#{3,4} (\d+\.\d+)', text, re.M):
        secs.add(m.group(1))
    for m in re.finditer(r'§(\d+(?:\.\d+)*)', text):
        ref = m.group(1)
        # 只查两段式及以下（三段的 REPORT 交叉引用不在本文范围）
        if ref.count('.') <= 1 and ref not in secs and ref.split('.')[0] not in {
                str(n) for n in nums}:
            warn('I7', f'交叉引用 §{ref} 找不到对应小节')

    print()
    fails = [p for p in problems if p[0] == 'FAIL']
    warns = [p for p in problems if p[0] == 'WARN']
    for lvl, msg in problems:
        print(f'  [{lvl}] {msg}')
    print(f'\nFAIL {len(fails)} / WARN {len(warns)}')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
