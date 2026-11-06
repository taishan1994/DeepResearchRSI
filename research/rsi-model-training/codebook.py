"""把 61 篇纳入工作编码成可统计的标签表。

## 为什么需要一张编码表

综述里「29 篇用可判定奖励」这类数字不是读出来的，是**数出来的**。
数之前必须先有一张「每篇属于哪一类」的表，否则统计不可复现，
也无法被第三方核对。

## 编码口径（codebook）

三个维度，每个都必须能由摘要原文判定，不依赖读全文：

- `layer`：这篇工作的**主要贡献改的是什么**
    - `weights`  模型参数（自生成数据/奖励 → 再训练）
    - `evaluator` 评判器本身（judge / reward model / verifier）
    - `harness`  冻结模型的提示、代码、记忆、技能、编排
    - `context`  推理时的上下文（反思、记忆、技能库），不落盘成代码
    - `process`  改进过程本身（让 agent 去训练模型 / 改写自己的改进策略）
    - `analysis` 测量、审计、理论、综述（不提出改进方法，或方法不是重点）
- `reward`：仅 `weights` 层填写，**奖励信号从哪来**
    - `answer` 结果可判定（答案、测试、执行器、环境反馈）
    - `judge`  由模型打分（自评、或学到的评判器）
    - `proxy`  用统计量或自生成信号替代判定（置信度、熵、特权示范、末 token 概率）
- `metric`：摘要里给出的主指标类型（用于统计「报了什么」）
    - `pass1` / `passk` / `winrate` / `accuracy` / `success` / `speed` / `none`

## 这张表是判断，不是事实

每一行都可以被反对：Self-Rewarding 既可算 `weights` 也可算 `evaluator`。
故 paper 的附录会给出判据，让读者能按自己的口径重数。
"""
from __future__ import annotations
import csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# arxiv_id: (layer, reward, metric)
LABELS: dict[str, tuple[str, str, str]] = {
    "2203.14465": ("weights",   "answer", "accuracy"),   # STaR
    "2308.08998": ("weights",   "judge",  "none"),       # ReST
    "2401.01335": ("weights",   "answer", "winrate"),    # SPIN
    "2401.10020": ("weights",   "judge",  "winrate"),    # Self-Rewarding
    "2407.19594": ("weights",   "judge",  "winrate"),    # Meta-Rewarding
    "2402.06457": ("weights",   "answer", "accuracy"),   # V-STaR
    "2403.09629": ("weights",   "answer", "accuracy"),   # Quiet-STaR
    "2404.19733": ("weights",   "answer", "accuracy"),   # Iterative RPO
    "2502.18449": ("weights",   "answer", "pass1"),      # SWE-RL
    "2411.02337": ("weights",   "answer", "success"),    # WebRL
    "2504.20073": ("weights",   "answer", "success"),    # RAGEN
    "2505.03335": ("weights",   "answer", "accuracy"),   # Absolute Zero
    "2508.05004": ("weights",   "answer", "accuracy"),   # R-Zero
    "2508.14029": ("weights",   "answer", "passk"),      # SvS
    "2511.16043": ("weights",   "answer", "pass1"),      # Agent0
    "2512.18552": ("weights",   "answer", "pass1"),      # SSR
    "2506.10943": ("weights",   "answer", "accuracy"),   # SEAL
    "2610.32770": ("weights",   "proxy",  "accuracy"),   # On-Policy Self-Training
    "2510.14943": ("weights",   "proxy",  "accuracy"),   # LaSeR
    "2503.00735": ("weights",   "answer", "accuracy"),   # LADDER
    "2506.01716": ("weights",   "answer", "success"),    # Self-Challenging
    "2511.10395": ("weights",   "answer", "success"),    # AgentEvolver
    "2610.41296": ("weights",   "proxy",  "accuracy"),   # Auxiliary Rewards
    "2607.23802": ("weights",   "answer", "success"),    # RLSVR
    "2609.36750": ("weights",   "judge",  "accuracy"),   # GMAE
    "2505.19866": ("weights",   "answer", "accuracy"),   # HS-STaR
    "2502.04780": ("weights",   "answer", "accuracy"),   # SiriuS
    "2408.02666": ("evaluator", "judge",  "winrate"),    # Self-Taught Evaluators
    "2408.08435": ("harness",   "na",     "accuracy"),   # ADAS
    "2410.04444": ("harness",   "na",     "speed"),      # Gödel Agent
    "2505.22954": ("harness",   "na",     "pass1"),      # DGM
    "2504.15228": ("harness",   "na",     "success"),    # SICA
    "2506.13131": ("harness",   "na",     "speed"),      # AlphaEvolve
    "2509.19349": ("harness",   "na",     "none"),       # ShinkaEvolve
    "2406.07496": ("harness",   "na",     "accuracy"),   # TextGrad
    "2310.03714": ("harness",   "na",     "accuracy"),   # DSPy
    "2309.16797": ("harness",   "na",     "accuracy"),   # Promptbreeder
    "2309.03409": ("harness",   "na",     "accuracy"),   # OPRO
    "2309.08532": ("harness",   "na",     "accuracy"),   # EvoPrompt
    "2610.32026": ("harness",   "na",     "none"),       # RSI-Opt
    "2611.04035": ("harness",   "na",     "success"),    # Recursa
    "2303.17651": ("context",   "na",     "accuracy"),   # Self-Refine
    "2303.11366": ("context",   "na",     "pass1"),      # Reflexion
    "2305.16291": ("context",   "na",     "none"),       # Voyager
    "2409.07429": ("context",   "na",     "success"),    # AWM
    "2610.33624": ("process",   "na",     "winrate"),    # RSI Arena
    "2305.17493": ("analysis",  "na",     "none"),       # Curse of Recursion
    "2404.01413": ("analysis",  "na",     "none"),       # Is Collapse Inevitable
    "2504.13837": ("analysis",  "na",     "passk"),      # Does RL Incentivize
    "2610.30009": ("analysis",  "na",     "none"),       # Dreaming Learning
    "2610.27610": ("analysis",  "na",     "none"),       # Auditing the Product
    "2610.27465": ("analysis",  "na",     "none"),       # Recoverability
    "2610.35193": ("analysis",  "na",     "none"),       # Trustworthy RSI
    "2607.07663": ("analysis",  "na",     "none"),       # RSI survey
    "2610.38392": ("analysis",  "na",     "none"),       # Masked Erosion
    "2611.01304": ("analysis",  "na",     "none"),       # When LLMs Modify
    "2507.21046": ("analysis",  "na",     "none"),       # Survey self-evolving
    "2508.07407": ("analysis",  "na",     "none"),       # Comprehensive survey
    "2412.14352": ("analysis",  "na",     "none"),       # Inference-time survey
    "2510.08977": ("analysis",  "na",     "none"),       # Self-Confirming Loop
    "2601.22513": ("analysis",  "na",     "none"),       # Why Self-Rewarding Works
}


def main() -> int:
    pool = json.loads((HERE / "candidates_rsi.json").read_text(encoding="utf-8"))
    # notes/ 里是补取与标题检索的中间语料，见 notes/README.md。
    extra = json.loads((HERE / "notes" / "_extra.json").read_text(encoding="utf-8"))
    resolved = json.loads((HERE / "notes" / "_resolved.json").read_text(encoding="utf-8"))
    resolved_extra = json.loads((HERE / "notes" / "_resolved_extra.json").read_text(encoding="utf-8"))
    meta: dict[str, dict] = {}
    # ⚠️ 必须合并三处语料。候选池只有被检索式命中的论文；
    #    经典工作（STaR、SPIN、Self-Rewarding…）不在任何一条检索式的结果里
    #    ——它们的标题不含 self-improving/self-evolving 这类字面词。
    #    只读 candidates_rsi.json 会把 33 篇核心工作判成「不在语料中」。
    for r in pool + extra + resolved + resolved_extra:
        meta.setdefault(r["id"].split("v")[0], r)
    missing = [k for k in LABELS if k not in meta]
    if missing:
        raise SystemExit(f"标签里有 {len(missing)} 个 id 不在语料中：{missing}")

    rows = []
    for aid, (layer, reward, metric) in sorted(LABELS.items(), key=lambda kv: meta[kv[0]]["published"]):
        r = meta[aid]
        rows.append({
            "arxiv_id": aid,
            "source_id": "src-arxiv-" + aid.replace(".", "-"),
            "title": r["title"],
            "published": r["published"],
            "layer": layer,
            "reward": reward,
            "metric": metric,
        })
    out = HERE / "corpus_labels.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL,
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"编码 {len(rows)} 篇 -> {out.name}")
    from collections import Counter
    for key in ("layer", "reward", "metric"):
        print(f"  {key:7s}", dict(Counter(r[key] for r in rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
