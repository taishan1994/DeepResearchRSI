"""给 REPORT.md 补 §5.3：body.tex 内联拼接导致的静默失效。

## 这条值得单独写进 REPORT

它不是「某个脚本写错了」，而是**构建方式**的缺陷：
body.tex 把 7 个 .tex 内联拼接（不是 \\input 各节），
改完节文件后忘了重建，编译照样成功、PDF 页数不变，
但 PDF 里还是旧内容。

本轮实际踩到：改完 sec5_model.tex（新增 PDAF、窗口、正交等），
编译成功，但 PDF 字符数与改动前一模一样、`PDAF` 出现 0 次。

这类「构建产物成功但内容不是源码」的失效最难发现，
因为没有任何错误信号。故写进 REPORT 并给出检测手段。
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "REPORT.md"

SECTION = """### 5.3 body.tex 是内联拼接，改节文件后不重建会静默失效

`body.tex` 把 7 个 `.tex` **内联拼接**（不是 `\\input` 各节）。
本轮改完 `sec5_model.tex`（新增 PDAF、窗口、正交轴等内容）后直接编译：
成功、页数仍是 7 页，但 PDF 字符数与改动前**一字不差**，
`PDAF` 出现 0 次——PDF 里还是旧的 §5。

这是最难发现的一类失效：**构建产物看起来成功，内容却不是源码**。
没有任何错误信号，只有对比「预期出现的关键词」才能发现。

修法：改用 `paper/build_body.py` 统一重建，并在重建后断言
关键内容确实进来了（脚本会打印 `含 PDAF 8 次` 这样的核对行）。
另外发现它之后，就不能再用手改 body.tex 的方式修 LaTeX——
每次都会被下次重建覆盖。圈码包裹也因此改在源 `.tex` 上做
（见 `paper/wrap_circled.py`）。

"""


def main() -> int:
    s = TARGET.read_text(encoding="utf-8")
    if "5.3 body.tex" in s:
        print("§5.3 已存在")
        return 0

    # 插在 §6 脚本表之前
    anchor = "## 6. 脚本"
    i = s.find(anchor)
    if i < 0:
        # 退一步：插在 5.2 段落末尾
        print("[!] 找不到 §6 锚点")
        return 1

    s = s[:i] + SECTION + s[i:]
    TARGET.write_text(s, encoding="utf-8", newline="\n")
    print(f"已插入 §5.3，REPORT.md {len(s):,} 字符")
    print("  含 5.3:", s.count("5.3 body.tex"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
