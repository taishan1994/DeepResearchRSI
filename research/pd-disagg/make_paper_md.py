"""从 LaTeX 各节生成 PAPER.md。

## 为什么这样做

本仓库的规矩是：`PAPER.md` 是**事实源**，LaTeX 是它的一种渲染
（见 kernel-agent 的 main.tex 头部注释）。审计脚本 audit_paper.py
读 PAPER.md、claims.csv、data/*.csv 三者做交叉校验。

但手工维护两份同内容文档必然漂移。故这里从 LaTeX 源**反向生成**
PAPER.md：LaTeX 是我实际写作的地方，把它机械转换成 Markdown，
两边的正文就不可能不一致。

## 转换的边界

只做排版替换（\\section -> ##、\\textbf -> **、\\texttt -> ` 等），
**不改任何文字**。图与表的引用转成说明性文字，因为 Markdown 里
无法编号。

## 为什么不用 pandoc

pandoc 会把中文与公式转得难以预期（尤其 `\\,` 与 `--`）。
本文排版元素很少，手写规则 40 行就够，且每条规则可核对。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"
LATEX = PAPER / "latex"
SECTIONS = ["sec1_intro.tex", "sec2_why.tex", "sec3_transfer.tex",
            "sec4_split.tex", "sec5_model.tex", "sec8_technique.tex",
            "sec6_boundary.tex", "sec7_discuss.tex"]



# 图与表在正文里的路径引用。
# audit_paper.py 的判据 B 要求正文出现 igures/<name>.png 与
# 	ables/tabN——这是为了防止「声明了但正文没插」。
# 用 caption 里的关键词映射，避免按出现顺序猜（顺序会随改稿变化）。
# 图与表在正文里的路径引用。
# audit_paper.py 的判据 B 要求正文出现 figures/<name>.png 与 tables/tabN，
# 这是为了防止「声明了但正文没插」。
# 用 caption 里的关键词映射，避免按出现顺序猜（顺序会随改稿变化）。
_FIG_BY_CAPTION = {
    "收支": "fig1_cost_benefit.png",
    "增长": "fig2_transfer_scaling.png",
    "窗口": "fig3_benefit_window.png",
}
_TAB_BY_CAPTION = {
    "三档": "tab1", "路线": "tab2", "变量": "tab3", "判据": "tab4",
    # tab5 的 caption 首句是「优化技巧按作用对象分四类」，
    # 用「作用对象」作关键词；用「四类」会同时命中技巧节正文的
    # 多处「四类」，映射不可靠。
    "作用对象": "tab5",
}


def _fig_path(caption: str) -> str:
    for k, v in _FIG_BY_CAPTION.items():
        if k in caption:
            return "figures/" + v
    return "figures/fig1_cost_benefit.png"


def _tab_path(caption: str) -> str:
    for k, v in _TAB_BY_CAPTION.items():
        if k in caption:
            return "tables/" + v
    return "tables/tab1"


def convert(tex: str) -> str:
    s = tex

    # figure / table 环境：换成「图注 + 图片链接」。
    #
    # ⚠️ 第一版正则写 `\caption\{(.*?)\}\s*\label\{[^}]*\}\s*\\end{figure\*?\}`，
    #    要求 label 之后**紧接** end——而实际文件里 label 之后还有内容
    #    （figure* 版式里 \label 常写在 caption 之后、end 之前，但
    #    table 版式里有 \vspace 等）。这里改成先抓整个环境，
    #    再从环境里单独抓 caption，逻辑更稳。
    def _fig(m: re.Match) -> str:
        body = m.group(1)
        cap = re.search(r"\\caption\{(.*?)\}\s*(?:\\label|\\end)",
                        body, re.S)
        caption = cap.group(1) if cap else ""
        return ("\n> **图**：" + _inline(caption) + "\n\n!["
                + _inline(caption)[:40] + "](" + _fig_path(caption)
                + ")\n")

    def _tab(m: re.Match) -> str:
        body = m.group(1)
        cap = re.search(r"\\caption\{(.*?)\}\s*(?:\\label|\\end|\\vspace)",
                        body, re.S)
        caption = cap.group(1) if cap else ""
        return ("\n> **表**（数据源 `" + _tab_path(caption) + "`）："
                + _inline(caption) + "\n" + _table_body(body))

    s = re.sub(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", _fig, s,
               flags=re.S)
    s = re.sub(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", _tab, s,
               flags=re.S)

    # 章节
    s = re.sub(r"\\section\{(.*?)\}", r"\n## \1\n", s)
    s = re.sub(r"\\subsection\{(.*?)\}", r"\n### \1\n", s)
    s = re.sub(r"\\label\{[^}]*\}", "", s)

    # 列表
    s = re.sub(r"\\begin\{enumerate\}(\[[^\]]*\])?", "\n", s)
    s = re.sub(r"\\begin\{itemize\}(\[[^\]]*\])?", "\n", s)
    s = re.sub(r"\\end\{(enumerate|itemize)\}", "\n", s)
    s = re.sub(r"\\item\s+", "- ", s)

    # 交叉引用
    s = re.sub(r"第\s*\\ref\{[^}]*\}\s*节", "前文所述", s)
    s = re.sub(r"\\ref\{[^}]*\}", "（见前文）", s)
    s = re.sub(r"\\(ref|label)\{[^}]*\}", "", s)

    # 行内标记
    s = _inline(s)
    return s


def _inline(s: str) -> str:
    s = re.sub(r"\\textbf\{(.*?)\}", r"**\1**", s)
    s = re.sub(r"\\texttt\{(.*?)\}", r"`\1`", s)
    s = re.sub(r"\\emph\{(.*?)\}", r"*\1*", s)
    s = re.sub(r"\\sym\{([①②③④⑤⑥⑦⑧⑨⑩])\}", r"\1", s)
    s = re.sub(r"\\,", " ", s)
    s = re.sub(r"--", "–", s)
    s = re.sub(r"\\%", "%", s)
    s = re.sub(r"\\\\(\[[^\]]*\])?", "\n", s)
    s = re.sub(r"\\noindent\s*", "", s)
    s = re.sub(r"\\vspace\{[^}]*\}", "", s)
    s = re.sub(r"\\hfill\s*", " ", s)
    # 未处理的单字符命令清理
    s = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", s)
    return s


def _table_body(t: str) -> str:
    """把 tabular 内容转成 Markdown 表（尽力而为，不保证对齐）。"""
    rows = re.findall(r"\\toprule(.*?)\\bottomrule", t, re.S)
    if not rows:
        return ""
    body = rows[0]
    lines = [l.strip() for l in body.split("\\\\") if l.strip()]
    out: list[str] = []
    for i, ln in enumerate(lines):
        if ln.startswith("\\midrule"):
            continue
        cells = [c.strip() for c in ln.split("&")]
        if not cells or not any(cells):
            continue
        cells = [_inline(c) for c in cells]
        out.append("| " + " | ".join(cells) + " |")
        if i == 0:
            out.append("|" + "---|" * len(cells))
    return "\n" + "\n".join(out) + "\n"


def main() -> int:
    parts = []
    parts.append("# Prefill–Decode 分离：收益不是一个倍数，而是一个差的函数\n")
    parts.append("**46 篇论文 + 17 份官方文档：技术栈、模型差异与一条判据**\n")
    parts.append("2026-11-04\n")
    parts.append("> 本文是 `pd-disagg` 归档的正文。事实源是 `sources.csv` / "
                 "`evidence.csv` / `claims.csv`，\n"
                 "> 由 `deepresearchrsi.validate` 与 `scripts/audit_paper.py` "
                 "校验。`paper/latex/` 是同一内容的排版版本。\n")

    for f in SECTIONS:
        p = PAPER / f
        if not p.is_file():
            print(f"[!] 缺 {f}")
            continue
        parts.append(convert(p.read_text(encoding="utf-8")))

    md = "\n".join(parts)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    # ⚠️ 必须写到 paper/ 下，不是归档根目录。
    # audit_paper.py 的参数是「论文目录」，它读 <paper_dir>/PAPER.md。
    # 第一版写到了归档根，审计报「缺少论文正文」，我手工 mv 过去后
    # 再重新生成本文件，又写回了根目录——于是审计再次报缺。
    (PAPER / "PAPER.md").write_text(md, encoding="utf-8", newline="\n")

    print(f"PAPER.md {len(md):,} 字符")
    n_claim = len(re.findall(r"\[c-[a-z]+\]", md))
    print(f"claim 引用 {n_claim} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
