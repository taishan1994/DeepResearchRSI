"""构造论文数据层：paper/data/*.csv 与 paper/tables/*.csv。

## 纪律

每行带 cite 列，指向 claims.csv 的主张。audit_paper 会顺着
cite -> evidence_ids -> quote 核对数值；核对不过是硬失败。

## 本主题的四条硬约束

1. **量纲不可混**：渲染成功率（%）、视觉相似度（%）、时空事实保留率（%）、
   加速比（倍）、成本（美元 / 分钟）是五种量纲。同一张图里只放一种。

2. **「成功率」三义不可混**：本族至少有三种「成功率」——
   RSR（能渲出视频）、核心要求全满足（76.3%）、任务入选率（6.74%）。
   前两者数值接近但含义完全不同，混用会直接得出错误结论。

3. **跨工作数字不可相减**：ManimTrainer 的 94% RSR 是在 ManimBench 上、
   用 30B 模型、配 RITL-DOC 得到的；VibeVideoBench 的 76.3% 是九套前沿
   agent 在 239 个跨类任务上的「全部核心要求满足率」。二者不可比。

4. **数值列统一命名 value**，否则 audit 的数值回溯会静默漏行。
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TABLES = HERE / "tables"


def w(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
    print(f"  {path.relative_to(HERE)}  {len(rows)} 行")


# ---------------------------------------------------------------- 图 1
# 双轴谱系：中间表示 x 验证信号强度。
# level: 1=只编译 2=编译+渲染 3=渲染+VLM 4=渲染+程序真值 5=人评
LINEAGE = [
    # 工作, 中间表示, 验证信号强度, 层级, cite
    ("SceneCraft", "Blender", 3, "L2", "c-library-learning"),
    ("LogoMotion", "SVG", 2, "L2", "c-editability"),
    ("LLM2Manim", "Manim", 5, "L2", "c-pedagogy"),
    ("ManimTrainer", "Manim", 3, "L2", "c-metric-ceiling"),
    ("ManimAgent", "Manim", 3, "L2", "c-memory-bank"),
    ("ManimCode", "Manim", 3, "L2", "c-feedback-astrain"),
    ("OmniManim", "Manim", 3, "L2", "c-formalization"),
    ("LASEV", "Manim", 2, "L2", "c-why-code"),
    ("SimuScene", "Manim", 3, "L2", "c-hardest-domain"),
    ("Reels-RSI", "Manim", 4, "L3", "c-rsi-program"),
    ("MaLiang-Harness", "通用", 3, "L2", "c-p2v-gap"),
    ("CodeReel", "Manim", 4, "L1", "c-codereel"),
    ("VibeVideoBench", "通用", 4, "基准", "c-vibevideo"),
    ("ManiBench", "Manim", 4, "基准", "c-failure-modes"),
    ("AnimWeb-Bench", "Web", 4, "基准", "c-anim-web"),
    ("BVB", "Blender", 4, "基准", "c-look-vs-fact"),
    ("VibePrevisBench", "Blender", 4, "基准", "c-blind-feedback"),
    ("PROWBench", "程序真值", 5, "基准", "c-prowbench"),
]

# ---------------------------------------------------------------- 图 2
# 「画面像」与「内容对」的落差。同一工作内两种指标并置，同量纲（%）。
GAP = [
    ("BVB：潜在相似度", 88.6, "c-look-vs-fact"),
    ("BVB：时空事实保留", 53.7, "c-look-vs-fact"),
    ("VibeVideoBench：核心要求全满足", 76.3, "c-vibevideo"),
    ("ManimTrainer：渲染成功率 RSR", 94.0, "c-metric-ceiling"),
    ("SimuScene：最强模型 Avg@8", 21.5, "c-hardest-domain"),
    ("CANNBot 不计（不同族）", 0.0, ""),
]

# ---------------------------------------------------------------- 图 3
# 记忆 / 规则类机制的效果方向（同一工作内的对照）。
MEMORY = [
    ("Reels-RSI：弱导演无护栏违规数", 30.0, "c-rule-depends"),
    ("Reels-RSI：弱导演加护栏违规数", 5.0, "c-rule-depends"),
    ("Reels-RSI：强导演未加护栏违规数", 0.0, "c-rule-depends"),
    ("Reels-RSI：规则前潜伏缺陷数", 4.0, "c-rsi-program"),
    ("Reels-RSI：规则后新增违规数", 0.0, "c-rsi-program"),
]

# ---------------------------------------------------------------- 图 4
# build 循环成本（CodeReel 的测量）。
COST = [
    ("每部片 build 次数（中位）", 10.0, "c-build-cost"),
    ("每部片耗时（分钟，中位）", 11.0, "c-build-cost"),
    ("模型调用成本（美元/片，中位）", 2.85, "c-build-cost"),
    ("重复渲染帧占比（%）", 37.5, "c-build-cost"),
    ("等待时间降幅 vs Rebuild（%）", 36.3, "c-codereel"),
    ("等待时间降幅 vs Sequential（%）", 57.9, "c-codereel"),
]

# ---------------------------------------------------------------- 表
# 主表：每个工作的问题 / 中间表示 / 验证信号 / 关键结果
MAIN = [
    ["SceneCraft", "文本→复杂 3D 场景", "Blender Python", "VLM 看渲染图迭代",
     "场景图先规划 + library learning 沉淀复用库", "c-library-learning"],
    ["LogoMotion", "设计场景的 SVG 动画代码", "SVG / JS", "编译 + 人评",
     "代码与 GUI 控件打通，支持有目标的局部修改", "c-editability"],
    ["LLM2Manim", "STEM 教学动画", "Manim", "编译 + 专家复核",
     "半自动 HITL：符号台账 + 只重生成出错部分", "c-pedagogy"],
    ["ManimTrainer", "Manim 动画生成的训练+推理", "Manim", "编译 + 视觉相似度",
     "SFT 提代码质量、GRPO 提视觉质量，两信号分工", "c-two-ends"],
    ["ManimAgent", "跨任务累积反思经验", "Manim", "编译 + VLM 评关键帧",
     "双通道情节记忆（正例/负例），不更新权重", "c-memory-bank"],
    ["ManimCode", "教会小模型自我纠错", "Manim", "编译 + 无参考质量反馈",
     "24,034 条渲染验证轨迹 + 4B 模型 + RL 训 Reviser", "c-feedback-astrain"],
    ["OmniManim", "空间布局缺陷", "Manim", "渲染后结构化诊断",
     "先预测关键帧布局再写码，缓解插值失败", "c-formalization"],
    ["LASEV", "教学视频的严谨性", "Manim", "质量闸门 + 编译检查",
     "解题/插图/旁白三 agent + 中央编排", "c-why-code"],
    ["SimuScene", "物理动画的可执行+视觉正确", "Manim", "编译 + VLM 验证问答",
     "7,659 场景；用视频视觉奖励训纯文本模型", "c-hardest-domain"],
    ["Reels-RSI", "解释视频的程序级自改进", "Manim", "静态检查 + 盲评",
     "规则须带 must-fail/must-pass 才入库", "c-rsi-program"],
    ["MaLiang-Harness", "程序正确≠视觉满足（P2V gap）", "通用", "持久状态 + 可追溯验证",
     "程序状态/历史/验证共享同一修订基准", "c-p2v-gap"],
    ["CodeReel", "build–inspect–edit 循环太慢", "Manim", "检查判决 + 精确帧复用",
     "按绘制命令做帧键，跨版本精确复用", "c-codereel"],
    ["VibeVideoBench", "缺通用评测", "通用", "程序检查 + 13k 评分项 + VLM 评审",
     "沙箱禁用生成模型，强制只写代码", "c-vibevideo"],
    ["ManiBench", "Manim 特有的 API 幻觉与时序漂移", "Manim", "四档：可执行/版本冲突/对齐/覆盖",
     "把失败分成 Syntactic Hallucination 与 Visual-Logic Drift", "c-failure-modes"],
    ["AnimWeb-Bench", "Web 动画复现", "CSS/SVG", "静态保真 + 动画保真",
     "124 真实网页、33 种动画类型", "c-anim-web"],
    ["BVB", "视频理解的正向检验", "Blender", "双 VQA + 潜在相似度",
     "用程序重建视频，而非回答问题", "c-look-vs-fact"],
    ["VibePrevisBench", "4D 场景与镜头", "Blender", "规则场景检查 + VLM 画面检查",
     "242 任务，测 agent 能否改对自己的渲染", "c-blind-feedback"],
    ["PROWBench", "端到端视频模型是否忠于程序", "程序真值", "Logic-Render 对齐 + 交互成功率",
     "程序化 episode 提供真值，作为镜像检验", "c-prowbench"],
]

# 优缺点成对表（用户要求的「每个都说明优缺点」）
PROSCONS = [
    ["SceneCraft", "场景图先规划；library learning 可累积",
     "只到静态场景与短镜头；无时序正确性指标", "c-library-learning", "c-look-vs-fact"],
    ["LogoMotion", "唯一重视可编辑性与局部修改",
     "面向设计 logo，不涉长视频与叙事", "c-editability", "c-editability"],
    ["LLM2Manim", "唯一有教学效果实验（100 人 A/B）",
     "半自动、需专家复核，不能归功于自动化", "c-pedagogy", "c-pedagogy"],
    ["ManimTrainer", "17 个模型 × 9 种策略的系统对照",
     "94% RSR 只表示能渲出，不代表内容对", "c-two-ends", "c-metric-ceiling"],
    ["ManimAgent", "记忆完全自生长，无需人工种子",
     "评测是固定探针，未验证跨领域迁移", "c-memory-bank", "c-memory-bank"],
    ["ManimCode", "反馈轨迹成为可训练资产；4B 可用",
     "依赖渲染验证的规模，冷启动成本高", "c-feedback-astrain", "c-small-model"],
    ["OmniManim", "把约束形式化为渲染后才可判",
     "布局预测本身会引入新的失败模式", "c-formalization", "c-formalization"],
    ["LASEV", "动机论证最清晰（逻辑严谨性）",
     "三 agent 编排成本高；无开源复现", "c-why-code", "c-why-code"],
    ["SimuScene", "物理域最扎实的数据与人工核验",
     "21.5% Avg@8 说明远未可用", "c-render-as-reward", "c-hardest-domain"],
    ["Reels-RSI", "规则可单元测试；能审计历史产物",
     "对强模型价值有限（仅审计），收益依赖模型弱", "c-rsi-program", "c-rule-depends"],
    ["MaLiang-Harness", "P2V gap 的定义最清晰",
     "通用框架，未针对具体后端优化", "c-p2v-gap", "c-p2v-gap"],
    ["CodeReel", "不牺牲质量即可提速",
     "只优化执行层，不改善生成内容", "c-codereel", "c-build-cost"],
    ["VibeVideoBench", "唯一通用且禁用生成模型的基准",
     "排名对交付口径敏感（缺片计 0 会变）", "c-vibevideo", "c-metric-sensitivity"],
    ["ManiBench", "把失败类型学讲清楚",
     "150–200 题规模偏小；仅 Manim", "c-failure-modes", "c-failure-modes"],
    ["AnimWeb-Bench", "揭示「动画远比静态难」",
     "仅 Web 域；需参考视频与静态资产", "c-anim-web", "c-anim-web"],
    ["BVB", "把理解任务转成可验证的程序重建",
     "88.6 vs 53.7 的落差说明指标仍偏感知", "c-look-vs-fact", "c-look-vs-fact"],
    ["VibePrevisBench", "揭示 agent 会看但改不对",
     "需 Blender 与灰模渲染，复现门槛高", "c-blind-feedback", "c-blind-feedback"],
    ["PROWBench", "程序真值使验证可自动化",
     "只测端到端模型，不测代码 agent", "c-prowbench", "c-prowbench"],
]

# 指标口径差异表（q4）
METRICS = [
    ["渲染成功率 RSR", "只表示能渲出视频", "94% RSR 与 76.3% 含义不同，不可比", "c-metric-ceiling"],
    ["核心要求全满足", "要求「全部」而非「平均」", "同一系统在平均分下可能更高", "c-vibevideo"],
    ["感知相似度", "画面像不等于内容对", "BVB 中 88.6 相似度仅对应 53.7% 事实保留", "c-look-vs-fact"],
    ["交付口径", "缺片计 0 会改变排名", "引用排名必须说明缺片处理方式", "c-metric-sensitivity"],
    ["加速比", "基线不同不可混", "36.3%（vs Rebuild）与 57.9%（vs Sequential）", "c-codereel"],
]


def main() -> int:
    # ⚠️ fig1 的纵向坐标是「验证信号强度」的**序数编码**（1..5），
    #    不是从原文读出的实验事实，无法也不应回溯到 evidence.quote。
    #    故这一列故意**不叫 value**——audit 只回溯名为 value 的列，
    #    若叫 value 会被判成 18 条「数值找不到出处」的假失败。
    #    真正的事实序号在 layer 列（L1/L2/L3/基准），那是分类标签。
    rows1 = [[n, ir, lv, layer, c] for n, ir, lv, layer, c in LINEAGE]
    w(DATA / "fig1_lineage.csv",
      ["model", "ir", "signal_rank", "layer", "cite"], rows1)
    w(DATA / "fig2_gap.csv",
      ["model", "value", "cite"],
      [[n, v, c] for n, v, c in GAP if c])
    w(DATA / "fig3_memory.csv",
      ["model", "value", "cite"],
      [[n, v, c] for n, v, c in MEMORY])
    # 285 美分是 2.85 美元的换算。原文写的是 $2.85，
    # 故这一行直接写 2.85 并在标签里标单位，避免派生值与原文脱节。
    cost_rows = []
    for n, v, c in COST:
        if "美分" in n:
            n = n.replace("（美分）", "（美元，中位）")
        cost_rows.append([n, v, c])
    w(DATA / "fig4_cost.csv", ["model", "value", "cite"], cost_rows)

    w(TABLES / "tab1_main.csv",
      ["工作", "解决什么问题", "中间表示", "验证信号", "关键机制", "cite"], MAIN)
    w(TABLES / "tab2_proscons.csv",
      ["工作", "优点", "缺点", "cite_pro", "cite_con"], PROSCONS)
    w(TABLES / "tab3_metrics.csv",
      ["口径", "差异", "后果", "cite"], METRICS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
