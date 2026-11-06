"""构造论文的数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每一行带一个 cite 列，指向 claims.csv 的主张。audit_paper.py 会顺着
cite -> evidence_ids -> quote 核对每个数值；核对不过就不许出图。
故这里的数字必须先在证据的 quote 里出现过——不是「差不多」，是字面出现。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLES_DIR = HERE / "tables"
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


# 图 1：同一模型上「表面指标」与「能力指标」的分歧。
# 数字全部来自 e-014（one-shot 17→0，loop 10→25）。
GAP = [
    ("BF16：一次性解出", 17, "c-lossless-not-ppl"),
    ("AWQ：一次性解出", 0, "c-lossless-not-ppl"),
    ("BF16：循环解出", 10, "c-lossless-not-ppl"),
    ("AWQ：循环解出", 25, "c-lossless-not-ppl"),
]

# 图 2：敏感度代理的标定质量（与真实激活下目标函数的 rank 相关）。
# 0.83 / 0.81 / 0.83 来自 e-050，0.25 来自 e-052。
PROXY = [
    ("传播式探针 Qwen3-8B", 0.83, "c-sensitivity-proxy"),
    ("传播式探针 Qwen3.5-9B", 0.81, "c-sensitivity-proxy"),
    ("传播式探针 Qwen3.8-27B", 0.83, "c-sensitivity-proxy"),
    ("既有方法 HAWQ-V2", 0.25, "c-sensitivity-proxy"),
]

# 图 3：局部排序被整体重排推翻的比例。
# 79 条 / 17 条来自 e-080；24 次 / 21 次来自 e-073。
LOCAL = [
    ("局部排序总数", 79, "c-local-global"),
    ("被整模型反馈推翻", 17, "c-local-global"),
    ("修订总数", 24, "c-agent-loop"),
    ("PPL 下降的修订", 21, "c-agent-loop"),
]

# 图 4：同一请求的路径分歧随量化放大。
# 37.4 / 82.5 来自 e-023。
DIVERGE = [
    ("16-bit 权重", 37.4, "c-flat-score"),
    ("4-bit 权重", 82.5, "c-flat-score"),
]

T_OBJECT = [
    ["层", "被优化的是什么", "参数化", "「正确」由什么定义"],
    ["kernel / 算子", "一段可独立编译的 GPU 程序", "实现方式（离散）", "allclose + 隐藏测试集"],
    ["端到端 / 服务", "系统设计 + 运行时状态", "调度与算法（混合）", "无损判据 + SLO"],
    ["量化 / 表示", "权重与激活的数值表示", "bit / 粒度 / 分组（连续）", "前沿位置 + 退化阈值"],
]

T_DEF = [
    ["定义", "保护什么", "什么时候会漏"],
    ["perplexity 相对增量", "语言建模的平均似然", "安全对齐、稀有词定义能力"],
    ["下游基准准确率", "任务级平均表现", "过程行为、一次性解到循环解的迁移"],
    ["与 FP16 的分布散度", "整个预测分布的位移", "方向——KLD 测不出分歧落在哪"],
    ["过程诊断量", "失败发生在哪一步", "需要重跑日志，非默认产出"],
]

T_ROUTE = [
    ["路线", "分配单元", "代理/依据", "代表工作"],
    ["层间位宽分配", "整个线性层", "per-layer 敏感度分数", "层位宽分配 / MXSens"],
    ["块内 + 块间双层", "block / 专家", "块内便宜代理 + 块间整模型目标", "Q-Strata"],
    ["tile 级分配", "硬件对齐的二维 tile", "校准打分 + 保留预算", "TileQuant / AlignQuant"],
    ["无数据探针", "tensor / 层", "传播式随机探针", "谱平坦探针（400B）"],
    ["训练期动态分配", "层（随训练变）", "前向误差估计", "Q-PACE"],
]

T_REPORT = [
    ["项", "为什么必须写"],
    ["基线是什么", "「近乎无损」常来自基准准确率只掉一两点"],
    ["位宽之外还改了什么", "分组、粒度、校准集都会改变结论"],
    ["过程诊断量", "误差预算会吸收额外失败，分数看不见"],
    ["跨架构复核", "同一位宽在不同架构上结果不同"],
    ["循环成本", "校准、搜索、恢复训练三笔账要分开报"],
]

T_BOUND = [
    ["条件", "现象", "证据类型"],
    ["换架构", "同一位宽结果不同，敏感部件是模型特定的", "跨 11 个 TTS 架构的统一协议"],
    ["换任务", "逐字记忆比通用能力掉得更快", "5 个精度 × 3 个规模 × 2 套语料"],
    ["换负载", "RAG 接地性可以在答案准确率不变时变差", "离线 KV cache 审计"],
    ["换场景", "多轮更新下末值检索对数线性下降", "前摄干扰实验"],
]

T_COST = [
    ["环节", "代价的量级", "可否避免"],
    ["敏感度探针", "单机数十秒到数百秒（8B–400B）", "否，但很便宜"],
    ["校准", "一次前向；无校准方法可打平", "部分可以"],
    ["位分配搜索", "取决于块内候选数", "可用代理降"],
    ["恢复训练", "主成本；序列长度选择就值 1.9 个点", "低比特下难以避免"],
]

TABLES_DEF = [
    ("tab1_object.csv", ["层", "被优化的是什么", "参数化", "「正确」由什么定义"], T_OBJECT[1:]),
    ("tab2_defs.csv", ["定义", "保护什么", "什么时候会漏"], T_DEF[1:]),
    ("tab3_route.csv", ["路线", "分配单元", "代理/依据", "代表工作"], T_ROUTE[1:]),
    ("tab6_report.csv", ["项", "为什么必须写"], T_REPORT[1:]),
    ("tab5_boundary.csv", ["条件", "现象", "证据类型"], T_BOUND[1:]),
    ("tab4_cost.csv", ["环节", "代价的量级", "可否避免"], T_COST[1:]),
]


def main() -> int:
    claims = {r["claim_id"] for r in read_csv(SLUG / "claims.csv")}
    bad = []
    for group in (GAP, PROXY, LOCAL, DIVERGE):
        for row in group:
            if row[-1] not in claims:
                bad.append(row)
    if bad:
        print("[FAIL] 引用了不存在的主张：")
        for row in bad:
            print("  ", row)
        return 1

    write(DATA, "fig1_gap.csv", ["item", "value", "cite"], GAP)
    write(DATA, "fig2_proxy.csv", ["proxy", "rho", "cite"], PROXY)
    write(DATA, "fig3_local.csv", ["item", "count", "cite"], LOCAL)
    write(DATA, "fig4_divergence.csv", ["precision", "percent", "cite"], DIVERGE)
    for name, header, rows in TABLES_DEF:
        write(TABLES_DIR, name, header, rows)
    print("数据层完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())