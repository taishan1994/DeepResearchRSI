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

from . import invariants
from pathlib import Path

CLAIM_REF_RE = re.compile(r"\[(c-[a-z0-9-]+)\]")
SRC_REF_RE = re.compile(r"\[(src-[a-z0-9-]+)\]")
EVIDENCE_REF_RE = re.compile(r"\[(e-[a-z0-9-]+)\]")

# 与 packages/schemas/json/source.schema.json 的枚举保持一致
SKU_VALUES = {
    "ws", "mq", "se", "all", "na", "unspecified",
    "mq+ws", "se+ws", "mq+se", "mq+se+ws",
}
# sku=unspecified 是允许的，但它是一个可统计的欠账状态；
# 校验器只检查枚举合法性与「比较型主张不该是单值」，不强制补全。

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

    # 预先收集全部 claim 名，供 evidence 引用错误时给出「e-xxx 其实是 c-xxx」的提示。
    # 必须在遍历 claims 之前算好，否则后出现的 claim 无法被前面的引用提示到。
    claim_names: set[str] = {
        (row.get("claim_id") or "").strip()
        for row in claims
        if (row.get("claim_id") or "").strip().startswith("c-")
    }

    claim_ids: set[str] = set()
    sku_unspecified = 0
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
                hint = ""
                if eid.startswith("c-"):
                    hint = "（疑把 claim_id 当成 evidence_id 引用）"
                elif eid.startswith("e-"):
                    # 常见错法：把 claim 名加上 e- 前缀当作 evidence_id。
                    twin = "c-" + eid[2:]
                    if twin in claim_names:
                        hint = f"（{twin} 是 claim_id；应以真实 evidence id 引用其证据）"
                errors.append(f"claims.csv[{cid}]: 引用不存在的 evidence {eid}{hint}")
            elif eid.startswith("c-"):
                errors.append(
                    f"claims.csv[{cid}]: evidence_ids 中出现 claim 前缀的 id {eid}"
                )
        ceids = [x.strip() for x in (row.get("counter_evidence_ids") or "").split(";") if x.strip()]
        for eid in ceids:
            if eid not in evidence_ids:
                hint = ""
                if eid.startswith("c-"):
                    hint = "（疑把 claim_id 当成 evidence_id 引用）"
                elif eid.startswith("e-"):
                    twin = "c-" + eid[2:]
                    if twin in claim_names:
                        hint = f"（{twin} 是 claim_id；应以真实 evidence id 引用其证据）"
                errors.append(f"claims.csv[{cid}]: 引用不存在的反证 {eid}{hint}")
            elif eid.startswith("c-"):
                errors.append(
                    f"claims.csv[{cid}]: counter_evidence_ids 中出现 claim 前缀的 id {eid}"
                )
        _parse_date(row.get("as_of", ""), where=f"claims.csv[{cid}].as_of")
        if row.get("claim_type") == "prediction" and not (row.get("derivation") or "").strip():
            errors.append(f"claims.csv[{cid}]: prediction 缺少 derivation（不变量 C2）")
        # SKU 枚举校验。unspecified 合法，但它是一个可统计的欠账状态，
        # 故这里只拒绝非法值，并把 unspecified 计入 stats 对外暴露。
        sku = (row.get("sku") or "").strip().lower()
        if sku and sku not in SKU_VALUES:
            errors.append(
                f"claims.csv[{cid}]: 非法 sku {sku!r}（允许 {sorted(SKU_VALUES)}）"
            )
        elif sku == "unspecified":
            sku_unspecified += 1

        # facets：主题无关的维度标注，替代写死的 sku。
        # 约定：facets 里出现 unspecified 同样计入欠账统计（与 sku 口径一致），
        # 这样换主题后「没写明条件的断言有多少」依然可测。
        raw_facets = (row.get("facets") or "").strip()
        if raw_facets:
            try:
                parsed = json.loads(raw_facets)
            except json.JSONDecodeError:
                errors.append(
                    f"claims.csv[{cid}]: facets 不是合法 JSON（{raw_facets[:40]!r}）"
                )
                parsed = None
            # 只有成功解析且确实是对象时才继续校验内部；
            # 解析失败已在上面报错，不再重复报「必须是对象」。
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if not re.fullmatch(r"[a-z][a-z0-9_]*", str(k)):
                        errors.append(
                            f"claims.csv[{cid}]: facets 键 {k!r} 不合规"
                            "（须为小写字母开头的 [a-z0-9_]）"
                        )
                    if not isinstance(v, str) or not v:
                        errors.append(
                            f"claims.csv[{cid}]: facets[{k!r}] 须为非空字符串"
                        )
                    elif v == "unspecified":
                        sku_unspecified += 1
            elif parsed is not None:
                errors.append(f"claims.csv[{cid}]: facets 必须是 JSON 对象")

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

    # 不变量 C3：disputed 主张必须给出反证（冲突并列，不单方断言）。
    c3_violations: list[str] = []
    for row in claims:
        if (row.get("confidence") or "").strip() != "disputed":
            continue
        cid = (row.get("claim_id") or "").strip()
        counters = [
            x.strip()
            for x in (row.get("counter_evidence_ids") or "").split(";")
            if x.strip()
        ]
        if not counters:
            c3_violations.append(cid)
            continue
        for ce in counters:
            if ce not in {r.get("evidence_id", "").strip() for r in evidence}:
                errors.append(
                    f"claims.csv[{cid}]: counter_evidence_ids 引用了不存在的 {ce}"
                )
    stats_extra["c3_violations"] = len(c3_violations)
    for cid in c3_violations:
        errors.append(
            f"claims.csv[{cid}]: confidence=disputed 但未给出 counter_evidence_ids"
            "（不变量 C3：冲突必须并列双方，不得单方断言）"
        )

    # 不变量 S2：access != open 的来源不得用于支撑 high/medium 主张。
    non_open = {
        (row.get("source_id") or "").strip()
        for row in sources
        if (row.get("access") or "open").strip() != "open"
    }
    if non_open:
        owner = {
            (row.get("evidence_id") or "").strip(): (row.get("source_id") or "").strip()
            for row in evidence
        }
        for row in claims:
            if (row.get("confidence") or "").strip() not in ("high", "medium"):
                continue
            cid = (row.get("claim_id") or "").strip()
            for e in [
                x.strip()
                for x in (row.get("evidence_ids") or "").split(";")
                if x.strip()
            ]:
                if owner.get(e) in non_open:
                    errors.append(
                        f"claims.csv[{cid}]: 用 access!=open 的来源 {owner[e]} 支撑 "
                        "high/medium 主张（不变量 S2）"
                    )

    # 不变量 R2：brief.yaml 的每个子问题必须有合法 status。
    brief_path = root / "brief.yaml"
    if brief_path.exists():
        brief_text = brief_path.read_text(encoding="utf-8")
        pairs = re.findall(
            r"id:\s*(q\d+)([\s\S]*?)(?=\n\s*- id:|\Z)", brief_text
        )
        r2_bad = 0
        for qid, body in pairs:
            m = re.search(r"status:\s*(\w+)", body)
            st = m.group(1) if m else ""
            if st not in ("answered", "partial", "unanswered"):
                errors.append(
                    f"brief.yaml[{qid}]: 非法 status {st!r}"
                    "（不变量 R2：必须为 answered/partial/unanswered）"
                )
                r2_bad += 1
        stats_extra["subquestions"] = len(pairs)
        stats_extra["r2_violations"] = r2_bad

    # 不变量 C1：confidence=high 需要至少一条 trust_tier=primary 的 supports 证据。
    # 强制阻断。若无一手证据，正确做法是补证据或降为 medium，而不是放宽规则。
    evidence_owner: dict[str, str] = {}
    evidence_stance: dict[str, str] = {}
    for row in evidence:
        eid = (row.get("evidence_id") or "").strip()
        evidence_owner[eid] = (row.get("source_id") or "").strip()
        evidence_stance[eid] = (row.get("stance") or "").strip()
    source_tier = {
        (row.get("source_id") or "").strip(): (row.get("trust_tier") or "").strip()
        for row in sources
    }

    c1_violations: list[str] = []
    for row in claims:
        if (row.get("confidence") or "").strip() != "high":
            continue
        cid = (row.get("claim_id") or "").strip()
        eids = [x.strip() for x in (row.get("evidence_ids") or "").split(";") if x.strip()]
        ok = any(
            source_tier.get(evidence_owner.get(e, "")) == "primary"
            and evidence_stance.get(e) == "supports"
            for e in eids
        )
        if not ok:
            c1_violations.append(cid)
    stats_extra["c1_violations"] = len(c1_violations)
    stats_extra["sku_unspecified"] = sku_unspecified
    for cid in c1_violations:
        errors.append(
            f"claims.csv[{cid}]: confidence=high 但缺少 trust_tier=primary 的 supports 证据"
            "（不变量 C1；请补一手证据，或将置信度降为 medium）"
        )

    # ---------------- ADR-0002 的内容完整性不变量：S1 / D1 / E1 ----------------
    # 这三条原先只检查「字段非空」，与 ADR 写明的语义不符：
    #   S1 要求「必填且带时区」——非空不保证带时区
    #   D1 要求「改版新增记录、不覆盖」——原先完全没实现
    #   E1 要求「quote 是原文子串」——非空不代表是原文
    # 实现放在 invariants.py，此处只做汇总，避免本文件继续膨胀。
    inv_errors, s1_ok = invariants.check_s1_timezone(sources)
    errors.extend(inv_errors)

    d1_errors, d1_docs = invariants.check_d1_versions(root)
    errors.extend(d1_errors)

    e1_errors, e1_checked, e1_unverifiable = invariants.check_e1_substring(
        root, evidence
    )
    errors.extend(e1_errors)

    stats_extra["s1_with_tz"] = s1_ok
    stats_extra["d1_documents"] = d1_docs
    stats_extra["e1_checked"] = e1_checked
    # e1_unverifiable 单独统计：没有快照不是「通过」，而是「没查」。
    # 把它混进通过数会把缺口伪装成合格。
    stats_extra["e1_unverifiable"] = e1_unverifiable

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


def format_coverage_warnings(stats: dict[str, int]) -> list[str]:
    """把「检查未执行 / 未覆盖」翻译成人能看懂的警告行。

    单独成函数，是因为 validate.py 的 main 与 scripts/validate_research.py
    都要用它。各写一份必然漂移，而这里漂移的后果是
    「一个归档默默不检查却显示 OK」——不该有两套说法。
    """
    out: list[str] = []
    checked = stats.get("e1_checked", 0)
    unchecked = stats.get("e1_unverifiable", 0)
    if checked == 0 and unchecked > 0:
        out.append(
            f"[!] E1 未执行：{unchecked} 条证据没有可比对的文档快照。"
        )
        out.append("    这不等于通过——quote 是否为原文子串尚未验证。")
        out.append("    补快照：见 services/ingestion 与 ADR-0002。")
    elif unchecked:
        out.append(
            f"[!] E1 部分未覆盖：{unchecked} 条证据无快照（已校验 {checked} 条）"
        )
    return out


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
            # 「无法校验」必须显式喊出来，不能只在统计串里当一个小数字。
            # 否则一个没有任何快照的归档会安静地显示 [OK]，
            # 而它几千条证据的 E1 其实一条都没验过——
            # 这正是「把缺口伪装成合格」，比报错更危险。
            for w in format_coverage_warnings(stats):
                print("       " + w)
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
