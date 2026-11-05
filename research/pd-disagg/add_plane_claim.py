"""新增主张 c-plane：四类之外的实现平面维度。

## 为什么需要单独一条主张

第 8 节的 c-technique 承载「四类技巧」。本节的发现是：
四类只覆盖了「分离带来的额外成本」，而实现平面还有数据面 /
执行面 / 控制面三层，其中至少五个维度不落在四类里。

这两件事的置信度与依据来源不同（前者主要来自论文，
后者主要来自 2026 年的框架工程博客），分开记便于读者判断。

## 必须写进 statement 的数字

判据 C 要求 data/*.csv 的每个值能在对应 claim 里逐字找到。
本节引用的关键数字：
  2200 / 1500  H200 吞吐提升
  2.65         PCP8 vs TP8 的 prefill 加速
  93 / 2.3     token 上限带来的 TPGS 与 P90 交互性
  13           kernel 融合的每层延迟降幅
  5            latent-tail MoE 融合的端到端降幅
  3 / 31       长上下文 indexer 的延迟改善区间
  92           DeepSeek V4 早期布局的碎片化 tensor 数
  10           FP4 indexer 省下的 KV 显存比例
  512          长 prefill 的 token 阈值

## 三个反例的措辞

反例比正面技巧更有信息量，但容易被写成「某团队失败了」。
改成「某策略在特定条件下不成立」，并写清条件——
这样它才是可复用的判据。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLAIM = {
    "claim_id": "c-plane",
    "statement": (
        "第 8 节的四类技巧按「作用于 KV 传输成本的哪个环节」划分，"
        "覆盖分离引入的额外成本，但不覆盖整个优化栈。按实现平面可分成"
        "数据面、执行面、控制面三层，其中五个维度不落在四类里："
        "（1）算子融合等 kernel 改进——vLLM 把每 H200 吞吐从约 1500 "
        "提到 2200 tok/s，六项关键优化与 KV 传输无关；对称内存加 "
        "kernel 内融合使每层延迟降约 13%，latent-tail MoE 融合降端到端"
        "约 5%，长上下文 indexer 在 GB300 上改善约 3% 至 31%。"
        "（2）并行策略选择——DeepSeek V4 在 32K prompt 上 PCP8 相对 "
        "TP8 有 2.65 倍 prefill 加速。（3）KV 池分层与打包布局——"
        "DeepSeek V4 早期布局碎成 92 个独立 tensor，打包后减少描述符与"
        "P/D 传输开销，开 FP4 indexer 时省约 10% 的 KV 显存。"
        "（4）调度顺序——给单条请求每步可调度 token 数设上限（如 512 "
        "token），在 B300 上跑 DeepSeek V4 Pro 使每 GPU 每秒总 token 数"
        "提升最多 93%、P90 交互性约 2.3 倍，代价是长请求自身的 TTFT 变高。"
        "（5）路由策略。"
        "三个反例界定了这些手段的适用条件：流水线并行不适合热轮次"
        "（前缀已缓存、新增 token 太少，流水线 bubble 吃掉收益）；"
        "decode 上下文并行对 DeepSeek V4 只打平 DEP 而未超过，"
        "因为其压缩稀疏注意力含 indexer、compressor 与主注意力三层，"
        "并行必须跟随模型架构；按队列深度或 KV 利用率做均衡，"
        "全部劣于 session 粘性路由——迁移要取 KV，预取的块临时占用"
        "目标 rank 的 KV 容量，导致队列更均衡但并发更少。"
    ),
    "claim_type": "synthesis",
    "as_of": "2026-11-05",
    "confidence": "high",
    "evidence_ids": ";".join(f"e-{i:03d}" for i in range(63, 79)),
    "counter_evidence_ids": "",
    "derivation": "把三份 2026 年框架工程博客/文档里与 KV 传输无关的"
                  "优化项按实现平面归为三层；三个反例取自原文的"
                  "「bitter lessons」小节。",
    "notes": "第 4 轮新增。触发点：用户问「除 ABCD 四类还有其它的吗」。"
             "结论是四类不完备但不错误，故保留并补三平面作为上位框架。",
}


def main() -> int:
    p = HERE / "claims.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    if any(r["claim_id"] == CLAIM["claim_id"] for r in rows):
        print("c-plane 已存在")
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
    print(f"  c-plane 引用 {len(CLAIM['evidence_ids'].split(';'))} 条证据")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
