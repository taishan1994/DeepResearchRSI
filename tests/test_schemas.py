"""契约与校验器的不变量测试。

不需要 pytest 也能跑：`python tests/test_schemas.py`
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "python"))

from deepresearchrsi import Claim, Evidence, Source  # noqa: E402
from deepresearchrsi.validate import ValidationError, validate_research_dir  # noqa: E402

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append(f"{name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        FAILURES.append(f"{name}: 未预期异常 {type(exc).__name__}: {exc}")
    else:
        print(f"[PASS] {name}")


def _source(**kw) -> Source:
    base = dict(
        source_id="src-test",
        url="https://example.com",
        source_type="official",
        trust_tier="primary",
        fetched_at=datetime(2026, 10, 27, tzinfo=timezone.utc),
    )
    base.update(kw)
    return Source(**base)


# ---------- Source ----------

def test_source_requires_tz() -> None:
    try:
        _source(fetched_at=datetime(2026, 10, 27))
    except ValueError as exc:
        assert "S1" in str(exc) or "timezone" in str(exc), f"错误信息未提及时区: {exc}"
        return
    raise AssertionError("naive datetime 应被拒绝（不变量 S1）")


def test_source_id_prefix() -> None:
    try:
        _source(source_id="bad-id")
    except ValueError:
        return
    raise AssertionError("非 src- 前缀应被拒绝")


def test_source_ok() -> None:
    s = _source()
    assert s.source_id == "src-test", "source_id 不符"


# ---------- Evidence ----------

def test_evidence_quote_required() -> None:
    try:
        Evidence(evidence_id="e-x", document_id="d", quote="   ", locator="p1")
    except ValueError:
        return
    raise AssertionError("空 quote 应被拒绝（不变量 E1）")


def test_evidence_id_prefix() -> None:
    try:
        Evidence(evidence_id="bad", document_id="d", quote="q", locator="p1")
    except ValueError:
        return
    raise AssertionError("非 e- 前缀应被拒绝")


def test_evidence_ok() -> None:
    e = Evidence(evidence_id="e-x", document_id="d", quote="原文", locator="§1")
    assert e.stance == "supports", "默认 stance 应为 supports"


# ---------- Claim ----------

def test_claim_needs_evidence() -> None:
    try:
        Claim(
            claim_id="c-x",
            statement="某事实",
            claim_type="spec",
            as_of=date(2026, 10, 27),
            confidence="high",
            evidence_ids=[],
        )
    except ValueError:
        return
    raise AssertionError("无证据的主张应被拒绝（不变量 C1）")


def test_claim_prediction_needs_derivation() -> None:
    try:
        Claim(
            claim_id="c-x",
            statement="某预测",
            claim_type="prediction",
            as_of=date(2026, 10, 27),
            confidence="high",
            evidence_ids=["e-a"],
        )
    except ValueError:
        return
    raise AssertionError("prediction 缺 derivation 应被拒绝（不变量 C2）")


def test_claim_prediction_with_derivation_ok() -> None:
    c = Claim(
        claim_id="c-x",
        statement="某预测",
        claim_type="prediction",
        as_of=date(2026, 10, 27),
        confidence="high",
        evidence_ids=["e-a"],
        derivation="由 A 与 B 推导",
    )
    assert c.derivation, "derivation 应保留"


# ---------- validate_research_dir ----------

def _write(root: Path, name: str, header: str, rows: list[str]) -> None:
    (root / name).write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def test_validator_detects_dangling_evidence() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(
            root,
            "sources.csv",
            "source_id,url,fetched_at\n",
            ['src-a,https://a,2026-10-27T00:00:00+00:00'],
        )
        _write(root, "evidence.csv", "evidence_id,source_id,quote\n", [])
        _write(
            root,
            "claims.csv",
            "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n",
            ["c-a,某事实,spec,2026-10-27,high,e-missing"],
        )
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "e-missing" in str(exc), f"未指出悬空证据: {exc}"
            return
        raise AssertionError("悬空证据引用应被检出")


def test_validator_accepts_clean_archive() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(
            root,
            "sources.csv",
            "source_id,url,fetched_at\n",
            ["src-a,https://a,2026-10-27T00:00:00+00:00"],
        )
        _write(
            root,
            "evidence.csv",
            "evidence_id,source_id,quote\n",
            ["e-a,src-a,原文片段"],
        )
        _write(
            root,
            "claims.csv",
            "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n",
            ["c-a,某事实,spec,2026-10-27,high,e-a"],
        )
        (root / "REPORT.md").write_text("引用 [c-a] 与 [e-a] 与 [src-a]。\n", encoding="utf-8")
        stats = validate_research_dir(root)
        assert stats["claims"] == 1, f"统计错误: {stats}"


def test_validator_detects_report_dangling_claim() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(
            root,
            "sources.csv",
            "source_id,url,fetched_at\n",
            ["src-a,https://a,2026-10-27T00:00:00+00:00"],
        )
        _write(root, "evidence.csv", "evidence_id,source_id,quote\n", [])
        _write(root, "claims.csv", "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n", [])
        (root / "REPORT.md").write_text("引用了不存在的 [c-ghost]。\n", encoding="utf-8")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "c-ghost" in str(exc), f"未指出悬空主张: {exc}"
            return
        raise AssertionError("报告中的悬空 claim 引用应被检出")


def test_real_archive_passes() -> None:
    target = ROOT / "research" / "rtx-pro-6000"
    if not target.is_dir():
        print("  (跳过：research/rtx-pro-6000 不存在)")
        return
    stats = validate_research_dir(target)
    assert stats["claims"] > 0, "真实留档应包含主张"


def test_validator_rejects_bad_source_type() -> None:
    """校验器必须拒绝 schema 枚举之外的 source_type（防止可信度误填进类型列）。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "case"
        root.mkdir()
        (root / "brief.yaml").write_text("topic: t\n", encoding="utf-8")
        (root / "sources.csv").write_text(
            "source_id,url,source_type,publisher,title,published_at,updated_at,"
            "fetched_at,language,trust_tier,access,license,notes\n"
            'src-a,https://e.com,secondary,p,t,,,2026-01-01T00:00:00+00:00,en,secondary,open,,\n',
            encoding="utf-8",
        )
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "source_type" in str(exc), str(exc)
        else:
            raise AssertionError("非法 source_type 未被拒绝")


def test_report_header_counts_match_data() -> None:
    """REPORT.md 末尾声明的计数必须与实际 CSV 行数一致（防止静默漂移）。"""
    import re as _re
    target = ROOT / "research" / "rtx-pro-6000"
    if not target.is_dir():
        print("  (skip: archive absent)")
        return
    stats = validate_research_dir(target)
    report = (target / "REPORT.md").read_text(encoding="utf-8")
    m = _re.search(
        r"sources=(\d+), evidence=(\d+), claims=(\d+), claims_high=(\d+)", report
    )
    assert m, "REPORT.md missing validation-result line"
    got = tuple(int(x) for x in m.groups())
    want = (stats["sources"], stats["evidence"], stats["claims"], stats["claims_high"])
    assert got == want, f"header counts {got} != actual {want}"


def test_docs_quote_real_counts() -> None:
    """顶层 README / research/README / evals/cases README 若引用规模数字，必须与实际一致。"""
    import csv as _csv
    import re as _re
    target = ROOT / "research" / "rtx-pro-6000"
    if not target.is_dir():
        print("  (skip: archive absent)")
        return

    with (target / "sources.csv").open(encoding="utf-8-sig") as fh:
        n_src = sum(1 for _ in _csv.DictReader(fh))
    with (target / "evidence.csv").open(encoding="utf-8-sig") as fh:
        n_ev = sum(1 for _ in _csv.DictReader(fh))
    with (target / "claims.csv").open(encoding="utf-8-sig") as fh:
        n_cl = sum(1 for _ in _csv.DictReader(fh))

    # 匹配形如 "136 来源" / "872 证据" / "573 主张" 的声明
    pattern = _re.compile(r"(\d+)\s*(来源|证据|主张)")
    actual = {"来源": n_src, "证据": n_ev, "主张": n_cl}

    for rel in ("README.md", "research/README.md", "evals/cases/README.md"):
        f = ROOT / rel
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for num, kind in pattern.findall(text):
            got = int(num)
            want = actual[kind]
            assert got == want, f"{rel}: 声明 {got} {kind}，实际 {want}"


def test_brief_matches_report_appendix() -> None:
    """brief.yaml 的子问题集合必须与 REPORT.md 附录 A 表格一致（不变量 R2）。"""
    import re as _re
    target = ROOT / "research" / "rtx-pro-6000"
    if not target.is_dir():
        print("  (skip: archive absent)")
        return
    brief = (target / "brief.yaml").read_text(encoding="utf-8")
    report = (target / "REPORT.md").read_text(encoding="utf-8")

    m = _re.search(r"## 附录 A.*?(?=\n## |\Z)", report, _re.S)
    if not m:
        print("  (skip: no appendix A)")
        return
    rows = _re.findall(
        r"^\|\s*(q\d+)\s*\|\s*([^|]*)\|\s*([^|]*)\|", m.group(0), _re.M
    )
    if not rows:
        print("  (skip: appendix table empty)")
        return

    appendix = {}
    for qid, _q, status in rows:
        if qid in appendix:
            continue
        s = status.strip()
        appendix[qid] = (
            "answered" if "✅" in s else "partial" if "⚠" in s
            else "unanswered" if "❌" in s else "other"
        )

    brief_ids = _re.findall(r"id:\s*(q\d+)", brief)
    brief_status = _re.findall(r"status:\s*(\w+)", brief)

    assert len(brief_ids) == len(brief_status), (
        f"brief.yaml 中 {len(brief_ids)} 个 id 但 {len(brief_status)} 个 status"
    )
    brief_map = dict(zip(brief_ids, brief_status))

    only_brief = sorted(set(brief_map) - set(appendix))
    only_report = sorted(set(appendix) - set(brief_map))
    assert not only_brief, f"brief.yaml 有而附录缺: {only_brief[:8]}"
    assert not only_report, f"附录有而 brief.yaml 缺: {only_report[:8]}"

    mismatch = [
        (q, brief_map[q], appendix[q]) for q in appendix if brief_map[q] != appendix[q]
    ]
    assert not mismatch, f"状态不一致 (id, brief, appendix): {mismatch[:8]}"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        check(fn.__name__, fn)
    print()
    if FAILURES:
        print(f"{len(FAILURES)} 项失败：")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"全部 {len(tests)} 项通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
