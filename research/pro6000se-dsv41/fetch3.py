"""抓取 GitHub 上的工程文档（raw README / 优化笔记）。

⚠️ 不抓 GitHub 的 HTML 页面：README 是异步渲染，抓到的只有壳。
   这是 pd-disagg 归档里踩过的同一个坑（nvidia-nixl 快照里 RDMA/NVLink 各 0 次）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "packages" / "schemas" / "python"))
from deepresearchrsi.invariants import write_snapshot  # noqa: E402

TARGETS = [
    ("src-rtx6kpro-readme", "doc-rtx6kpro-readme", "rtx6kpro-readme",
     "https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/README.md"),
    ("src-r6k-dspark", "doc-r6k-dspark", "r6k-dspark",
     "https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/"
     "optimization/dspark-upstream-consolidation.md"),
    ("src-deepgemm-236", "doc-deepgemm-236", "deepgemm-236",
     "https://api.github.com/repos/deepseek-ai/DeepGEMM/issues/236/comments?per_page=100"),
    ("src-vllm-recipe", "doc-vllm-recipe", "vllm-recipe",
     "https://raw.githubusercontent.com/vllm-project/vllm/main/docs/recipes/"
     "deepseek_v41flash.md"),
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
                       parser_version="fetch3.py/1", variant="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
