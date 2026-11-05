"""重建 body.tex，并把 references 用正确的单反斜杠挂上。

## 反复出错的地方

`\\input{...}` 在 Python 字符串里写 `"\\\\input"` 得到的是**两个**
反斜杠（`0x5c 0x5c`），而 LaTeX 需要**一个**（`0x5c`）。
两个反斜杠在 LaTeX 里是「强制换行」，于是报
`There's no line here to end`。

前几轮我在 PowerShell here-string 里反复被这个问题缠住，
每次都要靠读码点才发现。这次改成用 chr(92) 拼，一次写对。

## 为什么这里必须重建而不是 edit

body.tex 是把 7 个 .tex **内联拼接**生成的（不是 \\input 各节）。
改了 sec5_model.tex 后不重建，body.tex 里还是旧的 §5——
表现为「编译成功但 PDF 内容没变」，是最难发现的一类失效。
本轮就踩了一次：PDF 字符数一字不差，PDAF 出现 0 次。
"""

from __future__ import annotations

from pathlib import Path

BS = chr(92)
HERE = Path(__file__).resolve().parent
LATEX = HERE / "latex"

SECTIONS = [
    "sec1_intro.tex", "sec2_why.tex", "sec3_transfer.tex",
    "sec4_split.tex", "sec5_model.tex",
    # 技巧层放在模型实践之后：它大量回指第 5 节的模型差异
    # （如「逐阶段量化的代价不对称」），放前面会断引用。
    "sec8_technique.tex",
    "sec9_plane.tex",
    "sec6_boundary.tex", "sec7_discuss.tex",
]


def main() -> int:
    blocks: list[str] = []
    for name in SECTIONS:
        p = HERE / name
        if not p.is_file():
            print(f"[!] 缺 {name}")
            continue
        blocks.append(f"%% ===== {name} =====\n"
                      + p.read_text(encoding="utf-8").rstrip() + "\n")
        print(f"  {name:<22} {p.stat().st_size:>6,} 字节")

    body = "\n".join(blocks).rstrip() + "\n"
    # 参考文献节：单反斜杠
    body += "\n" + BS + "input{references.tex}\n"

    out = LATEX / "body.tex"
    out.write_text(body, encoding="utf-8", newline="\n")

    print(f"\nbody.tex {len(body):,} 字符")
    # 校验关键内容确实进来了
    for probe in ("PDAF", "正交", "0.48", "HeteroPanacea"):
        print(f"  含 {probe:<14} {body.count(probe)} 次")
    # 校验 input 行只有一个反斜杠
    for i, line in enumerate(body.split("\n")):
        if "input{references.tex}" in line:
            cps = [hex(ord(c)) for c in line[:6]]
            ok = cps[0] == "0x5c" and cps[1] != "0x5c"
            print(f"  input 行 {i + 1}: {cps} 单反斜杠={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
