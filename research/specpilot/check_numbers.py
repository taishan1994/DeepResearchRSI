"""核对：正文里出现的数字能不能在 analysis.json / repo_audit.json 里找到。

## 为什么要这个脚本

docs/LESSONS.md 2.1 的教训是「数字由脚本算」，但**光有脚本还不够**：
正文可能抄错、可能抄的是旧值。本脚本把这一步也机器化：

  * 从 REPORT.md 抽出一组**关键断言**（数对/短语），
  * 到 analysis.json + repo_audit.json + 各 CSV 里查，
  * 找不到或对不上就报错。

它不试图理解整篇文章（那做不到），只钉住那些**一旦漂移就会误导读者**的数字：
计数、去重后的行数、缺失条目数、争议数。

用法：python check_numbers.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_rows(name: str) -> list[dict]:
    p = HERE / name
    if not p.is_file():
        return []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    report = (HERE / "REPORT.md").read_text(encoding="utf-8")
    ana = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    repo = json.loads((HERE / "repo_audit.json").read_text(encoding="utf-8"))
    dang = json.loads((HERE / "dangling_audit.json").read_text(encoding="utf-8"))
    claims = load_rows("claims.csv")
    evidence = load_rows("evidence.csv")
    sources = load_rows("sources.csv")

    c = ana["counts"]
    checks: list[tuple[str, object, object]] = [
        # (说明, 正文里应出现的值, 数据里的值)
        ("来源数", c["sources"], len(sources)),
        ("证据数", c["evidence"], len(evidence)),
        ("主张数", c["claims"], len(claims)),
        ("高置信主张", c["claims_high"],
         sum(1 for x in claims if x["confidence"] == "high")),
        ("争议主张", c["claims_disputed"],
         sum(1 for x in claims if x["confidence"] == "disputed")),
        ("快照数", c["documents"], len(load_rows("documents.csv"))),
        ("证据分层 paper", ana["evidence_by_layer"].get("paper"),
         sum(1 for e in evidence if e["source_id"] == "src-arxiv-2611-02501")),
        # 仓库侧
        ("文件总数", 3098, repo["files_total"]),
        ("setting py 去重", 145, repo["setting_py_distinct"]),
        ("setting py 原始", 316, repo["setting_py_files"]),
        ("去重行数", 145644, repo["setting_py_distinct_lines"]),
        ("开关数", 272, repo["env_switches_distinct"]),
        # 悬空引用
        ("被引用路径", 22, dang["refs_total"]),
        ("缺失路径", 10, len(dang["missing"])),
    ]

    bad: list[str] = []
    for label, in_report, from_data in checks:
        if in_report != from_data:
            bad.append(f"{label}: 正文/常量为 {in_report}，数据为 {from_data}")

    # 正文里必须**字面出现**的关键数字（防止正文与 JSON 各说一套）
    must_appear = [
        f"证据数：{c['evidence']}",
        f"主张数：{c['claims']}",
        f"e1_checked={c['evidence']}",
        "e1_unverifiable=0",
        f"22 条路径",
        f"其中 {len(dang['missing'])} 条不存在",
    ]
    for s in must_appear:
        if s not in report:
            bad.append(f"正文缺少关键数字：{s!r}")

    # 机器可读行必须与数据一致（test_report_header_counts_match_data 也查这个，
    # 但那个测试在别的归档失败时会提前 assert，本脚本保证本归档自己是对的）
    m = re.search(r"sources=(\d+), evidence=(\d+), claims=(\d+), claims_high=(\d+)",
                  report)
    if not m:
        bad.append("缺少机器可读校验行")
    else:
        got = tuple(int(x) for x in m.groups())
        want = (c["sources"], c["evidence"], c["claims"], c["claims_high"])
        if got != want:
            bad.append(f"校验行 {got} != 数据 {want}")

    if bad:
        print(f"[FAIL] {len(bad)} 处不一致：")
        for b in bad:
            print("   -", b)
        return 1
    print(f"[OK] {len(checks)} 项计数 + {len(must_appear)} 处正文数字 + 校验行，全部一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
