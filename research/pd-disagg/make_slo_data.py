"""登记 tab7（SLO 配置表）与 slo.csv 数据。

## 为什么 tab7 值得单独一张表

它是本节最硬的证据：三组应用、同一套系统、TTFT 跨 120 倍而 TPOT
几乎不变。这张表比任何叙述都能说明「决定配置的是两个 SLO 的相对松紧」。

## 数据来源纪律

全部取自 DistServe 的 Table 1 原文：
  Chatbot OPT-175B        TTFT 4.0s   TPOT 0.2s
  Code Completion OPT-66B TTFT 0.125s TPOT 0.2s
  Summarization OPT-66B   TTFT 15s    TPOT 0.15s

Chatbot 还有 OPT-13B（0.2s/0.1s）与 OPT-66B（0.4s/0.1s）两行，
这里只列 175B 那一行——三组应用各列一行更好读，且 175B 的
4.0s 最能体现「TTFT 宽松」。

## 120 倍怎么来的

15 / 0.125 = 120。这是**我算的**，不是原文写的。故在 note 里标明
「派生」，并在 DERIVED.md 里记录算式。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"
TABLES = HERE / "paper" / "tables"

SLO_ROWS = [
    ["Chatbot OPT-175B", "4.0", "0.2", "TTFT 宽松、TPOT 严"],
    ["Code Completion OPT-66B", "0.125", "0.2", "TTFT 极严"],
    ["Summarization OPT-66B", "15", "0.15", "TTFT 极宽松、TPOT 最严"],
]

NUM_ROWS = [
    ["chatbot_ttft", "4.0", "s", "c-slo", "Chatbot OPT-175B 的 TTFT（e-083）"],
    ["chatbot_tpot", "0.2", "s", "c-slo", "Chatbot OPT-175B 的 TPOT（e-083）"],
    ["code_ttft", "0.125", "s", "c-slo",
     "Code Completion OPT-66B 的 TTFT（e-083）"],
    ["code_tpot", "0.2", "s", "c-slo",
     "Code Completion OPT-66B 的 TPOT（e-083）"],
    ["summ_ttft", "15", "s", "c-slo",
     "Summarization OPT-66B 的 TTFT（e-083）"],
    ["summ_tpot", "0.15", "s", "c-slo",
     "Summarization OPT-66B 的 TPOT（e-083）"],
    ["ttft_span", "120", "x", "c-slo",
     "TTFT 跨度：15 / 0.125（派生值，见 DERIVED.md）"],
    ["code_rate_gain", "3.2", "x", "c-slo",
     "代码补全的请求率提升（e-085）"],
    ["code_slo_tighter", "1.5", "x", "c-slo",
     "代码补全同时收紧的 SLO 倍数（e-085）"],
    ["chat_slo_lo", "1.4", "x", "c-slo", "聊天的 SLO 收紧下界（e-085）"],
    ["chat_slo_hi", "1.8", "x", "c-slo", "聊天的 SLO 收紧上界（e-085）"],
    ["goodput_attainment", "90", "%", "c-slo",
     "goodput 的 SLO 达成率目标（e-084）"],
]


def write_csv(name: str, header: list[str], rows: list[list[str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    (TABLES / name).write_text(buf.getvalue(), encoding="utf-8",
                               newline="\n")
    print(f"  {name:<24} {len(rows)} 行")


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    write_csv("tab7_slo.csv", ["应用", "TTFT(s)", "TPOT(s)", "特征"],
              SLO_ROWS)

    p = DATA / "slo.csv"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["metric", "value", "unit", "cite", "note"])
    w.writerows(NUM_ROWS)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"  slo.csv {len(NUM_ROWS)} 行")

    # 自查：每个值都在 c-slo 里
    claims = {r["claim_id"]: r["statement"] for r in csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline=""))}
    bad = 0
    for r in NUM_ROWS:
        if r[1] not in claims.get(r[3], ""):
            print(f"  [!] {r[0]}={r[1]} 不在 {r[3]}")
            bad += 1
    print(f"自查：{bad} 个无法回溯")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
