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
            "source_id,url,fetched_at,trust_tier\n",
            ["src-a,https://a,2026-10-27T00:00:00+00:00,primary"],
        )
        _write(
            root,
            "evidence.csv",
            "evidence_id,source_id,quote,stance\n",
            ["e-a,src-a,原文片段,supports"],
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
    """REPORT.md 末尾声明的计数必须与实际 CSV 行数一致（防止静默漂移）。

    ⚠️ 旧实现只查 rtx-pro-6000。改为遍历**所有**归档：
       新增归档时自动纳入，不需要改测试。
    """
    import re as _re

    research = ROOT / "research"
    if not research.is_dir():
        print("  (skip: archive absent)")
        return
    archives = sorted(p for p in research.iterdir()
                      if p.is_dir() and (p / "claims.csv").exists())
    if not archives:
        print("  (skip: archive absent)")
        return
    for target in archives:
        stats = validate_research_dir(target)
        report = (target / "REPORT.md").read_text(encoding="utf-8")
        m = _re.search(
            r"sources=(\d+), evidence=(\d+), claims=(\d+), claims_high=(\d+)", report
        )
        assert m, f"{target.name}/REPORT.md missing validation-result line"
        got = tuple(int(x) for x in m.groups())
        want = (stats["sources"], stats["evidence"], stats["claims"],
                stats["claims_high"])
        assert got == want, (
            f"{target.name}/REPORT.md header counts {got} != actual {want}；"
            f"跑 python scripts/sync_report_counts.py --apply 修复"
        )


def test_docs_quote_real_counts() -> None:
    """顶层 README / research/README / evals/cases README 若引用规模数字，必须与实际一致。

    ⚠️ 旧实现硬编码只取 rtx-pro-6000 的三个计数，然后在**全文**里用
       (\\d+)\\s*(来源|证据|主张) 扫一遍，要求每个数字都等于该归档的值。
       只要新增第二个归档，表格里另一行的数字就会被拿去和 rtx-pro-6000 比，
       于是必然误报（本次就是这样：声明 36 来源，实际 447）。
       正确做法是**按 slug 逐行配对**：只比该行自己那三个数。
    """
    import csv as _csv
    import re as _re

    research = ROOT / "research"
    if not research.is_dir():
        print("  (skip: archive absent)")
        return

    def counts(slug: str) -> dict[str, int] | None:
        d = research / slug
        if not (d / "claims.csv").exists():
            return None
        out = {}
        for kind, name in (("来源", "sources"), ("证据", "evidence"), ("主张", "claims")):
            with (d / f"{name}.csv").open(encoding="utf-8-sig") as fh:
                out[kind] = sum(1 for _ in _csv.DictReader(fh))
        return out

    # 只匹配带 slug 的表格行，两种相对路径都要认：
    #   research/README.md: | [slug](./slug/REPORT.md) | 主题 | **N 来源 / …** |
    #   顶层 README.md:     | [slug](./research/slug/REPORT.md) | 主题 | **N 来源 / …** |
    #
    # ⚠️ 原先只写了 `./slug/REPORT.md` 一种。顶层 README 用的是
    #    `./research/slug/REPORT.md`，于是整份文件**一行都没匹配上**，
    #    落进下面的兜底分支，拿 rsi-model-training 的「53 来源」去和
    #    rtx-pro-6000 的 447 比，报出一个假的漂移。
    #    修正则，不是改文档——文档数字是对的。
    row_re = _re.compile(
        r"^\|\s*\[(?P<slug>[a-z0-9-]+)\]"
        r"\(\./(?:research/)?(?P=slug)/REPORT\.md\)\s*\|"
        r"\s*(?P<topic>[^|]*)\|(?P<scale>[^|]*)\|",
        _re.MULTILINE,
    )
    num_re = _re.compile(r"(\d+)\s*(来源|证据|主张)")

    checked = 0
    for rel in ("research/README.md", "README.md", "evals/cases/README.md"):
        f = ROOT / rel
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        matched_any = False
        for m in row_re.finditer(text):
            actual = counts(m.group("slug"))
            if actual is None:
                continue
            matched_any = True
            checked += 1
            for num, kind in num_re.findall(m.group("scale")):
                got = int(num)
                want = actual[kind]
                assert got == want, (
                    f"{rel}: 行 [{m.group('slug')}] 声明 {got} {kind}，实际 {want}"
                )
        # 退路：文件里若完全没有 slug 表格行，才用旧的全文扫描（单归档场景）。
        # 只在**整份文件**没有任何可配对行时启用——否则匹配失败会伪装成漂移。
        if not matched_any and "rtx-pro-6000" in text:
            actual = counts("rtx-pro-6000")
            if actual:
                for num, kind in num_re.findall(text):
                    got = int(num)
                    want = actual[kind]
                    assert got == want, f"{rel}: 声明 {got} {kind}，实际 {want}"

    if not checked:
        print("  (skip: 无可配对的归档表格行)")


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


def test_run_requires_stop_note() -> None:
    """不变量 R1：stop_reason 为 budget_exhausted / gap_remaining 时必须给 stop_note。"""
    import json as _json
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "case"
        root.mkdir()
        (root / "brief.yaml").write_text("topic: t\n", encoding="utf-8")

        def _write_run(reason: str, note) -> None:
            doc = {
                "run_id": "run-x",
                "as_of": "2026-10-27",
                "stop_reason": reason,
                "budget": {"limits": {"max_tool_calls": 5}},
                "trace": [{"seq": 1, "kind": "search", "summary": "s"}],
            }
            if note is not None:
                doc["stop_note"] = note
            (root / "run.json").write_text(
                _json.dumps(doc, ensure_ascii=False), encoding="utf-8"
            )

        _write_run("gap_remaining", None)
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "stop_note" in str(exc), str(exc)
        else:
            raise AssertionError("缺失 stop_note 未被拒绝（R1）")

        _write_run("answered", None)
        validate_research_dir(root)  # answered 不要求 stop_note


def test_run_rejects_dangling_trace_refs() -> None:
    """run.json 的 trace 不得引用不存在的 source / evidence / claim。"""
    import json as _json
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "case"
        root.mkdir()
        (root / "brief.yaml").write_text("topic: t\n", encoding="utf-8")
        doc = {
            "run_id": "run-x",
            "as_of": "2026-10-27",
            "stop_reason": "answered",
            "budget": {"limits": {}},
            "trace": [
                {"seq": 1, "kind": "fetch", "summary": "s", "source_ids": ["src-nope"]}
            ],
        }
        (root / "run.json").write_text(_json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "src-nope" in str(exc), str(exc)
        else:
            raise AssertionError("悬空 source 引用未被拒绝")


def test_c1_high_requires_primary_support() -> None:
    """不变量 C1：high 置信主张必须有 primary 来源的 supports 证据。"""
    def _build(root: Path, tier: str, stance: str, conf: str) -> None:
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier\n",
               [f"src-a,https://a,2026-10-27T00:00:00+00:00,{tier}"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               [f"e-a,src-a,原文片段,{stance}"])
        _write(root, "claims.csv",
               "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n",
               [f"c-a,某事实,spec,2026-10-27,{conf},e-a"])
        (root / "REPORT.md").write_text("引用 [c-a] [e-a]。\n", encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        # secondary + high -> 必须拒绝
        root = Path(td) / "a"
        root.mkdir()
        _build(root, "secondary", "supports", "high")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "C1" in str(exc), str(exc)
        else:
            raise AssertionError("secondary 证据支撑 high 主张未被拒绝（C1）")

    with tempfile.TemporaryDirectory() as td:
        # primary 但 stance=context -> 仍必须拒绝（C1 要求 supports）
        root = Path(td) / "b"
        root.mkdir()
        _build(root, "primary", "context", "high")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "C1" in str(exc), str(exc)
        else:
            raise AssertionError("primary 但非 supports 未被拒绝（C1）")

    with tempfile.TemporaryDirectory() as td:
        # secondary + medium -> 允许
        root = Path(td) / "c"
        root.mkdir()
        _build(root, "secondary", "supports", "medium")
        validate_research_dir(root)


def test_c3_disputed_requires_counter_evidence() -> None:
    """不变量 C3：disputed 主张必须给出 counter_evidence_ids。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier\n",
               ["src-a,https://a,2026-10-27T00:00:00+00:00,primary"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               ["e-a,src-a,正面,supports", "e-b,src-a,反面,refutes"])
        _write(root, "claims.csv",
               "claim_id,statement,claim_type,as_of,confidence,evidence_ids,"
               "counter_evidence_ids\n",
               ["c-a,有争议的事实,spec,2026-10-27,disputed,e-a,"])
        (root / "REPORT.md").write_text("引用 [c-a] [e-a] [e-b]。\n", encoding="utf-8")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "C3" in str(exc), str(exc)
        else:
            raise AssertionError("disputed 未给反证未被拒绝（C3）")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier\n",
               ["src-a,https://a,2026-10-27T00:00:00+00:00,primary"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               ["e-a,src-a,正面,supports", "e-b,src-a,反面,refutes"])
        _write(root, "claims.csv",
               "claim_id,statement,claim_type,as_of,confidence,evidence_ids,"
               "counter_evidence_ids\n",
               ["c-a,有争议的事实,spec,2026-10-27,disputed,e-a,e-b"])
        (root / "REPORT.md").write_text("引用 [c-a] [e-a] [e-b]。\n", encoding="utf-8")
        validate_research_dir(root)  # 给了反证就允许


def test_r2_rejects_bad_subquestion_status() -> None:
    """不变量 R2：brief.yaml 的 status 必须是三值之一。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, "sources.csv", "source_id,url,fetched_at\n", [])
        _write(root, "evidence.csv", "evidence_id,source_id,quote\n", [])
        _write(root, "claims.csv",
               "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n", [])
        (root / "REPORT.md").write_text("空报告。\n", encoding="utf-8")
        (root / "brief.yaml").write_text(
            "subquestions:\n"
            "  - id: q1\n"
            "    question: 测试\n"
            "    status: answered\n"
            "  - id: q2\n"
            "    question: 测试2\n"
            "    status: done\n",  # 非法值
            encoding="utf-8",
        )
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "R2" in str(exc), str(exc)
        else:
            raise AssertionError("非法子问题状态未被拒绝（R2）")


def test_s2_non_open_source_cannot_support() -> None:
    """不变量 S2：access!=open 的来源不得支撑 high/medium 主张。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier,access\n",
               ["src-a,https://a,2026-10-27T00:00:00+00:00,primary,blocked"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               ["e-a,src-a,片段,supports"])
        _write(root, "claims.csv",
               "claim_id,statement,claim_type,as_of,confidence,evidence_ids\n",
               ["c-a,某事实,spec,2026-10-27,high,e-a"])
        (root / "REPORT.md").write_text("引用 [c-a] [e-a]。\n", encoding="utf-8")
        try:
            validate_research_dir(root)
        except ValidationError as exc:
            assert "S2" in str(exc), str(exc)
        else:
            raise AssertionError("blocked 来源支撑 high 主张未被拒绝（S2）")


def test_all_sources_listed_in_references() -> None:
    """sources.csv 的每个来源都必须出现在 REPORT.md 的参考文献一节里。

    曾经有 141 个来源但参考文献只列了 42 个——正文引用了数据，读者却找不到出处。
    """
    import csv as _csv
    import re as _re
    target = ROOT / "research" / "rtx-pro-6000"
    if not target.is_dir():
        print("  (skip: archive absent)")
        return
    report = (target / "REPORT.md").read_text(encoding="utf-8")
    m = _re.search(r"## 15\. 参考文献([\s\S]*?)(?=\n## 附录 A|\Z)", report)
    if not m:
        print("  (skip: no references section)")
        return
    listed = set(_re.findall(r"\[(src-[a-z0-9\-]+)\]", m.group(1)))
    with (target / "sources.csv").open(encoding="utf-8-sig") as fh:
        all_src = {r["source_id"] for r in _csv.DictReader(fh)}
    missing = sorted(all_src - listed)
    assert not missing, f"未列入参考文献的来源 ({len(missing)}): {missing[:10]}"


def test_evidence_ids_reject_claim_prefix() -> None:
    """回归：evidence_ids 里混入 c- 前缀（把 claim_id 当 evidence_id）必须被拒绝。

    这一类错误在历史上重复出现过多次，且旧实现的报错只说
    「引用不存在的 evidence」，无法提示真正的成因。
    """
    def _build(root: Path, mode: str) -> None:
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier\n",
               ["src-a,https://a,2026-10-27T00:00:00+00:00,primary"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               ["e-a,src-a,原文片段,supports"])
        header = "claim_id,statement,claim_type,as_of,confidence,evidence_ids,counter_evidence_ids"
        if mode == "evidence_ids":
            rows = ["c-a,某事实,spec,2026-10-27,medium,c-a,"]
        else:
            rows = ["c-a,某事实,spec,2026-10-27,medium,e-a,",
                    "c-b,另一个事实,spec,2026-10-27,medium,e-a,c-a"]
        _write(root, "claims.csv", header + "\n", rows)
        (root / "REPORT.md").write_text("引用 [c-a] [e-a]。\n", encoding="utf-8")

    for mode in ("evidence_ids", "counter_evidence_ids"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / mode
            root.mkdir()
            _build(root, mode)
            try:
                validate_research_dir(root)
            except ValidationError as exc:
                msg = str(exc)
                assert "claim_id" in msg or "claim 前缀" in msg, msg
            else:
                raise AssertionError(f"{mode} 中的 c- 前缀未被拒绝")
    return None


def test_evidence_ids_hint_e_prefix_claim_twin() -> None:
    """回归：用 e- 前缀引用一个真实 claim 名时，报错须点明对应的 c- 名字。

    这是 c- 前缀检查的补集。历史上实际错法是把 claim 名冠以 e-
    （例如 claim `c-bb-x` 被写成 `e-bb-x`），此时 id 本身以 e- 开头，
    旧检查完全无法提示成因。
    """
    def _build(root: Path, mode: str) -> None:
        _write(root, "sources.csv", "source_id,url,fetched_at,trust_tier\n",
               ["src-a,https://a,2026-10-27T00:00:00+00:00,primary"])
        _write(root, "evidence.csv", "evidence_id,source_id,quote,stance\n",
               ["e-a,src-a,原文片段,supports"])
        header = "claim_id,statement,claim_type,as_of,confidence,evidence_ids,counter_evidence_ids"
        # c-target 是真实存在的 claim；错误引用写作 e-target
        if mode == "evidence_ids":
            rows = ["c-target,某事实,spec,2026-10-27,medium,e-a,",
                    "c-user,另一事实,spec,2026-10-27,medium,e-target,"]
        else:
            rows = ["c-target,某事实,spec,2026-10-27,medium,e-a,",
                    "c-user,另一事实,spec,2026-10-27,medium,e-a,e-target"]
        _write(root, "claims.csv", header + "\n", rows)
        (root / "REPORT.md").write_text("引用 [c-target] [c-user] [e-a]。\n", encoding="utf-8")

    for mode in ("evidence_ids", "counter_evidence_ids"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / mode
            root.mkdir()
            _build(root, mode)
            try:
                validate_research_dir(root)
            except ValidationError as exc:
                msg = str(exc)
                assert "c-target" in msg, msg
                assert "claim_id" in msg, msg
            else:
                raise AssertionError(f"{mode} 中的 e- 前缀 claim 孪生未被提示")
    return None


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
