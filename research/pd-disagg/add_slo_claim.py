"""新增主张 c-slo 并接入正文。

## 主张的核心命题

同一个技巧在不同 SLO 下方向相反。这不是"有 tradeoff"，
而是"存在两个被同一旋钮反向拉扯的目标"。

## 必须进 statement 的数字

  4.0 / 0.125 / 15  三组应用的 TTFT（秒）
  0.2 / 0.15        对应 TPOT（秒）
  120               TTFT 的跨度倍数（15 / 0.125）
  3.2 / 1.5         代码补全的请求率提升与 SLO 收紧倍数
  1.4 / 1.8         聊天的 SLO 收紧区间
  90                goodput 的 SLO 达成率目标

## 一处措辞纪律

原文说的是「第一个 chunk 的 KV 被加载 N-1 次」。写成
「N-1 次」而不是「多次」—— 具体机制比模糊表述可检验。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLAIM = {
    "claim_id": "c-slo",
    "statement": (
        "同一个优化技巧在不同 SLO 形状下方向相反，故「某技巧提升多少」"
        "的结论必须带上 SLO 条件。最干净的机制例子是 chunked prefill 的 "
        "token 预算：它由两个相互竞争的因素决定——TBT 的 SLO 要求与 "
        "chunk 切分自身的开销。从压低 TBT 看预算越小越好，但预算太小会让 "
        "prefill 过度切分：一个 prompt 切成 N 个 chunk 时第一个 chunk 的 "
        "KV cache 要被加载 N-1 次、第二个 N-2 次，计算量不变而 HBM 重复"
        "读取增加。故调小预算则 TBT 变好、吞吐变差，调大则相反。"
        "调度侧同样反向：优先 prefill 会让已在跑的 decode 停等而抬高延迟，"
        "优先 decode 则压住 prefill、抬高 TTFT。"
        "应用层的证据是 DistServe 的三组配置：Chatbot OPT-175B 的 TTFT "
        "4.0 秒、TPOT 0.2 秒；Code Completion OPT-66B 的 TTFT 0.125 秒、"
        "TPOT 0.2 秒；Summarization OPT-66B 的 TTFT 15 秒、TPOT 0.15 秒。"
        "TTFT 跨约 120 倍而 TPOT 几乎不变，说明决定配置的不是「SLO 严不严」"
        "而是「两个 SLO 的相对松紧」——代码补全与摘要的偏好方向完全相反。"
        "同一套系统报告的收益结构也随之不同：代码补全支撑 3.2 倍更高请求率"
        "同时 SLO 更严 1.5 倍，聊天则是 SLO 更严 1.4 倍至 1.8 倍。"
        "因此 goodput 应按「在 SLO 达成率目标（如 90%）下每 GPU 能服务的"
        "最大请求率」定义，报告收益时必须同时报 SLO 形状。"
    ),
    "claim_type": "synthesis",
    "as_of": "2026-11-05",
    "confidence": "high",
    "evidence_ids": ";".join(f"e-{i:03d}" for i in range(79, 86)),
    "counter_evidence_ids": "",
    "derivation": "从 Sarathi-Serve 的 token budget 机制与 DistServe 的"
                  "三组应用配置中提取 SLO 方向性；数字全部取自原文表格"
                  "与正文，未做换算。",
    "notes": "第 5 轮新增。触发点：上一轮末尾提出「按 SLO 类型切，"
             "看同一技巧是否反向」，本轮证明确实反向。",
}


def main() -> int:
    p = HERE / "claims.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    if any(r["claim_id"] == CLAIM["claim_id"] for r in rows):
        print("c-slo 已存在")
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

    # ---- 接入 body ----
    bp = HERE / "paper" / "build_body.py"
    s = bp.read_text(encoding="utf-8")
    if "sec10_slo" not in s:
        old = '    "sec9_plane.tex",'
        new = '    "sec9_plane.tex",\n    "sec10_slo.tex",'
        assert old in s, "build_body 锚点未找到"
        s = s.replace(old, new, 1)
        bp.write_text(s, encoding="utf-8", newline="\n")
        print("build_body 已接入 sec10")

    # ---- 接入 PAPER.md ----
    mp = HERE / "make_paper_md.py"
    m = mp.read_text(encoding="utf-8")
    if "sec10_slo" not in m:
        old = '"sec8_technique.tex", "sec9_plane.tex",'
        new = '"sec8_technique.tex", "sec9_plane.tex", "sec10_slo.tex",'
        if old in m:
            m = m.replace(old, new, 1)
            mp.write_text(m, encoding="utf-8", newline="\n")
            print("PAPER.md 生成已接入 sec10")
        else:
            print("[!] PAPER.md 锚点未找到")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
