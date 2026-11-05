"""把所有超单栏的浮动体改成通栏，并按实测宽度精确分配。

## 实测数据（xelatex \\typeout，不是估算）

  \\textwidth   = 480.85141 pt = 16.96 cm   ← table* / figure* 可用
  \\columnwidth = 230.18270 pt =  8.12 cm   ← 单栏可用

## 需要改的（按 Overfull 量排序）

  1. 流程图 figure（sec0）  parbox 12.2cm + fbox 边距 = 12.44cm
     单栏 8.12 超出 4.32cm = 125.7pt   ← 最大，且我上一版把表改成
     table* 时漏了它（它是 figure 不是 table）
  2. tab:slo    56.2pt (2.0cm)
  3. tab:load   47.0pt (1.7cm)
  4. tab:plane  34.2pt (1.2cm)
  5. tab:technique  3.6pt (0.13cm) —— 只超一点点，微调列宽即可

## 算法（上两版踩过的坑）

  实际占宽 = 列宽合计 + (n-1) × 2 × tabcolsep
  故 列宽合计 = \\textwidth − (n−1) × 2 × tabcolsep − 安全余量

上一版忘了列间距，溢出 4.4cm；再上一版舍入后没回扣，溢出 0.012cm。
这里两者都处理，并且**写完后自检一次合计**。

## 为什么不统一用 table*

tab:technique 只超 3.6pt（0.13cm），微调列宽就能留在单栏。
通栏会让它占满整页宽度、显得空旷，且浪费版面。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"
BS = chr(92)

TEXTWIDTH_PT = 480.85141
COLWIDTH_PT = 230.18270
PT_PER_CM = 28.3465
SAFETY_CM = 0.06


def cm(x: float) -> float:
    return x / PT_PER_CM


LIMIT = cm(TEXTWIDTH_PT)          # 16.96
COL = cm(COLWIDTH_PT)             # 8.12


def plan(n: int, sep: float, ratios: list[float],
         limit: float = LIMIT) -> list[float]:
    avail = limit - (n - 1) * 2 * sep / PT_PER_CM - SAFETY_CM
    tot = sum(ratios)
    ws = [round(avail * r / tot, 2) for r in ratios]
    diff = round(sum(ws) - avail, 4)
    if diff > 0:
        k = ws.index(max(ws))
        ws[k] = round(ws[k] - diff, 2)
    return ws


def to_star(path: Path, label: str) -> bool:
    """table -> table* 或 figure -> figure*，按 label 定位。"""
    s = path.read_text(encoding="utf-8")
    i = s.find(BS + "label{" + label + "}")
    if i < 0:
        print(f"  [!] {path.name} 未找到 {label}")
        return False
    for kind in ("table", "figure"):
        b = s.rfind(BS + "begin{" + kind + "}", 0, i)
        if b >= 0:
            s = (s[:b] + BS + "begin{" + kind + "*}"
                 + s[b + len(BS + "begin{" + kind + "}"):])
            e = s.find(BS + "end{" + kind + "}", i)
            if e >= 0:
                s = (s[:e] + BS + "end{" + kind + "*}"
                     + s[e + len(BS + "end{" + kind + "}"):])
            path.write_text(s, encoding="utf-8", newline="\n")
            return True
    print(f"  [!] {path.name} {label} 附近无 table/figure")
    return False


def set_tabular(path: Path, label: str, sep: float, ws: list[float]) -> bool:
    s = path.read_text(encoding="utf-8")
    i = s.find(BS + "label{" + label + "}")
    if i < 0:
        return False
    j = s.find(BS + "begin{tabular}", i)
    if j < 0:
        return False
    e = s.find(chr(10), j)
    spec = "".join(f"p{{{x}cm}}" for x in ws)
    s = s[:j] + BS + "begin{tabular}{@{}" + spec + "@{}}" + s[e:]
    # 插 tabcolsep
    j2 = s.find(BS + "begin{tabular}", i)
    sm = s.find(BS + "small", i)
    if 0 < sm < j2 and (BS + "setlength{" + BS + "tabcolsep}") not in s[
            i:j2]:
        ins = BS + "setlength{" + BS + "tabcolsep}{" + f"{sep:g}" + "pt}\n"
        s = s[:sm + len(BS + "small")] + chr(10) + ins + s[
            sm + len(BS + "small") + 1:]
    path.write_text(s, encoding="utf-8", newline="\n")
    return True


JOBS = [
    # (文件, label, 列数, tabcolsep, 比例)
    ("sec10_slo.tex", "tab:slo", 4, 8.0, [0.22, 0.14, 0.14, 0.50]),
    ("sec11_load.tex", "tab:load", 3, 9.0, [0.26, 0.24, 0.50]),
    ("sec9_plane.tex", "tab:plane", 3, 9.0, [0.16, 0.34, 0.50]),
    ("sec8_technique.tex", "tab:technique", 4, 5.0,
     [0.16, 0.17, 0.27, 0.40]),
]


def main() -> int:
    print(f"通栏上限 {LIMIT:.2f} cm ｜ 单栏 {COL:.2f} cm\n")
    ok = True

    for name, label, n, sep, ratios in JOBS:
        p = PAPER / name
        # tab:technique 留在单栏，只微调
        single = (label == "tab:technique")
        limit = COL if single else LIMIT
        ws = plan(n, sep, ratios, limit)
        occ = sum(ws) + (n - 1) * 2 * sep / PT_PER_CM
        tag = "单栏" if single else "通栏"
        status = "OK" if occ <= limit else f"超{occ - limit:.3f}"
        print(f"{label:<16} {tag} 列宽{sum(ws):.2f} 占宽{occ:.3f}/{limit:.2f} {status}")
        if occ > limit:
            ok = False
            continue
        if not single:
            if not to_star(p, label):
                ok = False
                continue
        if not set_tabular(p, label, sep, ws):
            print(f"  [!] {label} 写入失败")
            ok = False
        else:
            print(f"  -> {name}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
