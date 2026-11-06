"""一条命令重建整个归档、LaTeX 论文并跑完全部校验。

## 为什么要有一个总入口

本归档有 5 个生成脚本，彼此有依赖顺序（编码 -> 档案 -> 主张 -> 统计 -> 论文）。
顺序错了不会报错，只会产出**旧数字**：例如先跑 analyze 再跑 codebook，
analysis.json 里还是上一版的分层计数，而所有校验都会通过。

故依赖顺序写在这里，而不是靠记忆。

## 论文走 LaTeX

论文的成品是 latex/main.pdf（双栏 NeurIPS 风格），由 md_to_tex.py 从
PAPER.md 转出 body.tex 再编译。PAPER.md 仍是唯一事实源，LaTeX 是它的
一种渲染——与 check_paper.py 校验的是同一份正文，不会各自漂移。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

STEPS = [
    ("codebook.py", "61 篇 -> corpus_labels.csv"),
    ("build_archive.py", "sources / evidence / documents"),
    ("build_claims.py", "claims.csv"),
    ("analyze.py", "analysis.json"),
]


def main() -> int:
    for script, note in STEPS:
        print(NL + "=== " + script + " ===")
        code = subprocess.run([sys.executable, str(HERE / script)]).returncode
        if code != 0:
            print("[FAIL] " + script + " 退出码 " + str(code) +
                  "，后续步骤不再执行——在失败的上游产物上继续跑，"
                  "只会得到一份自洽的错数据")
            return code
        print("      -> " + note)

    print(NL + "=== 论文层 ===")
    paper = HERE / "paper"
    # 1) 图表重建（figures/*.png 与 tables/*.md 由 CSV 生成）
    # 2) 参考文献表（只列正文真正引用的来源）
    # 3) LaTeX 编译两遍 + 版式校验
    # 4) 三道论文校验（引用闭合、内部自洽、数值可回溯）
    chain = [
        [sys.executable, str(ROOT / "scripts" / "render_paper.py"), str(paper)],
        [sys.executable, str(paper / "make_references.py")],
        [sys.executable, str(ROOT / "scripts" / "build_paper_latex.py"), str(paper)],
        [sys.executable, str(ROOT / "scripts" / "validate_research.py"), str(HERE)],
        [sys.executable, str(ROOT / "scripts" / "audit_paper.py"), str(paper)],
        [sys.executable, str(ROOT / "scripts" / "check_paper.py"), str(paper)],
    ]
    failed = []
    for cmd in chain:
        print(NL + "=== " + Path(cmd[1]).name + " ===")
        if subprocess.run(cmd).returncode != 0:
            failed.append(Path(cmd[1]).name)

    print()
    if failed:
        print("[FAIL] 失败步骤：" + ", ".join(failed))
        return 1
    print("[OK]   " + HERE.name + " 全部产物已重建")
    return 0


NL = chr(10)

if __name__ == "__main__":
    raise SystemExit(main())
