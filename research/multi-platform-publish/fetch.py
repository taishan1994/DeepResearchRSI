#!/usr/bin/env python
"""抓取 multi-platform-publish 的来源正文快照。

约定与 pro6000se-dsv41 一致：正文写进 documents/<stem>.txt，元数据写进
documents.csv（content_hash 由 invariants.write_snapshot 计算）。

⚠️ 抓 HTML 后必须抽正文再存。直接存整页会把 nav/footer 一起存进去，
   于是 E1「quote 是原文子串」会在导航栏里意外命中——通过，但毫无意义。

⚠️ JSON 接口（GitHub API / 小红书文档索引）必须原样存，不能过 HTML 抽取器：
   它们的「正文」就是 JSON 文本，抽成纯文本反而破坏引文。
"""

from __future__ import annotations

import json
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


def fetch(url: str, *, raw: bool | str = False) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    resp.raise_for_status()
    if raw == "npm":
        return npm_readme(resp.text)
    ctype = resp.headers.get("content-type", "")
    if raw or "json" in ctype:
        return resp.text
    if "html" in ctype:
        return html_to_text(resp.text)
    return resp.text


def npm_readme(body: str) -> str:
    """从 npm registry 的整包文档里解出 readme，并在前面加一段可读来源头。

    ⚠️ 不能直接把整包 JSON 存成快照：
       ① readme 在里面是 JSON 字符串，换行被转义成字面量 `\\n`，
          多行引文就不再是原文子串，E1 会全数失败；
       ② 整包里还有所有历史版本的 dist/tarball 元数据，约 40KB，
          与论证无关却会把快照撑大十倍。
    """
    doc = json.loads(body)
    latest = doc["dist-tags"]["latest"]
    meta = doc["versions"][latest]
    head = (
        f"# {meta['name']} {latest}\n\n"
        f"source: https://registry.npmjs.org/{meta['name']}\n"
        f"description: {meta.get('description', '')}\n\n---\n\n"
    )
    return head + doc.get("readme", "")


# (source_id, document_id, stem, url, parser_version, raw)
#
# ⚠️ raw=True 表示**原样存响应体**，不走 HTML 抽取器。
#    README / JSON 接口的「正文」就是它自己的文本，过一遍抽取器只会破坏引文。
# ⚠️ 这里刻意**不收录**两个抓不到正文的 URL（GitHub repos API、知乎门户）：
#    它们会 403 / 只返回 SPA 外壳。抓不到的东西登记成来源，
#    会让「来源数」看起来比可核验的更多——见 LESSONS 1.6。
TARGETS = [
    # ---------------- 开源工具 ----------------
    ("src-wechatsync-readme", "doc-wechatsync-readme", "wechatsync-readme",
     "https://raw.githubusercontent.com/wechatsync/Wechatsync/v2/README.md",
     "fetch.py/1", True),
    ("src-wechatsync-site", "doc-wechatsync-site", "wechatsync-site",
     "https://www.wechatsync.com/", "fetch.py/1", False),
    ("src-artipub-readme", "doc-artipub-readme", "artipub-readme",
     "https://raw.githubusercontent.com/crawlab-team/artipub/master/README.md",
     "fetch.py/1", True),
    ("src-juejin-mcp", "doc-juejin-mcp", "juejin-mcp",
     "https://raw.githubusercontent.com/iceycn/juejin-release-mcp/main/README.md",
     "fetch.py/1", True),
    ("src-wechatsync-cli", "doc-wechatsync-cli", "wechatsync-cli",
     "https://registry.npmjs.org/@wechatsync/cli", "fetch.py/1", True),
    # ⚠️ multi-publisher 没有独立仓库页可抓，npm registry 的 readme 就是它唯一的公开文档。
    #    故这里不是「抓了包元数据」，而是「抓了它全部文档」。
    #
    #    ⚠️ 但它不能走 raw=True：原始响应是一整个 registry 文档（约 40KB），
    #    readme 作为其中的 JSON 字符串存在，换行被转义成 `\n`。
    #    那样存下来，多行引文就不再是原文子串，E1 会全部失败。
    #    故单独解出 readme 再拼一个可读头，见 fetch_npm_readme()。
    ("src-multi-publisher", "doc-multi-publisher", "multi-publisher",
     "https://registry.npmjs.org/multi-publisher", "fetch.py/1", "npm"),
    # ---------------- 平台官方能力 ----------------
    ("src-wx-draft-add", "doc-wx-draft-add", "wx-draft-add",
     "https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add",
     "fetch.py/1", False),
    ("src-wx-freepublish", "doc-wx-freepublish", "wx-freepublish",
     "https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_submit",
     "fetch.py/1", False),
    # ⚠️ 这是**文档导航接口**，不是文档页。门户是 SPA，文档页抓不到正文；
    #    而导航接口是纯 JSON，可穷举类目——「小红书没有内容发布类目」这条
    #    否定性断言正是靠它成立的（LESSONS 1.7b：否定判断需要穷尽性证据）。
    ("src-xhs-open-nav", "doc-xhs-open-nav", "xhs-open-nav",
     "https://open.xiaohongshu.com/api/doc/list", "fetch.py/1", True),
    ("src-zhihu-api-ref", "doc-zhihu-api-ref", "zhihu-api-ref",
     "https://raw.githubusercontent.com/dawnswwwww/zhihu-cli/main/"
     "skills/zhihu-cli/references/api-reference.md", "fetch.py/1", True),
    # ---------------- 商业 SaaS 自述 ----------------
    ("src-yixiaoer", "doc-yixiaoer", "yixiaoer",
     "https://xueyuan.yixiaoer.cn/article/47005", "fetch.py/1", False),
    ("src-yimei", "doc-yimei", "yimei",
     "https://www.yimeizhushou.com/", "fetch.py/1", False),
    # ⚠️ 这篇只抓到「概述」一节（正文需 JS 渲染，1.2K 字符）。
    # 它的价值恰恰在于与官方类目清单冲突：它说有笔记/评论接口，
    # 而官方 /api/doc/list 只返回电商类目。按 ADR-0003 并列呈现，不作裁决。
    ("src-xhs-tencent", "doc-xhs-tencent", "xhs-tencent",
     "https://cloud.tencent.com.cn/developer/article/2735161", "fetch.py/1", False),
]


def main(argv: list[str]) -> int:
    only = set(argv)
    for sid, did, stem, url, pv, raw in TARGETS:
        if only and sid not in only:
            continue
        dest = ROOT / "documents" / f"{stem}.txt"
        if dest.is_file() and dest.stat().st_size > 2000 and not only:
            print(f"[skip] {stem} 已存在 {dest.stat().st_size} B")
            continue
        try:
            text = fetch(url, raw=raw)
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
