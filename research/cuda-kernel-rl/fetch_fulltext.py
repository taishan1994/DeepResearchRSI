"""抓取 arXiv 论文全文（HTML），落成文档快照。

## 为什么需要它——本轮的核心动因

上一轮的综述声明了一个限制：「全部分析基于 arXiv 摘要，未读全文」。
由此留下三件说不清的事：

  1. 各工作是否真做了消融？摘要只报最好的数。
  2. 7 篇「未点名算法」到底用了什么？
  3. **中间奖励的净效果**——有没有「有中间奖励 vs 无」的对照？

第 3 条是上一轮论文里最重要的空白：我批评各工作只报最好的数，
却也无法证明他们没做消融。**这是把自己的无知写成了别人的缺陷。**

arXiv 自 2023 年起为多数论文提供 HTML 版（`arxiv.org/html/<id>vN`），
内容含完整正文、表格、附录。故这个限制本不该存在。

## 与摘要快照的区别

`documents/` 原本只放摘要（来自 papers.json）。全文快照需分开命名，
否则 D1 的 content_hash 会因「同一 document_id 两种来源」而误判改版：

    documents/doc-arxiv-XXXX-XXXXX.txt        摘要（parser=arxiv-abstract-v1）
    documents/doc-arxiv-XXXX-XXXXX-full.txt   全文（parser=arxiv-html-v1）

E1 校验时优先用全文——它包含摘要，判据更严。

## 只取正文，不取导航

arXiv HTML 有大量导航与元数据。用 BeautifulSoup 取 `<article>` 或
`main` 内的文本，去掉 reference 之外的结构噪音。
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
UA = {"User-Agent": "DeepResearchRSI/1.0 (research archive; contact: local)"}
SLEEP = 2.5


def fetch_html(arxiv_id: str) -> str | None:
    """取 HTML 全文。返回正文纯文本，失败返回 None。"""
    for suffix in ("v1", "v2", "v3", ""):
        url = f"https://arxiv.org/html/{arxiv_id}{suffix}"
        try:
            r = requests.get(url, timeout=45, headers=UA)
            if r.status_code != 200:
                continue
            text = extract_body(r.text)
            if text and len(text) > 3000:
                return text
        except Exception as exc:  # noqa: BLE001
            print(f"    [!] {url}: {str(exc)[:60]}")
        time.sleep(SLEEP)
    return None


def extract_body(html: str) -> str:
    """从 arXiv HTML 里抽正文纯文本。

    优先 `<article>`（LaTeXML 的正文容器），退回 `<main>`，再退回全文。
    删除 script/style/nav/footer，以及参考文献之后的部分——
    references 对论证无用于此处的检查，且体积很大。
    """
    # 去掉明显非正文的块
    html = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ",
                  html, flags=re.S | re.I)

    m = re.search(r"<article\b.*?</article>", html, re.S | re.I)
    if not m:
        m = re.search(r"<main\b.*?</main>", html, re.S | re.I)
    body = m.group(0) if m else html

    # 参考文献之后截断
    cut = re.search(r'<section[^>]*id="(?:bib|references|BIB)"', body, re.I)
    if cut:
        body = body[:cut.start()]

    # 表格里的单元格之间保留分隔，否则数字会粘成一串
    body = re.sub(r"</t[dh]>", " | ", body, flags=re.I)
    body = re.sub(r"</tr>", "\n", body, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", body)
    # HTML 实体
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def main() -> int:
    import csv
    DOCS.mkdir(exist_ok=True)

    # 只抓「core」层：infra/adjacent 的全文对本文论证不是必需
    targets: list[tuple[str, str]] = []
    with (HERE / "sources.csv").open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if "layer=core" not in (r.get("notes") or ""):
                continue
            m = re.search(r"src-arxiv-(\d{4})-(\d{4,5})", r["source_id"])
            if m:
                targets.append((f"{m.group(1)}.{m.group(2)}", r["title"]))

    print(f"抓取 {len(targets)} 篇 core 论文全文\n")
    ok = 0
    for aid, title in targets:
        did = "doc-arxiv-" + aid.replace(".", "-")
        out = DOCS / f"{did}-full.txt"
        if out.is_file() and out.stat().st_size > 3000:
            print(f"  [skip] {aid} 已存在")
            ok += 1
            continue
        print(f"  {aid}  {title[:52]}")
        text = fetch_html(aid)
        if text:
            out.write_text(text, encoding="utf-8", newline="\n")
            print(f"         -> {len(text):,} 字符")
            ok += 1
        else:
            print("         -> 无法取得全文")
        time.sleep(SLEEP)

    print(f"\n成功 {ok}/{len(targets)}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    raise SystemExit(main())
