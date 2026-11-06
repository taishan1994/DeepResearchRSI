#!/usr/bin/env python
"""抓取 pro6000se-dsv41 的来源正文快照。

约定与 pd-disagg 一致：正文写进 documents/<stem>.txt，元数据写进
documents.csv（content_hash 由 invariants.write_snapshot 计算）。

⚠️ 抓 HTML 后必须抽正文再存。直接存整页会把 nav/footer 一起存进去，
   于是 E1「quote 是原文子串」会在导航栏里意外命中——通过，但毫无意义。
   这里用 bs4 去掉 script/style/nav/header/footer/aside，再按块标签换行。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "packages" / "schemas" / "python"))
from deepresearchrsi.invariants import write_snapshot  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

DROP = ["script", "style", "nav", "header", "footer", "aside", "form",
        "noscript", "svg", "iframe"]
BLOCK = ["p", "div", "section", "article", "li", "tr", "h1", "h2", "h3",
         "h4", "h5", "h6", "pre", "blockquote", "table", "br", "dt", "dd"]


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(DROP):
        tag.decompose()
    for tag in soup.find_all(BLOCK):
        tag.append("\n")
    text = soup.get_text("\n")
    lines = [" ".join(ln.split()) for ln in text.split("\n")]
    out: list[str] = []
    for ln in lines:
        if not ln:
            if out and out[-1] != "":
                out.append("")
            continue
        out.append(ln)
    return "\n".join(out).strip()


def fetch(url: str, *, raw_json: bool = False) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if raw_json or "json" in ctype:
        return resp.text
    if "html" in ctype:
        return html_to_text(resp.text)
    return resp.text


# (source_id, document_id, stem, url, parser_version)
TARGETS = [
    ("src-deepseek-v41-news", "doc-deepseek-v41-news",
     "deepseek-v41-news",
     "https://api-docs.deepseek.com/news/news260910.md", "fetch.py/1"),
    ("src-hf-dsv41", "doc-hf-dsv41", "hf-dsv41",
     "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/raw/main/README.md",
     "fetch.py/1"),
    ("src-nvidia-pro6000se", "doc-nvidia-pro6000se", "nvidia-pro6000se",
     "https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/",
     "fetch.py/1"),
    ("src-qovery-selfhost", "doc-qovery-selfhost", "qovery-selfhost",
     "https://www.qovery.com/blog/self-host-deepseek-v4-1-flash-gpu-setup-own-cloud",
     "fetch.py/1"),
    ("src-tencent-deploy", "doc-tencent-deploy", "tencent-deploy",
     "https://cloud.tencent.cn/developer/article/2740943", "fetch.py/1"),
    ("src-deepseek-api-pricing", "doc-deepseek-api-pricing", "deepseek-api-pricing",
     "https://api-docs.deepseek.com/quick_start/pricing", "fetch.py/1"),
    ("src-vllm-dsv41-recipe", "doc-vllm-dsv41-recipe", "vllm-dsv41-recipe",
     "https://docs.vllm.ai/en/latest/getting_started/examples/deepseek_v41flash.html",
     "fetch.py/1"),
    ("src-sglang-dsv41", "doc-sglang-dsv41", "sglang-dsv41",
     "https://docs.sglang.io/docs/basic_usage/deepseek_v41flash", "fetch.py/1"),
]


def main(argv: list[str]) -> int:
    only = set(argv)
    for sid, did, stem, url, pv in TARGETS:
        if only and sid not in only:
            continue
        dest = ROOT / "documents" / f"{stem}.txt"
        if dest.is_file() and dest.stat().st_size > 2000 and not only:
            print(f"[skip] {stem} 已存在 {dest.stat().st_size} B")
            continue
        try:
            text = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {sid}: {type(exc).__name__}: {exc}")
            continue
        if len(text) < 500:
            print(f"[WARN] {sid}: 正文仅 {len(text)} 字符，可能被墙或需要 JS")
        write_snapshot(ROOT, did, text, source_id=sid,
                       parser_version=pv, variant="")
        print(f"[OK]   {sid}: {len(text):,} 字符 / {len(text.encode()):,} 字节")
        time.sleep(0.6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
