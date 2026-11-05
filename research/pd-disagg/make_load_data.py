"""登记 tab8（缓存收益的三个来源与基线）与 load.csv。

## tab8 为什么必须带「基线」一列

三个来源的幅度差别大（5.5-36.6x vs 3.8/46/8.6x），若只列幅度，
读者会以为它们可比。实际上一个的基线是「同节点复用」，
另一个是「本地 KV offload」。**基线不同，数字不可比**——
这一列是这张表存在的理由。

## 数据纪律

  · 94.2 / 131 / 2242 / 12 / 80 / 5.2 / 81.4  来自 Codex trace 统计
  · 95.4 / 99.5 / 5.5 / 36.6 / 1 / 4           来自 CXL 可行性研究
  · 3.8 / 46 / 8.6                             来自 Mooncake 集成报告
  · 100 / 3.8 / 256                            来自长上下文与 offload 粒度

三组必须分开标注来源，不合并成一张「缓存收益」表。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"
TABLES = HERE / "paper" / "tables"

TAB_ROWS = [
    ["CXL 可行性研究",
     "TTFT 降 5.5x 至 36.6x",
     "同节点复用（外部命中率 95.4-99.5%）"],
    ["Mooncake 集成",
     "吞吐 3.8x、TTFT 降 46x、端到端 8.6x",
     "本地 KV offload，非「无缓存」"],
]

NUM_ROWS = [
    ["traces", "610", "条", "c-load", "Codex/SWE-bench Pro 的 trace 数"],
    ["turns_median", "33", "轮", "c-load", "每条 trace 的中位轮数"],
    ["hit_rate", "94.2", "%", "c-load", "缓存命中率"],
    ["io_ratio", "131", ":1", "c-load", "输入输出比"],
    ["growth_per_turn", "2242", "token", "c-load", "每轮上下文增长"],
    ["ctx_lo", "12", "K token", "c-load", "轨迹上下文起点"],
    ["ctx_hi", "80", "K token", "c-load", "轨迹上下文终点"],
    ["delay_median", "5.2", "s", "c-load", "轮间隔中位数"],
    ["delay_p99", "81.4", "s", "c-load", "轮间隔 P99"],
    ["long_ctx", "100", "K token", "c-load", "长上下文的 token 量"],
    ["kv_gb", "3.8", "GB", "c-load", "Kimi-2.5 FP8 在该长度下的 KV"],
    ["offload_gran", "256", "token", "c-load", "offload 的块粒度"],
    ["ext_hit_lo", "95.4", "%", "c-load", "CXL 研究的外部命中率下界"],
    ["ext_hit_hi", "99.5", "%", "c-load", "CXL 研究的外部命中率上界"],
    ["ttft_gain_lo", "5.5", "x", "c-load", "TTFT 降幅下界"],
    ["ttft_gain_hi", "36.6", "x", "c-load", "TTFT 降幅上界"],
    ["gap_lo", "1", "%", "c-load", "sharing gap 下界"],
    ["gap_hi", "4", "%", "c-load", "sharing gap 上界"],
    ["mc_tput", "3.8", "x", "c-load", "Mooncake 集成的吞吐提升"],
    ["mc_ttft", "46", "x", "c-load", "Mooncake 集成的 TTFT 降幅"],
    ["mc_e2e", "8.6", "x", "c-load", "Mooncake 集成的端到端降幅"],
]


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["来源", "幅度", "基线"])
    w.writerows(TAB_ROWS)
    (TABLES / "tab8_load.csv").write_text(buf.getvalue(), encoding="utf-8",
                                          newline="\n")
    print(f"  tab8_load.csv {len(TAB_ROWS)} 行")

    p = DATA / "load.csv"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["metric", "value", "unit", "cite", "note"])
    w.writerows(NUM_ROWS)
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"  load.csv {len(NUM_ROWS)} 行")

    claims = {r["claim_id"]: r["statement"] for r in csv.DictReader(
        (HERE / "claims.csv").open(encoding="utf-8", newline=""))}
    bad = 0
    for r in NUM_ROWS:
        if r[1] not in claims.get(r[3], ""):
            print(f"  [!] {r[0]}={r[1]} 不在 {r[3]}")
            bad += 1
    print(f"自查：{bad} 个无法回溯")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
