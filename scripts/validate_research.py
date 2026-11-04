#!/usr/bin/env python
"""校验 research/ 下研究留档的自洽性。

用法:
    python scripts/validate_research.py research/rtx-pro-6000
    python scripts/validate_research.py research/*      # 校验全部
    python scripts/validate_research.py                # 默认校验 research/ 下所有子目录
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi.validate import (  # noqa: E402
    ValidationError,
    format_coverage_warnings,
    validate_research_dir,
)


def _targets(argv: list[str]) -> list[Path]:
    if argv:
        out: list[Path] = []
        for arg in argv:
            p = Path(arg)
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve()
            out.extend(sorted(d.resolve() for d in p.parent.glob(p.name) if d.is_dir()))
        return out
    base = ROOT / "research"
    return sorted(d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_"))


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str]) -> int:
    targets = _targets(argv)
    if not targets:
        print("没有找到研究目录。")
        return 0
    failed = 0
    for target in targets:
        try:
            stats = validate_research_dir(target)
        except ValidationError as exc:
            failed += 1
            print(f"[FAIL] {_label(target)}")
            print(exc)
        else:
            detail = ", ".join(f"{k}={v}" for k, v in stats.items())
            print(f"[OK]   {_label(target)}  ({detail})")
            for w in format_coverage_warnings(stats):
                print("       " + w)
    print(f"\n{len(targets) - failed}/{len(targets)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
