"""ADR-0002 三条不变量（E1 / S1 / D1）的判据测试。

⚠️ 为什么必须写这个文件
   这三条在 ADR 里写明「由 validate_research.py 在 CI 中机器校验」，
   但实现原先只有：
       if not quote: 报错
       if not fetched_at: 报错
   「非空」不等于「是原文子串」，也不等于「带时区」。D1 完全没实现。
   而错误信息里还写着「（不变量 E1）」——读起来像是验过了。

   更隐蔽的一次：本文件第 3 条用例抓到一个真 bug。
   evidence 里填 source_id（src-arxiv-2507-14111），
   快照名却是 document_id（doc-arxiv-2507-14111），
   两者差一个前缀，导致 19 条证据全部落到「无法校验」，
   而输出仍是 [OK]——检查静默失效。

本文件验证：
   S1: 无时区的时间戳必须被拒
   S1: 带时区（+08:00 / Z）通过
   D1: 同一 document_id 两个 content_hash 必须被拒
   D1: 一个 document_id 一个 hash 通过
   E1: quote 不是原文子串必须被拒
   E1: quote 是原文子串通过
   E1: 空白/换行差异不算改写（PDF 抽取的常态）
   E1: 没有快照时计入「无法校验」，不得计入「通过」

不依赖 pytest：`python tests/test_invariants.py`
"""

from __future__ import annotations

import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi import invariants  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


# ---------------------------------------------------------------- S1
def test_s1() -> None:
    bad = [{"source_id": "src-a", "fetched_at": "2026-11-03"}]
    errs, ok = invariants.check_s1_timezone(bad)
    check("S1 拒绝无时区时间戳", len(errs) == 1 and ok == 0, str(errs))

    good = [{"source_id": "src-a", "fetched_at": "2026-11-03T10:00:00+08:00"},
            {"source_id": "src-b", "fetched_at": "2026-11-03T02:00:00Z"}]
    errs, ok = invariants.check_s1_timezone(good)
    check("S1 接受带时区时间戳", not errs and ok == 2, str(errs))

    empty = [{"source_id": "src-a", "fetched_at": ""}]
    errs, ok = invariants.check_s1_timezone(empty)
    check("S1 拒绝空 fetched_at", len(errs) == 1, str(errs))


# ---------------------------------------------------------------- D1
def test_d1(tmp: Path) -> None:
    d = tmp / "d1"
    d.mkdir()
    rows = [
        {"document_id": "doc-a", "content_hash": "h1"},
        {"document_id": "doc-a", "content_hash": "h2"},
    ]
    _write_docs(d, rows)
    errs, n = invariants.check_d1_versions(d)
    check("D1 拒绝同 ID 多哈希", len(errs) == 1 and n == 1, str(errs))

    d2 = tmp / "d1ok"
    d2.mkdir()
    _write_docs(d2, [{"document_id": "doc-a", "content_hash": "h1"},
                     {"document_id": "doc-b", "content_hash": "h2"}])
    errs, n = invariants.check_d1_versions(d2)
    check("D1 不同 ID 各自哈希通过", not errs and n == 2, str(errs))


def _write_docs(d: Path, rows: list[dict[str, str]]) -> None:
    import csv
    with (d / "documents.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["document_id", "content_hash"])
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- E1
def test_e1(tmp: Path) -> None:
    d = tmp / "e1"
    (d / "documents").mkdir(parents=True)
    body = ("We present CUDA-L1, which delivers an average speedup of x3.12 "
            "with a median speedup of x1.42 over 250 kernels.")
    (d / "documents" / "doc-arxiv-2507-14111.txt").write_text(body, encoding="utf-8")

    # 用 source_id 形式引用，验证 src- -> doc- 的映射（这是抓出过真 bug 的点）
    ok_ev = [{"evidence_id": "e-001", "source_id": "src-arxiv-2507-14111",
              "quote": "average speedup of x3.12"}]
    errs, checked, skipped = invariants.check_e1_substring(d, ok_ev)
    check("E1 原文子串通过（src- 映射到 doc-）",
          not errs and checked == 1 and skipped == 0, f"{errs} c={checked} s={skipped}")

    bad_ev = [{"evidence_id": "e-002", "source_id": "src-arxiv-2507-14111",
               "quote": "average speedup of x9.99"}]
    errs, checked, _ = invariants.check_e1_substring(d, bad_ev)
    check("E1 改写/编造的 quote 被拒", len(errs) == 1 and checked == 1, str(errs))

    # 换行与多空格不算改写
    spaced = [{"evidence_id": "e-003", "source_id": "src-arxiv-2507-14111",
               "quote": "average  speedup\n of x3.12"}]
    errs, checked, _ = invariants.check_e1_substring(d, spaced)
    check("E1 空白差异不算改写", not errs and checked == 1, str(errs))

    # 没有快照 -> 计入 unverifiable，不得算作通过
    d2 = tmp / "e1nosnap"
    d2.mkdir()
    ev = [{"evidence_id": "e-004", "source_id": "src-nothing",
           "quote": "anything"}]
    errs, checked, skipped = invariants.check_e1_substring(d2, ev)
    check("E1 无快照计入未校验而非通过",
          not errs and checked == 0 and skipped == 1, f"c={checked} s={skipped}")

    # ---- 多快照：摘要 + 全文共存 ----
    # 背景：cuda-kernel-rl 第二轮抓了全文后，一度让 E1「优先用全文」，
    # 结果 14 条摘要级证据全部失败——因为同一句话在两种来源里表示不同：
    #   摘要（Atom API）：  ... by up to 26%, and on average 9%.
    #   全文（LaTeXML）：   ... by up to $26\%$, and on average $9\%$.
    # 用全文校验摘要级引文会把正确证据判成伪造，比不检查更糟
    # （它会训练人去改对的证据）。故判据改为「任一快照匹配即通过」。
    d3 = tmp / "e1multi"
    (d3 / "documents").mkdir(parents=True)
    (d3 / "documents" / "doc-arxiv-9999-00001.txt").write_text(
        "Experiments show CuAsmRL improves performance by up to 26%, "
        "and on average 9%.", encoding="utf-8")
    (d3 / "documents" / "doc-arxiv-9999-00001-full.txt").write_text(
        "Experiments show CuAsmRL improves performance by up to $26\\%$, "
        "and on average $9\\%$.", encoding="utf-8")

    abstract_ev = [{"evidence_id": "e-005",
                    "document_id": "doc-arxiv-9999-00001",
                    "quote": "by up to 26%, and on average 9%."}]
    errs, checked, _ = invariants.check_e1_substring(d3, abstract_ev)
    check("E1 摘要级引文在全文存在时仍通过",
          not errs and checked == 1, str(errs))

    fulltext_ev = [{"evidence_id": "e-006",
                    "document_id": "doc-arxiv-9999-00001",
                    "quote": "improves performance by up to $26\\%$"}]
    errs, checked, _ = invariants.check_e1_substring(d3, fulltext_ev)
    check("E1 正文级引文（LaTeX 形式）通过", not errs and checked == 1, str(errs))

    # 归一放宽的是排版标记，不是文字：改数字仍须被抓
    fake_ev = [{"evidence_id": "e-007",
                "document_id": "doc-arxiv-9999-00001",
                "quote": "by up to 31%, and on average 9%."}]
    errs, checked, _ = invariants.check_e1_substring(d3, fake_ev)
    check("E1 归一后仍能抓出改过的数字",
          len(errs) == 1 and checked == 1, str(errs))


def main() -> int:
    test_s1()
    tmp = Path(tempfile.mkdtemp(prefix="invariants-"))
    try:
        test_d1(tmp)
        test_e1(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    bad = 0
    for name, ok, detail in RESULTS:
        if ok:
            print(f"[PASS] {name}")
        else:
            bad += 1
            print(f"[FAIL] {name}\n       {detail}")
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} 通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
