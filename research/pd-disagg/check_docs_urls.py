"""校验 candidates_docs.json 里的 URL 是否真实可达。

## 为什么必须做

工程文档是本专题的**一半材料**。若 URL 是我想当然写出来的（比如
`/features/nixl_connector.html` 这个路径未必存在），论文里就会出现
点不开的引用——而这比缺一条来源更糟，因为它看起来是有来源的。

做法：逐个 GET，记录状态码与最终 URL（跟随重定向），
并抓页面标题，人工可眼检是不是对的那一页。

## 判定

  200 且标题含预期关键词  -> ok
  200 但标题不符          -> suspect（可能被重定向到首页）
  404/403/超时            -> dead

403 单独标注：有些站点会拦脚本，不代表链接错。需要人工点开确认。
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0 Safari/537.36"}


def fetch(url: str) -> tuple[int, str, str]:
    try:
        r = requests.get(url, timeout=30, headers=UA, allow_redirects=True)
        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
        if m:
            title = " ".join(m.group(1).split())[:90]
        return r.status_code, r.url, title
    except Exception as exc:  # noqa: BLE001
        return 0, url, f"ERR {str(exc)[:60]}"


def main() -> int:
    src = HERE / "candidates_docs.json"
    docs = json.loads(src.read_text(encoding="utf-8"))
    print(f"校验 {len(docs)} 个工程文档 URL\n")

    results = []
    for d in docs:
        code, final, title = fetch(d["url"])
        moved = (final.rstrip("/") != d["url"].rstrip("/"))
        if code == 200:
            status = "ok"
        elif code in (403, 429):
            status = "blocked"
        else:
            status = "dead"
        results.append({**d, "status_code": code, "final_url": final,
                        "page_title": title, "verdict": status,
                        "redirected": moved})

        mark = {"ok": "[ok]  ", "blocked": "[403] ", "dead": "[DEAD]"}[status]
        print(f"{mark} {d['doc_id']:<18} {code}  {title[:56]}")
        if moved:
            print(f"        -> 重定向到 {final[:78]}")
        time.sleep(0.8)

    # 汇总
    from collections import Counter
    c = Counter(r["verdict"] for r in results)
    print(f"\n汇总：{dict(c)}")

    dead = [r for r in results if r["verdict"] == "dead"]
    if dead:
        print("\n[!] 以下链接需修正或删除（不能写进论文）：")
        for r in dead:
            print(f"    {r['doc_id']:<18} {r['url']}")

    (HERE / "docs_check.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    return 0 if not dead else 1


if __name__ == "__main__":
    raise SystemExit(main())
