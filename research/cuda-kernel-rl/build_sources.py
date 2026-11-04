"""从候选池里确定纳入范围，并生成 sources.csv。

## 判定原则（写下来，否则下次还得重新想）

本专题的问题是「**CUDA kernel 生成中的强化学习**」。一篇论文要进来，
必须同时满足：

  A. 研究对象是「生成或优化 GPU kernel」（CUDA / Triton / Ascend 均可）
  B. RL 是其**方法**，而不是其**工具**

## 被剔除的两类（都是 B 的反面）

1. **用 RL 的 kernel**：`rl-triton`（为 RL 的 credit assignment 写 Triton kernel）、
   `AReaL-TIK`（优化 RL 训练用的 kernel）、`GEAR`（RL 的 experience replay 系统）。
   方向正好相反——它们用 kernel 服务 RL，不是用 RL 生成 kernel。

2. **同名不同义**：
   - `RLVR is a Kernel, Not a Function` —— 这里的 kernel 是统计学「核函数」，与 GPU 无关
   - `Taming Extreme Tokens: Covariance-Aware GRPO with Gaussian-Kernel` —— 同上

## 边界情形（纳入并说明理由）

- `GPU Forecasters`：预测 kernel 性能，不直接生成。但 RL 训练 kernel 生成模型时
  最大的成本是「跑一遍测速」，能预测就能降低奖励获取成本。作为**使能技术**纳入。
- `CuAsmRL`（2025-01）：在 SASS 层用深度 RL 调度指令，是本方向的早期形态，
  虽不是 LLM 驱动，但作为方法谱系的起点纳入。

## 输出

sources.csv：source_id / url / source_type / publisher / title /
            published_at / updated_at / fetched_at / language / trust_tier /
            access / license / notes
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDS = HERE / "candidates_rl.json"
OLD = HERE.parent / "cuda-kernel-gen" / "paper" / "papers.json"

# 明确剔除：ID -> 剔除理由
EXCLUDE = {
    "2609.22547": "kernel 指统计学核函数，与 GPU 无关",
    "2605.11538": "kernel 指高斯核，与 GPU 无关",
    "2310.05205": "用 kernel 服务 RL（experience replay），方向相反",
    "2608.17641": "用 kernel 服务 RL（credit assignment），方向相反",
    "2609.35140": "用 kernel 服务 RL（rollout/update 对齐），方向相反",
    "2609.37851": "rollout 与 kernel 分离指样本生成，非 GPU kernel",
    "2603.16428": "主题是单卡微调的异构协同，非 kernel 生成",
}

TZ = timezone(timedelta(hours=8))
FETCHED = datetime.now(TZ).replace(microsecond=0).isoformat()

# 人工判定的 trust_tier：谁第一次产生了这段观测
#   primary   = 论文自己跑了实验、测了数
#   secondary = 转述他人数据
# 本专题全部是学术论文自测，故 academic -> primary。
# 例外：综述/立场类论文不产生观测 -> secondary。
SURVEY_LIKE = {"2601.07160"}  # AscendKernelGen 系统性研究，含自测，仍算 primary


def src_id(aid: str) -> str:
    return "src-arxiv-" + aid.replace(".", "-")


def main() -> int:
    pool: dict[str, dict] = {}
    for p in json.loads(CANDS.read_text(encoding="utf-8")):
        pool[p["id"]] = p
    # 旧数据集里也有 RL 论文，补充进来（候选池的检索式可能漏掉早期的）
    if OLD.is_file():
        for p in json.loads(OLD.read_text(encoding="utf-8")):
            aid = p.get("id")
            if aid and aid not in pool:
                pool[aid] = p

    rl_re = re.compile(
        r"reinforcement learning|\bRL\b|RLVR|GRPO|PPO|reward", re.I)
    kern_re = re.compile(r"kernel|triton|cuda|sass|gpu program", re.I)
    gen_re = re.compile(
        r"generat|optimi[sz]|program|synthes|writ|code", re.I)

    rows: list[dict[str, str]] = []
    skipped: list[tuple[str, str]] = []
    for aid, p in sorted(pool.items(), key=lambda kv: kv[1]["published"],
                         reverse=True):
        if aid in EXCLUDE:
            skipped.append((aid, EXCLUDE[aid]))
            continue
        blob = (p["title"] + " " + p["abstract"])
        if not (rl_re.search(blob) and kern_re.search(p["title"])):
            continue
        if not gen_re.search(blob):
            continue
        rows.append({
            "source_id": src_id(aid),
            "url": f"https://arxiv.org/abs/{aid}",
            "source_type": "academic",
            "publisher": "arXiv",
            "title": p["title"],
            "published_at": p["published"],
            "updated_at": p.get("updated") or p["published"],
            "fetched_at": FETCHED,
            "language": "en",
            "trust_tier": "primary",
            "access": "open",
            "license": "arXiv 非独占许可",
            "notes": "",
        })

    header = ["source_id", "url", "source_type", "publisher", "title",
              "published_at", "updated_at", "fetched_at", "language",
              "trust_tier", "access", "license", "notes"]
    with (HERE / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"sources.csv: {len(rows)} 条")
    print(f"剔除 {len(skipped)} 条：")
    for aid, why in skipped:
        print(f"  {aid}  {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
