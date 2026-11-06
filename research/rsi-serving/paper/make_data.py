"""构造论文的数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每一行带一个 cite 列，指向 claims.csv 的主张。audit_paper.py 会顺着
cite -> evidence_ids -> quote 核对每个数值；核对不过就不许出图。
故这里的数字必须先在证据里出现过。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLES = HERE / "tables"
SLUG = HERE.parent


def read_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write(dir_: Path, name, header, rows):
    dir_.mkdir(exist_ok=True)
    p = dir_ / name
    with p.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"  {dir_.name}/{name}: {len(rows)} 行")


# 图 1：端到端报告增益与口径 —— (系统, 数值, 口径, cite)
GAIN = [
    ("AIConfigurator 配置搜索（dense）", 40.0, "相对默认配置的提升（%）", "c-ceiling"),
    ("跨模型编译（每轮几何均值）", 1.37, "六种单卡投机解码配置 / B300+5090", "c-gain"),
    ("SEIS 对 mini-sglang", 3.27, "Qwen3-0.6B / H100 单请求吞吐", "c-gain"),
    ("VibeServe 对调优 SGLang", 2.30, "397B MoE / 四张 MI300A / goodput", "c-gain"),
    ("SpecPilot 对 stock（单请求）", 2.13, "H100 / sealed final", "c-gain"),
    ("SpecPilot 对 AR（单请求）", 10.87, "H100 / 相对自回归", "c-gain"),
    ("SpecPilot 对 AR（批处理）", 3.93, "H100 / 相对自回归", "c-gain"),
]

# 图 2：harness 自改进的漏斗 —— 数字全部来自 e-100 / e-101。
# ⚠️ 原本这里画的是「三轮累计增益」折线（1.16 / 1.55 / 2.13），
# 但 1.55 在任何证据里都找不到——它是两轮论文表格的拼接值。
# 按 P2（数值可回溯）删掉该曲线，改成这张台账里有逐条出处的漏斗。
FUNNEL = [
    ("提出", 125, "c-harness"),
    ("实现", 24, "c-harness"),
    ("评估", 12, "c-harness"),
    ("有效", 3, "c-harness"),
    ("无效", 4, "c-harness"),
]

# 图 3：代价结构 —— (项目, 数值, 单位, cite)
COST = [
    ("单轮墙钟（下界）", 7, "小时", "c-cost"),
    ("单轮墙钟（上界）", 20, "小时", "c-cost"),
    ("十三轮合计墙钟", 164, "小时", "c-cost"),
    ("十三轮合计 GPU", 530, "GPU-小时", "c-cost"),
    ("穷举配置搜索", 25000, "GPU-小时", "c-cost"),
]

# 图 4：反号证据 —— (机制, 收益, 条件, cite)
REVERSAL = [
    ("24 节点树", -14.9, "FP8 目标 / 批处理", "c-boundary"),
    ("24 位置块", -9.9, "BF16 Qwen3.8-27B / 批处理", "c-boundary"),
    ("TLV", -13.0, "BF16 Qwen3.8-27B / 批处理", "c-boundary"),
]

# 表 1：三层对象与判据 —— 分类表，无 cite 列
T_OBJECT = [["层", "被优化的是什么", "正确性判据", "性能判据"],
    ["kernel / 算子", "一段可独立编译的 GPU 程序", "allclose + 隐藏测试集", "稳健计时"],
    ["端到端 / 服务", "系统设计 + 运行时状态", "无损判据 + 下游任务", "吞吐 / 延迟 / SLO"],
    ["配置 / 容量", "并行、精度、调度参数", "与参考引擎输出一致", "代理模型预测 + 实测校准"],
    ["量化 / 压缩", "权重与 KV 的表示", "perplexity / KL / 准确率阈值", "精度-吞吐前沿"],
]

T_LADDER = [["判据层", "回答什么", "本主题的实例"],
    ["成本模型", "该往哪优化", "ceiling 三分之积"],
    ["晋级判据", "是否真的更好", "配对运行 + 95% 下界"],
    ["无损判据", "是否还正确", "token forcing + 两条拒绝规则"],
    ["成本核算", "这么做值不值", "GPU-小时 vs 穷举基线"],
]

T_LOSS = [["系统", "数值门", "下游门", "统计门"],
    ["SpecPilot", "exact pass 的 argmax", "sealed final 未见请求", "rate rule + event rule"],
    ["SEIS", "perplexity 5% / KL 0.05", "GSM8K + 检索任务", "—（无显式统计门）"],
]

T_BOUND = [["条件", "机制", "证据"],
    ["批处理", "每请求验证工作约翻倍，摊薄收益", "24 节点树 −14.9%"],
    ["任务饱和", "已到顶的系统测不出差别", "比较失效"],
    ["平均情况代理", "解析近似扭曲 SLA，甚至反转结论", "模拟器论文自述"],
    ["离线 autotune 假设", "MoE 下最优配置取决于路由分布", "1.45x 差距"],
]

T_PROTO = [["项", "为什么必须写"],
    ["基线是什么", "稻草人基线可制造 10.6x vs 2.03x"],
    ["是否配对运行", "跨机器绝对值从 1.174x 漂到 1.0049x"],
    ["是否有下界", "点估计无法区分改进与噪声"],
    ["无损怎么判", "逐位相同会误杀，准确率会漏放"],
    ["循环成本", "530 GPU-小时换来的结论与免费结论不等价"],
]

T_HARNESS = [["阶段", "数量", "说明"],
    ["提议", "125", "一次回顾会话产出的 harness 改动建议"],
    ["实现", "24", "真正落地的改动"],
    ["评估", "12", "在新会话里做 A/B 的改动"],
    ["有效", "2 + 1", "2 次消除、1 次减少目标重复工作"],
    ["无效", "4", "7 次可评估改动中没有减少"],
]


TABLES_DIR = HERE / "tables"

TABLES_DEF = [
    ("tab1_object.csv", ["层", "被优化的是什么", "正确性判据", "性能判据"], T_OBJECT[1:]),
    ("tab2_ladder.csv", ["判据层", "回答什么", "本主题的实例"], T_LADDER[1:]),
    ("tab3_lossless.csv", ["系统", "数值门", "下游门", "统计门"], T_LOSS[1:]),
    ("tab4_boundary.csv", ["条件", "机制", "证据"], T_BOUND[1:]),
    ("tab5_protocol.csv", ["项", "为什么必须写"], T_PROTO[1:]),
    ("tab6_harness.csv", ["阶段", "数量", "说明"], T_HARNESS[1:]),
]


def main() -> int:
    claims = {r["claim_id"] for r in read_csv(SLUG / "claims.csv")}
    bad = []
    for group in (GAIN, FUNNEL, COST, REVERSAL):
        for row in group:
            if row[-1] not in claims:
                bad.append(row)
    if bad:
        print("[FAIL] 引用了不存在的主张：")
        for row in bad:
            print("  ", row)
        return 1

    write(DATA, "fig1_gain.csv", ["system", "value", "metric", "cite"], GAIN)
    write(DATA, "fig2_funnel.csv", ["stage", "count", "cite"], FUNNEL)
    write(DATA, "fig3_cost.csv", ["item", "value", "unit", "cite"], COST)
    write(DATA, "fig4_reversal.csv", ["mechanism", "gain", "condition", "cite"], REVERSAL)
    for name, header, rows in TABLES_DEF:
        write(TABLES_DIR, name, header, rows)
    print("数据层完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())