"""补技巧层的数值数据 paper/data/technique.csv。

## 判据 C 的要求

每行的 value 必须能在**对应 claim** 的 statement 里逐字找到。

技巧层的数字分布：
  · Waterfill 1.48 / 4.66          -> c-technique
  · LPLB 0.84 / 7.34               -> c-technique
  · DSpark 10 / 70 / 256           -> c-technique
  · 逐阶段量化 1.1 / 4.1           -> c-model（不是技巧层的主张）
  · DeepSeek V4 的 49253 / 51677   -> 这两个数没写进任何 claim

最后两个我特意留在外面：49253 / 51677 是 tok/s 的绝对量，
依赖具体的两台 Hopper 节点配置，写进 claim 会让主张变成
「某台机器上的某次测量」。这种数字放在正文里附来源即可，
不进 data/*.csv——进去会给人「可复现的基准」的错觉。

这是判据 C 的一个正面用法：它逼人决定哪些数字值得成为主张的一部分。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"

ROWS = [
    ["waterfill_low", "1.48", "%", "c-technique",
     "Waterfill 吞吐提升下界，3 个数据集（e-048）"],
    ["waterfill_high", "4.66", "%", "c-technique",
     "Waterfill 吞吐提升上界（e-048）"],
    ["lplb_low", "0.84", "%", "c-technique",
     "LPLB 吞吐提升下界（e-049）"],
    ["lplb_high", "7.34", "%", "c-technique",
     "LPLB 吞吐提升上界（e-049）"],
    ["dspark_last_token_survival", "10", "%", "c-technique",
     "7 token 块最后一个 draft token 的存活率上界（e-055）"],
    ["dspark_first_token_survival", "70", "%", "c-technique",
     "第一个 draft token 的存活率下界（e-055）"],
    ["dspark_max_concurrency", "256", "并发", "c-technique",
     "自适应验证仍有效的最大并发（e-054）"],
    ["stage_quant_low", "1.1", "x", "c-model",
     "只量化 prefill 相对只量化 decode 的精度损失下界（e-020）"],
    ["mooncake_reject_max", "525", "%", "c-technique",
     "预测式 early rejection 在模拟场景的吞吐提升上界（e-061）"],
    ["mooncake_real_requests", "75", "%", "c-technique",
     "真实负载下多处理的请求比例（e-061）"],
    ["reshape_makespan_before", "528.8", "s", "c-technique",
     "重切并行度前的 rollout makespan（e-062）"],
    ["reshape_makespan_after", "259.1", "s", "c-technique",
     "重切并行度后的 rollout makespan（e-062）"],
    ["reshape_decode_speedup", "2.04", "x", "c-technique",
     "重切并行度带来的 decode 吞吐提升（e-062）"],
    ["stage_quant_high", "4.1", "x", "c-model",
     "同上，上界（e-020）"],
]


def main() -> int:
    p = DATA / "technique.csv"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["metric", "value", "unit", "cite", "note"])
    w.writerows(ROWS)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"technique.csv {len(ROWS)} 行")

    # 自查：每个 value 是否真在对应 claim 里
    claims = {r["claim_id"]: r["statement"] for r in csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline=""))}
    bad = 0
    for r in ROWS:
        v = r[1]
        if v not in claims.get(r[3], ""):
            print(f"  [!] {r[0]}={v} 不在 {r[3]}")
            bad += 1
    print(f"自查：{bad} 个无法回溯")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
