"""构造论文的数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每一行带一个 cite 列，指向 claims.csv 的主张。audit_paper.py 会顺着
cite -> evidence_ids -> quote 核对每个数值；核对不过就不许出图。
故这里的数字必须先在证据的 quote（或主张的 statement/derivation）里出现过。

## 本主题的一个约束

这条线上的增益数字口径互不相同（相对 vLLM 默认 / 相对调优后的 SGLang /
相对朴素 PyTorch）。把它们放进同一张柱状图就是造假。
故四张图只画**同一篇论文内部的对照**：交付漏斗、跨档位反号、验证覆盖率、
诚实基线前后的缩水。跨论文的增益只进表，且逐行标注基线。
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
    print("  %s/%s: %d 行" % (dir_.name, name, len(rows)))


# 图 1：交付漏斗。33 次运行 -> 22 次通过验证 -> 13 次超过最强基线。
# 三个数都在 e-030 的 quote 里。
FUNNEL = [
    ("提交的运行", 33, "c-delivery-uneven"),
    ("通过验证", 22, "c-delivery-uneven"),
    ("超过最强基线", 13, "c-delivery-uneven"),
]

# 图 2：同一 agent 跨档位反号。2.84 / 0.98 / 1.47 都在 e-032 的 quote 里。
CROSS = [
    ("GPT 6.1 Sol @ Qwen3.5 9B", 2.84, "c-delivery-uneven"),
    ("GPT 6.1 Sol @ Qwen3.8 27B INT4", 0.98, "c-delivery-uneven"),
    ("该档参考值", 1.47, "c-delivery-uneven"),
]

# 图 3：验证覆盖。5/33 与 8/11 分别在 e-040、e-041 的 quote 里。
VERIFY = [
    ("做了「自然停止」检查的提交", 5, "c-verification-gap"),
    ("全部提交", 33, "c-verification-gap"),
    ("提交前已有症状的失败", 8, "c-verification-gap"),
    ("全部未通过", 11, "c-verification-gap"),
]

# 图 4：诚实基线把增益打回原形。10.6 与 2.03 都在 c-measurement 的 statement 里。
HONEST = [
    ("对着朴素基线", 10.6, "c-measurement"),
    ("对着诚实基线", 2.03, "c-measurement"),
]

T_GAPS = [
    ["缺口", "原来的做法", "ServerBench 的改法"],
    ["负载简化", "独立请求，或固定 prefill / decode 场景", "回放真实 coding-agent 会话：多轮、共享前缀、并行子 agent 分支、轮间延迟"],
    ["只比加速比", "相对基线的加速或吞吐，负载固定", "每美元 GPU 成本的合格 token 价值，且「服务多少负载」由 agent 决定"],
    ["只查正确性", "对参考实现或测试集查输出", "在全新部署、留出种子上回放，并检查完整提示、输出长度、流式一致性与留出集准确率"],
]

T_LADDER = [
    ["尺度", "任务数", "来源", "判据形状", "代表"],
    ["单 kernel", "250 个负载", "PyTorch 算子", "fast_p + 正确性", "KernelBench"],
    ["优化补丁", "54 个任务", "vLLM / SGLang 已合并 PR", "硬指标 + 软指标", "ISO-Bench"],
    ["仓库级功能", "53 / 36 个任务", "SGLang 生产变更 / Megatron-LM·vLLM·verl", "隐藏功能测试 + 回归测试", "SWE-Serve / InfraDev"],
    ["整套服务系统", "33 次运行", "真实 coding-agent 轨迹", "端到端回放 + 独立验证", "ServerBench"],
]

T_GAIN = [
    ["工作", "报告的增益", "基线是什么", "可否跨行比较"],
    ["ServerBench", "4.87 倍（Gemma E4B）", "vLLM 参考", "否：目标函数不同"],
    ["VibeServe", "2.3 倍 goodput", "调优后的 SGLang（397B MoE，4×MI300A）", "否：goodput 非 dollars-per-dollar"],
    ["SEIS", "3.27 倍吞吐", "原始 mini-sglang（Qwen3-0.6B，H100）", "否：单请求场景"],
    ["InferenceBench", "最高 8.08 倍", "朴素 PyTorch", "否：两小时预算内"],
    ["KernelBench", "不到 20% 追平", "PyTorch", "否：单 kernel"],
    ["AutoTuneBench", "10.6 倍 → 2.03 倍", "朴素 → 诚实基线", "这是对上一行的修正"],
]

T_FAIL = [
    ["失败模式", "具体表现", "出处"],
    ["容量与并发不协调", "先提并发再改服务，TPOT 恶化后不收敛负载", "ServerBench"],
    ["反馈脱离负载", "用随机文本探针判断优化好坏", "ServerBench"],
    ["验证覆盖不到新路径", "准入边界、跨请求前缀复用、抢占恢复都没测", "ServerBench"],
    ["过早收敛", "枚举了很多技术，却只在一个框架里试少数配置", "InferenceBench"],
    ["优化压力诱发刷分", "优化目标本身把 agent 推向 reward hacking", "InferenceBench"],
    ["窄分布硬编码", "对特定张量值绕过计算来「加速」", "KernelBench-Verified"],
    ["识别对但写不出", "找到正确瓶颈，交不出可用解法", "ISO-Bench"],
    ["本地正确不等于生产正确", "单元测试过，端到端服务测试挂", "SWE-Serve"],
]

T_MEASURE = [
    ["失效模式", "后果", "对策"],
    ["稻草人基线", "加速比被高估", "基线冻结成代码，外部锚定"],
    ["绝对时间不跨机", "同一配置换机器就变", "配对种子统计，跨机变异系数上限"],
    ["饱和任务", "比较无意义", "预注册读数，饱和任务上做 A/B"],
    ["基础设施缺陷", "把环境问题当成结论", "审计留痕，协议外结果在数据库层拒绝"],
]

T_POSITION = [
    ["能力", "谁做到了", "缺哪一半"],
    ["自动改整套服务系统", "VibeServe / SEIS / ServerBench", "—"],
    ["跨会话继承经验与代码", "SEIS", "判定权不在循环里"],
    ["目标函数塑形行为", "ServerBench", "开发预算一次性，无继承"],
    ["独立验证与事后评审", "ServerBench", "验证由人设计，未自动化"],
    ["agent 自己演化评测", "尚无", "SEIS 作者列为「下一步」"],
]

TABLES_DEF = [
    ("tab1_gaps.csv", ["缺口", "原来的做法", "ServerBench 的改法"], T_GAPS[1:]),
    ("tab2_ladder.csv", ["尺度", "任务数", "来源", "判据形状", "代表"], T_LADDER[1:]),
    ("tab3_gain.csv", ["工作", "报告的增益", "基线是什么", "可否跨行比较"], T_GAIN[1:]),
    ("tab4_fail.csv", ["失败模式", "具体表现", "出处"], T_FAIL[1:]),
    ("tab5_measure.csv", ["失效模式", "后果", "对策"], T_MEASURE[1:]),
    ("tab6_position.csv", ["能力", "谁做到了", "缺哪一半"], T_POSITION[1:]),
]


def main() -> int:
    claims = {r["claim_id"] for r in read_csv(SLUG / "claims.csv")}
    bad = []
    for group in (FUNNEL, CROSS, VERIFY, HONEST):
        for row in group:
            if row[-1] not in claims:
                bad.append(row)
    if bad:
        print("[FAIL] 引用了不存在的主张：")
        for row in bad:
            print("  ", row)
        return 1

    write(DATA, "fig1_funnel.csv", ["item", "count", "cite"], FUNNEL)
    write(DATA, "fig2_cross.csv", ["item", "value", "cite"], CROSS)
    write(DATA, "fig3_verify.csv", ["item", "count", "cite"], VERIFY)
    write(DATA, "fig4_honest.csv", ["item", "speedup", "cite"], HONEST)
    for name, header, rows in TABLES_DEF:
        write(TABLES_DIR, name, header, rows)
    print("数据层完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
