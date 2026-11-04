"""抓取 26 篇 core 论文的全文，落成快照。

复用 cuda-kernel-rl 里验证过的做法（arXiv HTML -> <article> -> 纯文本），
但这里有一个本专题特有的需求：**要能读到智能体循环的描述**。

故截断点不是「参考文献之前」，而是保留到附录末尾——因为智能体的
工具清单、失败分类、轮次预算常常写在附录里（实测 TritonRL 的消融在
正文表 3，而 Dr. Kernel 的对照组设计写在图注）。

## 快照命名

    documents/doc-arxiv-XXXX-XXXXX.txt        摘要（来自候选 JSON）
    documents/doc-arxiv-XXXX-XXXXX-full.txt   全文

与 cuda-kernel-rl 一致，E1 会同时尝试两者。
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
    html = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ",
                  html, flags=re.S | re.I)
    m = re.search(r"<article\b.*?</article>", html, re.S | re.I)
    if not m:
        m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else html

    # 表格单元格之间留分隔，否则数字粘连
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
    inc = json.loads((HERE / "included_agent.json").read_text(encoding="utf-8"))
    core = inc["core"] + inc["adjacent"]

    print(f"抓取 {len(core)} 篇（core+adjacent）全文\n")
    ok = 0
    for c in core:
        aid = c["arxiv_id"]
        did = "doc-arxiv-" + aid.replace(".", "-")
        out = DOCS / f"{did}-full.txt"
        # 摘要快照：若已由 build 阶段写入则跳过
        if out.is_file() and out.stat().st_size > 3000:
            print(f"  [skip] {aid}")
            ok += 1
            continue
        print(f"  {aid}  {c['title'][:56]}")
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
