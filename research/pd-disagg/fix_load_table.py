"""把 sec11 的裸 tabular 改成引用 tab:load 的正式表格。

## 为什么要改

正文里原本用一个 center+tabular 内联小表。问题有两个：
  1. 它没有编号，读者无法在正文里引用它
  2. paper.json 里登记了 tab8，但正文没有 \ref{tab:load}，
     审计会报「正文可能没有引用表」

改成 table 环境后，tab8 的数据文件与正文的 \ref 对上。

## 为什么用 tabular 内联而不是 \input 表格文件

LaTeX 侧的表由 paper/tables/tab8_load.csv 生成到 PAPER.md（供
markdown 版使用），但 .tex 里的排版需要手工控制列宽（p{} 单位），
故 tex 侧保持内联，只加 label 与 caption。两边的数据必须一致——
tab8_load.csv 与本节文字同源于 claims.csv 的 c-load。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
SEC = HERE / "paper" / "sec11_load.tex"
BS = chr(92)

OLD_HEAD = (
    BS + "begin{center}\n"
    + BS + "small\n"
    + BS + "begin{tabular}{@{}p{2.6cm}p{1.9cm}p{4.4cm}@{}}\n"
)
NEW_HEAD = (
    BS + "begin{table}[t]\n"
    + BS + "centering\n"
    + BS + "caption{缓存能换回多少：三个不同性质的数。幅度差别主要来自\n"
    + "基线不同，故第三列是这张表的关键。}\n"
    + BS + "label{tab:load}\n"
    + BS + "small\n"
    + BS + "begin{tabular}{@{}p{2.6cm}p{1.9cm}p{4.4cm}@{}}\n"
)
OLD_TAIL = BS + "end{tabular}\n" + BS + "end{center}"
NEW_TAIL = BS + "end{tabular}\n" + BS + "end{table}"


def main() -> int:
    s = SEC.read_text(encoding="utf-8")
    n_head = s.count(OLD_HEAD)
    n_tail = s.count(OLD_TAIL)
    print(f"头部候选 {n_head} 处 | 尾部候选 {n_tail} 处")
    if n_head != 1:
        print("[!] 头部不是恰好一处，停止以免改错表")
        return 1
    s = s.replace(OLD_HEAD, NEW_HEAD, 1)
    i = s.rfind(OLD_TAIL)
    if i < 0:
        print("[!] 尾部未找到")
        return 1
    s = s[:i] + NEW_TAIL + s[i + len(OLD_TAIL):]
    SEC.write_text(s, encoding="utf-8", newline="\n")
    print(f"已改：{len(s)} 字符")
    print("检查：", "table 环境", s.count(BS + "begin{table}"),
          "| label", s.count(BS + "label"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
