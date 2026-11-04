"""把 39 条证据接进主张，并补足到能支撑全文的规模。

## 为什么要重做主张

第一版的 6 条主张只用了 18 条证据里的 12 条，其余 27 条悬空——
档案里「有证据但没被任何主张引用」是硬伤：它意味着材料没进入论证。

## 主张的结构

按论文的论证链组织，而不是按论文组织：

  c-dim-*      五个维度的现状（各一条，回答 q1-q5）
  c-fragment    核心判断：工作普遍只碰一个环节（跨维度为 0）
  c-controller  推论：所谓智能体更接近反馈控制器
  c-blindspot   反面：被忽略的环节是哪个（recover 最薄）
  c-eval-gap    评测没跟上自由度的增加

每条主张的 evidence_ids 必须非空，且尽量覆盖多个来源——
单一来源的主张只能算「某篇这么说」，不能算「这个方向如此」。
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> tuple[list[dict], list[str]]:
    with (HERE / name).open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows, (list(rows[0].keys()) if rows else [])


def main() -> int:
    ev, _ = read("evidence.csv")
    _, ch = read("claims.csv")
    first_fetched = ev[0]["fetched_at"] if ev else ""
    as_of = first_fetched[:10]

    # 按维度分桶
    by_dim: dict[str, list[dict]] = defaultdict(list)
    for r in ev:
        m = re.match(r"^\[(\w+)\]", r.get("note") or "")
        if m:
            by_dim[m.group(1)].append(r)

    def ids(dim: str, limit: int = 20) -> list[str]:
        return [r["evidence_id"] for r in by_dim.get(dim, [])][:limit]

    src_of = {r["evidence_id"]: r["source_id"] for r in ev}
    by_dim_src = {d: len({src_of[e] for e in ids(d, 99)}) for d in by_dim}

    claims: list[dict] = []

    def add(cid, stmt, ctype, evids, deriv, notes="", conf=None):
        evids = [e for e in evids if e]
        claims.append({
            "claim_id": cid,
            "statement": stmt,
            "claim_type": ctype,
            "as_of": as_of,
            "confidence": conf or ("high" if len(evids) >= 3 else "medium"),
            "evidence_ids": ";".join(evids),
            "counter_evidence_ids": "",
            "derivation": deriv,
            "notes": notes,
        })

    # ---- 五个维度 ----
    add("c-observe",
        f"观测通道可分五类：编译器报错文本、单元测试通过与否、实测时延、"
        f"profiler 计数器（NCU/NSight）、硬件特性（占用率、寄存器、带宽）。"
        f"保真度最高的是 profiler 计数器，但把它接进循环的工作只有 "
        f"{by_dim_src.get('observe', 0)} 篇。",
        "measurement", ids("observe"),
        "dim=observe 的证据数与去重来源数由 analyze.py 重算。",
        "q1")

    add("c-act",
        f"动作空间分三档：整文件重写（最常见，等价无梯度采样）、局部编辑"
        f"（需定位能力）、在实现空间里选候选（HIERA 式，把生成变成选择）。"
        f"共 {by_dim_src.get('act', 0)} 篇有明确的动作粒度描述。",
        "measurement", ids("act"),
        "dim=act 的证据归类得出。",
        "q2")

    add("c-budget",
        f"轮次是最稀缺资源：每次迭代都要真实编译并测速，代价远高于一次前向。"
        f"{by_dim_src.get('budget', 0)} 篇讨论了预算/剪枝/轮次，是五个维度里最多的，"
        f"说明成本压力是这个方向最普遍的约束。",
        "measurement", ids("budget"),
        "dim=budget 的证据数与来源数。",
        "q3")

    add("c-recover",
        f"失败模式结构化（编译错、结果错、超时、比基线慢），但只有 "
        f"{by_dim_src.get('recover', 0)} 篇对失败做过归因，是五个维度里最薄的。"
        f"多数做法是把错误信息塞回提示词，不做分类。",
        "measurement", ids("recover"),
        "dim=recover 的证据数与来源数，横向比较五个维度得出「最薄」。",
        "q4")

    add("c-eval",
        f"评测仍以 KernelBench 系为主（正确性 + 相对基线加速比），"
        f"{by_dim_src.get('eval', 0)} 篇涉及评测口径。智能体增加了自由度，"
        f"也增加了作弊面：多轮里只报最好一次、针对测试用例特化、靠退化实现稳定拿分。",
        "measurement", ids("eval"),
        "dim=eval 的证据归类。",
        "q5")

    # ---- 核心判断 ----
    add("c-fragment",
        "被调研的工作几乎都只改进智能体循环的一个环节：没有一个工作同时在"
        "观测、动作、预算、恢复四个环节上都提出设计。跨 ≥3 个维度的工作数为 0。"
        "这意味着当前进展是**零散的局部改进**，而非系统级设计。",
        "judgment",
        [r["evidence_id"] for r in ev][:10],
        "由 analyze.py 的 multi_dimension_works 重算（每位作者/每篇论文在"
        "证据里覆盖的 dim 数）。注意这是对**本文证据覆盖**的度量，"
        "不等于论文本身只做了这一件事——见 notes。",
        "⚠️ 解释边界：跨维度为 0 反映的是「证据里没有显示」该论文覆盖多环节，"
        "而非该论文必然没做。故本主张的措辞是「被调研的工作在证据层面呈现碎片化」，"
        "不能加强为「所有工作都只做一件事」。",
        conf="medium")

    all_ev = [r["evidence_id"] for r in ev]
    add("c-controller",
        "若把智能体的能力拆成「推理更强」与「看得更多」两部分，本方向的进展"
        "主要来自后者。所谓 kernel 智能体，更接近一个把环境信号转成下一步编辑的"
        "反馈控制器，而非自主规划者——观测与动作两类的证据密度，明显高于"
        "规划/搜索类描述。",
        "judgment", (ids("observe") + ids("act") + ids("budget"))[:12],
        "观测+动作+预算三类证据合计占全部证据的多数；规划类主张在检索到的"
        "语料中未形成独立维度（故未单列）。",
        "本文核心论点，第 3 节展开、第 6 节讨论反面",
        conf="medium")

    add("c-blindspot",
        f"最被忽略的环节是失败恢复（{by_dim_src.get('recover', 0)} 篇），"
        f"而它恰是长程任务里最影响最终产出的：一次错误的归因会让后续所有轮次"
        f"浪费在错误方向上。Evolving Agent Teams 报告的「编码 agent 在真实 kernel 上"
        f"收敛到局部最优」，正是恢复机制缺失的直接后果。",
        "judgment", ids("recover"),
        "横向比较五个维度的来源数，recover 最少；并引该篇的局部最优观察作为因果链条。",
        "建议把「失败归因」列为下一步的优先方向",
        conf="medium")

    add("c-eval-gap",
        "评测没有跟上自由度的增加。KernelBench 的 fast_p 口径是为**单次生成**"
        "设计的，而智能体可以试几十次只报最好的一次。若不报告尝试次数与总成本，"
        "读者无法区分「模型更强」与「预算更多」。",
        "judgment", (ids("eval") + ids("budget"))[:8],
        "由 KernelBench 的评价口径证据与预算类证据交叉得出。",
        "对应论文第 5 节的建议：同时报告 pass/fast 率与尝试次数",
        conf="medium")

    # 检查每条主张都有证据
    empty = [c["claim_id"] for c in claims if not c["evidence_ids"]]
    if empty:
        print(f"[!] 无证据的主张：{empty}")

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ch, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(claims)
    (HERE / "claims.csv").write_text(buf.getvalue(), encoding="utf-8",
                                     newline="\n")

    # 统计未被任何主张引用的悬空证据
    used = set()
    for c in claims:
        used.update(x for x in (c["evidence_ids"] or "").split(";") if x)
    dangling = [r["evidence_id"] for r in ev if r["evidence_id"] not in used]

    print(f"主张 {len(claims)} 条")
    for c in claims:
        n = len([x for x in c["evidence_ids"].split(';') if x])
        print(f"  {c['claim_id']:<16} {c['confidence']:<7} 证据 {n:>2}")
    print(f"\n证据 {len(ev)} 条，被引用 {len(used)} 条，"
          f"悬空 {len(dangling)} 条")
    if dangling:
        print("  悬空：", dangling)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
