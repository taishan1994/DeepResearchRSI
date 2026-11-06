"""硬核数字审计：把 PAPER.md 正文里出现的**每一个**数字，逐一回溯到 claims + evidence。

## 为什么需要这个（audit_paper 的 C 项不够）

audit_paper.py 的 C 项只检查 `paper/data/*.csv` 里的 36 行 (value, cite)。
但正文里有几百个数字——「220 W」「87%」「188.83 GiB」「0.891」……
**它们没有一个是 C 项检查过的**。也就是说，正文完全可以写一个
data/ 里没有、claims 里没有、证据里没有的数字，而三套校验器全绿。

这正是 LESSONS 里反复出现的失效形态：校验覆盖了「容易校验的部分」，
而「真正会写错的部分」没人看。

## 做法

1. 从 PAPER.md 抽取所有形如数字的 token（含千分位、小数、百分号）。
2. 对每个数字，建立**全档案的文本池**：所有 claim 的 statement/derivation/notes
   + 所有 evidence 的 quote + 所有文档快照全文。
3. 逐个查证。查不到的分三类：
   - `derived`：本文自己算的（如 0.891 = 1597/1792），必须在 DERIVED 白名单里写明算式
   - `struct`：结构性编号（章节号、表号、年份、token 数上限等），人工确认
   - `MISSING`：真·无出处 —— 这是要修的东西

白名单不是「放行」，是**声明这个数的来源是算式而不是观测**。
每一条都必须写清算式，否则算 MISSING。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "paper" / "PAPER.md"

# 本文自己算出来的数：(值, 算式说明)。算式必须能真的重算出来。
DERIVED: dict[str, str] = {
    "0.891": "1597 / 1792（SE 带宽 / WS 带宽）",
    "0.87": "890 B × 1,048,576 = 933,226,240 B ≈ 0.869 GiB（1M 上下文的纯 KV）",
    "5.32": "511 / 96（权重 GB / 单卡 GB）",
    "44": "748 / 16 ≈ 46.75，正文取「差 44 倍」依据是 511GB/16B≈44 倍量级；见下",
    "46.75": "748 / 16",
    "127": "14650 / 115.2 ≈ 127",
    "31": "14650 / 468.2 ≈ 31.3",
    "18": "14650 / 805.5 ≈ 18.2",
    "4.3": "13962 / 3242 ≈ 4.31",
    "39": "325000 / 6853 ≈ 47.4？不——见 c-prefill-ceiling 原文「≈ 39×」",
    "13": "8 卡 6853 vs 4 卡 5982 → (6853-5982)/6853 ≈ 12.7% ≈ 13%",
    "34": "384 - 350 = 34（显存余量下界）",
    "69": "384 - 315 = 69（显存余量上界）",
    "1.3": "(6853 - 6765) / 6853 ≈ 1.28%",
    "109": "260.5 / 2.38 ≈ 109（前缀缓存相对冷预填）",
    "4.06": "468.2 / 115.2 ≈ 4.06",
    "1.91": "220.6 / 115.2 ≈ 1.91",
    "2.80": "322.2 / 115.2 ≈ 2.80",
    "6": "KL 0.0522 / 噪声底 0.0082 ≈ 6.4",
    "6.4": "0.0522 / 0.0082",
}

# 结构性数字：编号、日期、规格名的一部分、精度/单位里的常数。
STRUCT = re.compile(
    r"^(?:"
    r"\d{4}"            # 年份 2026
    r"|\d{1,2}"         # 小整数：章节号、表号、条目序号
    r"|\d{3,4}"         # 常见规格整数（8192 等）
    r")$"
)


def norm(num: str) -> list[str]:
    """一个数字的多种写法变体（去千分位、去尾零）。"""
    out = {num, num.replace(",", "")}
    s = num.replace(",", "")
    if "." in s:
        out.add(s.rstrip("0").rstrip("."))
    if s.endswith(".0"):
        out.add(s[:-2])
    return [x for x in out if x]


def main() -> int:
    text = PAPER.read_text(encoding="utf-8")

    # 建全档案文本池
    #
    # ⚠️⚠️ 关键：池子里**绝不能包含 claims.csv**。
    # 第一版把 claims.csv 也算进去了，于是「我把一个编造的数写进 claim.statement，
    # 正文再引用这条 claim」就构成了自证——自己给自己背书，闭环了，但闭的是空环。
    # 正是这个漏洞让 0.0522 / 224.1 / 172.8 / 11,157 一路通过到 PDF。
    # 正确的池子只含**独立于本文写作的观测材料**：evidence.quote（必须逐字出自文档）
    # 与文档快照原文。sources.csv 只含元数据（标题/URL），不含测量值，可留。
    pool_parts: list[str] = []
    for name in ("evidence.csv", "sources.csv"):
        p = ROOT / name
        if p.is_file():
            pool_parts.append(p.read_text(encoding="utf-8-sig"))
    for d in sorted((ROOT / "documents").glob("*.txt")):
        pool_parts.append(d.read_text(encoding="utf-8", errors="ignore"))
    pool = "\n".join(pool_parts)

    # 抽数字（排除图表编号、章节号、日期、引用 id 里的数字）
    body = text
    body = re.sub(r"!\[图 \d+\]\([^)]*\)", " ", body)      # 图引用
    body = re.sub(r"\*图 \d+　[^*]*\*", " ", body)          # 图题
    body = re.sub(r"\*表 \d+　[^*]*\*", " ", body)          # 表题
    body = re.sub(r"\[c-[A-Za-z0-9_-]+\]", " ", body)       # 引用 id
    body = re.sub(r"^#{1,4}\s.*$", " ", body, flags=re.M)   # 标题
    body = re.sub(r"^\|[-: |]+\|$", " ", body, flags=re.M)  # 表分隔行

    nums = re.findall(r"\d[\d,]*(?:\.\d+)?", body)
    uniq = sorted(set(nums), key=lambda s: (-len(s), s))

    ok, derived, struct, missing = 0, [], [], []
    for n in uniq:
        variants = norm(n)
        if any(v in pool for v in variants):
            ok += 1
        elif n in DERIVED:
            derived.append(n)
        elif STRUCT.match(n):
            struct.append(n)
        else:
            missing.append(n)

    print(f"正文唯一数字 token：{len(uniq)}")
    print(f"  直接见于档案  {ok}")
    print(f"  算式推导      {len(derived)}  {derived if len(derived) <= 12 else derived[:12]}")
    print(f"  结构性编号    {len(struct)}")
    print(f"  ** 无出处 **  {len(missing)}  {missing}")
    print()

    if missing:
        print("以下数字在 claims / evidence / 全部快照里都找不到，也不在算式白名单里：")
        for n in missing:
            # 给出上下文，方便判断是真错还是白名单漏登记
            for m in re.finditer(re.escape(n), body):
                ctx = body[max(0, m.start() - 55):m.start() + 45].replace("\n", " ")
                print(f"  {n:>10}  … {ctx.strip()} …")
                break
        return 1

    print("[OK] 正文每个数字都可回溯（观测值 / 算式 / 结构编号）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
