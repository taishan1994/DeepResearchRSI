"""登记 tab:layers（六层关系表）与 onepage.csv。

## 这张表的特殊之处

它不含任何测量数字——它是**结构表**，列出六层各自回答什么、
能否决什么、在论文哪一节。故 onepage.csv 里不写 metric/value，
而是记录「这张表本身」。

## 为什么仍然要有 csv

本仓库的规矩是：正文里的表都要有数据文件，审计才能核对
表与档案例一致。结构表也一样——它的「数据」是那六行的内容，
写成 csv 后可以逐行核对，避免正文与表格漂移。

## 不做什么

不给这张表编造数字。它没有数字。
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "paper" / "data"
TABLES = HERE / "paper" / "tables"

LAYERS = [
    ["1", "负载形态", "输入长什么样", "整类技巧的用武之地", "sec:load"],
    ["2", "SLO 形状", "要什么", "技巧的方向", "sec:slo"],
    ["3", "收益边界", "值不值得做", "分离本身", "sec:boundary"],
    ["4", "中间结论", "——", "三者都成立的区间", "sec:onepage"],
    ["5", "实现平面", "栈里有哪几层", "保证不漏", "sec:plane"],
    ["6", "四类技巧", "传输账怎么省", "给出同类替代", "sec:technique"],
    ["7", "模型差异", "具体模型怎么做", "给出起点配置", "sec:model"],
]


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["层", "切法", "回答什么", "能否决什么", "节"])
    w.writerows(LAYERS)
    (TABLES / "tab9_layers.csv").write_text(buf.getvalue(),
                                            encoding="utf-8", newline="\n")
    print(f"  tab9_layers.csv {len(LAYERS)} 行")

    # 结构表没有数字，故 data 侧只记元信息
    p = DATA / "onepage.csv"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["item", "value", "cite", "note"])
    w.writerow(["layers", str(len(LAYERS)), "",
                "六层关系表（结构表，无测量数字）"])
    w.writerow(["decision_steps", "4", "",
                "判断顺序的四步：负载/SLO/窗口/每类选一个"])
    w.writerow(["veto_layers", "4", "",
                "前四层是否决层，后三层是执行层"])
    p.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print("  onepage.csv 3 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
