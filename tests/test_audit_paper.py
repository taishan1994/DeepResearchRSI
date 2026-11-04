"""audit_paper.py 的 P1–P3 判据测试：确认它们能失败，也能不误报。

⚠️ 为什么专门写这个文件
   P1–P3 在 cuda-kernel-gen 上「从来没跑过」（缺 paper.json），
   而补上之后立刻暴露出两类真问题：
     - 一个凭空出现的数字（1.19x，原文没有，我写进了图注）
     - 一组数字挂错了主张（11/13/22/9/15 挂在只说「8 条可比」的 claim 上）
   两者都说明：**判据必须用反例验证过，否则「通过」毫无意义**。

本文件用临时目录构造最小归档，验证：
   1. 引用闭合：正文引用不存在的 claim -> 报错
   2. 图表落地：paper.json 声明了但文件不存在 -> 报错
   3. 数值回溯：data 里的数在 claim/evidence 里找不到 -> 报错
   4. 派生值：Amdahl 能由公式重算出的值 -> 放行（1.2903 这类）
   5. 派生值：编造的数（公式算不出） -> 仍然报错
   6. CSV 表：表格产物是 .csv 而非 .md -> 不误报
   7. 健康样本 -> 全过

不依赖 pytest：`python tests/test_audit_paper.py`
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_paper.py"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def build_archive(
    root: Path,
    *,
    paper_claims: list[str],
    fig_files: list[str],
    table_kind: str = "md",
    data_rows: list[dict[str, str]] | None = None,
    claim_derivation: str = "",
) -> Path:
    """造一个最小研究归档，返回 paper 目录。"""
    slug = root / "demo"
    paper = slug / "paper"
    (paper / "figures").mkdir(parents=True)
    (paper / "tables").mkdir(parents=True)
    (paper / "data").mkdir(parents=True)

    # claims.csv：一条 measurement + 可选派生
    claims = [{
        "claim_id": "c-main",
        "statement": "该系统实测 3.12x。",
        "claim_type": "measurement",
        "as_of": "2026-11-03",
        "confidence": "high",
        "evidence_ids": "e-001",
        "counter_evidence_ids": "",
        "derivation": claim_derivation,
        "notes": "",
    }]
    write_csv(slug / "claims.csv",
              ["claim_id", "statement", "claim_type", "as_of", "confidence",
               "evidence_ids", "counter_evidence_ids", "derivation", "notes"],
              claims)

    write_csv(slug / "evidence.csv",
              ["evidence_id", "source_id", "locator", "quote", "quote_type",
               "stance", "fetched_at", "note"],
              [{"evidence_id": "e-001", "source_id": "src-1", "locator": "摘要",
                "quote": "it delivers an average speedup of x3.12",
                "quote_type": "quote", "stance": "supports",
                "fetched_at": "2026-11-03T00:00:00+08:00", "note": ""}])

    # 正文：引用 paper_claims 里给出的 id
    body = "## 1　引言\n\n" + "".join(f"有据的陈述 [{c}]。" for c in paper_claims)
    # 表格按「表 N　标题」形式交叉引用（与 cuda-kernel-gen 一致）
    body += "\n\n图表见 figures/fig1.png 与 表 1　表一。\n"
    (paper / "PAPER.md").write_text(body, encoding="utf-8")

    # 图：真实写一个大于 4096 字节的占位图
    for name in fig_files:
        (paper / "figures" / name).write_bytes(b"\x89PNG\r\n" + b"0" * 5000)

    # 表
    if table_kind == "md":
        (paper / "tables" / "tab1.md").write_text(
            "| 系统 | 数值 |\n|---|---|\n| A | 3.12 |\n" + "x" * 80,
            encoding="utf-8")
    else:
        write_csv(paper / "tables" / "tab1_bench.csv",
                  ["基准", "数值", "备注"],
                  [{"基准": "A", "数值": "3.12",
                    "备注": "占位行，用于让文件超过 audit_paper 的 80 字节下限"}])

    # data
    if data_rows:
        write_csv(paper / "data" / "fig1.csv",
                  ["label", "value", "unit", "cite"], data_rows)

    tid = "tab1"
    spec = {
        "paper_id": "paper-demo",
        "slug": "demo",
        "title": "demo",
        "as_of": "2026-11-03",
        "language": "zh",
        "abstract": "",
        "keywords": [],
        "sections": [{"section_id": "sec-1", "number": 1, "title": "引言",
                      "file": "PAPER.md", "cites": paper_claims}],
        "figures": [{"figure_id": "fig1", "kind": "bar", "title": "图一",
                     "caption": "图一", "cites": ["c-main"],
                     "data_file": "data/fig1.csv",
                     "output": fig_files[0]}],
        "tables": [{"table_id": tid, "title": "表一", "caption": "表一",
                    "cites": ["c-main"],
                    "data_file": f"tables/tab1{'.md' if table_kind == 'md' else '_bench.csv'}"}],
    }
    (paper / "paper.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    return paper


def run(paper_dir: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(AUDIT), str(paper_dir)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="auditpaper-"))
    try:
        # 1. 健康样本
        a = build_archive(tmp / "ok", paper_claims=["c-main"],
                          fig_files=["fig1.png"])
        rc, out = run(a)
        check("健康样本通过", rc == 0, out[-300:])

        # 2. 悬空引用
        a = build_archive(tmp / "dangling", paper_claims=["c-main", "c-ghost"],
                          fig_files=["fig1.png"])
        rc, out = run(a)
        check("悬空引用被报出", rc != 0 and "c-ghost" in out, out[-300:])

        # 3. 声明了图但没生成
        a = build_archive(tmp / "nofig", paper_claims=["c-main"],
                          fig_files=["fig1.png"])
        (a / "figures" / "fig1.png").unlink()
        rc, out = run(a)
        check("缺图被报出", rc != 0 and "图未生成" in out, out[-300:])

        # 4. 数值在 claim/evidence 里找不到
        a = build_archive(tmp / "badnum", paper_claims=["c-main"],
                          fig_files=["fig1.png"],
                          data_rows=[{"label": "A", "value": "999.9",
                                      "unit": "x", "cite": "c-main"}])
        rc, out = run(a)
        check("编造数值被报出", rc != 0 and "999.9" in out, out[-300:])

        # 5. 派生值：Amdahl 能重算出来的应当放行
        a = build_archive(
            tmp / "derived_ok", paper_claims=["c-main"], fig_files=["fig1.png"],
            data_rows=[{"label": "p=30%", "value": "1.2903",
                        "unit": "x", "cite": "c-main"}],
            claim_derivation="Amdahl：S = 1/((1-p)+p/k)，k = 4 倍。"
                             "p = 30% 时 S ≈ 1.2903。")
        rc, out = run(a)
        check("Amdahl 派生值放行", rc == 0, out[-400:])

        # 6. 派生值：公式算不出的仍然报错（关键是第 5 条不能变成万能放行）
        a = build_archive(
            tmp / "derived_bad", paper_claims=["c-main"], fig_files=["fig1.png"],
            data_rows=[{"label": "p=30%", "value": "5.5",
                        "unit": "x", "cite": "c-main"}],
            claim_derivation="Amdahl：S = 1/((1-p)+p/k)，k = 4 倍。"
                             "p = 30% 时 S ≈ 1.2903。")
        rc, out = run(a)
        check("公式算不出的值仍报错", rc != 0 and "5.5" in out, out[-400:])

        # 7. 表格产物是 csv 而非 md，不应误报
        a = build_archive(tmp / "csvtab", paper_claims=["c-main"],
                          fig_files=["fig1.png"], table_kind="csv")
        rc, out = run(a)
        check("CSV 表格不误报", rc == 0, out[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    bad = 0
    for name, ok, detail in RESULTS:
        if ok:
            print(f"[PASS] {name}")
        else:
            bad += 1
            print(f"[FAIL] {name}\n{detail}")
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
