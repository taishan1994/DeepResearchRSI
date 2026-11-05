"""精确设置两张通栏表的列宽（修正版）。

## 上一版的两个错误

1. **舍入后仍超宽**：plan() 先算可用宽度再按比例舍入到两位小数，
   四舍五入会让合计超出 0.012cm。修法：先舍入，再从最大的那一列
   扣掉差值，保证合计严格不大于可用宽度；同时留 0.05cm 余量
   抵消 TeX 的断行容差。

2. **正则抓错了 tabular**：sec0_onepage.tex 里有三个 tabular
   （流程图用的 @{}c@{}、以及表格本体），我的正则从文件头搜，
   抓到了流程图的那个，于是把 p{...} 写进了流程图里。
   修法：以 label 为锚，只在其后的第一个 tabular 上做替换。

## 硬数据（xelatex 实测，非估算）

  \\textwidth = 480.85141 pt = 16.96 cm
  tabcolsep 每侧，故 n 列之间占 (n-1) × 2 × tabcolsep
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "paper"

TEXTWIDTH_PT = 480.85141
PT_PER_CM = 28.3465
SAFETY_CM = 0.05


def pt2cm(x: float) -> float:
    return x / PT_PER_CM


def plan(n_cols: int, tabcolsep: float, ratios: list[float]) -> list[float]:
    avail_pt = TEXTWIDTH_PT - (n_cols - 1) * 2 * tabcolsep
    avail_cm = pt2cm(avail_pt) - SAFETY_CM
    total = sum(ratios)
    ws = [round(avail_cm * r / total, 2) for r in ratios]
    # 把舍入差从最大列扣掉，保证合计 <= avail_cm
    diff = round(sum(ws) - avail_cm, 4)
    if diff > 0:
        k = ws.index(max(ws))
        ws[k] = round(ws[k] - diff, 2)
    return ws


def set_spec(path: Path, label: str, sep: float, ws: list[float]) -> bool:
    """把以 label 为锚的那张表的 tabcolsep 与列说明替换掉。"""
    s = path.read_text(encoding="utf-8")
    anchor = chr(92) + "label{" + label + "}"
    i = s.find(anchor)
    if i < 0:
        print(f"  [!] {path.name} 未找到 {label}")
        return False
    j = s.find(chr(92) + "begin{tabular}", i)
    if j < 0:
        print(f"  [!] {path.name} 在 {label} 之后未找到 tabular")
        return False
    e = s.find(chr(10), j)
    spec_new = "".join(f"p{{{x}cm}}" for x in ws)
    line_new = (chr(92) + "begin{tabular}{@{}" + spec_new + "@{}}")
    s = s[:j] + line_new + s[e:]

    # tabcolsep：若已有则替换，没有则插在 \small 之后
    k = s.find(chr(92) + "setlength{" + chr(92) + "tabcolsep}", i)
    if k > 0 and k < j + 200:
        m = re.match(r"\\setlength\{\\tabcolsep\}\{([\d.]+)pt\}",
                     s[k:k + 40])
        if m:
            s = (s[:k] + chr(92) + "setlength{" + chr(92) + "tabcolsep}{"
                 + f"{sep:g}" + "pt}" + s[k + m.end():])
    else:
        sm = s.find(chr(92) + "small", i)
        if 0 < sm < j:
            s = (s[:sm] + chr(92) + "small" + chr(10) + chr(92)
                 + "setlength{" + chr(92) + "tabcolsep}{" + f"{sep:g}"
                 + "pt}" + s[sm + len(chr(92) + "small"):])

    path.write_text(s, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    limit = pt2cm(TEXTWIDTH_PT)
    ok = True

    for name, label, sep, ratios in [
        ("sec0_onepage.tex", "tab:layers", 7.0, [0.05, 0.20, 0.34, 0.29, 0.12]),
        ("sec3_transfer.tex", "tab:transport", 9.0,
         [0.13, 0.24, 0.20, 0.14, 0.29]),
    ]:
        ws = plan(5, sep, ratios)
        occ = sum(ws) + 4 * 2 * pt2cm(sep)
        status = "OK" if occ <= limit else f"超 {occ - limit:.3f}cm"
        print(f"{label:<16} {ws}  合计{sum(ws):.2f}  占宽{occ:.3f}  {status}")
        if occ > limit:
            ok = False
            continue
        set_spec(PAPER / name, label, sep, ws)
        print(f"  已写入 {name}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
