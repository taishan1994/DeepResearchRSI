"""验证 md_to_tex.py 的 inline() 转义与保留是否正确。

## 为什么单独一个测试文件

`inline()` 是本转换器唯一的「文字→LaTeX」入口，段落、列表项、表格单元格
全部经过它。它错一次，整篇 PDF 都错。

本轮它出过两次真问题：
  1. 完全不转义 -> `make_references.py` 的下划线让 XeLaTeX 报 Missing $
  2. 哨兵用了字面 `\\x00`，同函数里的 `\\f`（在 repr 路径中出现）
     被 Python 当成换页符，静默吞掉字母 f

故这里用「输入 -> 期望输出」的固定用例，任何一处退化都会立刻显形。

跑法：python tests_inline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from md_to_tex import inline  # noqa: E402

CASES: list[tuple[str, str, str]] = [
    # (说明, 输入, 期望输出)
    ("下划线转义",
     "由 make_references.py 生成",
     r"由 make\_references.py 生成"),
    ("百分号转义",
     "提升 92% 与 23%",
     r"提升 92\% 与 23\%"),
    ("与号与井号",
     "A & B 与 C#1",
     r"A \& B 与 C\#1"),
    ("反斜杠不被二次转义", "路径 D:\\github",
     r"路径 D:\textbackslash{}github"),
    ("Markdown 链接",
     "见 [CUDA-L1](https://arxiv.org/abs/2507.14111) 一文",
     r"见 \href{https://arxiv.org/abs/2507.14111}{CUDA-L1} 一文"),
    ("自动链接 <url>",
     "<https://arxiv.org/abs/2501.08071>",
     r"\url{https://arxiv.org/abs/2501.08071}"),
    ("行内代码保留下划线",
     "`fetch_rl.py` 与 `analysis.json`",
     r"\texttt{fetch\_rl.py} 与 \texttt{analysis.json}"),
    ("粗体",
     "**没有报告**这个",
     r"\textbf{没有报告}这个"),
    ("内部引用标记被删",
     "结论如此 [c-ablation-exists]",
     "结论如此"),
    ("美元数学原样",
     "期望 $x_1 + y$ 的值",
     r"期望 $x_1 + y$ 的值"),
    ("链接 URL 里的下划线不被转义",
     "[源码](https://x.com/a_b/c)",
     r"\href{https://x.com/a_b/c}{源码}"),
]


def main() -> int:
    bad = 0
    for name, src, want in CASES:
        got = inline(src)
        if got == want:
            print(f"[PASS] {name}")
        else:
            bad += 1
            print(f"[FAIL] {name}")
            print(f"       输入 {src!r}")
            print(f"       期望 {want!r}")
            print(f"       实得 {got!r}")

    print(f"\n{len(CASES) - bad}/{len(CASES)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
