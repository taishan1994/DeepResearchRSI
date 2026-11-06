"""抓取 SpecPilot 论文（arXiv 2611.02501）全文，落成快照。

复用 kernel-agent/fetch_fulltext.py 里验证过的做法：
arXiv HTML -> <article> -> 纯文本，保留到附录末尾。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"


def extract_body(html: str) -> str:
    html = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ",
                  html, flags=re.S | re.I)
    m = re.search(r"<article\b.*?</article>", html, re.S | re.I)
    if not m:
        m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else html

    body = re.sub(r"</t[dh]>", " | ", body, flags=re.I)
    body = re.sub(r"</tr>", "\n", body, flags=re.I)
    body = re.sub(r"<h[1-6]\b[^>]*>", "\n\n## ", body, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", body)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&times;", "x"), ("&nbsp", " ")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def main() -> int:
    raw = DOCS / "_raw.html"
    if not raw.is_file():
        print(f"[!] 缺 {raw}，先下载 https://arxiv.org/html/2611.02501v1")
        return 1
    t = extract_body(raw.read_text(encoding="utf-8", errors="replace"))
    out = DOCS / "doc-arxiv-2611-02501-full.txt"
    out.write_text(t, encoding="utf-8", newline="\n")
    print(f"-> {out.name}: {len(t):,} 字符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
