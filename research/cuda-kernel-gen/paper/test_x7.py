"""验证 check_latex 的 X7 能真正抓到「图注自我重复编号」。

⚠️ 一个检查项如果从不失败，它就没有价值 —— 无法区分
   「确实没问题」和「判据写错了永远通过」。
   故这里用最小 LaTeX 文档造一个已知有病的样本，
   确认 X7 报 FAIL；再造一个健康样本，确认不误报。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# TeX 工具链的位置因机器而异，不能写死。
# 优先级：显式环境变量 > PATH 里已有 xelatex > 常见安装位置。
# 都找不到时 TEXDIR 保持不存在的路径，下面的 `if TEXDIR.exists()` 会跳过，
# 此时依赖系统 PATH 里的 xelatex；若也没有，测试会以「找不到 xelatex」失败，
# 而不是静默通过。
def _find_texdir() -> Path:
    env = os.environ.get("TINYTEX_BIN") or os.environ.get("TEXDIR")
    if env:
        return Path(env)
    found = shutil.which("xelatex")
    if found:
        return Path(found).parent
    return Path("")  # 不存在，让 exists() 为假


TEXDIR = _find_texdir()

BAD = r"""\documentclass[twocolumn]{article}
\usepackage{ctex}
\usepackage{graphicx}
\begin{document}
\section{A}
正文占位。这是一段足够长的中文，用来把页面填起来，避免别的检查项干扰。
\begin{figure*}[t]
\centering
% 不插入真图，用文字模拟「图内标题」与「caption」都带编号的情形
\caption{图 1：图 1}
\end{figure*}
\end{document}
"""

GOOD = r"""\documentclass[twocolumn]{article}
\usepackage{ctex}
\usepackage{graphicx}
\begin{document}
\section{A}
正文占位。这是一段足够长的中文，用来把页面填起来，避免别的检查项干扰。
\begin{figure*}[t]
\centering
\caption{本文纳入的论文按月份分布。红色区域为新增时段。}
\end{figure*}
\end{document}
"""


def build(tex: str, d: Path) -> Path | None:
    (d / 'main.tex').write_text(tex, encoding='utf-8')
    env = None
    if TEXDIR.exists():
        import os
        env = dict(os.environ)
        env['PATH'] = str(TEXDIR) + ';' + env.get('PATH', '')
    for _ in range(2):
        r = subprocess.run(['xelatex', '-interaction=nonstopmode', 'main.tex'],
                           cwd=d, capture_output=True, text=True, env=env)
    pdf = d / 'main.pdf'
    return pdf if pdf.exists() else None


def main() -> int:
    import os
    # 自己把 TinyTeX 加进 PATH，不依赖调用者的 shell 环境。
    # 否则换一个没设 PATH 的终端就报 FileNotFoundError，
    # 看起来像测试坏了，实际是环境没配。
    if TEXDIR.exists() and str(TEXDIR) not in os.environ.get('PATH', ''):
        os.environ['PATH'] = str(TEXDIR) + ';' + os.environ.get('PATH', '')
    if shutil.which('xelatex') is None:
        print('(skip: 没有 xelatex)')
        return 0

    results: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        # 有病样本
        d1 = Path(td) / 'bad'
        d1.mkdir()
        pdf1 = build(BAD, d1)
        if pdf1 is None:
            print('(skip: 编译失败)')
            return 0
        r1 = subprocess.run(
            ['python', str(HERE / 'check_latex.py'), str(pdf1)],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        out1 = (r1.stdout or '') + (r1.stderr or '')
        if 'X7' in out1 and 'FAIL' in out1:
            results.append('[PASS] 有病样本被 X7 抓到')
        else:
            results.append(f'[FAIL] 有病样本没被 X7 抓到\n{out1[-400:]}')

        # 健康样本
        d2 = Path(td) / 'good'
        d2.mkdir()
        pdf2 = build(GOOD, d2)
        r2 = subprocess.run(
            ['python', str(HERE / 'check_latex.py'), str(pdf2)],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        out2 = (r2.stdout or '') + (r2.stderr or '')
        if 'X7 图注无自我重复编号' in out2:
            results.append('[PASS] 健康样本未被误报')
        else:
            results.append(f'[FAIL] 健康样本被误报\n{out2[-400:]}')

    for r in results:
        print(r)
    return 0 if all(x.startswith('[PASS]') for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
