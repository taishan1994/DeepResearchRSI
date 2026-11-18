"""登记 code-to-video 一族的来源与文档快照。

## 快照存放

`documents/doc-arxiv-<虚线 id>-full.txt` 是 arXiv HTML 全文的纯文本。
document_id 为 `doc-arxiv-<虚线 id>`（**不带** -full），与 evidence 的
document_id 主键保持一致——上一份归档就在这里踩过坑（带后缀导致关联断裂，
表象是「证据不足」）。

## 为什么每篇都要留全文

本族的核心分歧不在结论，而在**判据**：同一个「渲染成功率」在不同工作里
指代不同（能跑通 / 能跑通且画面过关 / 能跑通且时轴对齐）。
只有保留全文，才能核对这些指标的定义原文，而不是靠摘要推断。
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))
FETCHED = datetime.now(TZ).replace(microsecond=0).isoformat()

# (aid, 标题, 发布日, 支线, 标签, 备注)
ARXIV = [
    # ---- 基准线：测「渲染是否忠于程序」或「agent 能否写出可渲染程序」 ----
    ("2610.35864", "VibeVideoBench: Evaluating Multimodal Agents on Code-Driven Video Generation",
     "2026-10-26", "bench", "bench-general",
     "本族最完整的通用基准：239 任务 / 12 类 / 中英双语，沙箱内禁用任何图像视频生成模型，"
     "只能写代码。最强者在 76.3% 任务上满足全部核心要求。"
     "它还揭示「交付」是第二根轴——把缺片算 0 会改变排名"),
    ("2610.02205", "PROWBench: Do Video Models Render What the Program Specifies?",
     "2026-10-01", "bench", "bench-adherence",
     "问的是**视觉是否忠于程序**：170 个程序化 episode、600 条代理视频，"
     "把实体状态与时间戳事件记成可回放的世界记录。"
     "它测的是端到端视频模型，故是本族的反面参照：程序给得出真值，像素模型对不上"),
    ("2603.13251", "ManiBench: A Benchmark for Testing Visual-Logic Drift and Syntactic Hallucinations in Manim Code Generation",
     "2026-02-24", "bench", "bench-manim",
     "把 Manim 生成的失败分成两类并分别命名：Syntactic Hallucinations（API 幻觉）"
     "与 Visual-Logic Drift（时序/因果错）。四档评分含 Version-Conflict Error Rate，"
     "这一项本族独有——Manim CE 与 ManimGL 的 API 不兼容"),
    ("2611.09769", "AnimWeb-Bench: Benchmarking Animated Webpage Code Generation from Videos",
     "2026-11-06", "bench", "bench-web",
     "把「代码生成视频」搬到 CSS/SVG 动画：124 个真实网页、33 种动画类型。"
     "关键发现是「复现动画远难于复现静态外观」，且显式看帧能提升 agent 表现"),
    ("2611.15789", "VibePrevisBench: Evaluating Agentic Coding for 4D Scene Generation in Blender",
     "2026-11-11", "bench", "bench-blender",
     "242 个 4D 场景任务。最重要的一条观测是「agent 会看自己的渲染，但改不对」——"
     "这直接反驳「给了视觉反馈就能自我纠正」的乐观假设"),
    ("2609.15478", "BVB: Benchmarking Agentic Video Understanding via Programmatic Reconstruction in Blender",
     "2026-09-14", "bench", "bench-recon",
     "把视频理解改写成「用 Blender 程序重建视频」。最好模型潜在相似度 88.6，"
     "但只保留 53.7% 的时空事实——**画面像 ≠ 内容对**，这是本族最锋利的一组数字"),
    # ---- Manim 线：教育 / 数学动画 ----
    ("2610.14495", "Reels-RSI: Program-Level Self-Improvement for Code-Rendered Explainer Videos",
     "2026-10-10", "manim", "rsi-program",
     "明确提出「解释视频是程序而非像素」，自我改进发生在程序层。"
     "规则要带 must-fail 与 must-pass 两个例子才算入库（即记忆本身被单元测试）。"
     "最有价值的是反向结论：规则对强导演是审计，对弱导演才是护栏"),
    ("2606.30296", "ManimAgent: Self-Evolving Multimodal Agents for Visual Education",
     "2026-06-29", "manim", "memory-bank",
     "双通道情节记忆（正例存成功理由、负例存已证实的坑），不更新权重、无人工种子。"
     "评测用 fixed-probe：固定探针任务，随记忆增长看 Pass@1 升、反思轮数降"),
    ("2611.08294", "ManimCode: Learning Visual Self-Correction for Educational Animation",
     "2026-11-05", "manim", "sft-4b",
     "本族唯一把小模型做到可用的工作：24,034 条渲染验证轨迹 + 角色条件 SFT 训 4B 模型，"
     "再用 RL 训 Reviser。它的意义是证明「反馈轨迹」本身是可训练资产"),
    ("2605.15585", "See Before You Code: Learning Visual Priors for Spatially Aware Educational Animation Generation",
     "2026-05-15", "manim", "layout-prior",
     "把问题形式化为 render-feedback-aware constrained code generation："
     "约束只有在渲染后才可判。先预测关键帧布局再写码，以缓解下游插值造成的中间帧失败"),
    ("2604.18364", "Training and Agentic Inference Strategies for LLM-based Manim Animation Generation",
     "2026-04-20", "manim", "sft+grpo",
     "17 个 30B 以下开源模型的系统对照：SFT 提代码质量，GRPO 提视觉质量。"
     "最强配置 94% Render Success Rate + 85.7% Visual Similarity"),
    ("2604.05266", "LLM2Manim: Pedagogy-Aware AI Generation of STEM Animations",
     "2026-04-07", "manim", "hitl-pedagogy",
     "唯一做了教学效果实验的工作：100 名本科生 A/B，后测 83% vs 78%。"
     "它是半自动 HITL 管线，专家复核后才渲染——这条限制值得单独讨论"),
    ("2602.11790", "Beyond End-to-End Video Models: An LLM-Based Multi-Agent System for Educational Video Generation (LASEV)",
     "2026-02-12", "manim", "multiagent-edu",
     "明确以「端到端视频模型逻辑不严谨」为动机，拆成解题 / 插图 / 旁白三个 agent，"
     "经质量闸门与迭代批评。它把「为什么要代码」这个动机讲得最清楚"),
    ("2602.10840", "Training and Benchmarking Code Generation for Physics-Inspired Animations (SimuScene)",
     "2026-02-11", "manim", "physics-reward",
     "物理动画的代码生成：7,659 场景、334 人工核验测试集。"
     "最强模型仅 21.5% Avg@8，说明「可执行且视觉正确」远比想象难。"
     "它还用视频视觉奖励训纯文本模型，是本族「渲染即奖励」的干净实例"),
    # ---- 效率层 ----
    ("2611.22967", "CodeReel: Accelerating Code-to-Video Agents with Exact Frame Reuse and Blocking-Aware Scheduling",
     "2026-11-17", "efficiency", "build-loop",
     "不生成内容，只优化 build–inspect–edit 循环：按绘制命令给帧做键做精确复用，"
     "检查先行、渲染并行。等待时间降 36.3%（对 Rebuild）/ 57.9%（对 Sequential）。"
     "它量化了本族一个被忽略的成本：一部片子中位 11 分钟、$2.85、10 次 build"),
    # ---- Blender 线 ----
    ("2403.01248", "SceneCraft: An LLM Agent for Synthesizing 3D Scene as Blender Code",
     "2024-03-02", "blender", "scene-graph",
     "本族早期代表作：先把场景建成场景图，再翻成数值约束写 Blender Python，"
     "用 VLM 看渲染图迭代。library learning 把常用函数沉淀成可复用库，"
     "这是「不调权重也能累积能力」的早期形态"),
    # ---- 通用 harness ----
    ("2609.34309", "MaLiang-Harness: A Programmable Path to Image and Video Generation",
     "2026-09-28", "harness", "p2v-gap",
     "本族目前最好的理论表述：提出 Program-to-Visual (P2V) gap——程序正确执行"
     "不等于满足视觉要求。用持久程序状态 + 可追溯生成过程 + 修订感知验证来桥接。"
     "不绑定单一后端，故可作为跨支线的公共框架"),
    # ---- SVG 线 ----
    ("2405.07065", "LogoMotion: Visually-Grounded Code Synthesis for Creating and Editing Animation",
     "2024-02-24", "svg", "editable-code",
     "面向设计场景的 SVG 动画代码合成：把代码与 GUI 编辑控件打通，"
     "使非程序员能做「有目标的局部修改」。它是本族里唯一以**可编辑性**为主指标的工作"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    src_rows, doc_rows = [], []
    missing = []
    for aid, title, pub, line, tag, note in ARXIV:
        dash = aid.replace(".", "-")
        snap = DOCS / f"doc-arxiv-{dash}-full.txt"
        if not snap.is_file():
            missing.append(aid)
            continue
        sid = f"src-arxiv-{aid}"
        did = f"doc-arxiv-{aid}"
        url = f"https://arxiv.org/abs/{aid}"
        src_rows.append([sid, url, "academic", title, pub, FETCHED, "primary",
                         f"line={line}｜tag={tag}｜{note}"])
        doc_rows.append([did, sid, f"documents/{snap.name}", sha(snap),
                         snap.stat().st_size, "arxiv-html-v1"])

    if missing:
        print(f"[FAIL] 缺快照 {len(missing)} 篇：{missing}")
        return 1

    with (HERE / "sources.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["source_id", "url", "source_type", "title", "published_at",
                    "fetched_at", "trust_tier", "notes"])
        w.writerows(src_rows)

    with (HERE / "documents.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["document_id", "source_id", "snapshot", "content_hash",
                    "bytes", "parser_version"])
        w.writerows(doc_rows)

    print(f"sources {len(src_rows)} ／ documents {len(doc_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
