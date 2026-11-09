"""把 rsi-inference-bench 的来源与文档层建起来。

## 为什么这一篇的来源类型和站内其他篇不一样

站内 13 个归档里，12 个是纯 arXiv 的。这一篇不是：
它的**锚点没有论文**。RSI-Inference Bench 的 README 写着 `Paper: coming soon`，
CITATION.cff 也只是 `@misc` 指向仓库本身。所以它的第一手事实全部在仓库里
（README、任务说明书、task.toml、leaderboard.html）。

这不是缺陷，而是这一族基准的共同形态：**arXiv 上没有它，检索式再怎么写也捞不到。**
这正是它此前从未入库的直接原因，故本脚本把「为什么漏」写成了一等公民。

## 一个文件一个 source 的粒度

arXiv 论文按 `source_id = src-arxiv-<id>`；仓库文件按语义分组成
`src-ml-rsi-bench-*`。同一个仓库的不同文件不合并成一个 source，
因为它们的 trust_tier 与可回溯性不同：
  README      —— 作者自述的口径
  task.toml   —— 机器可读的判据（oracle_speedup 这类数字只在这里）
  leaderboard —— 发布时的排行榜快照（带时间戳，会变）
  instruction —— 任务书原文，禁令条款只在这里
"""

from __future__ import annotations

import csv
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent / "_rel_docs" / "rsi-bench"
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
FETCHED = datetime.now(TZ).replace(microsecond=0).isoformat()

# 仓库快照：(id 后缀, 本地文件, 来源标题, 发布日, parser_version, 备注)
REPO = [
    ("readme", "readme.md",
     "RSI-Inference Bench README：赛道定义、评分工序、仓库入口", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜口径｜三条赛道（Day-0 10 / Optimization 20 / Bug Fix 7）、"
     "pass@1 与 speed-up 的算法、8 小时离线预算、独立 verifier。"
     "⚠️ 徽章写 Paper: coming soon，故本条是这一篇唯一的一手口径来源"),
    ("leaderboard", "leaderboard_raw.html",
     "RSI-Inference Bench leaderboard 原始快照（docs/leaderboard.html，含内嵌 window.RSI_LEADERBOARD）",
     "2026-10-25", "raw-copy-v1",
     "layer=anchor｜结果｜逐字节下载的原始 HTML。数据在 window.RSI_LEADERBOARD 里，"
     "写着 snapshot id=2026-10-25T2208Z：15 个 agent × 两条赛道 + 37 题每题每 agent 的 "
     "passes/attempts/f2p。⚠️ 它的数字写成 `.2667` 这种省略前导零的形式，"
     "不是合法 JSON——这份原文是这一事实的唯一证据"),
    ("leaderboard-json", "rsi-leaderboard.json",
     "RSI-Inference Bench leaderboard 的重序列化版（分析用，非一手）",
     "2026-10-25", "derived-json-v1",
     "layer=anchor｜结果｜由 leaderboard_raw.html 内嵌对象**重排版**得到（补前导零、缩进）。"
     "⚠️ 这不是一手材料：它的每一个字都能在上一条里找到，"
     "保留它只为让「逐题聚合」这类计算可被重跑，故 parser_version 标 derived"),
    ("task-day0-sd3", "task_sd3_instruction.md",
     "task 说明书：Support Stable Diffusion 3 in SGLang（2×H100）", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜任务书｜最长的一份 day-0 任务书（143 行）：把 CLIP-L/CLIP-G/T5/MMDiT/"
     "scheduler/16 通道 VAE 接进 SGLang 的 registry 与 pipeline stage。"
     "禁令原文在此：Complete Diffusers/Transformers models, pipelines and loaders are prohibited"),
    ("task-day0-minimax", "task_minimax_instruction.md",
     "task 说明书：Support MiniMax-M3-MXFP8 in vLLM（4×B200，TP4）", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜任务书｜唯一显式要求「efficiency 也算验收」的 day-0 题："
     "MSA 四个算子要在长上下文下不随序列长度增长。说明 day-0 不完全是二元判据"),
    ("task-regression", "task_regression_instruction.md",
     "task 说明书：recover the decode-throughput regression（8×B200，DP8+EP）",
     "2026-10-16", "raw-copy-v1",
     "layer=anchor｜任务书｜回归赛道的判据写成连续值：几何平均 baseline_mean/candidate_mean，"
     "1.0x 不计分、无上限、guard shape 变慢则清零"),
    ("task-regression-toml", "task_regression_task.toml",
     "task.toml：regression_fp8_decode_throughput 的判据与 oracle", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜判据｜机器可读的那一半：noise_floor=1.03、oracle_speedup=1.206、"
     "guard min_ratio=0.95、pinned commit a4047d4e。"
     "「oracle 来自上游已合并修复」这句话只在这里写了 source=upstream_merged_fix"),
    ("task-optimize-qwen", "task_optimize_qwen_instruction.md",
     "task 说明书：vLLM throughput optimization on Qwen3.6-27B（1×H100）", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜任务书｜优化赛道的口径来源：CLI flag 翻转与改默认值被判 category=config、"
     "记 0 分——这是「判据防刷分」最直接的一条实现"),
    ("task-optimize-toml", "task_optimize_qwen_task.toml",
     "task.toml：optimize_qwen3_6_27b_1xh100_open 的判据与基线", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜判据｜优化赛道另一条：与 regression 共用 score_profile 但无 oracle，"
     "因为它不是「修一个已知缺陷」而是开放式提速"),
    ("task-day0-sd3-toml", "task_sd3_task.toml",
     "task.toml：support_sd3_2xh100_sglang 的 verifier 与超时", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜判据｜day-0 赛道的工序事实：agent timeout 与 verifier timeout 分开设，"
     "verifier 4 小时、build 2 小时——验证本身比 agent 干活还贵"),
    ("task-day0-minimax-toml", "task_minimax_task.toml",
     "task.toml：support_minimax_m3_4xb200_vllm 的判据与模型元数据", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜判据｜day-0 赛道里唯一带 efficiency 阈值的题，判据不是纯二元"),
    ("pier-readme", "pier_readme.md",
     "third_party/pier README：Harbor 兼容的 coding-agent 评测框架", "2026-10-16",
     "raw-copy-v1",
     "layer=adjacent｜harness｜承载 37 题的执行框架，vendored 进仓库。"
     "它决定了「可独立重跑」这一性质由谁提供"),
    ("acknowledgements", "acknowledgements", "ACKNOWLEDGEMENTS：基准的上游依赖",
     "2026-10-16", "raw-copy-v1",
     "layer=adjacent｜来源｜列出它依赖哪些公开基准与引擎，可反查它自认的谱系"),
    ("citation", "citation.cff", "CITATION.cff：作者与引用方式", "2026-10-16",
     "raw-copy-v1",
     "layer=anchor｜元数据｜5 位作者（Junteng Liu / Richard He Bai / Huangjie Zheng / "
     "Yizhe Zhang / Ruixiang Zhang），Apple ML Research。无 arXiv id"),
]

# arXiv 谱系：(arxiv_id, 标题, 发布日, 层, 标签, 备注)
ARXIV = [
    ("2410.07095", "MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering",
     "2024-10-09", "core", "gen1-kaggle",
     "这一族的起点：75 个 Kaggle 竞赛 + 人类奖牌基线。对象是「跑一个竞赛」，"
     "判据是相对人类奖牌的百分位"),
    ("2411.15114", "RE-Bench: Evaluating frontier AI R&D capabilities of language model agents against human experts",
     "2024-11-22", "core", "gen2-research-eng",
     "第二代：7 个开放式 ML 研究工程环境 + 61 位人类专家的 71 次 8 小时尝试。"
     "「8 小时预算 + 与人类比」的形状从这里来"),
    ("2603.08640", "PostTrainBench: Can LLM Agents Automate LLM Post-Training?",
     "2026-03-09", "core", "gen3-posttrain",
     "第三代：对象从「写代码」换成「训练一个模型」。"
     "首次把 reward hacking 当成一等发现（训练集当测试集、换 checkpoint、盗用 API key）"),
    ("2605.10906", "DataMaster: Data-Centric Autonomous AI Research",
     "2026-05-11", "adjacent", "posttrain-method",
     "在 PostTrainBench 上刷分的方法之一：DataTree + Data Pool + Global Memory。"
     "提供「这一族的分数是能被方法推上去的」的证据"),
    ("2606.31551", "AutoTrainess: Teaching Language Models to Improve Language Models Autonomously",
     "2026-06-30", "adjacent", "posttrain-method",
     "同为 PostTrainBench 上的方法：把 planning/data/training/eval 暴露成显式工作流"),
    ("2609.35561", "RSI-Master: Structuring Experiments to Guide Autonomous Model Improvement",
     "2026-09-28", "core", "gen3-method",
     "直接以 RSI 立论：Experiment OS + Reviewer 引导的 DAG。"
     "自报 0.0% hacking rate，且 35B 上超过人类开发的 Instruct 模型"),
    ("2611.03698", "Training LLM Agents to Automate LLM Post-Training with RSI-Dojo",
     "2026-10-29", "core", "gen4-internalize",
     "第四代的分水岭：把「做后训练」内化进权重，而不是靠脚手架。"
     "281 个可执行环境 + 轨迹微调，小模型追上前沿"),
    ("2611.06263", "CLEAR: Structured Specifications for Controllable Long-Horizon ML Research Engineering",
     "2026-11-04", "adjacent", "spec",
     "与本文同期的反向工作：不谈怎么让 agent 更强，谈怎么把规格写清使长程 ML 工程可控"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    src_rows, doc_rows = [], []

    for suffix, local, title, pub, parser, note in REPO:
        raw = REL / local
        if not raw.is_file():
            print(f"[FAIL] 缺快照：{raw}")
            return 1
        sid = f"src-ml-rsi-bench-{suffix}"
        did = f"doc-ml-rsi-bench-{suffix}"
        dst = DOCS / f"{did}.txt"
        shutil.copyfile(raw, dst)
        pub_at = "2026-10-16"
        upd_at = "2026-10-25" if suffix == "leaderboard" else pub_at
        src_rows.append([sid,
                         "https://github.com/apple-aiml-research/ml-rsi-inference-bench",
                         "official", "Apple ML Research / apple-aiml-research",
                         title, pub_at, upd_at, FETCHED, "en", "primary", "open",
                         "Apple Sample Code License", note])
        doc_rows.append([did, sid, sha(dst), parser,
                         dst.stat().st_size, f"documents/{did}.txt"])

    for aid, title, pub, layer, tag, note in ARXIV:
        raw = REL / f"arxiv-{aid}.txt"
        if not raw.is_file():
            print(f"[FAIL] 缺快照：{raw}")
            return 1
        sid = "src-arxiv-" + aid.replace(".", "-")
        did = "doc-arxiv-" + aid.replace(".", "-")
        dst = DOCS / f"{did}-full.txt"
        shutil.copyfile(raw, dst)
        src_rows.append([sid, f"https://arxiv.org/abs/{aid}", "academic", "arXiv",
                         title, pub, pub, FETCHED, "en", "primary", "open", "arXiv",
                         f"layer={layer}｜{tag}｜{note}"])
        doc_rows.append([did, sid, sha(dst), "arxiv-html-v1",
                         dst.stat().st_size, f"documents/{did}-full.txt"])

    with (HERE / "sources.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["source_id", "url", "source_type", "publisher", "title",
                    "published_at", "updated_at", "fetched_at", "language",
                    "trust_tier", "access", "license", "notes"])
        w.writerows(src_rows)

    with (HERE / "documents.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["document_id", "source_id", "content_hash", "parser_version",
                    "byte_size", "snapshot"])
        w.writerows(doc_rows)

    print(f"sources {len(src_rows)}（仓库 {len(REPO)} + arXiv {len(ARXIV)}）"
          f" ／ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
