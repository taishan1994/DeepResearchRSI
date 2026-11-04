"""用 GitHub raw README 替换渲染后的仓库页快照。

## 为什么需要

`nvidia-nixl.txt` 里 RDMA / NVLink / GPUDirect 各出现 **0 次**，
而 NIXL 的 README 一定有这些词。原因是 GitHub 的仓库首页正文是
异步渲染的，`requests.get` 拿到的是 HTML 壳 + 一段内嵌 JSON，
既没有完整 README，也没有可引用的段落。

这是**渠道问题**，不是判据问题。判据再宽也救不了不存在的文本。

## 做法

对 GitHub 类来源（nvidia-nixl、mooncake-repo、lmcache、deepseek-3fs、
deepseek-profile），改抓：

    https://raw.githubusercontent.com/<owner>/<repo>/HEAD/README.md

HEAD 而非 main/master：不同仓库默认分支不同，HEAD 由服务端解析。

## 代价与记录

raw README 没有网页里的补充说明（侧栏、release note 链接），
故**保留原 HTML 快照**为 `*.html.txt`，raw 版为正式快照。
若论文引用到网页独有内容，仍可回溯。
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

# doc_id -> (owner, repo)
GH = {
    "nvidia-nixl": ("ai-dynamo", "nixl"),
    "mooncake-repo": ("kvcache-ai", "Mooncake"),
    "lmcache": ("LMCache", "LMCache"),
    "deepseek-3fs": ("deepseek-ai", "3FS"),
    "deepseek-profile": ("deepseek-ai", "open-infra-index"),
}


def strip_md(md: str) -> str:
    """Markdown -> 纯文本，保留代码块与表格。"""
    # 代码围栏内容保留
    md = re.sub(r"^```[a-zA-Z]*\n", "\n", md, flags=re.M)
    md = re.sub(r"^```\s*$", "\n", md, flags=re.M)
    # 图片/徽章去掉
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    # 链接保留文字
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)
    # 表格分隔线
    md = re.sub(r"^\|[\s:|-]+\|$", "", md, flags=re.M)
    md = re.sub(r"^#{1,6}\s*", "", md, flags=re.M)
    md = re.sub(r"[*_`]{1,3}", "", md)
    md = re.sub(r"[ \t\u00a0]+", " ", md)
    md = re.sub(r"\n\s*\n+", "\n\n", md)
    return md.strip()


def main() -> int:
    print(f"替换 {len(GH)} 个 GitHub 仓库快照为 raw README\n")
    ok = 0
    for doc_id, (owner, repo) in GH.items():
        old = DOCS / f"{doc_id}.txt"
        bare = DOCS / f"{doc_id}.html.txt"
        if old.is_file() and not bare.is_file():
            old.rename(bare)          # 保留原 HTML 抓取

        got = None
        for name in ("README.md", "readme.md", "README.rst", "README"):
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{name}"
            try:
                r = requests.get(url, timeout=30, headers=UA)
                if r.status_code == 200 and len(r.text) > 300:
                    got = (name, r.text)
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.0)

        if not got:
            print(f"  [!] {doc_id}: 未取到 README（保留原 HTML 快照）")
            if bare.is_file() and not old.is_file():
                bare.rename(old)
            continue

        name, md = got
        text = strip_md(md)
        old.write_text(text, encoding="utf-8", newline="\n")
        print(f"  {doc_id:<18} {name} -> {len(text):>7,} 字符"
              f"（原 HTML {bare.stat().st_size if bare.is_file() else 0:,} 字节）")
        ok += 1
        time.sleep(1.2)

    print(f"\n成功 {ok}/{len(GH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
