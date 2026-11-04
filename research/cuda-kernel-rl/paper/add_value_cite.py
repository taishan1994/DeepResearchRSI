"""给图表 CSV 补上 `value` / `cite` 两列，让「数值可回溯」（P2）真正执行。

## 为什么必须补

`scripts/audit_paper.py` 的 C 段检查是这样实现的：遍历 `paper/data/*.csv`，
取每行的 `(value, cite)`，顺着 claim 追到 evidence.quote 核对。

我最初的 CSV 是 `form,papers` / `quarter,papers`——列名不匹配，
于是每一行都被 `continue` 跳过，`checked` 恒为 0。
审计输出「数值回溯 0 条」然后报 `[OK]`。

**这是最危险的一种通过：检查写了，但一行都没查。**
与上一轮 E1 的 `e1_checked=0` 是同一类问题——「没查」被记成「查过且合格」。

## 补法

每个 CSV 增加两列：
    value  该行的数值（纯数字，不带单位）
    cite   该数值所依据的 claim_id

这样审计会真的逐行回溯到证据原文。
代价是每行都要指定 cite——但这是应该的：
一个数字若说不清依据哪条证据，就不该出现在论文里。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
DATA = HERE / "data"

# 每个数据文件里，「数值」列该挂哪条 claim。
# 判定依据：这条 claim 的 evidence 里必须能找到这个数量级的事实。
#   - 时间线/算法/奖励形态的计数，本身是本文的统计结果，
#     依据是「这些论文确实属于这个方向」-> c-kernel-rl-fit
#     以及「算法分布单调」-> c-grpo-default-but-flawed
CITE_BY_FILE = {
    "fig1_timeline.csv": "c-kernel-rl-fit",
    "fig2_reward_forms.csv": "c-structural-reward",
    "fig3_algorithm.csv": "c-grpo-default-but-flawed",
}

# 逐行覆盖：反作弊那一行挂反作弊的主张，比挂「奖励形态」更准确
CITE_BY_ROW = {
    ("fig2_reward_forms.csv", "anti_hack"): "c-reward-hacking",
    ("fig2_reward_forms.csv", "profiling"): "c-profiling-reward",
}


def main() -> int:
    for name, default_cite in CITE_BY_FILE.items():
        path = DATA / name
        if not path.is_file():
            print(f"  [跳过] {name} 不存在")
            continue
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            continue
        header = list(rows[0].keys())
        # 找出数值列：优先名为 papers / count / value 的
        vcol = next((c for c in ("papers", "count", "value")
                     if c in header), None)
        if not vcol:
            print(f"  [!] {name} 找不到数值列，实际列：{header}")
            continue

        key = header[0]
        for r in rows:
            r["value"] = r[vcol]
            r["cite"] = CITE_BY_ROW.get((name, r[key]), default_cite)

        if "value" not in header:
            header += ["value", "cite"]
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n",
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  {name}  {len(rows)} 行已补 value/cite")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
