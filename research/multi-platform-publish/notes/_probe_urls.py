#!/usr/bin/env python
"""探测候选来源是否可抓、正文有多少字。

只做判断，不写正式快照——正式抓取走 fetch.py，这样「探测失败」的 URL
不会被登记成来源（避免把骨架页当证据）。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

DROP = ["script", "style", "nav", "header", "footer", "aside", "form",
        "noscript", "svg", "iframe"]


def to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(DROP):
        tag.decompose()
    return soup.get_text("\n")


URLS = [
    # ---- 工具侧 ----
    ("wechatsync-gh", "https://raw.githubusercontent.com/wechatsync/Wechatsync/main/README.md"),
    ("wechatsync-site", "https://www.wechatsync.com/"),
    ("artipub-gh", "https://raw.githubusercontent.com/crawlab-team/artipub/main/README.md"),
    ("npm-multi-publisher", "https://registry.npmjs.org/multi-publisher"),
    ("npm-wechatsync-cli", "https://registry.npmjs.org/@wechatsync/cli"),
    # ---- 平台能力侧 ----
    ("wx-draft-add", "https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html"),
    ("wx-draft-add2", "https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add"),
    ("wx-freepublish", "https://developers.weixin.qq.com/doc/offiaccount/Publish/Publish.html"),
    ("xhs-open", "https://open.xiaohongshu.com/"),
    ("zhihu-api", "https://www.zhihu.com/"),
    ("juejin-api", "https://open.juejin.cn/"),
    ("csdn-api", "https://blog.csdn.net/"),
]


def main() -> int:
    out = []
    for name, url in URLS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            text = to_text(r.text) if "html" in r.headers.get("content-type", "") else r.text
            n = len(text)
            flag = "OK  " if r.ok and n > 500 else "THIN" if r.ok else "FAIL"
            out.append(f"[{flag}] {name:22s} {r.status_code} {n:>8,} {url}")
        except Exception as exc:  # noqa: BLE001
            out.append(f"[ERR ] {name:22s} {'---':>3} {'':>8} {url}  ({type(exc).__name__})")
        time.sleep(0.4)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
