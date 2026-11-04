"""筛选 203 篇候选，按「体系性 vs 单点优化」分层。

## 与 kernel-agent 筛选的区别

那次最终必须人判，因为「用 CUDA 加速」与「生成 CUDA kernel」词汇全重叠。
本专题不同：**PD 分离有明确的技术指纹**——它必须同时触及
「P 与 D 两个阶段」与「KV 在两者间移动」这两件事。
只有一件事的工作（如纯 chunked prefill）是相邻而非核心。

故可用三段式规则 + 人工复核边界情况：

  A. 必须讲 LLM/DiT 推理服务（不是训练、不是别的领域）
  B. 必须同时出现「分离类动作」与「KV 位置变化」两类信号
  C. 排除同名不同义

## 分层

  core      直接研究 P/D 分离机制（架构、传输、调度）
  adjacent  为分离提供支撑（chunked prefill、KV 复用、路由、调度、基准）
  exclude   不相关

分层的意义见论文第 2 节：本领域的实际技术进步，一半在 adjacent 里。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- A. 推理服务语境 ----
SERVING = re.compile(
    r"\b(llm|large language model|inference|serving|served|deployment"
    r"|throughput|latency|slo|attention|transformer|difusion|dit)\b", re.I)

# ---- B1. 分离类动作 ----
DISAGG = re.compile(
    r"\b(disaggregat\w*|phase[- ]split\w*|split\w*\s*(?:the\s*)?(?:prefill|phase)"
    r"|separat\w+ (?:prefill|decod\w+|phase)|prefill[- ]decod\w+ separ\w+"
    r"|dedicat\w+ (?:prefill|decod)|p/d\b|pd[- ]disagg\w*)\b", re.I)

# ---- B2. KV 位置变化 ----
KV_MOVE = re.compile(
    r"\b(kv[- ]?cache\w*|kv\b)[^.]{0,60}"
    r"(transfer\w*|transmi\w+|migrat\w+|offload\w*|shar\w+|exchange\w+"
    r"|remote|network|rdma|nixl|mooncake|move[sd]?)\b", re.I)

# ---- B3. 两阶段的显式提及 ----
TWO_PHASE = re.compile(r"\bprefill\b", re.I), re.compile(r"\bdecod\w+", re.I)

# ---- C. 排除 ----
JUNK = [
    ("生物学/统计同名", re.compile(
        r"nucleotide|dummy encoding|regression|particle physics"
        r"|parkinson|photodiode", re.I)),
    ("训练侧", re.compile(
        r"\b(pretrain\w*|training|fine[- ]tun\w+)\b", re.I)),
]


def main() -> int:
    rows = json.loads((HERE / "candidates_pd.json").read_text(encoding="utf-8"))
    print(f"候选 {len(rows)} 篇\n")

    core, adjacent, dropped = [], [], []
    for r in rows:
        blob = r["title"] + " " + (r.get("summary") or "")
        title = r["title"]

        a = bool(SERVING.search(blob))
        d_hit = bool(DISAGG.search(blob))
        kv_hit = bool(KV_MOVE.search(blob))
        p_hit, dec_hit = TWO_PHASE[0].search(blob), TWO_PHASE[1].search(blob)
        two = bool(p_hit and dec_hit)

        junk = [n for n, p in JUNK if p.search(title)]

        rec = dict(r)
        rec["_disagg"] = d_hit
        rec["_kv_move"] = kv_hit
        rec["_two_phase"] = two
        rec["_junk"] = junk

        if junk or not a:
            dropped.append(rec)
        elif d_hit and (kv_hit or two):
            core.append(rec)
        elif two:
            adjacent.append(rec)
        else:
            dropped.append(rec)

    # core 内排序：奠基工作优先，再按时间
    core.sort(key=lambda r: (not r.get("_seed"), r["published"]), reverse=False)
    core.sort(key=lambda r: (r.get("_seed", False), r["published"]),
              reverse=True)

    print(f"core {len(core)} ｜ adjacent {len(adjacent)} ｜ 剔除 {len(dropped)}\n")
    print("=== core ===")
    for r in core:
        tag = "*" if r.get("_seed") else " "
        print(f" {tag}{r['arxiv_id']} {r['published'][:10]} "
              f"{r['title'][:70]}")
    print("\n=== adjacent（前 28）===")
    for r in adjacent[:28]:
        print(f"  {r['arxiv_id']} {r['published'][:10]} {r['title'][:70]}")

    (HERE / "screened_pd.json").write_text(
        json.dumps({"core": core, "adjacent": adjacent,
                    "dropped": [r["arxiv_id"] for r in dropped]},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n写入 screened_pd.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
