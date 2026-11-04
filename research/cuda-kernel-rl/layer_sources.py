"""给来源分层：核心 RL 方法 / 邻接 / 外围基础设施。

## 为什么必须分层

`sources.csv` 里 45 篇，但有 18 篇摘要一次 RL 都没提。它们是被
`optimi[sz]`、`gpu program` 这类宽泛词带进来的：

  - `MultiKernelBench` / `SOL-ExecBench` / `EdgeKernelBench`：纯基准
  - `KernelBench-Verified` / `Measuring the Checker`：评测协议审计
  - `Spec Sheets Are Not Kernels`：ISA 级审计
  - `STARK` / `EGG` / `CuBridge` / `PEAK`：多智能体或工具框架，不含训练

把它们和 `CUDA-L1`、`Dr. Kernel` 并列，会让「RL 方法有几篇」这个
统计失真，也会让综述的论证重心漂移。

## 分层定义

  core      摘要明确以 RL 为方法训练 kernel 生成模型
            （出现 reinforcement learning / RL / RLVR / GRPO / PPO
             且用于 kernel 生成或优化）
  adjacent  与 RL 训练直接相关但不含训练：奖励设计、数据合成、
            环境反馈、性能预测（降低奖励获取成本）
  infra     基准、评测协议、形式化验证、审计。作为证据引用，
            不作为「RL 方法」计数

## 输出

在 sources.csv 的 notes 列写 `layer=core|adjacent|infra`，
并打印分层统计。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "candidates_rl.json"
OLD = HERE.parent / "cuda-kernel-gen" / "paper" / "papers.json"

# 人工判定：adjacent 与 infra 逐条指定。
# 不能自动判——「摘要里没有 RL 字样」不等于无关，
# 例如 GPU Forecasters 全篇讲性能预测，是奖励成本的关键使能技术。
LAYER: dict[str, str] = {
    # ---- adjacent：服务 RL 训练但不训练模型 ----
    "2605.31464": "adjacent",  # GPU Forecasters：预测性能，替代实测
    "2608.01804": "adjacent",  # Don't Regenerate, Debug：反馈信号设计
    "2608.01804 ": "adjacent",
    "2608.01804": "adjacent",
    "2608.02712": "adjacent",  # Don't Regenerate, Debug
    "2603.10846": "adjacent",  # Cold-Start Drafting：课程/冷启动
    "2603.07169": "adjacent",  # Multi-Scenario：奖励场景化
    "2606.26453": "adjacent",  # Micro-Profiling：专家工具当环境信号
    "2606.16231": "adjacent",  # CUDA-Sensitive Instruction Tuning：SFT 前置
    "2606.26758": "adjacent",  # EGG：专家引导的 agent
    "2602.12305": "adjacent",  # OptiML：程序合成流水线
    "2511.12294": "adjacent",  # ProofWright：形式化验证当奖励来源
    "2510.16996": "adjacent",  # STARK：多 agent 精修
    "2512.19018": "adjacent",  # PEAK：性能工程助手
    "2507.17773": "adjacent",  # MultiKernelBench
    # ---- infra：基准与评测协议 ----
    "2607.16241": "infra",     # KernelBench-Verified
    "2609.22220": "infra",     # Measuring the Checker
    "2608.11693": "infra",     # Spec Sheets Are Not Kernels
    "2603.19173": "infra",     # SOL-ExecBench
    "2610.24648": "infra",     # EdgeKernelBench
    "2608.21836": "infra",     # LLM4LLM（部署闭环）
    "2605.05023": "infra",     # CuBridge（反汇编理解）
    "2602.14293": "infra",     # KernelBlaster（记忆增强，无训练）
    "2603.28342": "infra",     # Kernel-Smith（进化搜索，非 RL 训练）
}


def main() -> int:
    pool: dict[str, dict] = {}
    for p in json.loads(CANDS.read_text(encoding="utf-8")):
        pool[p["id"]] = p
    if OLD.is_file():
        for p in json.loads(OLD.read_text(encoding="utf-8")):
            if p.get("id"):
                pool.setdefault(p["id"], p)

    rl_re = re.compile(r"reinforcement learning|\bRL\b|RLVR|GRPO|PPO", re.I)

    rows: list[dict[str, str]] = []
    with (HERE / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("sources.csv 为空，先跑 build_sources.py")
        return 1

    counts = {"core": 0, "adjacent": 0, "infra": 0}
    for r in rows:
        sid = r["source_id"]
        aid = sid[len("src-arxiv-"):]
        aid = re.sub(r"^(\d{4})-(\d{4,5})$", r"\1.\2", aid)
        p = pool.get(aid, {})
        blob = (p.get("title", "") + " " + p.get("abstract", ""))
        if aid in LAYER:
            layer = LAYER[aid]
        elif rl_re.search(blob):
            layer = "core"
        else:
            layer = "adjacent"
        counts[layer] += 1
        note = r.get("notes") or ""
        note = re.sub(r"layer=\w+", "", note).strip()
        r["notes"] = (f"layer={layer} " + note).strip()

    header = list(rows[0].keys())
    with (HERE / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"分层完成：{counts}")
    print(f"合计 {sum(counts.values())} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
