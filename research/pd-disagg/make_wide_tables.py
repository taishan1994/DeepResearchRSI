"""一步完成：把表 1 / 表 2 改成通栏，并按实测宽度精确分配列宽。

## 为什么要重做

上一版分两步（先 set_tables 再 fit_width），中间被错误的正则写坏了一次，
已用 git checkout 还原。本脚本一次做完，避免中间态。

## 硬数据（xelatex 实测）

  \\textwidth = 480.85141 pt = 16.96 cm   ← table* 可用
  tabcolsep 每侧，n 列之间占 (n-1) × 2 × tabcolsep

## 三个必须守住的点

1. **列宽合计 + 列间距 <= 16.96cm**。上一版只算列宽合计，
   忘了 4 道间隔 (4×2×7pt=1.98cm)，导致溢出 4.4cm。

2. **正则以 label 为锚**。sec0_onepage.tex 有两个 tabular
   （流程图 @{}c@{} + 表格本体），从文件头搜会抓错。

3. **舍入后要回扣**。按比例舍入到两位小数会让合计多出 0.01cm 级别，
   必须从最大列扣掉，并留 0.05cm 安全余量。

## 内容改动

表 2 从 4 列扩到 5 列，新增「适用场景」——通栏后横向有空间，
不加内容会显得空。表 1 保持 5 列，只调宽。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"
BS = chr(92)

TEXTWIDTH_PT = 480.85141
PT_PER_CM = 28.3465
SAFETY_CM = 0.05


def pt2cm(x: float) -> float:
    return x / PT_PER_CM


def plan(n_cols: int, sep: float, ratios: list[float]) -> list[float]:
    avail = pt2cm(TEXTWIDTH_PT - (n_cols - 1) * 2 * sep) - SAFETY_CM
    tot = sum(ratios)
    ws = [round(avail * r / tot, 2) for r in ratios]
    diff = round(sum(ws) - avail, 4)
    if diff > 0:
        k = ws.index(max(ws))
        ws[k] = round(ws[k] - diff, 2)
    return ws


def widen(path: Path, label: str) -> Path | None:
    """把 table -> table*，并把结尾 end{table} 改成 end{table*}。"""
    s = path.read_text(encoding="utf-8")
    i = s.find(BS + "label{" + label + "}")
    if i < 0:
        print(f"  [!] {path.name} 未找到 {label}")
        return None
    b = s.rfind(BS + "begin{table}", 0, i)
    if b < 0:
        print(f"  [!] {path.name} {label} 之前未找到 begin{{table}}")
        return None
    s = s[:b] + BS + "begin{table*}" + s[b + len(BS + "begin{table}"):]
    e = s.find(BS + "end{table}", i)
    if e < 0:
        print(f"  [!] {path.name} 未找到 end{{table}}")
        return None
    s = s[:e] + BS + "end{table*}" + s[e + len(BS + "end{table}"):]
    path.write_text(s, encoding="utf-8", newline="\n")
    return path


def set_spec(path: Path, label: str, sep: float, ws: list[float]) -> bool:
    s = path.read_text(encoding="utf-8")
    i = s.find(BS + "label{" + label + "}")
    if i < 0:
        print(f"  [!] 未找到 {label}")
        return False
    j = s.find(BS + "begin{tabular}", i)
    e = s.find(chr(10), j)
    spec = "".join(f"p{{{x}cm}}" for x in ws)
    s = s[:j] + BS + "begin{tabular}{@{}" + spec + "@{}}" + s[e:]

    # 在 label 之后、tabular 之前插 tabcolsep
    j2 = s.find(BS + "begin{tabular}", i)
    sm = s.find(BS + "small", i)
    if 0 < sm < j2:
        ins = (BS + "setlength{" + BS + "tabcolsep}{" + f"{sep:g}" + "pt}"
               + chr(10))
        s = s[:sm + len(BS + "small")] + chr(10) + ins + s[
            sm + len(BS + "small") + 1:]
    path.write_text(s, encoding="utf-8", newline="\n")
    return True


# ---------------- 表 2 的表体：4 列 -> 5 列 ----------------
T2_OLD = (
    BS + "toprule" + chr(10)
    + "档位 & 典型承载 & 有效带宽 & 相对 " + BS + BS + chr(10)
    + BS + "midrule" + chr(10)
    + "同机 & NVLink & 417" + BS + ",GB/s$^{*}$ & 16.7× " + BS + BS + chr(10)
    + "跨机 & RDMA / IB & 25" + BS + ",GB/s$^{*}$ & 1× " + BS + BS + chr(10)
    + "经存储 & 共享存储 / CXL & $" + BS + "sim$2.5" + BS + ",GB/s & $"
    + BS + "sim$0.1× " + BS + BS + chr(10)
    + BS + "bottomrule" + chr(10)
)
T2_NEW = (
    BS + "toprule" + chr(10)
    + "档位 & 典型承载 & 有效带宽 & 相对 RDMA & 适用场景 " + BS + BS + chr(10)
    + BS + "midrule" + chr(10)
    + "同机 & NVLink & 417" + BS + ",GB/s$^{*}$ & 16.7× "
    + "& 单机内 prefill 与 decode 同置 " + BS + BS + chr(10)
    + "跨机 & RDMA / IB & 25" + BS + ",GB/s$^{*}$ & 1× "
    + "& 常规跨节点分离，本文默认基准 " + BS + BS + chr(10)
    + "经存储 & 共享存储 / CXL & $" + BS + "sim$2.5" + BS + ",GB/s & $"
    + BS + "sim$0.1× & 跨机高带宽通路缺失时的退路 " + BS + BS + chr(10)
    + BS + "bottomrule" + chr(10)
)


def main() -> int:
    limit = pt2cm(TEXTWIDTH_PT)
    ok = True

    # ---- 表 1 ----
    print("表 1 tab:layers")
    p = widen(PAPER / "sec0_onepage.tex", "tab:layers")
    if not p:
        return 1
    ws = plan(5, 7.0, [0.05, 0.20, 0.34, 0.29, 0.12])
    occ = sum(ws) + 4 * 2 * pt2cm(7.0)
    print(f"  列宽 {ws} 合计 {sum(ws):.2f} 占宽 {occ:.3f} / {limit:.2f} cm")
    if occ > limit:
        ok = False
    else:
        set_spec(p, "tab:layers", 7.0, ws)
        print("  已写入")

    # ---- 表 2 ----
    print("表 2 tab:transport")
    p = PAPER / "sec3_transfer.tex"
    s = p.read_text(encoding="utf-8")
    if T2_OLD in s:
        s = s.replace(T2_OLD, T2_NEW, 1)
        p.write_text(s, encoding="utf-8", newline="\n")
        print("  表体已扩为 5 列（加「适用场景」）")
    else:
        print("  [!] 表体锚点未找到")
        ok = False
    p = widen(p, "tab:transport")
    if not p:
        return 1
    ws = plan(5, 9.0, [0.13, 0.24, 0.20, 0.14, 0.29])
    occ = sum(ws) + 4 * 2 * pt2cm(9.0)
    print(f"  列宽 {ws} 合计 {sum(ws):.2f} 占宽 {occ:.3f} / {limit:.2f} cm")
    if occ > limit:
        ok = False
    else:
        set_spec(p, "tab:transport", 9.0, ws)
        print("  已写入")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
