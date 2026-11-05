"""新增主张 c-technique：优化技巧按作用对象分层。

## 为什么要新开一条主张

用户指出第 1 轮缺的是「优化技巧」这一层（lplb / waterfill / tbo /
dspark 只是例子）。这不是「补几个名词」的问题，而是缺了一整套
分析框架——读者需要知道有哪些技巧、按什么维度分类、
哪些可以叠加、哪些互相替代。

故新开 c-technique 承载这个框架，并把关键数字写进 statement
（判据 C 要求 data/*.csv 的每个值能在对应 claim 里逐字找到）。

## 分层依据

按**技巧作用于哪个环节**分四类，这是从证据里归纳出来的，
不是套用现成分类：

  A 省传输量     作用于 KV 字节数本身
  B 让传输不可见  作用于传输与计算的时序关系
  C 均衡负载     作用于每个 rank/实例分到多少工作
  D 省 decode 步  作用于要跑多少步 decode

关键性质：**同类互相替代，异类可以叠加**。
这一条是实用价值最高的，因为它直接回答「该上哪几个」。

## 一个必须点出的交互

PD 分离与这些技巧不是并列关系。以 LPLB 为例：DP attention 下
不同 EP rank 在同一步跑不同 forward 模式（prefill / decode / idle），
没有单个 rank 看得到全局 token 分布——这是 PD 带来的**新约束**，
均衡类技巧必须专门处理它（证据 e-051）。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

CLAIM = {
    "claim_id": "c-technique",
    "statement": (
        "PD 分离的优化技巧按作用对象分四类：省传输量（逐层传输、"
        "chunk 级传输、KV 压缩与量化、前缀缓存）、让传输不可见"
        "（TBO、SBO、DBO、piggyback）、均衡负载（Waterfill、LPLB、"
        "EPLB、请求迁移、弹性配比）、省 decode 步（DSpark 自适应验证、"
        "投机解码）。同类技巧互相替代，异类技巧可以叠加，故取舍问题不是"
        "「选哪个」而是「每类选一个」。各类的实测幅度差一到两个数量级："
        "Waterfill 在 DeepSeek-V3/R1 上把吞吐提升 1.48% 至 4.66%，"
        "LPLB 在有冗余副本时提升 0.84% 至 7.34%，而 DSpark 的自适应验证"
        "让投机解码在并发 1 到 256 全程停留在 Pareto 前沿。"
        "技巧都有前置依赖与适用下限：LPLB 在无冗余副本（red0）时只有"
        "开销没有收益；逐层传输在小 prompt 上因固定同步开销反而不值得；"
        "DBO 在 token 数低于阈值时不拆分。PD 分离给均衡类技巧带来一个新约束："
        "DP attention 下不同 EP rank 在同一步跑不同 forward 模式"
        "（prefill、decode 或 idle），没有单个 rank 看得到全局 token 分布，"
        "故均衡算法需要一个额外的 all-reduce 才能拿到全局视图。"
    ),
    "claim_type": "synthesis",
    "as_of": "2026-11-04",
    "confidence": "high",
    "evidence_ids": ";".join(f"e-{i:03d}" for i in range(41, 59)),
    "counter_evidence_ids": "",
    "derivation": "把 18 条技巧层证据按「作用对象」归纳为四类；"
                  "每类的实测幅度直接取原文报告值。",
    "notes": "第 3 轮新增。用户指出第 1 轮缺优化技巧这一层，"
             "故补此框架。举例的 lplb/waterfill/tbo/dspark 分别落在"
             "均衡、均衡、让传输不可见、省 decode 步四类里。",
}


def main() -> int:
    p = HERE / "claims.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    if any(r["claim_id"] == CLAIM["claim_id"] for r in rows):
        print("c-technique 已存在")
        return 0

    row = {k: "" for k in fields}
    for k, v in CLAIM.items():
        if k in fields:
            row[k] = v
    rows.append(row)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"claims.csv: {len(rows)} 条")
    print(f"  c-technique 引用 {len(CLAIM['evidence_ids'].split(';'))} 条证据")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
