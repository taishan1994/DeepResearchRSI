"""抓取 rtx6kpro 仓库里与本主题直接相关的模型页与硬件页。

这个仓库是唯一一组「在 RTX PRO 6000 / SM120 上真跑 DeepSeek-V4.1-Flash」
的第一手记录，故值得逐页取回。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "packages" / "schemas" / "python"))
from deepresearchrsi.invariants import write_snapshot  # noqa: E402

BASE = "https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/"

TARGETS = [
    ("src-r6k-dsv41-model", "doc-r6k-dsv41-model", "r6k-dsv41-model",
     BASE + "models/deepseek-v4.1-flash.md"),
    ("src-r6k-sm120", "doc-r6k-sm120", "r6k-sm120",
     BASE + "hardware/sm120-vs-sm100-architecture.md"),
]


def main(argv: list[str]) -> int:
    only = set(argv)
    for sid, did, stem, url in TARGETS:
        if only and sid not in only:
            continue
        dest = ROOT / "documents" / f"{stem}.txt"
        if dest.is_file() and dest.stat().st_size > 1500 and not only:
            print(f"[skip] {stem} 已存在 {dest.stat().st_size} B")
            continue
        try:
            text = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {sid}: {type(exc).__name__}: {exc}")
            continue
        print(f"[OK]   {sid}: {len(text):,} 字符")
        write_snapshot(ROOT, did, text, source_id=sid,
                       parser_version="fetch4.py/1", variant="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
