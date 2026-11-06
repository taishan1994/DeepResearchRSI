"""抓取 core 论文的 arXiv HTML 全文，落成快照。

复用 pd-disagg / cuda-kernel-rl 验证过的做法（arXiv HTML -> <article> -> 纯文本）。

## 为什么要全文而不只是摘要

本文的核心主张之一是「反馈信号的信噪比决定改进率」。要证明它，需要每一层的
具体数字：隐藏测试集前后的加速比、每次迭代的成本、收敛在第几轮、
测量重复几次。这些几乎都不在摘要里——摘要是作者最想让读者看到的那句话。

## 失败可接受

部分论文没有 HTML 版（arXiv 只对较新的论文生成 HTML）。抓不到时脚本不报错，
而是记录下来；对应的证据就只用摘要快照支撑，并在 evidence 的 locator 里标
abstract 而不是 fulltext#<section>，让「这条证据有多硬」可被程序区分。
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
UA = {"User-Agent": "DeepResearchRSI/1.0 (research archive; contact: local)"}
SLEEP = 2.5


def extract_body(html: str) -> str:
    html = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ", html,
                  flags=re.S | re.I)
    m = re.search(r"<article\b.*?</article>", html, re.S | re.I)
    if not m:
        m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else html
    body = re.sub(r"</t[dh]>", " | ", body, flags=re.I)
    body = re.sub(r"</tr>", "\n", body, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def fetch(aid: str) -> str | None:
    for suffix in ("v1", "v2", "", "v3"):
        url = f"https://arxiv.org/html/{aid}{suffix}"
        try:
            r = requests.get(url, timeout=45, headers=UA)
            if r.status_code == 200:
                t = extract_body(r.text)
                if t and len(t) > 3000:
                    return t
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {url}: {str(exc)[:50]}")
        time.sleep(SLEEP)
    return None


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    inc = json.loads((HERE / "included_rsi.json").read_text(encoding="utf-8"))
    # 只抓 core：adjacent 的角色是提供分母与判据，摘要足够，
    # 而全文抓取每篇要多花 10-20 秒与一次外部请求。
    core = inc["core"]
    print(f"抓取 {len(core)} 篇 core 论文全文\n")
    ok = 0
    for c in core:
        aid = c["arxiv_id"]
        did = "doc-arxiv-" + aid.replace(".", "-")
        out = DOCS / f"{did}-full.txt"
        if out.is_file() and out.stat().st_size > 3000:
            print(f"  [skip] {aid}")
            ok += 1
            continue
        print(f"  {aid}  {c['title'][:60]}")
        t = fetch(aid)
        if t:
            out.write_text(t, encoding="utf-8", newline="\n")
            print(f"         -> {len(t):,} 字符")
            ok += 1
        else:
            print("         -> 无 HTML 全文")
        time.sleep(SLEEP)
    print(f"\n成功 {ok}/{len(core)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
