"""导出论文表格与图表的数据文件。

## 单一数据源

所有数字来自 `paper/analysis.json`（由 `analyze.py` 生成，只读
sources/evidence/claims/papers）。本脚本只做**转格式**，不做计算。

## 为什么图也要 CSV

`paper.json` 的 figures 声明了 `data_file`，审计会核对文件是否存在。
更重要的是：图一旦只有 PNG，读者无法核实画的是什么；
留下 CSV，任何数字都能被追到源。

## 输出

  data/fig1_timeline.csv      季度 -> 论文数
  data/fig2_reward_forms.csv  奖励形态 -> 论文数
  data/fig3_algorithm.csv     算法 -> 论文数
  tables/tab1_algo.csv        同 fig3，带论文清单
  tables/tab2_reward.csv      同 fig2，带判定词
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
DATA = HERE / "data"
TABLES = HERE / "tables"
DATA.mkdir(exist_ok=True)
TABLES.mkdir(exist_ok=True)

# 判定词必须与 analyze.py 的 REWARD_TAGS 一致，否则表与图对不上。
# 这里重复一份是不得已：审计需要它能被读到，而 analyze.py 是脚本不是数据。
REWARD_PATTERNS = {
    "outcome": r"speedup|execution speed|correctness|pass@",
    "multi_turn": r"multi-turn|iterative|interact",
    "structural": r"structural|parallelization|data-flow|decompos",
    "profiling": r"profil|counter|hardware metric",
    "anti_hack": r"reward hack|cheat|hacking|trivial",
    "curriculum": r"curriculum",
    "contrastive": r"contrastive",
    "synthetic": r"synthetic|data synthes",
}
REWARD_ZH = {
    "outcome": "结果型（正确+加速）",
    "multi_turn": "多轮交互",
    "profiling": "profiling 驱动",
    "anti_hack": "反作弊机制",
    "synthetic": "合成数据/课程",
    "structural": "结构化代码奖励",
    "contrastive": "对比式",
    "curriculum": "课程学习",
}


def w(name: Path, header: list[str], rows: list[list]) -> None:
    with name.open("w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
    print(f"  {name.relative_to(HERE)}  ({len(rows)} 行)")


# ---- 图 1
w(DATA / "fig1_timeline.csv", ["quarter", "papers"],
  [[t["quarter"], t["count"]] for t in A["timeline"]])

# ---- 图 2
rs = A["reward_shift"]
w(DATA / "fig2_reward_forms.csv", ["form", "form_zh", "papers"],
  [[k, REWARD_ZH.get(k, k), v]
   for k, v in sorted(rs.items(), key=lambda kv: -kv[1])])

# ---- 图 3
am = A.get("algo_mix") or {}
order = ["GRPO", "对比式", "PPO", "未点名"]
w(DATA / "fig3_algorithm.csv", ["algorithm", "papers"],
  [[k, am.get(k, 0)] for k in order])

# ---- 表 1（带论文清单）
aw = A.get("algo_which") or {}
w(TABLES / "tab1_algo.csv", ["algorithm", "papers", "arxiv_ids"],
  [[k, am.get(k, 0), ";".join(aw.get(k, []))] for k in order])

# ---- 表 2（带判定词）
w(TABLES / "tab2_reward.csv", ["form", "form_zh", "papers", "pattern"],
  [[k, REWARD_ZH.get(k, k), v, REWARD_PATTERNS.get(k, "")]
   for k, v in sorted(rs.items(), key=lambda kv: -kv[1])])

print("完成")
