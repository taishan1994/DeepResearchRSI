"""生成 paper/paper.json —— 论文的结构化规格，供 P1–P3 审计。

## 为什么需要它

`scripts/audit_paper.py` 读 `paper.json` 来校验三条：

  P1 引用闭合   -> 读 sections/figures/tables 的 cites，确认每个 claim_id
                   都存在于 claims.csv，且每条主张都有证据
  P3 无凭空图表 -> 读 figures/tables 声明的产物路径，确认文件真实存在

没有这个文件，`audit_paper.py` 直接 exit，P1–P3 在本归档上从未跑过
（`cuda-kernel-gen` 就是这样，补建后才发现一处图注编造了 `1.19x`）。

## cites 的来源

正文里用 `[c-xxx]` 标注，本脚本从**每个章节的正文**里反推该章节引用了哪些主张。
不自动插标——语义位置要人判断。`cuda-kernel-gen` 曾用锚点自动插入，
16 处里 4 处语义错位。

## 图表

figures 的 `output` 必须是 figures/ 下真实存在的文件名；
tables 的 `data_file` 同理。审计会核。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"
OUT = HERE / "paper.json"

SLUG = "cuda-kernel-rl"
TITLE = "CUDA Kernel 强化学习：奖励设计的演进与它的两个结构性缺陷"
SUBTITLE = "算法没变，变的是奖励"

# 图表声明。output / data_file 必须与磁盘一致，审计会核。
FIGURES = [
    {
        "figure_id": "fig1",
        "kind": "timeline",
        "title": "按季度的核心论文数",
        "caption": "13 篇核心 RL 方法论文按季度分布。2026-Q4 仅 1 篇，"
                   "是检索截止所致，不代表领域降温。",
        "cites": ["c-kernel-rl-fit"],
        "data_file": "data/fig1_timeline.csv",
        "output": "fig1_timeline.png",
    },
    {
        "figure_id": "fig2",
        "kind": "distribution",
        "title": "奖励形态分布",
        "caption": "核心工作的奖励形态分布（一篇可含多种）。结果型与多轮交互各 9 篇，"
                   "并列最高；反作弊机制仅 3 篇。这个不对称是本文第 4 节的论据。",
        "cites": ["c-reward-hacking", "c-structural-reward"],
        "data_file": "data/fig2_reward_forms.csv",
        "output": "fig2_reward_forms.png",
    },
    {
        "figure_id": "fig3",
        "kind": "distribution",
        "title": "核心工作使用的算法",
        "caption": "算法分布。PPO 为 0——在 kernel 场景里无 critic 的 GRPO 因省去"
                   "价值网络开销而占优。7 篇未点名具体算法。",
        "cites": ["c-grpo-default-but-flawed"],
        "data_file": "data/fig3_algorithm.csv",
        "output": "fig3_algorithm.png",
    },
    {
        "figure_id": "fig4",
        "kind": "external",
        "title": "删掉 plan 奖励的代价",
        "caption": "TritonRL 表 3 在 KernelBench Level 1 上的 plan 奖励权重消融。"
                   "α=0.0 即禁用 plan 更新，correct 由 56.0 掉到 37.0。"
                   "数据直接取自该论文表 3，非本文测量。",
        "cites": ["c-ablation-exists", "c-ablation-metric-gap"],
        "data_file": "data/fig4_alpha_ablation.csv",
        # ⚠️ 这张图的数字是**外部事实**（从 TritonRL 表 3 抄来的），
        # 不像图 1-3 那样由 analyze.py 从语料统计得出。
        # 故标记 kind=external，审计 P2 不应要求它做「计数重算」。
        "external_source": "TritonRL (2510.17891) Table 3",
        "output": "fig4_alpha_ablation.png",
    },
]

TABLES = [
    {
        "table_id": "tab1",
        "title": "算法分布",
        "caption": "13 篇核心工作按算法归档。数字由 analyze.py 统计，非人工计数。",
        "cites": ["c-grpo-default-but-flawed"],
        "data_file": "tables/tab1_algo.csv",
    },
    {
        "table_id": "tab2",
        "title": "奖励形态分布",
        "caption": "奖励形态分布。判定词与统计逻辑见 analyze.py 的 REWARD_TAGS。",
        "cites": ["c-structural-reward", "c-reward-hacking"],
        "data_file": "tables/tab2_reward.csv",
    },
    {
        # ⚠️ 这张表原本没登记，于是 md_to_tex.py 按出现顺序把它编号成 tab3，
        #    又从 TABLE_TITLES 里取不到标题，回退成了首列表头「α」——
        #    PDF 里因此出现一个叫「α」的表。表的标题必须来自这里，不能靠推断。
        "table_id": "tab3",
        "title": "plan 奖励权重的消融",
        "caption": "TritonRL 表 3 在 KernelBench Level 1 上的消融（pass@10，%）。"
                   "α 为 plan 奖励权重，α=0 即禁用 plan 更新。"
                   "数据取自该论文表 3，非本文测量。",
        "cites": ["c-ablation-exists"],
        "data_file": "tables/tab3_alpha.csv",
    },
]


def sections() -> list[dict]:
    text = PAPER.read_text(encoding="utf-8")
    lines = text.split("\n")
    heads: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            heads.append((i, line[3:].strip()))

    out: list[dict] = []
    for idx, (start, title) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body = "\n".join(lines[start:end])
        cites = sorted(set(re.findall(r"\[(c-[a-z0-9-]+)\]", body)))
        m = re.match(r"^(\d+)", title)
        num = int(m.group(1)) if m else 0
        clean = re.sub(r"^\d+　?", "", title)
        out.append({
            "section_id": f"sec-{num}" if num else f"sec-{clean[:12]}",
            "number": num,
            "title": clean,
            "file": "PAPER.md",
            "cites": cites,
        })
    return out


def abstract() -> str:
    text = PAPER.read_text(encoding="utf-8")
    m = re.search(r"## 摘要\n(.*?)\n## ", text, re.S)
    if not m:
        return ""
    # 去掉 Markdown 粗体标记，保留纯文本
    return re.sub(r"\*\*|\n+", lambda x: "" if x.group(0).startswith("**") else " ",
                  m.group(1)).strip()


def keywords() -> list[str]:
    text = PAPER.read_text(encoding="utf-8")
    m = re.search(r"\*\*关键词\*\*：(.+)", text)
    if not m:
        return []
    return [k.strip() for k in re.split(r"[；;、,，]", m.group(1)) if k.strip()]


def main() -> int:
    spec = {
        "paper_id": f"paper-{SLUG}",
        "slug": SLUG,
        "title": TITLE,
        "subtitle": SUBTITLE,
        "as_of": "2026-11-04",
        "language": "zh",
        "abstract": abstract(),
        "keywords": keywords(),
        "sections": sections(),
        "figures": FIGURES,
        "tables": TABLES,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    n_cites = sum(len(s["cites"]) for s in spec["sections"])
    print(f"paper.json 已生成：{len(spec['sections'])} 节、"
          f"{len(FIGURES)} 图、{len(TABLES)} 表、正文引用 {n_cites} 处")
    missing = [s["section_id"] for s in spec["sections"] if not s["cites"]]
    if missing:
        print(f"  [!] 无引用的章节：{missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
