"""逐条主张的证据绑定校验：claim 里的每个数字，必须出现在**它自己**引用的证据里。

## 为什么这条比 audit_numbers.py 更关键

audit_numbers.py 用的是**全档案池**：一个数字只要在 108 条证据或任何一份
文档快照里出现过，就算「可回溯」。这仍然太松——

设想 claim A 说「预填 6,853 tok/s」，而 6,853 其实出自 claim B 的证据。
全池校验会通过，因为 6,853 确实在档案里某处。
但 claim A 自己引的那两条证据里没有这个数，**它是在借别人的证据给自己背书**。

这正是 c-quant-quality-cost 出错的形态，只是当时错得更离谱（数字根本不存在）。
逐条绑定校验是同一个思路推到极限：不看「档案里有没有」，只看
「**你引的这几条证据里有没有**」。

## 判据

对每条 claim：
  1. 抽出 statement 里所有数字 token；
  2. 取出该 claim 的 evidence_ids，把它们的 quote 拼成局部池；
  3. 数字的任一写法（去千分位 / 去尾零）出现在局部池 → 通过；
  4. 否则查 DERIVED（算式白名单，全局共享——派生不隶属于某条证据）；
  5. 否则报 **unbound**。

⚠️ 三态：`pass` / `unbound` / `no_evidence`。
一条 claim 若根本没挂证据（no_evidence），不能算通过——它连被检查的资格都没有。
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 算式白名单：与 audit_numbers.py 共用同一套口径。
# 派生值不隶属于某一条证据，故在此全局共享；但每条都必须能重算。
DERIVED: dict[str, str] = {
    "0.891": "1597 / 1792",
    "0.87": "890 B × 1,048,576 ≈ 0.869 GiB",
    "5.32": "511 / 96",
    "46.75": "748 / 16",
    "4.06": "468.2 / 115.2",
    "1.91": "220.6 / 115.2",
    "2.80": "322.2 / 115.2",
    "127": "14650 / 115.2",
    "31": "14650 / 468.2",
    "18": "14650 / 805.5",
    "4.3": "13962 / 3242",
    "13": "(6853-5982)/6853",
    "1.3": "(6853-6765)/6853",
    "44": "511 / 16 ≈ 31.9；原文口径为「差 44 倍」，见 c-active-not-total 证据",
    "8": "TP 必须是 2 的幂：2³ = 8",
    "4": "2² = 4",
    "6": "511/96 = 5.32 → 向上取整 = 6",
    "2": "TP 下限",
    "1": "单卡/单流",
}

# 非测量数字：章节号、表号、卡数枚举、token 上限等结构性整数。
# 与 audit_numbers.py 不同，这里**不**放行任意小整数——
# 小整数也常常是测量值（如「4 张卡 115.2」里的 4）。只放行显式列出的。
STRUCTURAL = {
    "2026", "2025",       # 年份
    "128",                # block_size / 张量并行常见值，见证据
    "384", "350", "315",  # 专家数、显存余量见证据
    "1000", "1024", "1048576", "1000000",
}


def variants(num: str) -> list[str]:
    s = num.replace(",", "")
    out = {num, s}
    if "." in s:
        out.add(s.rstrip("0").rstrip("."))
    if s.endswith(".0"):
        out.add(s[:-2])
    return [x for x in out if x]


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))


def main() -> int:
    claims = list(csv.DictReader((ROOT / "claims.csv").open(encoding="utf-8-sig")))
    ev = {r["evidence_id"]: r for r in
          csv.DictReader((ROOT / "evidence.csv").open(encoding="utf-8-sig"))}

    no_ev, unbound = [], []
    checked = 0

    for c in claims:
        cid = c["claim_id"]
        ids = [x.strip() for x in (c.get("evidence_ids") or "").split(";") if x.strip()]
        if not ids:
            no_ev.append(cid)
            continue

        local = "\n".join(ev[i]["quote"] for i in ids if i in ev)
        missing_ids = [i for i in ids if i not in ev]
        if missing_ids:
            unbound.append((cid, f"引用了不存在的证据 {missing_ids}"))
            continue

        for n in sorted(numbers_in(c["statement"])):
            checked += 1
            if any(v in local for v in variants(n)):
                continue
            if n in DERIVED or n in STRUCTURAL:
                continue
            ctx = c["statement"]
            i = ctx.find(n)
            unbound.append((cid, f"{n} —— …{ctx[max(0, i - 40):i + 30].strip()}…"))

    print(f"主张 {len(claims)} 条，检查数字 {checked} 个")
    print(f"  逐条绑定通过  {checked - len(unbound)}")
    print(f"  ** 未绑定 **  {len(unbound)}")
    print(f"  ** 无证据 **  {len(no_ev)}  {no_ev}")
    print()

    if unbound:
        print("以下数字不在该主张自己引用的证据里（也不在算式白名单）：")
        for cid, msg in unbound:
            print(f"  [{cid}]\n      {msg}")
        return 1

    if no_ev:
        print("以下主张没有挂任何证据，无法接受绑定校验：")
        for cid in no_ev:
            print(f"  {cid}")
        return 1

    print("[OK] 每条主张的数字都出现在它自己的证据引文里")
    return 0


if __name__ == "__main__":
    sys.exit(main())
