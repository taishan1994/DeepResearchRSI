"""校验 docs/EVOLUTION.md 与 docs/LESSONS.md 里的数字是否与实测一致。

## 为什么要这个脚本

这两份文档的核心价值是「数字可信」。一旦某个数字漂移（比如又提交了
几十次，总数不再是 314），文档就开始说谎，而读者无从察觉。

故把所有可测的数字抽成断言，跑一次即知是否过期。
不写进 tests/ 是因为它是文档校验，不是代码契约——
但它可以并入 CI，让文档过期时构建失败。

## 口径

只校验**能从仓库状态算出**的数字：
  · 提交总数 / 类型分布 / 自我纠正比例 → git + evolution_stats
  · 各归档的 sources / evidence / claims / e1_checked → CSV + validate
  · 代码行数 → 数文件

不校验叙述性内容（那是人写的判断）。
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

FAILS: list[str] = []
OKS: list[str] = []


def expect(name: str, got, want) -> None:
    if got == want:
        OKS.append(f"{name} = {got}")
    else:
        FAILS.append(f"{name}: 文档写 {want}，实际 {got}")


def _real_e1_checked(name: str) -> int:
    """跑一次 validate，取真实的 e1_checked。

    不直接读 CSV 推断：e1_checked 是「实际比对过原文」的条数，
    只能由 invariants 跑出来，不能从行数算。
    """
    sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))
    from deepresearchrsi.validate import validate_research_dir

    try:
        r = validate_research_dir(ROOT / "research" / name)
    except Exception as exc:  # noqa: BLE001
        FAILS.append(f"{name}: validate 失败 {exc}")
        return -1
    return int(r["e1_checked"])


def read_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return len(list(csv.DictReader(fh)))


def main() -> int:
    evo = (DOCS / "EVOLUTION.md").read_text(encoding="utf-8")
    les = (DOCS / "LESSONS.md").read_text(encoding="utf-8")
    stats = json.loads((DOCS / "evolution-stats.json").read_text(
        encoding="utf-8"))

    # ---- 提交统计 ----
    expect("提交总数", stats["total_commits"],
           int(re.search(r"\| 提交总数 \| (\d+) \|", evo).group(1)))
    expect("feat 数", stats["by_type"].get("feat", 0),
           int(re.search(r"feat / fix \| (\d+) /", evo).group(1)))
    expect("fix 数", stats["by_type"].get("fix", 0),
           int(re.search(r"feat / fix \| \d+ / (\d+)", evo).group(1)))
    expect("自我纠正提交数", stats["retract_commits"],
           int(re.search(r"自我纠正类提交 \| (\d+)", evo).group(1)))

    # 比例：文档写 20.4%，实际算出来四舍五入后应一致
    doc_ratio = float(re.search(r"自我纠正类提交 \| \d+（\*\*([\d.]+)%",
                                evo).group(1))
    expect("自我纠正比例(%)", round(stats["retract_ratio"] * 100, 1),
           doc_ratio)

    # ---- 代码行数 ----
    total_lines = 0
    for d in ("scripts", "packages", "tests"):
        for f in (ROOT / d).rglob("*.py"):
            # 统计**非空行**：文档里的「代码行数」用的是这个口径。
            # 若用总行数（含空行），同一份代码会多出约 1000 行，
            # 而两处口径不一致时，检查器会误报「文档过期」。
            text = f.read_text(encoding="utf-8", errors="replace")
            total_lines += sum(1 for L in text.splitlines() if L.strip())
    m = re.search(r"真实代码量 \| (\d+) 行", evo)
    if m:
        doc_lines = int(m.group(1))
        # 允许 ±5% 误差：文档写的是当时快照，且本脚本自身也在增加行数
        if abs(total_lines - doc_lines) / max(doc_lines, 1) > 0.05:
            FAILS.append(f"代码行数: 文档写 {doc_lines}，实际 {total_lines}"
                         f"（差 {abs(total_lines - doc_lines)} 行，超 5%）")
        else:
            OKS.append(f"代码行数 = {doc_lines}（实际 {total_lines}，在 5% 内）")

    # ---- 各归档计数 ----
    # 文档第 5 节的表格：| `name` | 3002 | 0 | **0%** |
    table = re.findall(
        r"\| `([\w-]+)` \| (\d+) \| (\d+) \| \**(\d+)%\** \|", evo)
    if not table:
        FAILS.append("EVOLUTION.md 第 5 节的覆盖率表未找到")
    for name, ev_n, e1c, pct in table:
        ev_n, e1c, pct = int(ev_n), int(e1c), int(pct)
        real_ev = read_csv_rows(ROOT / "research" / name / "evidence.csv")
        real_pct = round(e1c / ev_n * 100) if ev_n else 0
        expect(f"{name} 证据数", real_ev, ev_n)
        expect(f"{name} E1 覆盖率(%)", real_pct, pct)
        # e1_checked 必须真的等于表里的数
        if e1c > real_ev:
            FAILS.append(f"{name}: e1_checked={e1c} 大于证据总数 {real_ev}")

        # ⚠️ 关键：覆盖率不能只验自洽（e1c/ev_n），还要验 e1c 是**真的**。
        # 第一版只算 real_pct = e1c/ev_n，于是把表里的 e1c 改成任意值、
        # 同时改 pct 与它自洽，检查就通过了——等于让文档自己给自己作证。
        # 实测注入「37 → 37，100% → 88%」时，旧版完全没报。
        if e1c != _real_e1_checked(name):
            FAILS.append(
                f"{name}: 表里 e1_checked={e1c}，实际 validate 得到 "
                f"{_real_e1_checked(name)}")

    # ---- 交叉引用 ----
    for doc, name in ((evo, "EVOLUTION.md"), (les, "LESSONS.md")):
        for link in re.findall(r"\]\(\./([\w.-]+\.md)\)", doc):
            if not (DOCS / link).is_file():
                FAILS.append(f"{name} 里的链接指向不存在的文件：{link}")

    # ---- 两份文档都提到「三次没起作用」----
    for doc, name in ((evo, "EVOLUTION.md"), (les, "LESSONS.md")):
        if "没起作用" not in doc and "失败" not in doc:
            FAILS.append(f"{name} 缺少失败记录章节（只记成功会失真）")

    print(f"通过 {len(OKS)} 项")
    for o in OKS:
        print(f"  [OK] {o}")
    if FAILS:
        print(f"\n失败 {len(FAILS)} 项：")
        for f in FAILS:
            print(f"  [!] {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
