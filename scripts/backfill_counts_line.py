#!/usr/bin/env python
"""给缺「校验计数行」的归档补一行（历史遗留）。

背景：tests/test_schemas.py::test_report_header_counts_match_data 要求每个
research/<slug>/REPORT.md 都有一行形如
    sources=N, evidence=N, claims=N, claims_high=N
而 5 份历史归档没有。scripts/sync_report_counts.py 只能**替换**已有行，
不能**新增**，于是它对这些归档报「找不到校验计数行」并跳过——
测试红着，工具却说自己 OK。这是工具与测试之间的缺口，不是数据问题。

本脚本只做一件事：在 REPORT.md 末尾追加一节「校验结果」，数值由
validate_research_dir() 现算，不手写。默认 dry-run。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi.validate import validate_research_dir  # noqa: E402

ORDER = [
    "sources", "evidence", "claims", "claims_high", "claims_disputed",
    "trace_events", "c3_violations", "subquestions",
    "r2_violations", "c1_violations",
]

HEADING = "\n---\n\n## 校验结果\n\n"
TEMPLATE = (
    "`sources={line}`\n\n"
    "由 `python scripts/validate_research.py research/{slug}` 现算；"
    "E1 可校验 {e1} 条、无法校验 {unver} 条。\n"
)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    for slug in args.slugs:
        target = ROOT / "research" / slug
        report = target / "REPORT.md"
        if not report.is_file():
            print(f"[MISS] {slug}: 无 REPORT.md")
            continue
        text = report.read_text(encoding="utf-8")
        if "sources=" in text and "claims_high=" in text:
            print(f"[SKIP] {slug}: 已有计数行")
            continue
        stats = validate_research_dir(target)
        line = ", ".join(f"{k}={stats[k]}" for k in ORDER if k in stats)
        block = HEADING + TEMPLATE.format(
            line=line, slug=slug,
            e1=stats.get("e1_checked", 0), unver=stats.get("e1_unverifiable", 0),
        )
        if not args.apply:
            print(f"[DRY ] {slug}: 将追加 {line}")
            continue
        report.write_text(text.rstrip("\n") + "\n" + block, encoding="utf-8")
        print(f"[WROTE] {slug}: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
