"""给 §8 补三小节：数据通路层、准入与拒绝、并行度重切分。

## 为什么还要补

第一版 §8 按「省传输量 / 让传输不可见 / 均衡负载 / 省 decode 步」
分了四类，但漏掉三类同样属于优化技巧的东西：

  1. 数据通路层      zero-copy、GPUDirect RDMA、内存语义传输
                     —— 不是少传，而是让传输本身更便宜
  2. 准入与拒绝      预测式 early rejection、准入控制
                     —— 负载超过容量时不排队，直接拒
  3. 并行度重切分    运行中改 DP/TP/PP 布局并 reshard 权重与 KV
                     —— 比弹性改 P:D 比更激进的一层

这三类都在语料里，且都有实测数字。漏掉它们会让「技巧」这一层
看起来只覆盖算法侧，不覆盖数据通路与策略侧。

## 新证据的三处实测

  · Mooncake early rejection：模拟场景吞吐最高 +525%，真实负载
    多处理 75% 请求
  · 并行度重切分：rollout makespan 528.8s -> 259.1s，decode 吞吐 2.04x
  · CloudMatrix384：zero-copy 版本让 send/recv kernel 直接操作应用数据区

## 插入位置

放在「怎么选」之前，作为四类之后的补充三小节。
不放最前面，因为它们依赖前四类的概念（传输成本、EP 等）。
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

# ---- 追加证据 ----
SPECS = [
    ("e-059", "doc-arxiv-2508-02520",
     "We also have a zero-copy version in which the send and recv kernel",
     460, "t-path",
     "CloudMatrix384：zero-copy 版本让 send/recv kernel 直接操作应用数据区，"
     "省掉一次中间拷贝"),

    ("e-060", "doc-arxiv-2407-00079",
     "The transfer of these KVCache blocks across CPUs and GPUs is handled",
     440, "t-path",
     "Mooncake：KV 块跨 CPU/GPU 的搬移由独立的 GPUDirect RDMA 组件 "
     "Messenger 承担"),

    ("e-061", "doc-arxiv-2407-00079",
     "we developed a prediction-based early rejection policy", 520,
     "t-admit",
     "Mooncake：预测式 early rejection；模拟场景吞吐最高 +525%，"
     "真实负载多处理 75% 请求"),

    ("e-062", "doc-arxiv-2605-21312",
     "begins with Layout A and switches to Layout B", 620, "t-reshape",
     "运行中重切并行度：rollout makespan 528.8s -> 259.1s，"
     "decode 吞吐 2.04x，代价是权重 reshard 与 KV 重算"),
]

NEW_SECTION = r"""
\subsection{补充三类：数据通路、准入、并行度重切分}

上面四类是按「作用于哪个环节」分的。还有三类技巧不落在这四类里，
但都是 PD 部署上实际在用的，且各有独立的量级。

\noindent\textbf{① 数据通路层：不是少传，而是让每次传输更便宜。}

最典型的是 \textbf{zero-copy}：让发送/接收 kernel 直接操作应用的数据区，
省掉中间那一次拷贝\texttt{[c-technique]}。在 CloudMatrix384 的
send/recv 设计里，除了基于内存语义（MTE2/MTE3）的传输路径，
还专门提供 zero-copy 版本\texttt{[c-technique]}。

\noindent 与之配套的是 \textbf{GPUDirect RDMA}：让网卡直接读写显存，
绕过主机内存。Mooncake 把 KV 块在 CPU 与 GPU 之间的搬移交给一个
独立的 GPUDirect RDMA 组件（Messenger）\texttt{[c-technique]}。

\noindent 这一类的收益不在「传得少」，而在\textbf{把传输从「要经过
CPU 与两次拷贝」变成「网卡直接进显存」}。它与 A 类正交，可以叠加。

\noindent\textbf{② 准入与拒绝：容量不够时不排队，直接拒。}

这条在过载场景下最重要，也最常被忽略。传统研究假设所有请求都会被处理，
但真实的高负载场景下，\textbf{把注定超时的请求排进队列只会拖垮其它请求}。

\noindent Mooncake 的做法是\textbf{预测式 early rejection}：先预测这条
请求能否在 SLO 内完成，不能就早拒\texttt{[c-technique]}。效果：在
某些模拟场景下吞吐最高提升 \textbf{525\%} 且仍满足 SLO；在真实负载下
让 Kimi 多处理 \textbf{75\%} 的请求\texttt{[c-technique]}。

\noindent 这是本文所引技巧里\textbf{幅度最大的一条}，但它提升的不是
「单位时间算得更多」，而是「单位时间算的都是有用的」。二者在过载时
差别巨大。

\noindent 这也解释了为什么它属于 PD 的优化技巧：分离之后 P 与 D 的
队列是独立的，一条请求要过两个池子，\textbf{任一池子超时都白做}，
故准入判断必须放在分离之前，且要同时考虑两段的排队时间。

\noindent\textbf{③ 并行度重切分：运行中改 DP/TP/PP 布局。}

比「弹性改 P:D 比」更激进的一层——不只改两阶段的比例，而是改
\textbf{每个阶段内部的并行方式}，并为此重新切分权重与重算 KV。

\noindent 有一个完整的实测：某系统以 Layout A 起步，当活跃轨迹数降到
批量的 10\% 以下时切到 Layout B（DP=8、PP=16、TP=8），
切换要付一次\textbf{权重 reshard 与 KV 重物化}的代价
\texttt{[c-technique]}。收益：rollout makespan 从 528.8\,s 降到
259.1\,s，有效 decode 吞吐提升 2.04 倍\texttt{[c-technique]}。

\noindent 原文把这归因为「相位匹配的并行度」：Layout A 吸收密集突发，
而重新切分让稀疏尾部的 decode 效率回升\texttt{[c-technique]}。

\noindent 这一类的取舍很清晰：\textbf{重切分有一次性成本，
故只在相位持续足够久时才划算}。这与第 \ref{sec:boundary} 节的
「窗口」是同一个道理——收益要摊得平固定成本。

\subsection{怎么选：三条判据}"""


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0).isoformat()

    # ---- 证据 ----
    ep = HERE / "evidence.csv"
    erows = list(csv.DictReader(ep.open(encoding="utf-8", newline="")))
    ef = list(erows[0].keys())
    have = {r["evidence_id"] for r in erows}
    docs = {r["document_id"]: r["snapshot"] for r in csv.DictReader(
        (HERE / "documents.csv").open(encoding="utf-8", newline=""))}
    added = 0
    for eid, did, anchor, span, dim, note in SPECS:
        if eid in have:
            print(f"  {eid} 已存在")
            continue
        p = HERE / docs[did]
        text = " ".join(p.read_text(encoding="utf-8",
                                    errors="replace").split())
        i = text.find(" ".join(anchor.split()))
        if i < 0:
            print(f"  [!] {eid} 锚点未找到: {anchor[:40]}")
            continue
        row = {k: "" for k in ef}
        row.update({
            "evidence_id": eid, "document_id": did,
            "source_id": [r for r in csv.DictReader(
                (HERE / "documents.csv").open(encoding="utf-8",
                                              newline=""))
                if r["document_id"] == did][0]["source_id"],
            "quote": text[i:i + span].strip(),
            "locator": f"doc#{dim}", "quote_type": "quote",
            "stance": "supports", "fetched_at": now,
            "note": f"[{dim}] {note}",
        })
        erows.append(row)
        added += 1
        print(f"  + {eid} [{dim}] {note[:46]}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ef, lineterminator="\n")
    w.writeheader()
    w.writerows(erows)
    ep.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"evidence.csv: {len(erows)} 条（新增 {added}）")

    # ---- 把新证据挂到 c-technique ----
    cp = HERE / "claims.csv"
    crows = list(csv.DictReader(cp.open(encoding="utf-8", newline="")))
    cf = list(crows[0].keys())
    for r in crows:
        if r["claim_id"] != "c-technique":
            continue
        ids = [x for x in r["evidence_ids"].split(";") if x]
        for eid, *_ in SPECS:
            if eid not in ids:
                ids.append(eid)
        r["evidence_ids"] = ";".join(ids)
        print(f"  c-technique 现引用 {len(ids)} 条证据")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cf, lineterminator="\n")
    w.writeheader()
    w.writerows(crows)
    cp.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    # ---- 插入小节 ----
    sec = HERE / "paper" / "sec8_technique.tex"
    s = sec.read_text(encoding="utf-8")
    if "补充三类" in s:
        print("补充小节已存在")
        return 0
    marker = r"\subsection{怎么选：三条判据}"
    i = s.find(marker)
    if i < 0:
        print("[!] 找不到插入锚点")
        return 1
    s = s[:i] + NEW_SECTION.strip() + s[i + len(marker):]
    sec.write_text(s, encoding="utf-8", newline="\n")
    print(f"sec8_technique.tex {len(s):,} 字符")
    for probe in ("zero-copy", "GPUDirect", "525", "528.8", "2.04"):
        print(f"  含 {probe:<12} {s.count(probe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
