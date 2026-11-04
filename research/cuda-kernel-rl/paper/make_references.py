"""把 20 篇来源生成为论文末尾的参考文献章节（Markdown）。

## 为什么用脚本而不是手写

文献表是**最容易出错**的地方：标题抄漏一个词、链接少一位数字、
20 条里漏掉一条，肉眼都看不出来，而读者一点就发现。
故直接从 `sources.csv` 生成，不经过人手。

## 排布

按 `notes` 里的 layer 分三组（core / adjacent / infra），
组内按发表时间排序。载入论文时以「附录 C」形式置于 PDF 最后。

## 链接形式

arXiv 摘要页 URL（`https://arxiv.org/abs/XXXX.XXXXX`）。
不写 PDF 直链——直链会随版本变化，abs 页是稳定入口。
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # research/cuda-kernel-rl
SOURCES = HERE / "sources.csv"
OUT = Path(__file__).resolve().parent / "REFERENCES_SECTION.md"

LAYERS = [
    ("core", "核心 RL 方法（13 篇）"),
    ("adjacent", "邻接工作（奖励成本、环境信号，4 篇）"),
    ("infra", "评测与基础设施（3 篇）"),
]


def main() -> int:
    with SOURCES.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    for r in rows:
        note = r.get("notes") or ""
        r["_layer"] = "core"
        for key, _ in LAYERS:
            if f"layer={key}" in note:
                r["_layer"] = key
                break

    lines = [
        "## 附录 C　参考文献",
        "",
        "下列 20 篇为本文纳入的全部来源。编号仅供本文内部引用，"
        "标题后括号内为 arXiv 编号，链接指向 arXiv 摘要页。",
        "",
    ]

    n = 0
    for key, heading in LAYERS:
        group = [r for r in rows if r["_layer"] == key]
        if not group:
            continue
        # 组内按发表日期**降序**（最新在前）；缺日期的排最后。
        # 两趟排序：先按 source_id 升序定稳定的次级顺序，
        # 再按日期降序。sort 是稳定的，故同一天内仍是编号升序——
        # 若用单趟 key 配 reverse=True，次级键也会被倒过来。
        group.sort(key=lambda r: r["source_id"])
        group.sort(key=lambda r: r.get("published_at") or "0000", reverse=True)
        lines.append(f"**{heading}**")
        lines.append("")
        for r in group:
            n += 1
            title = (r.get("title") or "").strip().rstrip(".")
            url = (r.get("url") or "").strip()
            aid = r["source_id"].replace("src-arxiv-", "").replace("-", ".")
            # arXiv 编号取 2507.11948 形式
            if aid.count(".") >= 2:
                parts = aid.split(".")
                aid = parts[0] + "." + parts[1]
            date = (r.get("published_at") or "")[:7]
            lines.append(f"{n}. {title}（arXiv:{aid}，{date}）  ")
            lines.append(f"   <{url}>")
            lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{OUT.name} 已生成：{n} 条，{len(text)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
