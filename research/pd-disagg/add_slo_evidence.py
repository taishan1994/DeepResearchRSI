"""补第 8 轮：按 SLO 类型重切，找方向相反的技巧。

## 为什么这是下一个维度

前两轮已经换过两次维度：成本链（四类）、实现平面（三平面）。
这一轮换第三次：按 **SLO 类型**。它之所以必要，是因为同一个技巧
在不同 SLO 下会**方向相反**——这比"某个技巧好不好"更根本。

## 三个层次的反向证据

### 1）机制层：一个旋钮、两个 SLO（Sarathi-Serve）

原文："The token budget is determined based on two competing factors —
TBT SLO requirement and chunked-prefills overhead. From a TBT
minimization point of view, a smaller token budget is preferable...
However, smaller token budget can result in excessive chunking"。

即：token budget 调小 -> TBT 变好、吞吐变差；调大则相反。
这不是"参数有 tradeoff"，是**两个 SLO 被同一个旋钮反向拉扯**。

### 2）陈述层：优先谁就牺牲谁

原文："prioritizing prefills improves TTFT latency whereas prioritizing
decodes has the opposite effect"。这句话是反向性的直接陈述。

### 3）参数层：不同应用的 SLO 配比完全不同（DistServe Table 1）

  Chatbot OPT-175B        TTFT 4.0s    TPOT 0.2s
  Code Completion OPT-66B TTFT 0.125s  TPOT 0.2s
  Summarization OPT-66B   TTFT 15s     TPOT 0.15s

TTFT 跨 120 倍（0.125s vs 15s），而 TPOT 几乎不变（0.1-0.2s）。
说明**真正决定配置的不是"SLO 严不严"，是"两个 SLO 的相对松紧"**。

## 证据怎么取

全部用 anchor + find 切片，不手抄。表头那行包含 Application|Model|
Size|TTFT|TPOT|Dataset，取完整表头才能证明列的含义——
上一轮差点因为表头缺失而猜错列。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

# (eid, doc, anchor, span, dim, note)
SPECS = [
    ("e-079", "doc-arxiv-2403-02310",
     "The token budget is determined based on two competing factors",
     700, "t-slo",
     "一个旋钮两个 SLO：token budget 调小则 TBT 好、吞吐差；调大则相反"),

    ("e-080", "doc-arxiv-2403-02310",
     "However, prioritizing prefills leads to high latency", 360,
     "t-slo",
     "反向性陈述：优先 prefill 会让已在跑的 decode 停等，故延迟变高；"
     "反之优先 decode 则压住 prefill。这是同一个调度旋钮的两端"),

    ("e-081", "doc-arxiv-2403-02310",
     "Sarathi-Serve enables low TBT latency and high throughput at the "
     "expense of a marginal increase in TTFT", 380, "t-slo",
     "chunked prefill 以 TTFT 微增换 TBT 低与吞吐高；权衡由 chunk size 控制"),

    ("e-082", "doc-arxiv-2403-02310",
     "if a prefill sequence is split into", 420, "t-slo",
     "chunk 切细的代价机制：第一个 chunk 的 KV 被加载 N-1 次，"
     "第二个 N-2 次（HBM 重复读）"),

    ("e-083", "doc-arxiv-2401-09670",
     "Application | Model Size | TTFT | TPOT | Dataset", 420, "t-slo",
     "DistServe 的三组应用配置：Chatbot TTFT 4.0s/TPOT 0.2s、"
     "Code Completion 0.125s/0.2s、Summarization 15s/0.15s"),

    ("e-084", "doc-arxiv-2401-09670",
     "document summarization emphasizes low TPOT", 460, "t-slo",
     "同一系统下两类应用的偏好相反：摘要强调低 TPOT，"
     "而 goodput 要在 SLO 达成率（如 90%）下取最大请求率"),

    ("e-085", "doc-arxiv-2401-09670",
     "DistServe can sustain", 420, "t-slo",
     "同一套分离系统的收益随应用变化：代码补全 3.2x 请求率 + 1.5x 更严 SLO；"
     "聊天 1.4x-1.8x 更严 SLO"),
]


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()
    ep = HERE / "evidence.csv"
    rows = list(csv.DictReader(ep.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    have = {r["evidence_id"] for r in rows}
    docs = {r["document_id"]: (r["snapshot"], r["source_id"])
            for r in csv.DictReader(
                (HERE / "documents.csv").open(encoding="utf-8", newline=""))}
    added = 0
    for eid, did, anchor, span, dim, note in SPECS:
        if eid in have:
            print(f"  {eid} 已存在")
            continue
        snap, sid = docs[did]
        text = " ".join((HERE / snap).read_text(
            encoding="utf-8", errors="replace").split())
        i = text.find(" ".join(anchor.split()))
        if i < 0:
            print(f"  [!] {eid} 锚点未找到: {anchor[:44]}")
            continue
        row = {k: "" for k in fields}
        row.update({
            "evidence_id": eid, "document_id": did, "source_id": sid,
            "quote": text[i:i + span].strip(),
            "locator": f"doc#{dim}", "quote_type": "quote",
            "stance": "supports", "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        rows.append(row)
        added += 1
        print(f"  + {eid} [{dim}] {note[:50]}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    ep.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"\nevidence.csv: {len(rows)}（新增 {added}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
