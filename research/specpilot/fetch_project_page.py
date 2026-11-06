"""抓取 SpecPilot 项目主页，落成快照（供 E1 校验引用）。

与论文快照同样处理：HTML -> 纯文本，保留章节结构。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
URL = "https://stargazerx0.github.io/specpilot-project-page/"
UA = {"User-Agent": "DeepResearchRSI/1.0 (research archive; contact: local)"}


def extract_body(html: str) -> str:
    html = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ",
                  html, flags=re.S | re.I)
    m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else html
    body = re.sub(r"<h[1-6]\b[^>]*>", "\n\n## ", body, flags=re.I)
    body = re.sub(r"</(p|li|div|tr)>", "\n", body, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&times;", "x"), ("&mdash;", "-"), ("&ndash;", "-")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def main() -> int:
    r = requests.get(URL, timeout=60, headers=UA)
    r.raise_for_status()
    t = extract_body(r.text)
    out = DOCS / "specpilot-project-page.txt"
    out.write_text(t, encoding="utf-8", newline="\n")
    print(f"-> {out.name}: {len(t):,} 字符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
