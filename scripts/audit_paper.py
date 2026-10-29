"""校验论文与档案的一致性。

检查三件事，每一件都对应过一类真实错误：

A. **引用闭合**：论文里每个 [c-xxx] 都必须在 claims.csv 里存在。
   （历史上出现过 30 次「把 claim_id 当 evidence_id 引用」）
B. **图表落地**：paper.json 里声明的每张图/每张表，其 png/md 必须真的存在且非空。
   （防止「声明了但没生成」）
C. **关键数字可回溯**：论文正文里标注了 cite 的数值，必须能在对应 claim 的
   statement 里找到同一个数字。这一条最弱但也最有价值——它挡住「正文写了一个
   数据里没有的数」。

用法：
    python scripts/audit_paper.py research/rtx-pro-6000/paper
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CITE_RE = re.compile(r"\[(c-[A-Za-z0-9_-]+)\]")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="校验论文与档案的一致性")
    ap.add_argument("paper_dir", help="如 research/rtx-pro-6000/paper")
    args = ap.parse_args(argv)

    paper_dir = Path(args.paper_dir)
    slug_dir = paper_dir.parent
    main_md = paper_dir / "PAPER.md"
    spec_path = paper_dir / "paper.json"

    problems: list[str] = []

    if not main_md.is_file():
        raise SystemExit(f"缺少论文正文：{main_md}")
    if not spec_path.is_file():
        raise SystemExit(f"缺少论文规格：{spec_path}")

    text = main_md.read_text(encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    claims = {r["claim_id"]: r for r in read_csv(slug_dir / "claims.csv")}

    # A. 引用闭合
    cited = set(CITE_RE.findall(text))
    missing = sorted(cited - set(claims))
    for cid in missing:
        problems.append(f"A 引用了不存在的主张：{cid}")

    # A2. paper.json 里声明的 cites 也要存在
    declared = set()
    for item in spec.get("figures", []) + spec.get("tables", []):
        declared.update(item.get("cites", []))
    for s in spec.get("sections", []):
        declared.update(s.get("cites", []))
    for cid in sorted(declared - set(claims)):
        problems.append(f"A paper.json 声明了不存在的主张：{cid}")

    # B. 图表落地
    for fig in spec.get("figures", []):
        out = paper_dir / "figures" / (fig.get("output") or f"{fig['figure_id']}.png")
        if not out.is_file():
            problems.append(f"B 图未生成：{out.name}")
        elif out.stat().st_size < 4096:
            problems.append(f"B 图文件过小（可能是空图）：{out.name}")
    for tab in spec.get("tables", []):
        out = paper_dir / "tables" / f"{tab['table_id']}.md"
        if not out.is_file():
            problems.append(f"B 表未生成：{out.name}")
        elif out.stat().st_size < 80:
            problems.append(f"B 表文件过小：{out.name}")

    # B2. 正文必须真的插入了每一张图表
    for fig in spec.get("figures", []):
        name = fig.get("output") or f"{fig['figure_id']}.png"
        if f"figures/{name}" not in text:
            problems.append(f"B 正文没有插入图：{name}")
    for tab in spec.get("tables", []):
        # 表格可以两种方式进入正文：
        #   (a) 用 <!-- tables/tab-N.md --> 占位，由脚本内联；
        #   (b) 正文里直接写了这张表的内容（首行表头与 tables/tab-N.md 一致）。
        # 只检查路径会漏掉 (b)，故这里加上「表内容是否已内联」的判据。
        by_path = f"tables/{tab['table_id']}.md" in text
        by_label = tab["table_id"].replace("-", " ") in text
        by_content = False
        tab_file = paper_dir / "tables" / f"{tab['table_id']}.md"
        if tab_file.is_file():
            rows = [r for r in tab_file.read_text(encoding="utf-8-sig").split("\n") if r.strip()]
            if rows and rows[0].strip() in text:
                by_content = True
        if not (by_path or by_label or by_content):
            problems.append(f"B 正文可能没有引用表：{tab['table_id']}")

    # C. 关键数字可回溯：对 paper/data/*.csv 里每一行的 (value, cite) 对，
    #    顺着 claim 追到它的 evidence.quote 去核对。
    #
    #    这里的方向很关键：数字通常只在 evidence.quote 里逐字出现，
    #    而 claim.statement 是概括（「优势仅 1.5%-5.9%」），并不含每个明细值。
    #    所以正确的核对顺序是 claim -> evidence_ids -> quote，而不是只看 statement。
    evidence = {r["evidence_id"]: r for r in read_csv(slug_dir / "evidence.csv")}

    def num_variants(v: float) -> set[str]:
        # ⚠️ 必须包含「原样去掉尾零」的形式。
        # `f"{v:g}"` 只保留 6 位有效数字，18354.95 会变成 18355，
        # 于是证据里逐字出现的 18354.95 反而匹配不上——
        # 这不是数据错，是变体集漏了最基本的一种写法。
        out = {f"{v:g}", f"{v!r}"}
        # 去尾零原样：18354.95 / 673.0 -> 673
        raw = f"{v:.6f}".rstrip("0").rstrip(".")
        out.add(raw)
        if v == int(v):
            out.add(str(int(v)))
            out.add(f"{int(v):,}")
        else:
            out.add(f"{v:,.3f}".rstrip("0").rstrip("."))
            out.add(f"{v:,}")
        out.add(f"{abs(v):g}")
        return out

    def find_in(cid: str, raw: str) -> tuple[bool, str]:
        """返回 (是否找到, 在哪一层找到)。"""
        claim = claims[cid]
        try:
            v = float(raw)
        except ValueError:
            return True, "非数值"
        variants = num_variants(v)
        layers = [("statement", claim.get("statement") or ""),
                  ("derivation", claim.get("derivation") or ""),
                  ("notes", claim.get("notes") or "")]
        for eid in (claim.get("evidence_ids") or "").split(";"):
            eid = eid.strip()
            if eid in evidence:
                layers.append((f"evidence:{eid}", evidence[eid].get("quote") or ""))
        for name, body in layers:
            if any(x in body for x in variants):
                return True, name
        return False, ""

    checked = 0
    warnings_only: list[str] = []
    for data_file in sorted((paper_dir / "data").glob("*.csv")):
        for row in read_csv(data_file):
            cid = (row.get("cite") or "").strip()
            raw = (row.get("value") or "").strip()
            if not cid or not raw or cid not in claims:
                continue
            try:
                float(raw)
            except ValueError:
                continue
            checked += 1
            ok, where = find_in(cid, raw)
            if not ok:
                problems.append(
                    f"C 数值 {raw}（{data_file.name}）在主张 {cid} 及其全部证据里都找不到"
                )
            elif where != "statement":
                warnings_only.append(f"{raw} 只在 {where} 里（{cid}）")

    for w in warnings_only[:6]:
        print("  · 提示 " + w)
    if len(warnings_only) > 6:
        print(f"  · 提示 …… 另有 {len(warnings_only) - 6} 条同样情况")

    for p in problems:
        print("  - " + p)

    print()
    print(f"引用主张 {len(cited)} 个 ｜ 图 {len(spec.get('figures', []))} 张 ｜ "
          f"表 {len(spec.get('tables', []))} 张 ｜ 数值回溯 {checked} 条")
    if problems:
        print(f"[FAIL] {len(problems)} 个问题")
        return 1
    print("[OK]   论文与档案一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
