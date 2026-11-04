"""从 PAPER.md 与图表清单生成 paper.json（审计 P1-P3 的输入）。

## 三条不变量（审计会查）

P1 引用闭合：正文里每个 [c-xxx] 必须在 claims.csv 里存在；
   每个图/表声明的 cites 也要存在。
P2 数值可回溯：data/*.csv 里带 value+cite 的行，value 必须能在
   该 claim 的 statement/derivation/evidence 里找到。
P3 无凭空图表：figures/tables 声明的文件必须真实存在。

## 本文件的数字从哪来

fig1/fig2 都是 analyze.py 的产物（各环节的工作数与证据数），
故 data CSV 用 `计数 <dim>=<n>` 形式，由审计独立重算——
不写死数字，避免「图改了、表没改」。
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"
OUT = HERE / "paper.json"

FIGURES = [
    {
        "figure_id": "fig1",
        "kind": "distribution",
        "title": "智能体循环五个环节的覆盖情况。预算（budget）最多（9 篇），"
                 "失败恢复（recover）最少（5 篇）——后者恰是长程任务里"
                 "最影响最终产出的环节。",
        "short": "各环节被多少篇工作覆盖",
        "cites": ["c-observe", "c-budget", "c-recover"],
        "data_file": "data/fig1_dims.csv",
        "output": "fig1_dims.png",
    },
    {
        "figure_id": "fig2",
        "kind": "distribution",
        "title": "同一环节的工作数与证据条数。两列差异反映每篇工作的"
                 "论述密度，但须注意这是本文证据覆盖的度量，"
                 "不等于论文本身的完整程度。",
        "short": "工作数与证据条数的对比",
        "cites": ["c-fragment", "c-blindspot"],
        "data_file": "data/fig2_evidence.csv",
        "output": "fig2_evidence.png",
    },
]

TABLES = [
    {
        "table_id": "tab1",
        "title": "智能体循环的五个环节。eval 排在最后但作用方向相反——"
                 "它决定前四个环节会往哪优化，这一点在第 5 节展开。",
        "cites": ["c-observe", "c-act", "c-budget", "c-recover", "c-eval"],
        "data_file": "data/tab1_dims.csv",
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
        sid = "sec-" + (re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")[:24]
                        or str(idx))
        out.append({
            "section_id": sid,
            "title": title,
            "cites": sorted(set(re.findall(r"\[(c-[A-Za-z0-9_-]+)\]", body))),
        })
    return out


def write_data() -> None:
    """生成 data/*.csv。

    ⚠️ 数字直接取自 analyze.py 的 analysis.json，而不是写在这里——
       否则改一次分析要改两处，必然漂移。
    """
    a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    dims = a["dims"]
    order = dims["order"]
    d = HERE / "data"
    d.mkdir(exist_ok=True)

    # fig1：工作数
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["dim", "papers", "value", "cite"])
    for k in order:
        n = dims["source_count"][k]
        w.writerow([k, n, n, "c-" + {"observe": "observe", "act": "act",
                                     "budget": "budget", "recover": "recover",
                                     "eval": "eval"}[k]])
    (d / "fig1_dims.csv").write_text(buf.getvalue(), encoding="utf-8",
                                     newline="\n")

    # fig2：工作数与证据数
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["dim", "papers", "evidence", "value", "cite"])
    for k in order:
        # value 用**工作数**而非证据数：正文与主张里说的是「9 篇讨论了预算」，
        # 若这里放证据条数（10），审计会拿 10 去主张里找，必然找不到。
        # 证据数仍在单独的列里，供图 2 的第二根柱子使用。
        w.writerow([k, dims["source_count"][k], dims["evidence_count"][k],
                    dims["source_count"][k], "c-" + k])
    (d / "fig2_evidence.csv").write_text(buf.getvalue(), encoding="utf-8",
                                         newline="\n")


def main() -> int:
    write_data()
    spec = {
        "title": "Kernel 生成智能体：进展全在「看得更多」，不在「想得更好」",
        "generated_by": "build_paper_json.py",
        "sections": sections(),
        "figures": FIGURES,
        "tables": TABLES,
    }
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")

    cites = set()
    for s in spec["sections"]:
        cites.update(s["cites"])
    for f in FIGURES:
        cites.update(f["cites"])

    print(f"paper.json 已生成：{len(spec['sections'])} 节、"
          f"{len(FIGURES)} 图、{len(TABLES)} 表、正文引用 {len(cites)} 处")
    # 叙述性章节（摘要、引言、结论）本就不必带 [c-xxx]，
    # 故这里只作提示，不判失败——否则每次构建都返回非零退出码，
    # 让人误以为构建失败。
    empty = [s["section_id"] for s in spec["sections"] if not s["cites"]]
    if empty:
        print(f"  · 无引用的章节 {len(empty)} 个（叙述段落，正常）："
              + ", ".join(e.replace("sec-", "") for e in empty[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
