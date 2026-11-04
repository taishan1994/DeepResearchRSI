r"""抓取 17 个工程文档的正文，落成快照。

## 为什么工程文档要落快照

与论文一样，E1（引文必须是原文子串）需要原文留档。
但工程文档有两个特殊之处：

1. **会改版。** vLLM 的 `disagg_prefill` 页面在 2026 年改过至少一次
   （实验性 -> 生产可用的措辞变化）。不留快照，半年后无法复现引用。
2. **有大量表格与代码块。** 表格里的默认值（如 KV 传输端口、
   chunk size）恰恰是最可引用的东西，故提取时保留表格结构。

## 提取策略

不追求渲染质量，只求「文字与数字可检索」：
  · 去 script/style/nav/footer
  · <td> 间留分隔符，避免数字粘连（这是上一轮踩过的坑：
    LaTeXML 用非断行空格，`\s*` 才对；此处同理）
  · 折叠空白但保留段落边界

## 快照命名

    documents/<doc_id>.txt
与论文快照（doc-arxiv-xxx.txt）同目录，E1 会一并尝试。
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
DOCS = HERE / "documents"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36"}
SLEEP = 1.5


def extract(html: str) -> str:
    html = re.sub(r"<(script|style|nav|footer|header|svg)\b.*?</\1>", " ",
                  html, flags=re.S | re.I)
    # 表格：单元格间留分隔，否则「2048|4096」会粘成「20484096」
    html = re.sub(r"</t[dh]>", " | ", html, flags=re.I)
    html = re.sub(r"</tr>", "\n", html, flags=re.I)
    # 代码块保留换行
    html = re.sub(r"</(pre|code)>", "\n", html, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", html)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&#8212;", "—"), ("&#8211;", "–")):
        text = text.replace(a, b)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    docs = json.loads((HERE / "candidates_docs.json").read_text(
        encoding="utf-8"))
    print(f"抓取 {len(docs)} 个工程文档\n")

    ok = 0
    for d in docs:
        out = DOCS / f"{d['doc_id']}.txt"
        if out.is_file() and out.stat().st_size > 500:
            print(f"  [skip] {d['doc_id']}")
            ok += 1
            continue
        try:
            r = requests.get(d["url"], timeout=40, headers=UA,
                             allow_redirects=True)
            if r.status_code != 200:
                print(f"  [{r.status_code}] {d['doc_id']}")
                time.sleep(SLEEP)
                continue
            t = extract(r.text)
            if len(t) < 200:
                print(f"  [短] {d['doc_id']} 仅 {len(t)} 字符")
                time.sleep(SLEEP)
                continue
            out.write_text(t, encoding="utf-8", newline="\n")
            print(f"  {d['doc_id']:<20} -> {len(t):>7,} 字符")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [!] {d['doc_id']}: {str(exc)[:50]}")
        time.sleep(SLEEP)

    print(f"\n成功 {ok}/{len(docs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
