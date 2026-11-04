"""把 PAPER.md 转成 body.tex。

## 为什么不手写 body.tex

手写意味着同一份内容有两个副本，改一处必然忘另一处。
`cuda-kernel-gen` 的做法是手写 body.tex，结果正文改动后 PDF 与
PAPER.md 长期不一致，只能靠人工比对。

本脚本做**机械转换**：
  Markdown 标题  -> \\section / \\subsection
  **粗体**       -> \\textbf{}
  `代码`         -> \\texttt{}
  ![说明](路径)  -> figure 环境（含 caption）
  |表格|         -> booktabs tabular
  $$公式$$       -> equation 环境
  [c-xxx]        -> 删除（内部引用标记，不进排版）

## 图注里的编号

图注只写「图 N：说明」，编号由 LaTeX 的 \\caption 自动生成。
不在图内标题重复编号——这是上一份综述踩过的坑（出现「图 3：图 3」）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD = HERE / "PAPER.md"
OUT = HERE / "latex" / "body.tex"
SPEC = json.loads((HERE / "paper.json").read_text(encoding="utf-8"))

# 图 -> 标题。编号不写，交给 LaTeX。
FIG_TITLES = {f["output"]: f["title"] for f in SPEC["figures"]}
TABLE_TITLES = {t["table_id"]: t["title"] for t in SPEC["tables"]}


def esc_tex(s: str) -> str:
    """转义 LaTeX 特殊字符。中文不需要转义，只处理 ASCII 特殊符号。"""
    # 先保护已有的 LaTeX 命令（本文件的输入不含，但防未来）
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"),
                 ("_", r"\_"), ("$", r"\$")):
        s = s.replace(a, b)
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    return s


def inline(s: str) -> str:
    r"""行内标记转换。

    ⚠️ 顺序是本函数的全部难点，改之前务必读完。

    历史问题：本函数原先**只**处理粗体与行内代码，对普通文字不做任何转义。
    正文里恰好没有裸的 `_ % & #`，所以一直没暴露；但参考文献的
    `make_references.py` 一出现，`make_references.py` 里的下划线就让
    XeLaTeX 报 `Missing $ inserted`——`_` 在数学模式外是非法字符。

    正确做法是「先把要保留的 LaTeX 结构挖成占位符 → 转义剩下的文字
    → 再把占位符填回去」。若先转义再替换，`\href{...}` 的花括号与反斜杠
    会被一并转义，生成 `\textbackslash{}href` 这种垃圾。
    """
    # ---- 1. 挖出需要原样保留的结构，换成占位符 ----
    stash: list[str] = []
    # ⚠️ 哨兵不能用字面量 "\x00" 写进 f-string/正则——Python 会把
    #    "\x00{...}" 里的 \x00 正常解析，但同一函数里若出现 "\f"、"\a"
    #    这类序列（例如 repr 中的路径）会被当成转义字符，静默吞掉字母。
    #    故用 chr() 构造，且正则用 chr(0) 拼接。
    NUL = chr(0)

    def keep(latex: str) -> str:
        stash.append(latex)
        return f"{NUL}{len(stash) - 1}{NUL}"

    # <url> 自动链接 -> \url{}
    # \url 自己处理 _ ~ # %，故整个 URL 原样保留，不转义
    s = re.sub(r"<(https?://[^>\s]+)>",
               lambda m: keep(r"\url{" + m.group(1) + "}"), s)
    # [文字](url) -> \href{url}{文字}
    # URL 原样；显示文字仍需转义，故先把文字转义好再存起来
    s = re.sub(
        r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: keep(r"\href{" + m.group(2) + "}{"
                       + esc_tex(m.group(1)) + "}"),
        s)
    # `代码` -> \texttt{}
    s = re.sub(r"`([^`]+)`",
               lambda m: keep(r"\texttt{" + esc_tex(m.group(1)) + "}"), s)
    # $...$ 数学式：原样保留（不能对它做转义）
    s = re.sub(r"\$([^$]+)\$",
               lambda m: keep("$" + m.group(1) + "$"), s)

    # ---- 2. 删掉内部引用标记 [c-xxx] ----
    s = re.sub(r"\s*\[c-[a-z0-9-]+\]", "", s)

    # ---- 3. 转义剩下的普通文字 ----
    s = esc_tex(s)

    # ---- 4. 粗体（在转义后做，`*` 不受 esc_tex 影响）----
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: r"\textbf{" + m.group(1) + "}", s)

    # ---- 5. 填回占位符 ----
    def restore(m: re.Match[str]) -> str:
        return stash[int(m.group(1))]

    s = re.sub(NUL + r"(\d+)" + NUL, restore, s)
    return s


def convert_table(lines: list[str]) -> str:
    """Markdown 表格 -> booktabs tabular。"""
    rows = [ln.strip() for ln in lines if ln.strip().startswith("|")]
    if len(rows) < 2:
        return ""
    cells: list[list[str]] = []
    for r in rows:
        # 去掉首尾竖线后按 | 切
        parts = [c.strip() for c in r.strip("|").split("|")]
        cells.append(parts)
    # 第二行是 |---|---|
    header = cells[0]
    body = [r for r in cells[1:] if not re.fullmatch(r"[-:\s|]+", "|".join(r))]
    ncol = len(header)
    # ⚠️ 不能直接用 {lrr}：第一列是中文说明（「GRPO 及其变体」），
    # l 列不换行，会把表格撑出版心 39.8pt（实测）。
    # 用 tabularx：首列固定可换行宽度，其余列按内容右对齐。
    # 双栏版心宽约 \columnwidth，tabularx 的宽度必须显式给 \columnwidth。
    rest = "r" * (ncol - 1)
    out = [r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X"
           + rest + "}",
           r"\toprule"]
    out.append(" & ".join(inline(esc_tex(c)) if False else inline(c)
                          for c in header) + r" \\")
    out.append(r"\midrule")
    for r in body:
        # 补/截到 ncol，避免列数不齐导致编译失败
        r = (r + [""] * ncol)[:ncol]
        out.append(" & ".join(inline(c) for c in r) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabularx}")
    return "\n".join(out)


def main() -> int:
    md = MD.read_text(encoding="utf-8")
    # 参考文献章节由 make_references.py 从 sources.csv 生成，追加到正文末尾。
    # ⚠️ 不写进 PAPER.md：那会让「论文源文件」与「文献表的真实来源（sources.csv）」
    #    各存一份 20 条清单，改一处忘另一处。生成物只在这里拼接。
    refs = HERE / "REFERENCES_SECTION.md"
    if refs.is_file():
        md = md.rstrip("\n") + "\n\n" + refs.read_text(encoding="utf-8")
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    # 统计标题出现次数，用于给图/表分配编号（LaTeX 自动编号，这里只判"第几个"）
    fig_seen = 0
    tab_seen = 0
    sec = 0
    sub = 0
    appendix_done = False

    # 摘要：单独处理成 abstract 环境
    in_abstract = False
    in_code = False

    while i < len(lines):
        line = lines[i]
        st = line.strip()

        # ---- 摘要块 ----
        if st == "## 摘要":
            in_abstract = True
            out.append(r"\begin{abstract}")
            i += 1
            continue
        if in_abstract:
            if st.startswith("## "):
                in_abstract = False
                out.append(r"\end{abstract}")
                # 不 i+=1，让下面的标题处理接手
            elif st.startswith("**关键词**"):
                kw = st.split("：", 1)[-1]
                kw = re.sub(r"\*\*", "", kw)
                out.append(r"\vspace{4pt}\noindent\textbf{关键词：}" +
                           inline(kw))
                i += 1
                continue
            elif st:
                out.append(inline(st))
                i += 1
                continue
            else:
                out.append("")
                i += 1
                continue
        if in_abstract is False and st == r"\end{abstract}":
            i += 1
            continue

        # ---- HTML 注释块：跳过 ----
        if st.startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue

        # ---- 标题 ----
        if st.startswith("# "):
            # 主标题在 main.tex 里，跳过
            i += 1
            continue
        if st.startswith("## "):
            title = st[3:].strip()
            m = re.match(r"^(\d+)　?(.*)$", title)
            if m:
                sec = int(m.group(1))
                sub = 0
                out.append(r"\section{" + inline(m.group(2)) + "}")
            elif title.startswith("附录"):
                # ⚠️ \appendix 只能出现一次：它的作用是把后续 section
                # 的编号改成 A/B/C。若每个附录都写一遍，第二个会重置计数器，
                # 两个附录都叫「A」（实测本文附录 B 变回了 A）。
                if not appendix_done:
                    out.append(r"\appendix")
                    appendix_done = True
                out.append(r"\section{" +
                           inline(re.sub(r"^附录\s*[A-Z]　?", "", title)) + "}")
            else:
                out.append(r"\section*{" + inline(title) + "}")
            i += 1
            continue
        if st.startswith("### "):
            title = st[4:].strip()
            m = re.match(r"^(\d+\.\d+)　?(.*)$", title)
            txt = m.group(2) if m else title
            out.append(r"\subsection{" + inline(txt) + "}")
            i += 1
            continue

        # ---- 图片 ----
        m = re.match(r"^!\[(.*?)\]\((.+?)\)$", st)
        if m:
            alt, path = m.group(1), m.group(2)
            fname = Path(path).name
            fig_seen += 1
            title = FIG_TITLES.get(fname, alt)
            # ⚠️ 让图号跟随**文件名**，而不是出现顺序。
            # 本文的正文在第 3.2 节才提「图 2 奖励形态」，但 fig2 的
            # 图片块排在 3.3 节（讲完算法之后）——若按出现顺序自动编号，
            # fig1->图1、fig3->图2、fig2->图3，正文的「图 2」就指向了
            # 算法分布图（实测确实错位）。故显式把计数器设成文件名里的编号。
            fm = re.search(r"fig(\d+)", fname)
            out.append(r"\begin{figure}[t]")
            out.append(r"\centering")
            out.append(r"\includegraphics[width=\linewidth]{" +
                       "../figures/" + fname + "}")
            # caption 只写说明，编号由 LaTeX 生成（此处重置计数器对齐文件名）
            if fm:
                out.append(r"\setcounter{figure}{" + str(int(fm.group(1)) - 1) + "}")
            out.append(r"\caption{" + inline(title) + "}")
            out.append(r"\label{fig:" + fname.replace(".png", "") + "}")
            out.append(r"\end{figure}")
            i += 1
            continue

        # ---- 表格 ----
        if st.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            tab_seen += 1
            tid = f"tab{tab_seen}"
            out.append(r"\begin{table}[t]")
            out.append(r"\centering")
            out.append(r"\caption{" + inline(TABLE_TITLES.get(tid, "")) + "}")
            out.append(r"\label{" + tid + "}")
            out.append(r"\small")
            out.append(convert_table(block))
            out.append(r"\end{table}")
            continue

        # ---- 公式块 ----
        if st == "$$":
            out.append(r"\begin{equation*}")
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                out.append(lines[i])
                i += 1
            out.append(r"\end{equation*}")
            i += 1
            continue

        # ---- 列表 ----
        if re.match(r"^[-*] ", st):
            out.append(r"\begin{itemize}")
            while i < len(lines) and re.match(r"^[-*] ", lines[i].strip()):
                out.append(r"\item " + inline(lines[i].strip()[2:]))
                i += 1
            out.append(r"\end{itemize}")
            continue

        # ---- 普通段落 ----
        out.append(inline(line) if st else "")
        i += 1

    if in_abstract:
        out.append(r"\end{abstract}")

    text = "\n".join(out)
    # 压缩连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 参考文献章节整体包进 refs 环境（导言区定义为 \raggedright\small）。
    # ⚠️ 不这么做时，20 条 arXiv URL 作为不可断长 token 会逼迫 LaTeX
    #    把同段的中文标题逐词拆行（实测出现「Micro- / Profiling Tools as
    #    Expert Surrogates for LLM-Based GPU / Kernel / Optimization」）。
    #    配合导言区的 xurl + \UrlBreaks，URL 本身也能在任意字符处断开。
    m = re.search(r"\\section\{参考文献\}", text)
    if m:
        head = text[:m.end()]
        tail = text[m.end():]
        text = (head + "\n" + r"\begin{refs}" + tail.rstrip()
                + "\n" + r"\end{refs}" + "\n")

    OUT.write_text(text, encoding="utf-8", newline="\n")

    print(f"body.tex 已生成：{len(out)} 行")
    print(f"  figure {fig_seen} 个、table {tab_seen} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
