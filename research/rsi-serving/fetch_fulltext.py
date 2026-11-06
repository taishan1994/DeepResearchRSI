"""抓 23 篇 core+adjacent 的 arXiv HTML 全文。

为什么必须抓全文：本文的核心是判据（晋级阈值、无损失配率、注入故障），
这些只在正文的 §3 / §4 / 附录里。摘要里只有最终倍数，而倍数恰恰是本文
认为最不可比的东西。

率限制沿用 provider 的 3.2s；失败不清空已有快照。
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
UA = {"User-Agent": "Mozilla/5.0 (compatible; DeepResearchRSI/1.0)"}


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section)>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", html)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&")
              .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    txt = re.sub(r"[ \t]+", " ", txt)
    return re.sub(r"\n{3,}", "\n\n", txt)


def main() -> int:
    ids = sorted({p.name[len("doc-arxiv-"):-len(".txt")]
                  for p in DOCS.glob("doc-arxiv-*.txt")
                  if not p.name.endswith("-full.txt")})
    print(f"{len(ids)} 篇待抓")
    ok = fail = 0
    for tag in ids:
        aid = tag.replace("-", ".", 1)
        out = DOCS / f"doc-arxiv-{tag}-full.txt"
        if out.is_file() and out.stat().st_size > 8000:
            print(f"  = {aid} 已有全文")
            ok += 1
            continue
        url = f"https://arxiv.org/abs/{aid}"
        try:
            r = requests.get(f"https://arxiv.org/html/{aid}", headers=UA, timeout=60)
            if r.status_code != 200 or len(r.text) < 20000:
                print(f"  ! {aid} html {r.status_code} {len(r.text)}")
                fail += 1
            else:
                out.write_text(html_to_text(r.text), encoding="utf-8", newline="\n")
                print(f"  + {aid} {out.stat().st_size} bytes")
                ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {aid} {type(exc).__name__}: {str(exc)[:60]}")
            fail += 1
        time.sleep(3.2)
    print(f"成功 {ok} / 失败 {fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
