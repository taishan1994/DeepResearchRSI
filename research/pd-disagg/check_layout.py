"""检查 PDF 编译日志里的版面问题，尤其 Overfull hbox。

## 为什么需要

Overfull hbox 是「内容比它的盒子宽」，LaTeX 会在那种情况下
**照样生成 PDF**——不报错、不缺字形、页数正常，只是内容压到了
栏间距或页边之外。肉眼在小屏上看不出来。

本次实例：前两张表在单栏里声明 11.10cm 与（因脚注撑开的）15.12cm，
而单栏只有 8.12cm，溢出量最大 125.7pt（4.4cm）。
若不是量了 PDF 里的横线宽度，这个问题会一直留着。

## 判据

  · Overfull hbox 应当为 0
  · Missing character 应当为 0
  · 允许少量 Underfull（断行美学问题，不影响正确性）

## 自测

编译日志里的数字格式固定，用一条已知坏样本验证解析器能抓到。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "paper" / "latex" / "main.log"


def scan(text: str) -> dict[str, list]:
    over = [(float(m.group(1)), int(m.group(2)), int(m.group(3)))
            for m in re.finditer(
                r"Overfull \\hbox \(([\d.]+)pt too wide\)"
                r"(?: in paragraph at lines (\d+)--(\d+))?", text)]
    miss = re.findall(r"Missing character: There is no (\S+)", text)
    under = len(re.findall(r"Underfull \\vbox", text))
    return {"over": over, "miss": miss, "under": under}


def main() -> int:
    if not LOG.is_file():
        print(f"[!] 找不到 {LOG}")
        return 2
    text = LOG.read_text(encoding="utf-8", errors="replace")
    r = scan(text)

    print(f"Overfull hbox : {len(r['over'])} 处")
    for pt, a, b in r["over"][:8]:
        print(f"  {pt:8.2f} pt  body.tex {a}-{b} 行")
    print(f"Missing char  : {len(r['miss'])} 处")
    for c in r["miss"][:6]:
        print(f"  {c}")
    print(f"Underfull vbox: {r['under']} 处（仅影响美观）")

    # 反例自测
    probe = ("Overfull \\hbox (12.34pt too wide) in paragraph at lines 5--9\n"
             "Missing character: There is no 囧 in font x!\n")
    pr = scan(probe)
    caught = len(pr["over"]) == 1 and len(pr["miss"]) == 1
    print(f"\n反例自测：{'通过' if caught else '失败（解析器坏了）'}")

    bad = bool(r["over"]) or bool(r["miss"])
    if bad:
        print("\n[FAIL] 版面有溢出或缺字")
        return 1
    print("\n[OK] 版面无溢出、无缺字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
