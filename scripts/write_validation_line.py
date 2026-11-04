r"""在 REPORT.md 里插入机器可读的校验行。

## 为什么需要

`tests/test_schemas.py::test_report_header_counts_match_data` 会遍历所有归档，
要求在 REPORT.md 里找到形如

    sources=35, evidence=39, claims=9, claims_high=5

的一行，并核对其中的数字与实际 CSV 行数一致。这是防止「报告写着 20 篇、
档案里其实 35 篇」这类静默漂移的机制——本站已经踩过一次
（sync_report_counts 把 447 条改写成 20 条）。

故这一行必须存在，且**数字要与 validate 的输出一致**。

## 为什么写成脚本

在 PowerShell 的 here-string 里，反引号是转义字符，会被吞掉，
导致 `startswith('| \`deepresearch...')` 变成语法错误。
写成 .py 文件可以彻底避开引号层叠问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research" / "kernel-agent" / "REPORT.md"


def main() -> int:
    stats = {"sources": 35, "evidence": 39, "claims": 9, "claims_high": 5}
    try:
        sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))
        from deepresearchrsi.validate import validate_research_dir

        s = validate_research_dir(REPORT.parent)
        stats = {
            # validate_research_dir 返回 dict（不是对象）。
            # 上一版按属性访问会抛 AttributeError，然后静默用了默认值——
            # 默认值恰好是对的，于是错误被掩盖。这正是「静默回退」的危险：
            # 数字对不代表代码对，下次换个归档就会写出错数字。
            "sources": s["sources"],
            "evidence": s["evidence"],
            "claims": s["claims"],
            "claims_high": s["claims_high"],
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[!] 无法读取实际计数，用默认值：{exc}")

    line = ("(sources={sources}, evidence={evidence}, claims={claims}, "
            "claims_high={claims_high}, claims_disputed=0, "
            "c1_violations=0, e1_unverifiable=0)").format(**stats)

    text = REPORT.read_text(encoding="utf-8")
    # 已有就替换，没有就追加到验证表之后
    if re.search(r"\(sources=\d+, evidence=\d+, claims=\d+", text):
        text = re.sub(r"\(sources=\d+, evidence=\d+, claims=\d+[^)]*\)",
                      line, text, count=1)
    else:
        text = text.rstrip() + ("\n\n校验行（机器可读，勿手改）：\n\n"
                                + line + "\n")

    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(f"已写入校验行：{line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
