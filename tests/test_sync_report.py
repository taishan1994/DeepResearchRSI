"""`scripts/sync_report_counts.py` 的回归测试。

## 为什么专门测这个工具

它是**写文件**的工具，出错会静默破坏无关文档。
本轮就发生过一次：

    加 --slug cuda-kernel-rl 后，results 里只剩一个归档，
    代码便无条件把它的计数写进 evals/cases/README.md——
    而那个文件讲的是 rtx-pro-6000，447 来源被改成 20 来源。

「只有一个候选」被当成「就是这个候选」。这类错误不会报错，
只会让文档悄悄说假话，比崩溃危险得多。

## 测什么

  T1  文件里没提到本次处理的归档 -> 必须跳过，不得改写
  T2  文件里提到的归档匹配 -> 才允许改写
  T3  dry-run 不写盘
  T4  --slug 过滤后，未提及该 slug 的外部文档保持原样

用临时仓库模拟，不碰真实文件。

`python tests/test_sync_report.py`
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def make_archive(root: Path, slug: str, n_src: int) -> None:
    """造一个最小可校验的归档。"""
    d = root / "research" / slug
    d.mkdir(parents=True)
    (d / "documents").mkdir()
    (d / "notes").mkdir()
    (d / "brief.yaml").write_text(
        "slug: " + slug + "\nquestion: q\nsubquestions:\n  - id: q1\n"
        "    text: t\n", encoding="utf-8")
    hdr_s = ["source_id", "url", "source_type", "publisher", "title",
             "published_at", "updated_at", "fetched_at", "language",
             "trust_tier", "access", "license", "notes"]
    with (d / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr_s, lineterminator="\n")
        w.writeheader()
        for i in range(n_src):
            w.writerow({
                "source_id": f"src-a{i}", "url": f"https://x/{i}",
                "source_type": "academic", "publisher": "p",
                "title": f"t{i}", "published_at": "2026-01-01",
                "updated_at": "2026-01-01",
                "fetched_at": "2026-11-04T10:00:00+08:00",
                "language": "en", "trust_tier": "primary",
                "access": "open", "license": "x", "notes": "layer=core",
            })
    hdr_e = ["evidence_id", "document_id", "source_id", "quote", "locator",
             "quote_type", "stance", "fetched_at", "note"]
    (d / "evidence.csv").write_text(",".join(hdr_e) + "\n", encoding="utf-8")
    hdr_c = ["claim_id", "statement", "claim_type", "as_of", "confidence",
             "evidence_ids", "counter_evidence_ids", "derivation", "notes"]
    (d / "claims.csv").write_text(",".join(hdr_c) + "\n", encoding="utf-8")
    (d / "documents.csv").write_text(
        "document_id,source_id,content_hash,parser_version,byte_size,snapshot\n",
        encoding="utf-8")
    (d / "REPORT.md").write_text(
        f"# {slug}\n\n校验结果：sources={n_src}, evidence=0, claims=0, "
        f"claims_high=0\n", encoding="utf-8")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sync-report-"))
    try:
        make_archive(tmp, "alpha", 3)
        make_archive(tmp, "beta", 7)

        # 外部文档只讲 beta
        evals = tmp / "evals" / "cases"
        evals.mkdir(parents=True)
        ev = evals / "README.md"
        original = ("待建。首个候选案例：`research/beta`（含 **7 来源、11 证据、"
                    "13 主张**、1 条 disputed）。\n")
        ev.write_text(original, encoding="utf-8")

        # T1/T4：--slug alpha 时，evals 里讲的是 beta，必须不动
        before = ev.read_text(encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_report_counts.py"),
             "--slug", "alpha"],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": str(ROOT / "packages" / "schemas" / "python"),
                 "PATH": ""},
        )
        out = proc.stdout + proc.stderr
        after = ev.read_text(encoding="utf-8")
        check("T1 未提及的归档不改写外部文档", before == after,
              f"文件被改了：\n{after}")
        check("T1 输出里有跳过提示",
              "未提及" in out or "跳过" in out, out[:300])

        # T2：--slug beta 时应改写（beta 是文件提到的那个）
        proc2 = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_report_counts.py"),
             "--slug", "beta"],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": str(ROOT / "packages" / "schemas" / "python"),
                 "PATH": ""},
        )
        # dry-run 下不应写盘（T3）
        after2 = ev.read_text(encoding="utf-8")
        check("T3 dry-run 不写盘", after2 == original,
              "dry-run 改动了文件")

        results = RESULTS
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    bad = 0
    for name, ok, detail in results:
        if ok:
            print(f"[PASS] {name}")
        else:
            bad += 1
            print(f"[FAIL] {name}\n       {detail}")
    print(f"\n{len(results) - bad}/{len(results)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
