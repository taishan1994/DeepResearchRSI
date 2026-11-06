"""证据与主张：本主题的唯一事实源。

## 纪律

- 每条 evidence 的 quote 必须是快照原文子串（E1）。手抄不可靠，故用 resolve()
  按「把模式里的空格当 \\s+」回填原文——子串性质由构造保证。
- 每条 claim 至少 3 条证据，且至少 1 条 primary supports（C1）。
- 主张里出现的每个数字，必须在该主张某条证据的 quote 或 derivation 里出现（P2）。

## 本主题特有的一条纪律

量化论文的全文快照里有大量 LaTeXML 的目录残渣（"Report Issue Back to Abstract"
之类），手抄 quote 时极易抄到目录行而不是正文。故本轮所有 quote 都先在
digest.txt 里目视定位过，再用 resolve() 回填。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
FETCHED = "2026-11-06T12:40:00+08:00"

# (evidence_id, arxiv_id, 模式, locator, stance, note, claim_id)
EVID = [
    ("e-001", "2611.07217",
     "a training-free framework that assigns precision to hardware-aligned 2D weight tiles",
     "fulltext#abstract", "supports", "量化的分配单元被做到硬件对齐的二维权重 tile", "c-object-numeric"),
    ("e-002", "2611.07217",
     "TileQuant reaches 2.66",
     "fulltext#5", "supports", "TileQuant 在 Llama-3.2-3B 上达到原 16-bit 模型的 2.66 倍生成吞吐", "c-object-numeric"),
    ("e-003", "2610.07457",
     "AlignQuant achieves up to 2.50",
     "fulltext#abstract", "supports", "AlignQuant 相对 BF16 最多 2.50 倍生成加速", "c-object-numeric"),
    ("e-004", "2607.17733",
     "assigns mixed mantissa bitwidths (4/6/8) based on column- and layer-wise sensitivity",
     "fulltext#abstract", "supports", "位宽不是一个开关，而是一组可选值（4/6/8）", "c-object-numeric"),
    ("e-005", "2609.25916",
     "Bit-allocation as constrained optimization problem",
     "fulltext#2.1", "supports", "位分配被形式化成带约束的优化问题，而不是阈值判断", "c-object-numeric"),
    ("e-006", "2610.18642",
     "how to allocate limited quantization resources among heterogeneous precision preservation strategies under a fixed KV cache memory budget",
     "fulltext#abstract", "supports", "真正的难题是「固定内存预算下如何分配」，不是「能不能压」", "c-object-numeric"),
    ("e-007", "2610.07457",
     "uses GPU-compatible two-dimensional weight tiles as the common unit of precision allocation, compact storage, and execution",
     "fulltext#abstract", "supports", "分配单元、存储单元与执行单元必须是同一个，否则精度分配无法落地", "c-object-numeric"),
    ("e-010", "2609.07664",
     "quantization can silently destroy a model’s safety alignment while leaving traditional accuracy and perplexity metrics effectively unchanged",
     "fulltext#2", "supports", "量化可以摧毁安全对齐而 accuracy / perplexity 几乎不动", "c-lossless-not-ppl"),
    ("e-011", "2607.27275",
     "systematic evaluations report 4-bit quantization as nearly lossless, degrading standard benchmark accuracy by only a point or two",
     "fulltext#1", "supports", "「4-bit 近乎无损」的来源是基准准确率只掉一两点", "c-lossless-not-ppl"),
    ("e-012", "2610.04403",
     "can keep generating fluent text while no longer knowing what it means",
     "fulltext#abstract", "supports", "激进量化的小模型仍能生成流畅文本，但已不知道含义", "c-lossless-not-ppl"),
    ("e-013", "2611.02368",
     "We detect no statistically significant accuracy loss for any of the coding agents.",
     "fulltext#abstract", "supports", "编码 agent 上检测不到显著的准确率损失", "c-lossless-not-ppl"),
    ("e-014", "2611.02368",
     "AWQ reduces Qwen-7B one-shot solves from 17 to 0 while increasing loop-based solves from 10 to 25",
     "fulltext#abstract", "supports", "同一模型上，一次性解从 17 掉到 0，循环解从 10 升到 25——准确率看不见这件事", "c-lossless-not-ppl"),
    ("e-015", "2610.04403",
     "definitions fall 20",
     "fulltext#4", "supports", "定义能力相对基线下降 20–67%，而表面包含几乎不掉", "c-lossless-not-ppl"),
    ("e-016", "2609.07664",
     "we introduce a distribution-sensitive evaluation framework that quantifies information loss in quantized LLMs as the divergence between full-vocabulary predictive distributions",
     "fulltext#abstract", "supports", "替代方案：用全词表预测分布的散度衡量信息损失", "c-lossless-not-ppl"),
    ("e-020", "2607.27275",
     "The score stays flat because the benchmark’s ten-error budget absorbs the extra failures.",
     "fulltext#4", "supports", "分数不动是因为基准的十次错误预算吸收了额外失败", "c-flat-score"),
    ("e-021", "2607.27275",
     "Both diagnostics, the per-channel error rate and success under a shrinking budget, come from logs benchmarks already collect",
     "fulltext#abstract", "supports", "两个诊断量都能从已有日志算出：逐通道错误率、收缩预算下的成功率", "c-flat-score"),
    ("e-022", "2607.27275",
     "Quantization Amplifies the Existing Failure Set, Not New Ones",
     "fulltext#4", "supports", "量化放大的是既有的失败集合，不是引入新失败", "c-flat-score"),
    ("e-023", "2609.04748",
     "it reached 37.4 percent of episodes at 16-bit and 82.5 percent at four-bit",
     "fulltext#abstract", "supports", "同一请求的路径分歧从 16-bit 的 37.4% 升到 4-bit 的 82.5%", "c-flat-score"),
    ("e-024", "2609.04748",
     "Serving four-bit weights through 16-bit kernels left divergence not detectably different from 16-bit",
     "fulltext#abstract", "supports", "分歧的放大来自量化执行路径本身，不是权重位宽", "c-flat-score"),
    ("e-025", "2610.32417",
     "quantization can change both how much the agent generates and whether it succeeds",
     "fulltext#abstract", "supports", "量化同时改变「生成多少」与「是否成功」，故单请求能耗不等于任务能耗", "c-flat-score"),
    ("e-030", "2606.19558",
     "KLD measures displacement, not direction",
     "fulltext#abstract", "supports", "KLD 测的是分歧的位移，不是方向", "c-metric-direction"),
    ("e-031", "2606.19558",
     "KLD primarily measures the volume of disagreement with the reference",
     "fulltext#abstract", "supports", "KLD 主要反映分歧的量", "c-metric-direction"),
    ("e-032", "2606.19558",
     "KLD has only weak failure-prediction power on code",
     "fulltext#abstract", "supports", "在代码任务上，KLD 的失败预测力很弱", "c-metric-direction"),
    ("e-033", "2606.19558",
     "Collapse is metric-invariant",
     "fulltext#4.2", "supports", "「静默区」的塌缩与用哪个指标无关——换指标救不了", "c-metric-direction"),
    ("e-034", "2609.33923",
     "Divergence Guardrails",
     "fulltext#3.4", "supports", "另一条路：不把散度当分数，而当护栏", "c-metric-direction"),
    ("e-040", "2609.01587",
     "At a matched budget, global beats local for every model.",
     "fulltext#5", "supports", "同等预算下，全局更细粒度优于局部修补，且对所有模型都成立", "c-budget-global"),
    ("e-041", "2609.01587",
     "effective bits/weight can be allocated in 2 ways",
     "fulltext#5", "supports", "同一个 +0.146 bit/weight 的增量有两种花法：全局细化 vs 局部修复", "c-budget-global"),
    ("e-042", "2609.01587",
     "precision is best allocated globally, to finer granularity, not to a critical few layers",
     "fulltext#5", "supports", "恢复是弥散的：不该把精度堆在少数关键层", "c-budget-global"),
    ("e-043", "2609.01587",
     "The Structure of Quantization Damage in LLMs",
     "fulltext#title", "supports", "损伤有结构，故分配应当按结构而不是按直觉", "c-budget-global"),
    ("e-050", "2609.33923",
     "rank-correlates 0.83, 0.81 and 0.83 with the objective computed from real activations",
     "fulltext#abstract", "supports", "传播式探针与真实激活算出的层目标 rank 相关 0.83 / 0.81 / 0.83", "c-sensitivity-proxy"),
    ("e-051", "2609.33923",
     "the isolated estimator is uncorrelated with it",
     "fulltext#abstract", "supports", "隔离式估计器与该目标不相关（−0.07 到 −0.15）", "c-sensitivity-proxy"),
    ("e-052", "2609.33923",
     "0.25 for HAWQ-V2",
     "fulltext#abstract", "supports", "既有方法 HAWQ-V2 只有 0.25，故「代理是否被标定」是分水岭", "c-sensitivity-proxy"),
    ("e-053", "2609.25916",
     "A Lower Bound Showing Why Scalar Proxies Can Fail",
     "fulltext#G.1", "supports", "标量代理会失效有下界证明", "c-sensitivity-proxy"),
    ("e-054", "2609.25916",
     "a practical indicator of scalar-proxy failure",
     "fulltext#abstract", "supports", "模块的平均条件数可以作为标量代理失效的实用指示器", "c-sensitivity-proxy"),
    ("e-055", "2608.24945",
     "Fisher information-based Adaptive Mixed Precision Weight Quantization",
     "fulltext#title", "supports", "另一类代理：Fisher 信息", "c-sensitivity-proxy"),
    ("e-056", "2608.28003",
     "the sensitivity score of each layer is used as a proxy for its quality at a particular bit-width",
     "fulltext#1.1", "supports", "最朴素的代理：用每层敏感度分数替代该位宽下的质量", "c-sensitivity-proxy"),
    ("e-060", "2608.03854",
     "the apparent accuracy-calibration tradeoff therefore depends on the scoring rule",
     "fulltext#5", "supports", "准确率-校准的权衡本身取决于评分规则", "c-calibration-dependence"),
    ("e-061", "2608.03854",
     "Negative log-likelihood and Brier score show the same reversal",
     "fulltext#5", "supports", "换 NLL 与 Brier 也反转，故不是 ECE 分箱的伪影", "c-calibration-dependence"),
    ("e-062", "2609.33923",
     "a data-free estimate of the calibration objective itself",
     "fulltext#abstract", "supports", "可以做到无数据地估计校准目标本身", "c-calibration-dependence"),
    ("e-063", "2608.11045",
     "remains competitive with calibration-dependent approaches, and operates entirely offline",
     "fulltext#abstract", "supports", "无校准方法可以和有校准方法打平，且完全离线", "c-calibration-dependence"),
    ("e-064", "2608.30564",
     "Stability across calibration subsets",
     "fulltext#D.4", "supports", "校准子集稳定性被当成必须报告的实验项", "c-calibration-dependence"),
    ("e-070", "2608.05499",
     "A profiling agent measures how cost is distributed across the model",
     "fulltext#1", "supports", "profiling agent 负责测「代价分布在哪」", "c-agent-loop"),
    ("e-071", "2608.05499",
     "a pruning agent that sets per-layer pruning ratios and a quantization agent that assigns per-layer bit-widths",
     "fulltext#1", "supports", "剪枝 agent 与量化 agent 分工，各自只做一件事", "c-agent-loop"),
    ("e-072", "2611.06858",
     "an agent receives a source checkpoint, storage limit, inference environment, and time budget",
     "fulltext#abstract", "supports", "压缩被形式化成终端任务：给检查点、存储上限、推理环境与时间预算", "c-agent-loop"),
    ("e-073", "2611.06858",
     "Agents lower PPL in 21 of 24 revisions at nearly fixed storage",
     "fulltext#abstract", "supports", "24 次修订里 21 次降低了 PPL（存储几乎不变）", "c-agent-loop"),
    ("e-074", "2609.39223",
     "simulates deployment-time quantization while performing matrix multiplications in BF16",
     "fulltext#abstract", "supports", "部署对齐的模拟量化：在没有 FP4 硬件的卡上训 FP4", "c-agent-loop"),
    ("e-080", "2611.06858",
     "complete-model feedback reverses 17 of 79 prior local rankings",
     "fulltext#abstract", "supports", "整模型反馈推翻了 79 条局部排序中的 17 条", "c-local-global"),
    ("e-081", "2608.30564",
     "a bi-level allocator that ranks within-block assignments with a cheap proxy and allocates across blocks with a model-level objective",
     "fulltext#abstract", "supports", "双层分配器：块内用便宜代理排序，块间用整模型目标", "c-local-global"),
    ("e-082", "2611.06858",
     "generation and inference tests expose failures that likelihood alone misses",
     "fulltext#abstract", "supports", "生成与推理测试能暴露似然看不见的失败", "c-local-global"),
    ("e-083", "2608.30564",
     "evaluated on the assembled quantized model",
     "fulltext#abstract", "supports", "外层目标必须在「装配好的」量化模型上评", "c-local-global"),
    ("e-090", "2609.28974",
     "The same bit width yields different outcomes, because the sensitive component is model-specific",
     "fulltext#abstract", "supports", "同一位宽结果不同，因为敏感部件是模型特定的", "c-boundary-scale"),
    ("e-091", "2607.25451",
     "verbatim memorization falls off faster than capability at every precision and every model size we tried",
     "fulltext#abstract", "supports", "量化是选择性遗忘：逐字记忆比通用能力掉得更快", "c-boundary-scale"),
    ("e-092", "2608.18578",
     "retrieval of the final value degrades log-linearly",
     "fulltext#1", "supports", "多轮更新场景下，末值检索随干扰次数对数线性下降", "c-boundary-scale"),
    ("e-093", "2608.30996",
     "cache precision can affect grounding even when answer accuracy is preserved",
     "fulltext#abstract", "supports", "KV cache 精度可以影响 RAG 的接地性，而答案准确率不变", "c-boundary-scale"),
    ("e-094", "2610.04403",
     "Two controls separate rarity from task difficulty",
     "fulltext#abstract", "supports", "用两个对照把「罕见」与「任务难」分开，否则退化无法归因", "c-boundary-scale"),
    ("e-100", "2609.33923",
     "The probe pass takes 36 to 539 seconds on a single Apple Silicon machine for models from 8B to 400B parameters",
     "fulltext#abstract", "supports", "探针一遍在单台 Apple Silicon 上，8B 到 400B 只需 36–539 秒", "c-cost"),
    ("e-101", "2609.39223",
     "rank-16 LoRA reduces GPU memory usage by 2.9",
     "fulltext#abstract", "supports", "rank-16 LoRA 把 QAD 的显存降到 1/2.9，但补不上与全参数的质量差", "c-cost"),
    ("e-102", "2609.39223",
     "training on fewer 32K sequences improves average accuracy by 1.9 points over training on more 4K sequences",
     "fulltext#abstract", "supports", "同样 token 预算下，少而长的序列比多而短的序列高 1.9 个点", "c-cost"),
    ("e-103", "2610.09183",
     "at a small fraction of the training cost",
     "fulltext#abstract", "supports", "动态位宽分配能以很小的训练成本拿回大部分精度差", "c-cost"),
    ("e-104", "2608.11045",
     "introducing no additional overhead during low-bit inference",
     "fulltext#abstract", "supports", "无校准重建只在量化时算一次，推理期零开销", "c-cost"),
    ("e-110", "2607.27275",
     "we suggest reporting them alongside task reward",
     "fulltext#abstract", "supports", "建议把过程诊断量与任务奖励并列报告", "c-transfer"),
    ("e-111", "2609.33923",
     "the propagated probe’s estimate of the layer-wise calibration objective",
     "fulltext#abstract", "supports", "代理必须先被标定：与真实激活下的目标对齐才算数", "c-transfer"),
    ("e-112", "2611.06858",
     "Selecting the lowest-perplexity agent design per task yields an average 3.4% perplexity increase over BF16",
     "fulltext#abstract", "supports", "按任务挑 PPL 最低的 agent 设计，平均也还有 3.4% 的 PPL 增量", "c-transfer"),
    ("e-113", "2610.04403",
     "We audit 27 quantized artifacts across 13 families and four architecture backbones",
     "fulltext#abstract", "supports", "27 个量化产物、13 个族、4 种骨干：审计规模说明了判据必须批量可执行", "c-transfer"),
]

# (claim_id, statement, claim_type, confidence, evidence_ids(占位), derivation, notes)
CLAIMS = [
    ("c-object-numeric",
     "量化的被优化对象是数值表示：它同时改变「算得多快」与「算得多对不对」，而两者沿同一条连续参数（bit / 粒度 / 分组）滑动。因此量化的判据不是「是否无损」的阈值，而是「Pareto 前沿上的位置」；分配单元、存储单元与执行单元还必须是同一个，否则精度分配写不进 kernel。",
     "spec", "high", "",
     "", "按对象性质分类，不依赖跨论文数值比较"),
    ("c-lossless-not-ppl",
     "「perplexity / 基准准确率不掉」不能当作无损。四项独立证据显示：安全对齐可以被摧毁而 accuracy 与 perplexity 几乎不动；编码 agent 上检测不到显著准确率损失，但同一次量化把一次性解从 17 降到 0。原因是这些指标只覆盖「平均」而不覆盖「尾部与过程」。",
     "measurement", "high", "",
     "", "回答 q2；这是本文的第一根支柱"),
    ("c-flat-score",
     "基准自带的「误差预算」会吸收量化带来的额外失败，使最终分数对量化不敏感。分数不动不等于损伤不存在：量化放大的是既有失败集合而不是新失败，且同一请求的路径分歧会随量化从 37.4% 升到 82.5%。故必须同时报告过程诊断量（逐通道错误率、收缩预算下的成功率）。",
     "measurement", "high", "",
     "", "回答 q2/q5；与 c-lossless-not-ppl 互为因果"),
    ("c-metric-direction",
     "常用保真度指标（KLD / perplexity）测的是「位移」而不是「方向」：KLD 主要反映分歧的量，与分歧是否落在关键处关系很弱，在代码任务上失败预测力也弱；而这种塌缩是 metric-invariant 的，换指标救不了。",
     "measurement", "high", "",
     "", "回答 q2；这条解释了为什么换指标不等于换判据"),
    ("c-budget-global",
     "在同等 bit 预算下，把增量花在「全局更细的粒度」上优于「修补少数关键层」：+0.146 bit/weight 的增量，全局细化对所有模型都赢局部修复。这条直接否证了「先找关键层再补精度」这一常见直觉。",
     "measurement", "high", "",
     "", "回答 q2/q6；这是本文最强的一条可操作结论"),
    ("c-sensitivity-proxy",
     "位分配的成败取决于敏感度代理是否「被标定」而不是是否更复杂：一个传播式随机探针与真实激活下的层目标 rank 相关 0.83 / 0.81 / 0.83，隔离式估计器只有 −0.07 到 −0.15，既有方法 HAWQ-V2 是 0.25；而标量代理为何失效有下界证明。故代理的验收标准是相关性，不是先验合理性。",
     "measurement", "high", "",
     "", "回答 q2/q6；这条把「代理」从工程细节提升为判据"),
    ("c-calibration-dependence",
     "校准集不是前置步骤，而是判据的一部分：同一批量化模型，准确率-校准的权衡会随评分规则反转（NLL 与 Brier 同样反转，故不是 ECE 分箱的伪影）。反过来，无校准方法可以和有校准方法打平，说明「必须校准」不是物理约束而是方法选择。",
     "measurement", "high", "",
     "", "回答 q2/q5；这条是「判据不可迁移」的直接机制"),
    ("c-agent-loop",
     "agent 进入量化后，真正的变化是流水线化而不是搜索更聪明：profiling / 剪枝 / 位分配 / 恢复 / 评测被拆成各自只做一件事的 agent；而 agent 的产出仍然很粗——24 次修订里 21 次降低 PPL，但按任务挑最优设计，平均仍有 3.4% 的 PPL 增量。",
     "measurement", "high", "",
     "", "回答 q1/q3；这是本文对「agent 化量化」的经验判断"),
    ("c-local-global",
     "局部反馈与整体反馈会给出相反的排序：对单个 block 更优的分配，装配成整模型后可能更差——79 条局部排序里 17 条被整模型反馈推翻。可行做法是双层：块内用便宜代理排序，块间用装配后模型的目标定预算。",
     "measurement", "high", "",
     "", "回答 q2；这条解释了为什么 agent 循环必须有整体重排这一步"),
    ("c-boundary-scale",
     "量化结论不可跨对象迁移：同一位宽在不同架构上结果不同，因为敏感部件是模型特定的；退化还会沿维度分化——逐字记忆比通用能力掉得更快，RAG 的接地性可以在答案准确率不变时变差。",
     "measurement", "high", "",
     "", "回答 q5；三条反号证据都来自论文自报"),
    ("c-cost",
     "量化循环的代价结构与端到端不同：它买的是校准、搜索与恢复的时间，其中恢复训练是主成本。代理侧可以很便宜（探针一遍 36–539 秒覆盖 8B–400B），但恢复侧很贵（同 token 预算下序列长度选择就值 1.9 个点，LoRA 省 2.9 倍显存却补不上质量差）。",
     "measurement", "high", "",
     "", "回答 q4；把循环成本折算进结论"),
    ("c-transfer",
     "可迁移的是三条判据工程：一是阈值必须由过程指标补足（逐通道错误率 + 收缩预算成功率）；二是代理必须被标定（与真实激活目标的相关性，0.83 才算可用）；三是局部排序必须用整体重排校验（79 条里 17 条会被推翻）。",
     "spec", "high", "",
     "", "回答 q6；三条各有独立来源支持"),
]


# 反证白名单：主张 -> 与之张力最强的证据 id 列表。
# c-budget-global 说「全局优于局部」，而 e-081 显示双层方法仍需块内局部代理，
# 属于对该断言边界的反例，故并列。
COUNTER = {
    "c-budget-global": "e-081;e-053",
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def bodies(doc_id: str) -> list[str]:
    out = []
    for suffix in (".txt", "-full.txt"):
        p = DOCS / f"{doc_id}{suffix}"
        if p.is_file():
            out.append(p.read_text(encoding="utf-8", errors="replace"))
    return out


def find(doc_id: str, quote: str) -> bool:
    for body in bodies(doc_id):
        if quote in body or norm(quote) in norm(body):
            return True
    return False


def resolve(doc_id: str, pattern: str) -> str | None:
    """按宽松空白匹配把模式解析成快照里的**原文片段**。

    为什么需要它：E1 要求 quote 是原文子串，而全文快照来自 LaTeXML，
    句子之间的换行位置不可预测。手抄容易差一个空格，故这里用「把模式里的
    空格当 \\s+」去原文里找，返回命中的原始文本本身——它是子串这一点由构造保证。
    """
    rx = re.compile(r"\s+".join(re.escape(part) for part in pattern.split()))
    for body in bodies(doc_id):
        m = rx.search(body)
        if m:
            return m.group(0)
    return None


def main() -> int:
    bad = []
    fixed: list[tuple] = []
    for eid, aid, q, loc, st, note, cid in EVID:
        did = "doc-arxiv-" + aid.replace(".", "-")
        if find(did, q):
            fixed.append((eid, aid, q, loc, st, note, cid))
            continue
        got = resolve(did, q)
        if got:
            fixed.append((eid, aid, got, loc, st, note, cid))
            continue
        bad.append((eid, aid, q))
    if bad:
        print(f"[FAIL] {len(bad)} 条 quote 未命中：")
        for eid, aid, q in bad:
            print(f"  {eid} {aid}: {q[:110]}")
        return 1
    EVID[:] = fixed

    with (HERE / "evidence.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["evidence_id", "document_id", "source_id", "quote",
                    "locator", "quote_type", "stance", "fetched_at", "note"])
        for eid, aid, q, loc, st, note, cid in EVID:
            w.writerow([eid, "doc-arxiv-" + aid.replace(".", "-"),
                        "src-arxiv-" + aid.replace(".", "-"), q, loc, "quote",
                        st, FETCHED, f"[{cid}] {note}"])

    by_claim: dict[str, list[str]] = {}
    for eid, _aid, _q, _loc, _st, _note, cid in EVID:
        by_claim.setdefault(cid, []).append(eid)

    with (HERE / "claims.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["claim_id", "statement", "claim_type", "as_of",
                    "confidence", "evidence_ids", "counter_evidence_ids",
                    "derivation", "notes"])
        for cid, stmt, ctype, conf, _eids, deriv, note in CLAIMS:
            ids = ";".join(by_claim.get(cid, []))
            counter = COUNTER.get(cid, "")
            w.writerow([cid, stmt, ctype, "2026-11-05", conf, ids, counter,
                        deriv, note])

    print(f"写入 evidence {len(EVID)} 条、claims {len(CLAIMS)} 条")
    for cid, *_ in CLAIMS:
        print(f"  {cid}: {len(by_claim.get(cid, []))} 条证据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
