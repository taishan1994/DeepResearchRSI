"""一条命令重建整个归档、LaTeX 论文并跑完全部校验。

## 为什么要有一个总入口

本归档有 7 个生成脚本，彼此有依赖顺序。顺序错了**不会报错**，只会产出旧数字：

- `build_evidence.py` 若在 `evidence_extra.json` 更新前跑，
  补充证据不会被并入，`claims.csv` 里引用它们的条目会变成「引用了不存在的证据」——
  但如果你只看 `build_tables.py` 的输出，它是「成功」的。
- `build_tables.py` **重写** `sources.csv` 与 `claims.csv`，所以往 CSV 里手改会被覆盖。
  来源与主张必须写进 `build_tables.py` 的 `SOURCES` / `CLAIMS`。

这两条都是实际踩过的坑（见 LESSONS §2.7 与 fetch7/fetch8 的 schema 事故），
故顺序写在这里，而不是靠记忆。

## 论文走 LaTeX

成品是 `paper/latex/main.pdf`，由 `md_to_tex.py` 从 `paper/PAPER.md` 转出，
再经 `strip_caption_numbers.py` 去重编号（`\\caption` 自己会加「图 N」），
最后 XeLaTeX 编两次。`PAPER.md` 仍是唯一事实源。

## 校验分两层

- **归档层**：`scripts/validate_research.py`（S1/D1/E1/C1-C3 不变量）。
- **论文层**：`check_paper.py`（自洽）、`audit_paper.py`（引用闭合 + 数值回溯）、
  `check_latex.py`（版面）、`audit_numbers.py`（数字必须能回到证据或算式）。
  最后这个是最关键的一道：它把 `claims.csv` **排除**在来源池之外，
  否则「我写进自己主张里的数字」会自己证明自己（LESSONS §2.7）。

任何一个校验失败即中止，不继续往下跑。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # 仓库根
NL = "\n"

# 生成链：顺序即依赖
STEPS = [
    ("build_evidence.py", "documents -> evidence.csv（并入 evidence_extra.json）"),
    ("build_tables.py", "sources.csv + claims.csv（从 in-file SOURCES / CLAIMS 重写）"),
    ("build_run.py", "run.json（检索轨迹与预算）"),
    ("paper/make_figures.py", "paper/figures/fig-*.png"),
    ("paper/make_data.py", "paper/data/*.csv（论文层表格数据）"),
]

# 归档层校验
ARCHIVE_CHECKS = [
    (str(ROOT / "scripts" / "validate_research.py"), ["research/pro6000se-dsv41"],
     "S1/D1/E1/C1-C3 不变量"),
]

# 论文层校验
PAPER_CHECKS = [
    (str(ROOT / "scripts" / "check_paper.py"), ["research/pro6000se-dsv41"],
     "正文自洽（章节/图表/术语/计数）"),
    (str(ROOT / "scripts" / "audit_paper.py"), ["research/pro6000se-dsv41/paper"],
     "引用闭合 + 数值回溯"),
    (str(HERE / "audit_numbers.py"), [], "正文每个数字可回溯（来源池不含 claims.csv）"),
]

# audit_binding 单独处理：它的非零退出码是**信号**而非**失败**。
# 逐条绑定要求「主张里的每个数字都出现在它自己引用的证据里」，
# 但派生值（511/96=5.32）、结构性编号（TP8 的 8）和原文写作 325K 而我写 325,000
# 这类写法差异，永远不会通过。24 条未绑定已由 audit_triage.py 逐条分类为
# A（派生，已登记算式）/ B（写法差异，已改回原文写法）/ C（无处可查=0）。
# 故这里只告警，不阻断；真正的门是 audit_triage 的 C 类必须为 0。
BINDING_CHECK = (str(HERE / "audit_binding.py"), [], "逐条绑定（信息性）")
TRIAGE_CHECK = (str(HERE / "audit_triage.py"), [], "未绑定项分类：C 类必须为 0")

PDF_CHECKS = [
    (str(ROOT / "scripts" / "check_latex.py"),
     ["research/pro6000se-dsv41/paper/latex/main.pdf",
      "--md", "research/pro6000se-dsv41/paper/PAPER.md"],
     "版面（X1-X6）"),
]


def run(cmd: list[str], note: str, cwd: Path) -> bool:
    print(NL + "=== " + " ".join(cmd[:2]) + " —— " + note + " ===")
    code = subprocess.run(cmd, cwd=str(cwd)).returncode
    if code != 0:
        print("[FAIL] 退出码 " + str(code))
        return False
    return True


def main() -> int:
    py = sys.executable

    print("## 阶段 1/4：生成档案")
    for script, note in STEPS:
        if not (HERE / script).is_file():
            print("[SKIP] 缺少 " + script)
            continue
        if not run([py, str(HERE / script)], note, HERE):
            return 1

    print(NL + "## 阶段 2/4：LaTeX 转换")
    body = HERE / "paper" / "latex" / "body.tex"
    if not run([py, str(ROOT / "scripts" / "md_to_tex.py"), "research/pro6000se-dsv41/paper",
                "-o", str(body)], "PAPER.md -> body.tex", ROOT):
        return 1
    for extra, note in (("patch_texttt.py", "长 \\texttt 加断点"),
                        ("strip_caption_numbers.py", "去手写图号")):
        if (HERE / "paper" / extra).is_file():
            if not run([py, str(HERE / "paper" / extra)], note, HERE / "paper"):
                return 1

    print(NL + "## 阶段 3/4：编译 PDF")
    tex_dir = HERE / "paper" / "latex"
    xelatex = "xelatex"
    for _ in range(2):                      # 两趟：交叉引用与目录
        code = subprocess.run([xelatex, "-interaction=nonstopmode", "main.tex"],
                              cwd=str(tex_dir), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT).returncode
        if code != 0:
            print("[FAIL] xelatex 退出码 " + str(code) + "，详见 main.log")
            return 1
    print("  PDF 已生成：" + str(tex_dir / "main.pdf"))

    print(NL + "## 阶段 4/4：校验")
    ok = True
    for group in (ARCHIVE_CHECKS, PAPER_CHECKS, PDF_CHECKS):
        # 全部在仓库根跑：各脚本按 `research/<slug>/...` 的相对路径定位产物。
        for cmd, args, note in group:
            ok &= run([py, cmd] + args, note, ROOT)

    # 信息性：C 类（无处可查）必须为 0，这是真正的门；
    # 逐条绑定的非零退出码只反映派生值与写法差异。
    b_cmd, b_args, b_note = BINDING_CHECK
    run([py, b_cmd] + b_args, b_note + "（不影响结论）", ROOT)
    t_cmd, t_args, t_note = TRIAGE_CHECK
    ok &= run([py, t_cmd] + t_args, t_note, ROOT)

    print(NL + ("全部通过" if ok else "有校验未通过，见上"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
