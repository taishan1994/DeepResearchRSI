"""把全文证据并入归档：新增 evidence 与 claim，并改写受影响的结论。

## 本轮的实质发现

上一轮论文写了一句后来被证明是错的话：

    「没有任何工作报告『加了中间奖励之后，最终加速比是否真的提高』的对照实验。」

并把它列为「本方向最重要的空白」。

读全文后发现至少两篇做了这类对照：

1. `2510.17891` TritonRL
   表 3（Table 3）在 KernelBench Level 1 上消融 plan 奖励权重 α：
       α=0.0（禁用 plan 更新）  valid 98.0 | correct 37.0 | fast 3.0/1.0
       α=0.1（默认）            valid 99.0 | correct 56.0 | fast 5.0/1.0
   即：去掉层次化奖励中的 plan 部分，correct 从 56.0 掉到 37.0（-19 点）。
   正文原话：Ablation studies demonstrate that both robust reward design
            and hierarchical reward assignment are essential.

2. `2602.05885` Dr. Kernel
   图 2 明确对比 trained **without reward hacking check** 与
   **with hacking check enabled** 两个模型。数值在图中，文本层读不到，
   但对照本身存在，图注写明了设计。

## 因此要改的不是「补一句」，而是改结论

原来的第 5.3 节说「没有任何工作报告净效果」——这是错的。
正确说法应是：**有消融，但不报绝对加速比，只报 pass/fast 率**。
这个区别重要：pass 率的提升不等于用户感知的加速比提升。

## 证据纪律

新增证据的 quote 必须是**全文**的原文子串（E1 用 `-full.txt` 校验）。
故本脚本从 `documents/*-full.txt` 实取片段，不手写。
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
FETCHED = NOW.isoformat()
AS_OF = NOW.date().isoformat()


def full_text(aid: str) -> str:
    f = DOCS / f"doc-arxiv-{aid.replace('.', '-')}-full.txt"
    return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""


def read(name: str) -> tuple[list[dict], list[str]]:
    with (HERE / name).open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows, (list(rows[0].keys()) if rows else [])


def write(name: str, rows: list[dict], header: list[str]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    (HERE / name).write_text(buf.getvalue(), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- 新证据
NEW_EVIDENCE: list[dict] = []


def add_ev(aid: str, quote: str, note: str) -> str:
    """从全文里实取 quote，保证是原文子串。"""
    text = full_text(aid)
    if not text:
        print(f"  [!] {aid} 无全文")
        return ""
    if quote not in text:
        print(f"  [!] quote 不在 {aid} 全文中：{quote[:60]}")
        return ""
    eid = f"e-full-{len(NEW_EVIDENCE) + 1:02d}"
    NEW_EVIDENCE.append({
        "evidence_id": eid,
        "document_id": f"doc-arxiv-{aid.replace('.', '-')}",
        "source_id": f"src-arxiv-{aid.replace('.', '-')}",
        "quote": quote,
        "locator": "fulltext",
        "quote_type": "quote",
        "stance": "supports",
        "fetched_at": FETCHED,
        "note": note,
    })
    return eid


def main() -> int:
    print("从全文抽取证据…")

    # ---- TritonRL 的 α 消融 ----
    t = full_text("2510.17891")
    ev_alpha = ""
    # 表 3 的结论句
    m = re.search(
        r"Ablation studies demonstrate that both robust reward design and "
        r"hierarchical reward assignment are essential[^.]*\.", t)
    if m:
        ev_alpha = add_ev("2510.17891", m.group(0),
                          "TritonRL 明确声明消融证明奖励设计与层次化奖励分配"
                          "都是必需的——直接回应「中间奖励有无净效果」")

    ev_alpha_num = ""
    m = re.search(r"α \\alpha=0\.0 achieves[^.]*\.", t)
    if not m:
        m = re.search(
            r"setting α \\alpha=0\.0 , disabling plan updates, also degrades "
            r"results[^.]*\.", t)
    if m:
        ev_alpha_num = add_ev(
            "2510.17891", m.group(0),
            "α=0.0（禁用 plan 更新）会降低结果——去掉层次化奖励的对照")

    # 表 3 的对照数字（原文以 LaTeXML 的重复形式出现，取一行完整片段）
    ev_table = ""
    m = re.search(
        r"0\.0 0\.0 \| 98\.0 98\.0 \| 78\.0 78\.0 / 37\.0 37\.0 \| "
        r"3\.0 3\.0 / 1\.0 1\.0", t)
    if m:
        # 向前扩到本轮行的起点，形成可读片段
        s = max(0, m.start() - 120)
        frag = " ".join(t[s:m.end()].split())
        ev_table = add_ev("2510.17891", frag,
                          "表 3 中 α=0.0 的一行：correct 37.0")
    m2 = re.search(
        r"0\.1 0\.1 \( α\^\{?\*\}? \) \| 99\.0 99\.0 \| "
        r"82\.0 82\.0 / 56\.0 .*? \| 5\.0 \S+ / 1\.0 1\.0", t)
    ev_table2 = ""
    if m2:
        frag = " ".join(t[m2.start():m2.end()].split())
        ev_table2 = add_ev("2510.17891", frag,
                           "表 3 中 α=0.1（默认）的一行：correct 56.0，"
                           "比 α=0.0 高 19 点")

    # ---- Dr. Kernel 的 hacking check 对照 ----
    ev_dr_full = ""
    m = re.search(
        r"We report results from two models: Fast@1 of the model trained "
        r"without reward hacking check[^.]*\.", full_text("2602.05885"))
    if m:
        ev_dr_full = add_ev(
            "2602.05885", m.group(0),
            "Dr. Kernel 图 2 的对照组设计：有/无反作弊检查的两个模型")

    print(f"  新增 {len(NEW_EVIDENCE)} 条全文证据")

    # ---- 并入 evidence.csv ----
    ev_rows, ev_hdr = read("evidence.csv")
    existing = {r["evidence_id"] for r in ev_rows}
    for e in NEW_EVIDENCE:
        if e["evidence_id"] not in existing:
            ev_rows.append(e)
    write("evidence.csv", ev_rows, ev_hdr)

    # ---- 改写/新增主张 ----
    cl_rows, cl_hdr = read("claims.csv")
    by_id = {r["claim_id"]: r for r in cl_rows}

    new_claims = []

    # 1) 新主张：有消融，但报的是率不是加速比
    new_claims.append({
        "claim_id": "c-ablation-exists",
        "statement": "至少两篇核心工作做了奖励相关的消融对照：TritonRL 在 "
                     "KernelBench Level 1 上消融 plan 奖励权重 α（禁用后 "
                     "correct 从 56.0 降到 37.0，即 -19 个百分点），"
                     "Dr. Kernel 用「有/无 reward hacking check」两个模型做对照。"
                     "故「该方向无人报告中间奖励的净效果」这一判断不成立。",
        "claim_type": "measurement",
        "as_of": AS_OF,
        "confidence": "high",
        "evidence_ids": ";".join(x for x in
                                 [ev_alpha, ev_alpha_num, ev_table,
                                  ev_table2, ev_dr_full] if x),
        "counter_evidence_ids": "",
        "derivation": "TritonRL 表 3：α=0.0 时 correct=37.0，α=0.1 时 correct=56.0，"
                      "差值 19.0 个百分点。数字取自全文的表格行，"
                      "非摘要层可得。",
        "notes": "本条修正上一轮的结论，见 PAPER.md 第 5.3 节与第 6 节",
    })

    # 2) 质量修正：消融报告的指标是 pass/fast 率，不是绝对加速比
    new_claims.append({
        "claim_id": "c-ablation-metric-gap",
        "statement": "已发表的奖励消融报告的是 pass@k 与 fast@k 这类**比率**，"
                     "而非相对基线的绝对加速比。比率提升与用户感知的端到端加速"
                     "之间还差一步换算，这一步目前无人做。",
        "claim_type": "spec",
        "as_of": AS_OF,
        "confidence": "medium",
        "evidence_ids": ";".join(x for x in [ev_table, ev_table2] if x),
        "counter_evidence_ids": "",
        "derivation": "TritonRL 表 3 的列为 valid / compiled / correct / "
                      "fast1 / fast2，全为百分比通过率，无 ms 或相对 cuBLAS 的倍数。",
        "notes": "这是比「无人做消融」更准确、也更有限制的批评",
    })

    for c in new_claims:
        if c["claim_id"] not in by_id:
            cl_rows.append(c)
            print(f"  + 新主张 {c['claim_id']}")

    # 3) 修正旧主张：把「无人报净效果」改成准确表述
    target = by_id.get("c-grpo-default-but-flawed")
    if target:
        note = target.get("notes") or ""
        if "消融" not in note:
            target["notes"] = (note + "｜注：第 5.3 节原称「无人报告中间奖励的净效果」，"
                               "读全文后已修正——有消融，但只报通过率不报绝对加速比，"
                               "见 c-ablation-exists 与 c-ablation-metric-gap。").strip("｜")

    write("claims.csv", cl_rows, cl_hdr)

    print(f"\nevidence {len(ev_rows)} 条、claims {len(cl_rows)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
