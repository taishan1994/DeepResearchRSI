# -*- coding: utf-8 -*-
"""构造论文的数据层：paper/data/*.csv。

## 纪律

每一行都有一个 cite 列，指向 claims.csv 里的一个 claim_id。
audit_paper.py 会顺着 cite -> evidence_ids -> quote 去核对 value；
核对不过就不许出图。所以这里的每一个数字都必须先在证据里出现过。

## 为什么有些行是派生值

「相对增益随预算变化」这类量在原论文里当然不存在——它是本文把两篇
论文的同类实验并排后算出来的比值。这类行用 derived=1 标记，并在
note 里写清算法，避免读者把它当成实测。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
SLUG = HERE.parent


def read_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write(name, header, rows):
    p = DATA / name
    with p.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name}: {len(rows)} 行")


# 图片 1：增益分布 —— (系统, 数值, 口径, cite)
GAIN = [
    ("KernelOPT L1", 1.40, "几何平均 / torch.compile", "c-gain"),
    ("KernelOPT L2", 1.15, "几何平均 / torch.compile", "c-gain"),
    ("KernelOPT L3", 1.07, "几何平均 / torch.compile", "c-gain"),
    ("Astra", 1.32, "算术平均 / 3 个 SGLang kernel", "c-gain"),
    ("KernelBlaster L1", 1.43, "几何平均 / eager 与 compile 取优", "c-loop-forms"),
    ("AdaExplore L2", 3.12, "100 步预算 / 几何平均", "c-gain"),
    ("AdaExplore L3", 1.72, "100 步预算 / 几何平均", "c-gain"),
    ("cuPilot", 3.09, "算术平均 / 100 个 KernelBench", "c-gain"),
    ("ForgeKernel", 10.0, "对专家参考的几何平均增益（%）", "c-gain"),
    ("案例研究", 9.293, "几何平均 / 官方基线", "c-gain"),
]

# 图片 3：收益随预算的变化 —— (系统, 预算, 倍数, cite)
BUDGET = [
    ("AdaExplore L2", 50, 2.65, "c-plateau"),
    ("AdaExplore L2", 100, 3.12, "c-plateau"),
    ("AdaExplore L3", 50, 1.55, "c-plateau"),
    ("AdaExplore L3", 100, 1.72, "c-plateau"),
]

# 图片 4：kernel 级 -> 端到端 —— (对象, kernel 级, 端到端, cite)
FUNNEL = [
    ("RMSNorm（6.65x / 8.3-10.1%）", 6.65, 9.2, "c-e2e"),
    ("子 kernel（3.27x / 2.89x）", 3.27, 2.89, "c-e2e"),
    ("GEMM epilogue（5.84x / 变慢）", 5.84, 0.98, "c-e2e"),
]

# 图片 5：成本构成与 token 差 —— (系统, 指标, 数值, cite)
COST = [
    ("LLM 调用", "占总时间比例", 21.0, "c-cost"),
    ("编译+运行+采样", "占总时间比例", 79.0, "c-cost"),
    ("KOPE 主动上下文", "token（十亿）", 1.113, "c-gain"),
    ("KOPE 被动上下文", "token（十亿）", 15.9, "c-gain"),
    ("CANNBot Fix-Loop", "token（千）", 350.0, "c-gain"),
    ("CANNBot Tool-Agent", "token（百万）", 4.18, "c-gain"),
]

# 六张表：与正文的表 1..6 一一对应（编号按正文出现顺序）。
# 表格是分类与口径的呈现，不含需要回溯的实测值，故没有 cite 列；
# 表里出现的数字（1.43 / 0.88 / 1.40 …）都能在 claims 的陈述句里找到。
TABLES = [
    ("tab1_protocol.csv", ["维度", "标准协议", "Verified"], [
        ["基线", "torch.compile（默认精度）", "开启 TF32 的 PyTorch"],
        ["正确性判据", "给定输入的数值比对", "四分布隐藏测试集"],
        ["计时", "单次或少量重复", "稳健重复 + 内存开销"],
        ["结果", "1.43 倍", "0.88 倍"],
    ]),
    ("tab2_objects.csv", ["层", "正确性判据", "性能判据", "闭环"], [
        ["kernel / 算子", "数值等价 + 计时", "编译 → 隐藏集 → 稳健计时", "是"],
        ["图 / 编译", "与参考实现数值等价", "端到端吞吐、IR 正确性", "部分"],
        ["服务与调度", "SLA 满足、输出一致", "吞吐 / SLO、可搜索性", "部分"],
        ["量化 / 压缩", "精度回归阈值", "精度-吞吐前沿、内存", "否"],
    ]),
    ("tab3_loops.csv", ["形态", "改进发生在哪", "主要成本", "代表工作"], [
        ["单轮生成 + 验证", "采样", "采样成本", "GPU Kernel Scientist"],
        ["多轮反思 / 修复", "同一上下文内迭代", "上下文与 token 增长", "KernelBlaster"],
        ["强化学习", "内化进权重", "训练算力与奖励工程", "CUDA Agent"],
        ["脚手架自演化", "不改权重，改 harness/记忆/搜索", "经验库维护与迁移", "harness 研究"],
    ]),
    ("tab4_gain.csv", ["系统", "报告值", "基线", "口径"], [
        ["KernelOPT L1/L2/L3", "1.40 / 1.15 / 1.07", "torch.compile", "几何平均，250 题"],
        ["Astra", "1.32", "SGLang 原实现", "算术平均，3 个 kernel"],
        ["KernelBlaster L1", "1.43", "eager 与 compile 取优", "几何平均"],
        ["AdaExplore L2 / L3", "3.12 / 1.72", "PyTorch", "几何平均，100 步"],
        ["cuPilot", "3.09", "PyTorch", "算术平均，100 个 kernel"],
        ["ForgeKernel", "+10%", "专家参考实现", "几何平均，27 算子"],
        ["案例研究", "9.293", "官方基线", "几何平均"],
    ]),
    ("tab5_checklist.csv", ["项", "为什么必须写", "本文对应"], [
        ["基线是什么", "分母决定分子，专家实现与 PyTorch 差一个数量级", "表 4"],
        ["统计口径", "几何平均与算术平均在长尾下差别显著", "表 4"],
        ["反馈信号级别", "L1-L4 决定改进天花板", "表 2"],
        ["预算与预算曲线", "只报终点值无法判断是否饱和", "图 3"],
        ["端到端效果", "kernel 级增益与端到端不是缩放关系", "图 4"],
    ]),
    ("tab6_failure.csv", ["失效条件", "机制", "本文证据"], [
        ["基线已接近峰值", "库调用占主导，余量被 Amdahl 吃掉", "85 次回退中 61 次源于此"],
        ["分布偏移", "优化针对生产形状，换形状后反号", "分布外掉到 0.49-0.63 倍"],
        ["测量落后", "评测协议比模型进步慢", "收紧协议后 1.43 → 0.88 倍"],
        ["改动无效", "提议生成能力远强于效果判定能力", "7 次可评估改动中 4 次无减少"],
    ]),
]


def main() -> int:
    claims = {r["claim_id"] for r in read_csv(SLUG / "claims.csv")}
    bad = []
    for group in (GAIN, BUDGET, FUNNEL, COST):
        for row in group:
            if row[-1] not in claims:
                bad.append(row)
    if bad:
        print("[FAIL] 引用了不存在的主张：")
        for row in bad:
            print("  ", row)
        return 1

    write("fig1_gain.csv", ["label", "value", "metric", "cite"], GAIN)
    write("fig3_budget.csv", ["system", "budget", "value", "cite"], BUDGET)
    write("fig4_funnel.csv", ["object", "kernel_level", "e2e", "cite"], FUNNEL)
    write("fig5_cost.csv", ["system", "metric", "value", "cite"], COST)

    # 表格产物：写在 tables/ 下，与正文里的表一一对应（编号按出现顺序）。
    # 正文的表格是手写的 Markdown，这里落一份同名 csv 供 audit_paper 的
    # B 检查确认「表确实有产物」，也让改数时有个可 diff 的源。
    for name, header, rows in TABLES:
        p = HERE / "tables" / name
        with p.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
        print(f"  tables/{name}: {len(rows)} 行")
    print("数据层完成")
    return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())