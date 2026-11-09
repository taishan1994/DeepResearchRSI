"""构造论文的数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每一行带一个 cite 列，指向 claims.csv 的主张。audit_paper.py 会顺着
cite -> evidence_ids -> quote 核对每个数值；核对不过就不许出图。
故这里的数字必须先在证据的 quote（或主张的 statement）里出现过。

## 本主题的一条硬约束

Day-0 的 pass@1 与 Optimization 的 speed-up 是**不同量纲**：
前者是「比例」，后者是「倍数」，且分母分别是「尝试次数」与「基线实测」。
把它们放进同一张柱状图就是造假。

故四张图分三组，组内同量纲：
  图 1  赛道结构与题库构成（计数）
  图 2  day-0 的 pass@1 与 f2p（比例，同一批评测内的两个切面）
  图 3  day-0 逐题：谁过了、谁没过（计数）
  图 4  两条连续赛道的速度（倍数，仅同基准同 agent）
跨基准的增益倍数一个都不进图，只进表并逐行标注口径。

## 第二个约束：逐题数据从哪来

「谁过了哪道题」只能从 leaderboard 聚合，而聚合值（如某个 agent 在某题上
passes=1）不是 evidence.quote 的字面内容。故这类数字的做法是：
值写在 claim 的 statement 里，cite 指向该 claim，并在此处注明它是
**对 quote 所述快照的聚合**，不是新观测。
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


# 图 1：题库构成（计数，三种切面）。全部在 c-three-tracks 的 statement 里。
COMPOSE = [
    ("赛道 · Day-0 Model Support", 10, "题", "c-three-tracks"),
    ("赛道 · Inference Optimization", 20, "题", "c-three-tracks"),
    ("赛道 · Bug Fix", 7, "题", "c-three-tracks"),
    ("引擎 · vLLM", 20, "题", "c-three-tracks"),
    ("引擎 · SGLang", 17, "题", "c-three-tracks"),
    ("加速器 · B200", 20, "题", "c-three-tracks"),
    ("加速器 · H100", 17, "题", "c-three-tracks"),
]

# 图 2：两条连续赛道（倍数）。同量纲，可同图。
# 图号按正文出现次序：图 1 题库 → 图 2 两条赛道 → 图 3 逐题 → 图 4 两个切面
SPLIT = [
    ("Sonnet-5.5", "吞吐赛道", 1.5277, "c-oracle-exceeded"),
    ("Sonnet-5.5", "回归赛道", 2.1899, "c-oracle-exceeded"),
    ("Gemini-4-Argon", "吞吐赛道", 1.2833, "c-oracle-exceeded"),
    ("Gemini-4-Argon", "回归赛道", 1.7646, "c-oracle-exceeded"),
]

# 图 4：两个 agent 的两条 day-0 指标（比例，0—1）。同一批评测内的两个切面。
CEILING = [
    ("Sonnet-5.5", "pass@1", 0.2667, "c-ceiling-is-clustered"),
    ("Sonnet-5.5", "f2p 检查项通过率", 0.9006, "c-near-miss-gap"),
    ("最弱 agent", "f2p 检查项通过率", 0.2189, "c-near-miss-gap"),
]
# 注：这里只用带证据锚的三条。Opus-5.5 的 0.1333 与 Gemini-4-Argon 的 0.0667
# 在 leaderboard 的 model_support[1] / [5] 里逐字存在，但本文没有单引那两行，
# 按 P2（数值必须可回溯到 claim 或 evidence）故不入图——宁可少画两根柱子。

# 图 3：day-0 十题的通过情况（每题有多少 agent 曾全通过一次）。
# 这些计数是对 leaderboard 快照的逐题聚合，见本文件顶部第二段说明。
PER_TASK = [
    ("glm53_flash / SGLang", 6, "c-ceiling-is-clustered"),
    ("inkling_small / SGLang", 4, "c-ceiling-is-clustered"),
    ("deepseek_v4_flash / SGLang", 1, "c-ceiling-is-clustered"),
    ("deepseek_v41_flash / vLLM", 1, "c-ceiling-is-clustered"),
    ("kimi_linear / vLLM", 1, "c-ceiling-is-clustered"),
    ("gpt_oss_120b / SGLang", 0, "c-ceiling-is-clustered"),
    ("qwen38_flash_next / vLLM", 0, "c-ceiling-is-clustered"),
    ("diffusiongemma / vLLM", 0, "c-ceiling-is-clustered"),
    ("minimax_m3 / vLLM", 0, "c-ceiling-is-clustered"),
    ("sd3 / SGLang", 0, "c-ceiling-is-clustered"),
]

# 图 4：同一 agent 的两条连续赛道（倍数）。可放在一起，因为都是
# 「相对各自基线的几何平均加速比」，量纲相同。


# 表 1：四代对象（分类表，无数值 cite）
T_GEN = [
    ["代", "基准", "对象", "判据形状", "最好成绩"],
    ["一", "MLE-bench（2024-10）", "跑一个 Kaggle 竞赛（75 个）", "相对人类奖牌的百分位", "16.9%"],
    ["二", "RE-Bench（2024-11）", "一段开放式研究工程（7 个环境）", "与 61 位人类专家的分数比", "2 小时下 4 倍人类"],
    ["三", "PostTrainBench（2026-03）", "后训练一个模型", "下游基准平均分", "23.2% vs 51.1%"],
    ["三·后半", "RSI-Inference Bench（2026-10）", "改一个生产推理引擎（37 题）", "二元 / 几何平均加速比", "pass@1 0.2667"],
    ["四", "RSI-Dojo（2026-10）", "把「做后训练」内化进权重（281 环境）", "同第三代的下游分数", "+16.87 分"],
]

# 表 2：三条赛道的判据对照
T_TRACK = [
    ["赛道", "题数", "目标", "判据", "部分通过怎么算"],
    ["Day-0 Model Support", "10", "把新模型服务起来", "pass@1（全通过次数 / 尝试次数）", "按失败计"],
    ["Inference Optimization", "20", "更快", "几何平均加速比", "正确性不过记 1.00×"],
    ["Bug Fix", "7", "找到并修掉一个性能回归", "几何平均加速比", "同上，另有 guard 形状"],
]

# 表 3：三条禁令与它们堵住的捷径
T_BAN = [
    ["禁令", "堵住的捷径", "若不堵会怎样"],
    ["离线 + 禁查上游历史 / PR / issue / release notes / model hub", "抄那条已合并的修复", "回归题全变成检索题"],
    ["只翻 CLI flag 或改 config 默认值记 0 分", "调参冒充优化", "几何平均会被配置搜索刷满"],
    ["guard 工作负载 min_ratio = 0.95", "牺牲别的形状换计分形状", "单形状加速，端到端变慢"],
    ["pinned commit + git diff inference_base 定义补丁", "夹带与任务无关的改动", "补丁边界不可机械求出"],
    ["day-0 禁用上游 diffusers 整条 pipeline", "把上游实现搬进来当自己的", "考的变成搬运而非实现"],
]

# 表 4：成本结构
T_COST = [
    ["项", "数值", "说明"],
    ["单题 agent 预算", "30000 秒（8.33 小时）", "task.toml 的 agent.timeout_sec"],
    ["引擎重建预算", "7200 秒（2 小时）", "environment.build_timeout_sec"],
    ["验证器预算", "3600 秒（1 小时）", "verifier.timeout_sec"],
    ["SD3 单题检查项", "49 项（47 F2P + 2 P2P）", "全过才给二元奖励"],
    ["执行框架", "vendored 241 个文件", "datacurve/pier @ 3f688a1b"],
    ["权重钉法", "672 条清单 / 540 个 sha256", "model-manifest.json，不分发"],
]

# 表 5：这一族的方法侧进展（全部在 PostTrainBench 上，口径可比）
T_METHOD = [
    ["工作", "做法", "在 PostTrainBench 上", "改了判据吗"],
    ["PostTrainBench 基线", "—", "最好 agent 23.2%", "—"],
    ["DataMaster", "DataTree + Data Pool + Global Memory", "MLE-Bench Lite 奖牌率 +32.27%", "否"],
    ["RSI-Master", "Experiment OS + Reviewer 引导的 DAG", "7 题平均 46.53 → 54.49", "否"],
    ["RSI-Dojo", "281 个可执行环境 + 轨迹微调", "9B +8.74 / 35B +16.87 分", "否"],
]

# 表 6：本文的五条结论与它们的证据强度
T_CONC = [
    ["结论", "主张", "置信", "证据条数"],
    ["对象换过四代，判据每代重造", "c-four-generations", "high", "8"],
    ["三条赛道判据形状不同", "c-three-tracks / c-judgment-shapes", "high", "10"],
    ["天花板是分布不是标量", "c-ceiling-is-clustered", "high", "3"],
    ["失败是「差一点」", "c-near-miss-gap", "high", "2"],
    ["循环未闭合：判定权在循环外", "c-rsi-not-closed / c-method-not-judgment", "high", "7"],
]


TABLES_DEF = [
    ("tab1_generations.csv", ["代", "基准", "对象", "判据形状", "最好成绩"], T_GEN[1:]),
    ("tab2_tracks.csv", ["赛道", "题数", "目标", "判据", "部分通过怎么算"], T_TRACK[1:]),
    ("tab3_bans.csv", ["禁令", "堵住的捷径", "若不堵会怎样"], T_BAN[1:]),
    ("tab4_cost.csv", ["项", "数值", "说明"], T_COST[1:]),
    ("tab5_methods.csv", ["工作", "做法", "在 PostTrainBench 上", "改了判据吗"], T_METHOD[1:]),
    ("tab6_conclusions.csv", ["结论", "主张", "置信", "证据条数"], T_CONC[1:]),
]


def main() -> int:
    claims = {r["claim_id"] for r in read_csv(SLUG / "claims.csv")}
    bad = []
    for group in (COMPOSE, CEILING, PER_TASK, SPLIT):
        for row in group:
            if row[-1] not in claims:
                bad.append(row)
    if bad:
        print("[FAIL] 引用了不存在的主张：")
        for row in bad:
            print("  ", row)
        return 1

    write(DATA, "fig1_compose.csv", ["facet", "value", "unit", "cite"], COMPOSE)
    write(DATA, "fig2_split.csv", ["agent", "track", "value", "cite"], SPLIT)
    write(DATA, "fig3_pertask.csv", ["task", "value", "cite"], PER_TASK)
    write(DATA, "fig4_ceiling.csv", ["agent", "metric", "value", "cite"], CEILING)
    for name, header, rows in TABLES_DEF:
        write(TABLES, name, header, rows)
    print("数据层完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
