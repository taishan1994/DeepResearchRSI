"""研究留档的自洽性校验。

不依赖第三方库：用 csv + re 做字段与引用闭合检查。设计目标是"能在 CI 里
对 research/ 下每个任务目录直接跑"，因此只检查**机器可判定**的不变量：

- sources.csv / claims.csv / evidence.csv 的 ID 前缀与唯一性
- claims 引用的 evidence 是否都存在（引用闭合，不变量 C1 的基础）
- evidence 引用的 document/source 是否存在
- 关键字段非空、日期可解析
- REPORT.md 中 `[c-xxx]` 形式的 claim 引用是否都能在 claims.csv 找到
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

CLAIM_REF_RE = re.compile(r"\[(c-[a-z0-9-]+)\]")
SRC_REF_RE = re.compile(r"\[(src-[a-z0-9-]+)\]")
EVIDENCE_REF_RE = re.compile(r"\[(e-[a-z0-9-]+)\]")

# 与 packages/schemas/json/source.schema.json 的枚举保持一致
STOP_REASONS = {"answered", "budget_exhausted", "gap_remaining", "error"}
TRACE_KINDS = {
    "search", "fetch", "fetch_failed", "extract", "claim_added",
    "claim_revised", "claim_dropped", "gap_declared", "section_written", "validate",
}

SOURCE_TYPES = {
    "official",
    "vendor",
    "vendor-adjacent",
    "review",
    "academic",
    "community",
    "press",
    "retail",
    "independent",
}
TRUST_TIERS = {"primary", "secondary", "tertiary"}


class ValidationError(Exception):
    pass


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _parse_date(value: str, *, where: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValidationError(f"{where}: 无法解析日期 {value!r}") from exc


def validate_research_dir(path: str | Path) -> dict[str, int]:
    """校验一个 research/<slug>/ 目录，返回统计信息；失败时抛 ValidationError。"""
    stats_extra: dict[str, int] = {}
    root = Path(path)
    if not root.is_dir():
        raise ValidationError(f"不是目录: {root}")

    errors: list[str] = []

    sources = _read_csv(root / "sources.csv")
    evidence = _read_csv(root / "evidence.csv")
    claims = _read_csv(root / "claims.csv")

    source_ids: set[str] = set()
    for row in sources:
        sid = (row.get("source_id") or "").strip()
        if not sid.startswith("src-"):
            errors.append(f"sources.csv: 非法 source_id {sid!r}")
            continue
        if sid in source_ids:
            errors.append(f"sources.csv: 重复 source_id {sid}")
        source_ids.add(sid)
        if not (row.get("url") or "").strip():
            errors.append(f"sources.csv[{sid}]: url 为空")
        if not (row.get("fetched_at") or "").strip():
            errors.append(f"sources.csv[{sid}]: fetched_at 为空（不变量 S1）")
        _parse_date(row.get("published_at", ""), where=f"sources.csv[{sid}].published_at")
        # 枚举校验：与 json/source.schema.json 保持一致
        stype = (row.get("source_type") or "").strip()
        if stype and stype not in SOURCE_TYPES:
            errors.append(
                f"sources.csv[{sid}]: 非法 source_type {stype!r}（允许 {sorted(SOURCE_TYPES)}）"
            )
        tier = (row.get("trust_tier") or "").strip()
        if tier and tier not in TRUST_TIERS:
            errors.append(
                f"sources.csv[{sid}]: 非法 trust_tier {tier!r}（允许 {sorted(TRUST_TIERS)}）"
            )

    evidence_ids: set[str] = set()
    for row in evidence:
        eid = (row.get("evidence_id") or "").strip()
        if not eid.startswith("e-"):
            errors.append(f"evidence.csv: 非法 evidence_id {eid!r}")
            continue
        if eid in evidence_ids:
            errors.append(f"evidence.csv: 重复 evidence_id {eid}")
        evidence_ids.add(eid)
        if not (row.get("quote") or "").strip():
            errors.append(f"evidence.csv[{eid}]: quote 为空（不变量 E1）")
        sid = (row.get("source_id") or "").strip()
        if sid and sid not in source_ids:
            errors.append(f"evidence.csv[{eid}]: 引用了不存在的 source {sid}")

    claim_ids: set[str] = set()
    for row in claims:
        cid = (row.get("claim_id") or "").strip()
        if not cid.startswith("c-"):
            errors.append(f"claims.csv: 非法 claim_id {cid!r}")
            continue
        if cid in claim_ids:
            errors.append(f"claims.csv: 重复 claim_id {cid}")
        claim_ids.add(cid)
        eids = [x.strip() for x in (row.get("evidence_ids") or "").split(";") if x.strip()]
        if not eids:
            errors.append(f"claims.csv[{cid}]: 没有任何证据（不变量 C1）")
        for eid in eids:
            if eid not in evidence_ids:
                errors.append(f"claims.csv[{cid}]: 引用不存在的 evidence {eid}")
        ceids = [x.strip() for x in (row.get("counter_evidence_ids") or "").split(";") if x.strip()]
        for eid in ceids:
            if eid not in evidence_ids:
                errors.append(f"claims.csv[{cid}]: 引用不存在的反证 {eid}")
        _parse_date(row.get("as_of", ""), where=f"claims.csv[{cid}].as_of")
        if row.get("claim_type") == "prediction" and not (row.get("derivation") or "").strip():
            errors.append(f"claims.csv[{cid}]: prediction 缺少 derivation（不变量 C2）")

    report_path = root / "REPORT.md"
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        for cid in set(CLAIM_REF_RE.findall(text)):
            if cid not in claim_ids:
                errors.append(f"REPORT.md: 引用了不存在的 {cid}")
        for sid in set(SRC_REF_RE.findall(text)):
            if sid not in source_ids:
                errors.append(f"REPORT.md: 引用了不存在的 {sid}")
        for eid in set(EVIDENCE_REF_RE.findall(text)):
            if eid not in evidence_ids:
                errors.append(f"REPORT.md: 引用了不存在的 {eid}")

    # run.json：可选的运行轨迹（阶段 1 验收门槛「轨迹可看」）
    run_path = root / "run.json"
    if run_path.exists():
        try:
            run = json.loads(run_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"run.json: 无法解析 JSON（{exc}）")
            run = None
        if run is not None:
            rid = (run.get("run_id") or "").strip()
            if not rid.startswith("run-"):
                errors.append(f"run.json: 非法 run_id {rid!r}")
            if not (run.get("as_of") or "").strip():
                errors.append("run.json: as_of 为空")
            _parse_date(run.get("as_of", ""), where="run.json.as_of")
            reason = (run.get("stop_reason") or "").strip()
            if reason not in STOP_REASONS:
                errors.append(
                    f"run.json: 非法 stop_reason {reason!r}（不变量 R1，允许 {sorted(STOP_REASONS)}）"
                )
            if reason in ("budget_exhausted", "gap_remaining") and not (run.get("stop_note") or "").strip():
                errors.append(
                    f"run.json: stop_reason={reason} 时 stop_note 必须说明未解决部分（不变量 R1）"
                )
            trace = run.get("trace") or []
            if not isinstance(trace, list) or not trace:
                errors.append("run.json: trace 不得为空")
                trace = []
            seqs = []
            for ev in trace:
                if not isinstance(ev, dict):
                    errors.append("run.json: trace 元素必须是对象")
                    continue
                s = ev.get("seq")
                if not isinstance(s, int) or s < 1:
                    errors.append(f"run.json: 非法 trace seq {s!r}")
                    continue
                seqs.append(s)
                kind = (ev.get("kind") or "").strip()
                if kind not in TRACE_KINDS:
                    errors.append(f"run.json[trace seq={s}]: 非法 kind {kind!r}")
                if not (ev.get("summary") or "").strip():
                    errors.append(f"run.json[trace seq={s}]: summary 为空")
                for sid in ev.get("source_ids") or []:
                    if sid not in source_ids:
                        errors.append(f"run.json[trace seq={s}]: 引用了不存在的 source {sid}")
                for eid in ev.get("evidence_ids") or []:
                    if eid not in evidence_ids:
                        errors.append(f"run.json[trace seq={s}]: 引用了不存在的 evidence {eid}")
                for cid in ev.get("claim_ids") or []:
                    if cid not in claim_ids:
                        errors.append(f"run.json[trace seq={s}]: 引用了不存在的 claim {cid}")
            if seqs != sorted(seqs):
                errors.append("run.json: trace seq 必须递增")
            if len(seqs) != len(set(seqs)):
                errors.append("run.json: trace seq 必须唯一")
            stats_extra["trace_events"] = len(seqs)

    if errors:
        raise ValidationError("\n".join(f"  - {e}" for e in errors))

    stats = {
        "sources": len(sources),
        "evidence": len(evidence),
        "claims": len(claims),
        "claims_high": sum(1 for r in claims if r.get("confidence") == "high"),
        "claims_disputed": sum(1 for r in claims if r.get("confidence") == "disputed"),
    }
    stats.update(stats_extra)
    return stats


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python -m deepresearchrsi.validate <research_dir> [more_dirs...]")
        return 2
    failed = False
    for arg in argv[1:]:
        try:
            stats = validate_research_dir(arg)
        except ValidationError as exc:
            failed = True
            print(f"[FAIL] {arg}\n{exc}")
        else:
            detail = ", ".join(f"{k}={v}" for k, v in stats.items())
            print(f"[OK]   {arg}  ({detail})")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
