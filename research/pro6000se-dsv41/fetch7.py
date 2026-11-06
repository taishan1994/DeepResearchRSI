"""补抓 Workstation Edition 规格页，为「1792 GB/s」找一手出处。

为什么必须补：
    主张 c-se-vs-ws-bandwidth 说「SE 1597 低于 WS 1792」。但 1792 这个数
    在任何已抓快照里都不存在——它只出现在我记忆里的另一份归档。
    照抄过来就等于「正文写了一个档案里没有的数」，正是 audit_paper C 项要挡的事。
    宁可少一条推算，也不要一条无出处的数字。
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
TZ = timezone(timedelta(hours=8))

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

TARGETS = [
    ("doc-nvidia-pro6000ws", "src-nvidia-pro6000ws",
     "https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/"),
    ("doc-nvidia-pro6000ws2", "src-nvidia-pro6000ws",
     "https://www.nvidia.com/en-us/design-visualization/desktop-graphics/rtx-pro-6000/"),
]


def clean(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [" ".join(ln.split()) for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if not ln:
            continue
        if out and out[-1] == ln:
            continue
        out.append(ln)
    return "\n".join(out)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    rows: list[dict[str, str]] = []
    meta_path = HERE / "documents.csv"
    if meta_path.is_file():
        with meta_path.open(encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    have = {r["document_id"] for r in rows}

    for did, sid, url in TARGETS:
        if did in have:
            print(f"  已有 {did}，跳过")
            continue
        try:
            r = requests.get(url, headers=UA, timeout=45)
            r.raise_for_status()
        except Exception as exc:                      # noqa: BLE001
            print(f"  [!] {did} 抓取失败：{type(exc).__name__}: {exc}")
            continue
        text = clean(r.text)
        if "GB/s" not in text and "GB/s" not in text.replace(" ", ""):
            print(f"  [!] {did} 正文里没有 GB/s，可能被拦或需 JS：{len(text)} 字符")
            continue
        snap = DOCS / f"{did}.txt"
        snap.write_text(text, encoding="utf-8")
        rows.append({
            "document_id": did,
            "source_id": sid,
            "url": url,
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            "parser_version": "fetch7.py/1",
            "byte_size": str(len(text.encode("utf-8"))),
            "snapshot": f"documents/{snap.name}",
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
        })
        print(f"  [+] {did}  {len(text):,} 字符")
        for m in re.finditer(r"[\d,]+ GB/s", text):
            print(f"        {m.group(0)}")

    if rows:
        with meta_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
