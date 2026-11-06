"""补齐硬件页与官方技术报告（PDF 走 pymupdf 抽文本）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "packages" / "schemas" / "python"))
from deepresearchrsi.invariants import write_snapshot  # noqa: E402

BASE = "https://raw.githubusercontent.com/local-inference-lab/rtx6kpro/master/"


def pdf_text(url: str) -> str:
    import requests
    import pymupdf

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    tmp = ROOT / "documents" / "_tmp.pdf"
    tmp.write_bytes(resp.content)
    doc = pymupdf.open(tmp)
    parts = [page.get_text() for page in doc]
    doc.close()
    tmp.unlink(missing_ok=True)
    return "\n\n".join(parts)


TARGETS = [
    ("src-r6k-gpu-configs", "doc-r6k-gpu-configs", "r6k-gpu-configs",
     BASE + "hardware/gpu-configs.md", "text"),
    ("src-deepseek-v41-report", "doc-deepseek-v41-report", "deepseek-v41-report",
     "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/resolve/main/"
     "DeepSeek_V41_Tech_Report.pdf", "pdf"),
]


def main(argv: list[str]) -> int:
    only = set(argv)
    for sid, did, stem, url, kind in TARGETS:
        if only and sid not in only:
            continue
        try:
            text = pdf_text(url) if kind == "pdf" else fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {sid}: {type(exc).__name__}: {exc}")
            continue
        print(f"[OK]   {sid}: {len(text):,} 字符")
        write_snapshot(ROOT, did, text, source_id=sid,
                       parser_version=f"fetch5.py/1+{kind}", variant="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
