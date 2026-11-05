"""新增主张 c-load 并接入正文。

## 命题

负载形态是决策的输入，不是决策维度。它可以取消一整类技巧的
用武之地，而 SLO 只能翻转方向。

## 必须进 statement 的数字

  610 / 33    trace 数与中位轮数
  94.2        缓存命中率（%）
  131         输入输出比
  2242        每轮上下文增长（token）
  12 / 80     轨迹上下文起止（K token）
  5.2 / 81.4  轮间隔中位与 P99（秒）
  100 / 3.8   长上下文的 GB 数
  256         offload 粒度
  95.4 / 99.5 CXL 研究的外部命中率区间
  5.5 / 36.6  TTFT 降幅区间
  1 / 4       sharing gap
  3.8 / 46 / 8.6  Mooncake 集成的三项提升

## 纪律

三个来源的幅度基线不同，statement 里必须分别写清基线，
否则读者会把它们当成同一件事的三次测量。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLAIM = {
    "claim_id": "c-load",
    "statement": (
        "负载形态是优化决策的输入而非决策维度：它能取消一整类技巧的"
        "用武之地，而 SLO 形状只能翻转技巧的方向。真实 agentic 负载的"
        "统计（Codex/SWE-bench Pro 的 610 条 trace，中位每条 33 轮）显示："
        "缓存命中率 94.2%，输入输出比 131:1，每轮上下文增长约 2242 token，"
        "中位轨迹从 12K 涨到 80K，轮间隔中位数 5.2 秒、P99 为 81.4 秒。"
        "94.2% 的命中率把「省传输量」类与「隐藏传输」类技巧的收益空间"
        "压缩到剩余几个百分点；131:1 的输入输出比使 prefill 与 decode 的"
        "计算量完全不成比例，P:D 实例比极端倾斜。"
        "负载形态还决定传输是否发生：一个 100K token 上下文的 FP8 KV cache "
        "约 3.8 GB，繁忙实例服务多个长会话时会撑满本地容量并触发驱逐；"
        "为均衡负载而把会话迁到别的实例，该实例从未见过前缀、必须从头重算。"
        "故「该不该做会话粘性路由」没有独立答案，它是轮间隔与缓存容量的"
        "函数——轮间隔中位数仅 5.2 秒时前缀大概率仍在原实例上。"
        "命中率本身可能是假象：vLLM 的 KV 块按内容哈希寻址，哈希链默认用 "
        "os.urandom() 按进程播种，两个引擎对相同 token 算出不同哈希，"
        "每次跨实例查找都静默未命中，呈现一个看起来完全合理的零命中率；"
        "修法是在所有共享同一区域的副本上把 PYTHONHASHSEED 设为同值。"
        "另有粒度问题：offload 粒度为 256 token，任何非整数倍的前缀都要"
        "重算尾部的部分块。"
        "缓存的价值有三个不同性质的数，差别源于基线不同：CXL 可行性研究在"
        "外部命中率 95.4% 至 99.5% 下把 TTFT 降低 5.5 倍至 36.6 倍，"
        "sharing gap（跨节点与同节点复用的延迟比）只有 1% 至 4%，"
        "但作者声明两个副本都跑完整引擎、展示的是内存分离而非 P/D 分离、"
        "属可行性研究而非性能评估；Mooncake 集成报告吞吐 3.8 倍、"
        "TTFT 降低 46 倍、端到端降低 8.6 倍，其基线是本地 KV offload "
        "而非无缓存。"
    ),
    "claim_type": "synthesis",
    "as_of": "2026-11-05",
    "confidence": "high",
    "evidence_ids": ";".join(f"e-{i:03d}" for i in range(86, 93)),
    "counter_evidence_ids": "",
    "derivation": "从一份 agentic 负载的实测统计、一份 CXL 可行性研究与"
                  "一份 Mooncake 集成报告中提取负载形态量；三者的对比基线"
                  "不同，已在 statement 中分别标注。",
    "notes": "第 6 轮新增。触发点：上一轮末尾指出「负载形态决定配置」，"
             "本轮把数据补齐后证明确实如此，且能找到使前面整节失效的量。",
}


def main() -> int:
    p = HERE / "claims.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    if any(r["claim_id"] == CLAIM["claim_id"] for r in rows):
        print("c-load 已存在")
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

    bp = HERE / "paper" / "build_body.py"
    s = bp.read_text(encoding="utf-8")
    if "sec11_load" not in s:
        old = '    "sec10_slo.tex",'
        new = '    "sec10_slo.tex",\n    "sec11_load.tex",'
        assert old in s, "build_body 锚点未找到"
        s = s.replace(old, new, 1)
        bp.write_text(s, encoding="utf-8", newline="\n")
        print("build_body 已接入 sec11")

    mp = HERE / "make_paper_md.py"
    m = mp.read_text(encoding="utf-8")
    if "sec11_load" not in m:
        old = '"sec9_plane.tex", "sec10_slo.tex",'
        new = '"sec9_plane.tex", "sec10_slo.tex", "sec11_load.tex",'
        if old in m:
            m = m.replace(old, new, 1)
            mp.write_text(m, encoding="utf-8", newline="\n")
            print("PAPER.md 生成已接入 sec11")
        else:
            print("[!] PAPER.md 锚点未找到")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
