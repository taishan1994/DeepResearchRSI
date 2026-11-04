"""扩充证据：用新抓到的 8 篇全文把五个维度补厚。

## 为什么要扩

第一版只有 18 条证据，其中评测维度（q5）仅 3 条，且没有一条来自
KernelBench 原文——而它是整个方向的评测基座。原因很简单：
抓全文时只抓了 core，adjacent 全缺。

补齐 adjacent 后（34/35 篇有全文），可以引用到：
  - KernelBench 的 fast_p 指标定义（评测口径的源头）
  - CUDAHercules 的硬件感知专家级判定
  - LEAP / 多轮 RL 的预算与剪枝论述
  - MusaCoder / FM Agent 的智能体结构

## 纪律不变

quote 用 grab() 从全文实取，且经 _ok() 过滤题名与作者区。
新增证据全部标 dim，便于按维度聚合。
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import build_agent as B

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)


def main() -> int:
    # 复用 build_agent 的 grab（它依赖模块级 EVIDENCE / FAILS / _TITLES）
    inc = B.json.loads((HERE / "included_agent.json").read_text(encoding="utf-8"))
    B._TITLES = {c["arxiv_id"]: c["title"]
                 for t in ("core", "adjacent") for c in inc[t]}

    with (HERE / "evidence.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = list(rows[0].keys())
    have = {r["evidence_id"] for r in rows}
    B.EVIDENCE = rows          # 让 grab 接着编号
    B.FAILS = []

    new: list[str] = []

    # ---- q1 观测：KernelBench 的评测口径、CUDAHercules 的硬件感知 ----
    new.append(B.grab("2502.10517", [
        r"[A-Z][^.]{20,180}fast\s*p\b[^.]{0,160}\.",
        r"[A-Z][^.]{20,160}(?:correctness|performance)\s+(?:check|verif)\w*[^.]{0,160}\.",
    ], "observe", "KernelBench：fast_p 把「正确且加速」定义为一个共同判据"))

    new.append(B.grab("2605.08467", [
        r"[A-Z][^.]{20,180}hardware[- ]aware[^.]{0,180}\.",
        r"[A-Z][^.]{20,160}expert[- ]level[^.]{0,160}\.",
    ], "observe", "CUDAHercules：专家级判定需要硬件感知信号"))

    # ---- q2 动作空间：FM Agent / MusaCoder 的结构 ----
    new.append(B.grab("2510.26144", [
        r"[A-Z][^.]{20,180}multi[- ]agent[^.]{0,180}\.",
        r"[A-Z][^.]{20,160}(?:task decomposition|decompos\w+)[^.]{0,160}\.",
    ], "act", "FM Agent：多智能体的角色分工"))

    new.append(B.grab("2606.04847", [
        r"[A-Z][^.]{20,180}(?:full-stack|real hardware)[^.]{0,160}\.",
    ], "act", "MusaCoder：全栈训练与真实硬件执行"))

    # ---- q3 预算：LEAP 的剪枝成本、多轮 RL 的开销 ----
    new.append(B.grab("2608.01804", [
        r"[A-Z][^.]{20,180}(?:rollout|iteration)s?\b[^.]{0,60}(?:cost|expensive|slow)\w*[^.]{0,140}\.",
        r"[A-Z][^.]{20,160}prun\w+[^.]{0,160}\.",
    ], "budget", "LEAP：多轮 rollout 的执行开销"))

    new.append(B.grab("2607.20908", [
        r"[A-Z][^.]{20,180}(?:multi[- ]turn|turns?)\b[^.]{0,160}\.",
    ], "budget", "多轮 RL：turn 数是训练与推理的共同预算单位"))

    new.append(B.grab("2610.23950", [
        r"[A-Z][^.]{20,180}(?:context|compaction|long[- ]horizon)[^.]{0,160}\.",
    ], "budget", "Compaction：长程运行时上下文本身成为约束"))

    # ---- q4 恢复：KernelFoundry / 演化式做法的失败处理 ----
    new.append(B.grab("2603.12440", [
        r"[A-Z][^.]{20,180}(?:fail|invalid|error)\w*[^.]{0,160}\.",
    ], "recover", "KernelFoundry：演化过程中失败样本的处理"))

    new.append(B.grab("2609.04523", [
        r"[A-Z][^.]{20,180}(?:retry|retries|recover|fallback)\w*[^.]{0,160}\.",
    ], "recover", "MaxKernel：重试与回退"))

    # ---- q5 评测：benchmark 的结构性批评 ----
    new.append(B.grab("2605.04956", [
        r"[A-Z][^.]{20,200}(?:benchmark|evaluat)\w*[^.]{0,200}\.",
    ], "eval", "KernelBenchX：对现有评测覆盖面的质疑"))

    new.append(B.grab("2608.25124", [
        r"[A-Z][^.]{20,180}(?:wafer[- ]scale|translat\w+)[^.]{0,160}\.",
    ], "eval", "FABRICA：跨平台迁移带来的评测口径问题"))

    # 去重后写回
    added = [r for r in B.EVIDENCE[len(rows):] if r["evidence_id"] not in have]
    seen = set()
    uniq = []
    for r in added:
        if r["evidence_id"] in seen:
            continue
        seen.add(r["evidence_id"])
        uniq.append(r)

    # 重新编号，避免与已有冲突
    start = len(rows)
    for k, r in enumerate(uniq, 1):
        r["evidence_id"] = f"e-{start + k:03d}"

    rows.extend(uniq)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    (HERE / "evidence.csv").write_text(buf.getvalue(), encoding="utf-8",
                                       newline="\n")

    print(f"新增 {len(uniq)} 条，evidence 共 {len(rows)} 条")
    for r in uniq:
        print(f"  {r['evidence_id']} {r['note'][:46]}")
        print(f"        {r['quote'][:96]}")
    if B.FAILS:
        print("\n[!] 未取到：")
        for f in B.FAILS:
            print("   ", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
