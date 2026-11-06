"""把「句中」的主张引用挪到句子/段落末尾。

## 为什么

add_cites.py 用「锚点 + 追加」的方式插入引用，而不少锚点本身就停在句子中间，
于是渲染出来是：

    「16B 的模型，一张 24 GB 卡就够」。 [c-active-not-total]实际差 44 倍……

引用把一句话从中间截断，读起来像是排版事故。既有论文（rtx-pro-6000）的做法是
**引用一律挂在句末或段末**，本文应当一致。

## 判据

一个 `[c-xxx]` 后面**紧跟着非空白的中日韩字符**，说明它插在了句子中间。
（合法情形是后跟空格、标点、换行或行尾。）

处理：把它删掉，再插到该句结束标点（。！？；）之后——若本段没有，则放段末。
不动任何正文文字，只动引用的位置。
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE / "PAPER.md"

CITE = re.compile(r"[ \t]*\[(c-[A-Za-z0-9_-]+)\](?=[\u4e00-\u9fff])")
SENT_END = "。！？；"


def main() -> int:
    lines = PAPER.read_text(encoding="utf-8").split("\n")
    moved = 0
    out: list[str] = []

    for ln in lines:
        if not CITE.search(ln):
            out.append(ln)
            continue

        cites = [m.group(1) for m in CITE.finditer(ln)]
        # 先摘掉句中的那些
        stripped = CITE.sub("", ln)
        # 再逐个挂到「其后第一个句末标点之后」；找不到就挂行尾
        for cid in cites:
            tag = f" [{cid}]"
            pos = -1
            for i, ch in enumerate(stripped):
                if ch in SENT_END and "[" not in stripped[:i]:
                    pos = i
                    break
            if pos < 0:
                stripped = stripped.rstrip() + tag
            else:
                # 句末标点之后可能已有一个引用，则排在它后面
                j = pos + 1
                while j < len(stripped) and stripped[j] == "]":
                    j += 1
                if j < len(stripped) and stripped[j:j + 3] == " [c":
                    k = stripped.find("]", j)
                    k = k + 1 if k > 0 else len(stripped)
                    stripped = stripped[:k] + tag + stripped[k:]
                else:
                    stripped = stripped[:pos + 1] + tag + stripped[pos + 1:]
            moved += 1
        out.append(stripped)

    PAPER.write_text("\n".join(out), encoding="utf-8")
    print(f"已把 {moved} 处句中引用移到句末")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
