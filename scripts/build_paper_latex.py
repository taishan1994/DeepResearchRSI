"""一条命令构建 LaTeX 版论文，并跑版式校验。

用法：
    python scripts/build_paper_latex.py research/rtx-pro-6000/paper
    python scripts/build_paper_latex.py research/rtx-pro-6000/paper --check

它做四件事：
  1. md_to_tex.py      PAPER.md -> latex/body.tex
  2. xelatex 跑两遍     （第一遍写 .aux，第二遍解析交叉引用）
  3. check_latex.py    版式校验（溢界、填充率、完整性、缺字）
  4. 报告页数与体积

⚠️ 为什么必须跑两遍：LaTeX 的目录、图表编号、交叉引用都靠 .aux 中转，
   只跑一遍时第二遍的引用会显示为「??」。这不是可选项。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# TinyTeX 装在仓库外，故显式找 xelatex，不依赖 PATH。
TEX_CANDIDATES = [
    Path(r'D:\github\_tex\TinyTeX\bin\windows'),
    Path(r'C:\texlive\2026\bin\windows'),
    Path(r'C:\texlive\2025\bin\windows'),
]


def find_xelatex() -> str | None:
    for d in TEX_CANDIDATES:
        exe = d / 'xelatex.exe'
        if exe.is_file():
            return str(d)
    w = shutil.which('xelatex')
    return str(Path(w).parent) if w else None


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> int:
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    # LaTeX 把错误混在 stdout 里，故两路都看
    out = (r.stdout or '') + (r.stderr or '')
    fatal = [ln for ln in out.split('\n') if ln.startswith('!')]
    if fatal:
        for ln in fatal[:6]:
            print('   ', ln[:110])
    return 1 if fatal else r.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='构建 LaTeX 版论文')
    ap.add_argument('paper_dir')
    ap.add_argument('--check', action='store_true', help='只校验，不重新编译')
    args = ap.parse_args(argv)

    paper = Path(args.paper_dir).resolve()
    latex = paper / 'latex'
    main_tex = latex / 'main.tex'
    pdf = latex / 'main.pdf'
    if not main_tex.is_file():
        raise SystemExit(f'缺少 {main_tex}')

    texbin = find_xelatex()
    if not texbin:
        raise SystemExit('找不到 xelatex（检查 TEX_CANDIDATES 或 PATH）')

    env = dict(os.environ)
    env['PATH'] = texbin + os.pathsep + env.get('PATH', '')

    repo = Path(__file__).resolve().parent.parent
    failed: list[str] = []

    if not args.check:
        # 1. 转换
        code = run([sys.executable, str(repo / 'scripts' / 'md_to_tex.py'), str(paper)],
                   cwd=repo, env=env)
        if code != 0:
            failed.append('md_to_tex.py')

        # 2. 编译两遍
        for i in (1, 2):
            print(f'=== xelatex 第 {i} 遍 ===')
            code = run([str(Path(texbin) / 'xelatex.exe'), '-interaction=nonstopmode',
                        'main.tex'], cwd=latex, env=env)
            if code != 0:
                failed.append(f'xelatex#{i}')
                break

    # 3. 版式校验
    if pdf.is_file():
        print('=== check_latex.py ===')
        code = run([sys.executable, str(repo / 'scripts' / 'check_latex.py'),
                    str(pdf), '--md', str(paper / 'PAPER.md')], cwd=repo, env=env)
        if code != 0:
            failed.append('check_latex.py')

    print()
    if failed:
        print(f'[FAIL] 失败步骤：{", ".join(failed)}')
        return 1
    import pymupdf
    d = pymupdf.open(pdf)
    print(f'[OK]   LaTeX 版已重建：{pdf}')
    print(f'   {d.page_count} 页  {pdf.stat().st_size:,} 字节')
    return 0


if __name__ == '__main__':
    sys.exit(main())
