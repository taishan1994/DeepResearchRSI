"""核对 PDF 里的参考文献与 sources.csv 是否完全一致。

## 为什么需要

参考文献是**唯一一处把 20 篇来源全部列出**的地方，也是读者真正会点的东西。
它由 make_references.py 从 sources.csv 生成，但生成之后还要经过
Markdown -> LaTeX -> PDF 三道转换。任何一道丢了条目或改了链接，
肉眼都看不出来（20 条里少一条，翻页时不会有人数）。

故直接从 PDF 提取链接，与 sources.csv 的 URL 集合做双向比对：
  - sources.csv 有、PDF 没有 -> 漏了
  - PDF 有、sources.csv 没有 -> 多出来（可能是编造）

跑法：python check_references.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PDF = HERE / "latex" / "main.pdf"
SOURCES = ROOT / "sources.csv"


def main() -> int:
    with SOURCES.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    want = {(r.get("url") or "").strip().rstrip("/") for r in rows}
    want.discard("")

    doc = pymupdf.open(PDF)
    # 1) 取 PDF 里的可点链接
    got_links: set[str] = set()
    for pno in range(doc.page_count):
        for ln in doc[pno].get_links():
            uri = (ln.get("uri") or "").strip().rstrip("/")
            if uri.startswith("http"):
                got_links.add(uri)

    # 2) 取正文里显示的 URL 文本（防止链接注解存在但文字没渲染）
    #
    # ⚠️ 不能先把全部换行删掉再匹配：`\url` 排出来是独立一行，
    #    删换行会让它和下一行条目编号粘成
    #    "https://arxiv.org/abs/2610.23950" + "2. LEAP..." 这样一整串，
    #    于是每个 URL 都「匹配不上」（实测 20/20 全报缺失，而链接其实都在）。
    #    正确做法是逐行匹配，再对折行做一次宽松的拼合。
    lines = []
    for i in range(doc.page_count):
        lines.extend(doc[i].get_text().split("\n"))
    text = "\n".join(lines)

    # URL 提取：先按行找，再拼合被断行拆开的片段。
    # ⚠️ 不能用「行首是 http」判断——URL 常常和前面的中文括号同一行
    #    （实测 `2025-07）https://arxiv.org/abs/2507.05687`），
    #    那样会漏掉 7 条。故用正则在该行内定位。
    shown: set[str] = set()
    for k, ln in enumerate(lines):
        for m in re.finditer(r"https?://[\w./%~:\-]*", ln):
            url = m.group(0)
            j = k + 1
            # xurl 断行时，下一行是纯 URL 片段，拼回去。
            # ⚠️ 必须排除「纯数字」行——它是页码。否则最后一条 URL 会把
            #    页脚的 7 粘上去，变成 abs/2502.105177（实测由此虚报 1 条缺失）。
            while j < len(lines):
                nxt = lines[j].strip()
                if (nxt and re.fullmatch(r"[\w./%~:\-]+", nxt)
                        and not re.fullmatch(r"\d{1,3}", nxt)):
                    url += nxt
                    j += 1
                else:
                    break
            shown.add(url.rstrip("/,;.)"))

    print(f"sources.csv：{len(want)} 个 URL")
    print(f"PDF 链接注解：{len(got_links)} 个")
    print(f"PDF 可见文本：{len(shown)} 个\n")

    problems: list[str] = []

    missing_links = want - got_links
    if missing_links:
        problems.append(f"{len(missing_links)} 个 URL 在 sources.csv 里但没有可点链接："
                        + ", ".join(sorted(missing_links)[:5]))

    extra = got_links - want
    if extra:
        problems.append(f"{len(extra)} 个链接不在 sources.csv 里（可能编造）："
                        + ", ".join(sorted(extra)[:5]))

    # 可见文本只要求「每条都出现」，不要求完全相等——
    # 长 URL 会在排版时被断行，跨行拼接后可能与原串不完全一致。
    absent = [u for u in want if u not in shown]
    if absent:
        problems.append(f"{len(absent)} 个 URL 未在 PDF 文本中出现："
                        + ", ".join(sorted(absent)[:5]))

    # 条目数：参考文献区应有 20 个编号
    ref_zone = text[text.find("参考文献"):] if "参考文献" in text else text
    nums = set(int(x) for x in re.findall(r"(?<!\d)(\d{1,2})\.", ref_zone)
               if 1 <= int(x) <= 40)
    print(f"参考文献区出现的编号：{len([n for n in nums if n <= 20])} 个")

    if problems:
        for p in problems:
            print(f"[FAIL] {p}")
        return 1
    print("[OK]   参考文献与 sources.csv 完全一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
