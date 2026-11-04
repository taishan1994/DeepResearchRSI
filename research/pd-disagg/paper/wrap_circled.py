"""给各节 .tex 里的圈码包上 \\sym{}。

## 为什么需要

Times New Roman 不含 U+2460–2464（①②③④⑤），编译只报
`Missing character` 而不报错，PDF 上留空白——静默失效。

## 为什么不用 \\CJKfamily

试过 `\\newcommand{\\textcjkc}[1]{{\\CJKfamily{}#1}}`，空参数的
`\\CJKfamily{}` 不会切到中文字体，字体仍是 Times New Roman Bold，
缺字形照旧。模板里已有 `\\sym{}`（Segoe UI Symbol），实测含圈码，
直接用它。

## 为什么在源文件上改而不是在 body.tex 上改

body.tex 每次都从 7 个 .tex 重新生成（见 build_body.py）。
只改 body.tex 会在下次重建时丢失。故改源文件。

## 幂等

已经包过的不再重复包：先用 split 把 `\\sym{...}` 段摘出来，
只处理其余部分。
"""

from __future__ import annotations

import re
from pathlib import Path

BS = chr(92)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
HERE = Path(__file__).resolve().parent
SECTIONS = [
    "sec1_intro.tex", "sec2_why.tex", "sec3_transfer.tex",
    "sec4_split.tex", "sec5_model.tex", "sec6_boundary.tex",
    "sec7_discuss.tex", "references.tex",
]


def main() -> int:
    total = 0
    for name in SECTIONS:
        p = HERE / name
        if not p.is_file():
            continue
        s = p.read_text(encoding="utf-8")
        before = s.count(BS + "sym{")

        # 把已有的 \sym{...} 摘出来保护，避免二次包裹
        guard = BS + "sym{"
        parts = re.split("(" + re.escape(guard) + "[" + CIRCLED + "])", s)
        out: list[str] = []
        n_new = 0
        for part in parts:
            if part.startswith(guard):
                out.append(part)
            else:
                def wrap(m: re.Match) -> str:
                    nonlocal n_new
                    n_new += 1
                    return BS + "sym{" + m.group(0) + "}"
                out.append(re.sub("[" + CIRCLED + "]", wrap, part))
        s2 = "".join(out)

        if n_new:
            p.write_text(s2, encoding="utf-8", newline="\n")
            print(f"  {name:<22} 新包 {n_new} 处（原有 {before}）")
            total += n_new
        else:
            print(f"  {name:<22} 无需改动（已有 {before}）")

    print(f"\n共包裹 {total} 处圈码")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
