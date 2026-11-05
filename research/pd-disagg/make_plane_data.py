"""登记 sec9 的表与数据，并接入 PAPER.md 生成。

## 要做四件事

1. make_tables.py：新增 tab6_plane.csv（三平面）
2. make_tables.py：paper.json 登记 tab6 + sections 加「四类之外」
3. make_paper_md.py：SECTIONS 加 sec9，caption 映射加「三平面」
4. make_plane_data.py：数值 → paper/data/plane.csv

## 为什么 tab6 单独一张而不并进 tab5

tab5 是「技巧按作用对象分四类」，tab6 是「三平面」。
两者是**不同的切法**，并在一张表会让人以为三平面是四类的细分。
分开画才能表达「正交」这个意思。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"

ROWS = [
    ["h200_tps_before", "1500", "tok/s", "c-plane",
     "每 H200 吞吐改造前约值（e-063）"],
    ["h200_tps_after", "2200", "tok/s", "c-plane",
     "每 H200 吞吐改造后（e-063）"],
    ["pcp8_vs_tp8", "2.65", "x", "c-plane",
     "DeepSeek V4 32K prompt 的 prefill 加速（e-068）"],
    ["long_prefill_tpgs", "93", "%", "c-plane",
     "token 上限带来的 TPGS 提升上界（e-075）"],
    ["long_prefill_p90", "2.3", "x", "c-plane",
     "P90 交互性改善（e-075）"],
    ["kernel_fusion_per_layer", "13", "%", "c-plane",
     "对称内存 + kernel 融合的每层延迟降幅（e-066）"],
    ["moe_fusion_e2e", "5", "%", "c-plane",
     "latent-tail MoE 融合的端到端延迟降幅（e-065）"],
    ["indexer_lo", "3", "%", "c-plane",
     "长上下文 indexer 延迟改善下界（e-067）"],
    ["indexer_hi", "31", "%", "c-plane",
     "长上下文 indexer 延迟改善上界（e-067）"],
    ["dsv4_fragmented_tensors", "92", "个", "c-plane",
     "DeepSeek V4 早期 KV 布局的碎片化 tensor 数（e-073）"],
    ["fp4_kv_saving", "10", "%", "c-plane",
     "打包布局 + FP4 indexer 省下的 KV 显存（e-073）"],
    ["long_prefill_threshold", "512", "token", "c-plane",
     "长 prefill 每步可调度的 token 上限（e-075）"],
]


def main() -> int:
    p = DATA / "plane.csv"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["metric", "value", "unit", "cite", "note"])
    w.writerows(ROWS)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"plane.csv {len(ROWS)} 行")

    claims = {r["claim_id"]: r["statement"] for r in csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline=""))}
    bad = 0
    for r in ROWS:
        if r[1] not in claims.get(r[3], ""):
            print(f"  [!] {r[0]}={r[1]} 不在 {r[3]}")
            bad += 1
    print(f"自查：{bad} 个无法回溯")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
