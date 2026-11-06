"""抓取 SGLang cookbook / Artificial Analysis 配置页 / vLLM-ascend 教程。

单独一个脚本而不是塞进 fetch.py：这三者的 URL 需要先探测，
探测结果不稳定（docs.sglang.io 的 cookbook 是 mintlify 站点，
直接 GET 会返回 404 的 examples 路径）。
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
    ("src-sglang-cookbook", "doc-sglang-cookbook", "sglang-cookbook",
     "https://docs.sglang.io/cookbook/autoregressive/DeepSeek/DeepSeek-V4_1"),
    ("src-aa-configs", "doc-aa-configs", "aa-configs",
     "https://artificialanalysis.ai/hardware-inference-stack/configs"),
    ("src-vllm-ascend-dsv41", "doc-vllm-ascend-dsv41", "vllm-ascend-dsv41",
     "https://github.com/vllm-project/vllm-ascend/raw/main/docs/source/"
     "tutorials/models/DeepSeek-V4.1-Flash.md"),
    ("src-deepseek-v41-report", "doc-deepseek-v41-report", "deepseek-v41-report",
     "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/raw/main/"
     "DeepSeek_V41_Tech_Report.pdf"),
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
        if text.startswith("%PDF"):
            print(f"[WARN] {sid}: 返回的是 PDF 二进制，需另走 pymupdf")
            (ROOT / "documents" / f"{stem}.pdf").write_bytes(
                __import__("requests").get(url, timeout=60).content)
            continue
        print(f"[OK]   {sid}: {len(text):,} 字符")
        write_snapshot(ROOT, did, text, source_id=sid,
                       parser_version="fetch2.py/1", variant="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
