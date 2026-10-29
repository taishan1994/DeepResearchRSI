"""一条命令重建论文的全部产物：图、表、PDF，并做一致性校验。

这一步是「论文层」的编排器。它把三件事串起来：

    paper/data/*.csv + paper.json
        -> render_paper.py      生成 figures/*.png 与 tables/*.md
        -> render_paper_pdf.py  排成 PAPER.pdf
        -> audit_paper.py       校验引用闭合、图表落地、数值可回溯

设计原则：**校验在生成之后、报告之前**。若 audit 失败，脚本以非零码退出，
即使 PDF 已经写出来了——因为一份引用不闭合的 PDF 比没有 PDF 更危险。

用法：
    python scripts/build_paper.py research/rtx-pro-6000/paper
    python scripts/build_paper.py research/rtx-pro-6000/paper --check
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script: str, *args: str) -> int:
    cmd = [sys.executable, str(HERE / script), *args]
    print(f"\n=== {script} {' '.join(args)} ===")
    return subprocess.run(cmd).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="重建论文的全部产物")
    ap.add_argument("paper_dir")
    ap.add_argument("--check", action="store_true", help="只校验，不重写文件")
    args = ap.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    if not (paper_dir / "paper.json").is_file():
        raise SystemExit(f"缺少 paper.json：{paper_dir}")

    steps: list[tuple[str, list[str]]] = []
    if args.check:
        steps.append(("render_paper.py", [str(paper_dir), "--check"]))
        steps.append(("audit_paper.py", [str(paper_dir)]))
    else:
        steps.append(("render_paper.py", [str(paper_dir)]))
        steps.append(("render_paper_pdf.py", [str(paper_dir)]))
        steps.append(("audit_paper.py", [str(paper_dir)]))

    failed = []
    for script, sargs in steps:
        code = run(script, *sargs)
        if code != 0:
            failed.append(script)

    print()
    if failed:
        print(f"[FAIL] 失败步骤：{', '.join(failed)}")
        return 1
    print(f"[OK]   论文产物已重建：{paper_dir}")
    for f in sorted(paper_dir.glob("*")):
        if f.is_file():
            print(f"   {f.name:<16} {f.stat().st_size:>10,} B")
    fig_dir = paper_dir / "figures"
    if fig_dir.is_dir():
        print(f"   figures/         {len(list(fig_dir.glob('*.png')))} 张 PNG")
    tab_dir = paper_dir / "tables"
    if tab_dir.is_dir():
        print(f"   tables/          {len(list(tab_dir.glob('*.md')))} 张表")
    return 0


if __name__ == "__main__":
    sys.exit(main())
