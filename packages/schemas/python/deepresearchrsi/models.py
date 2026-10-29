"""数据类定义。字段与 docs/data-model.md、packages/schemas/json/*.schema.json 一一对应。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional

SourceType = Literal[
    "official", "vendor", "review", "academic", "community", "press", "retail"
]
TrustTier = Literal["primary", "secondary", "tertiary"]
Access = Literal["open", "paywalled", "blocked", "login_required"]
ClaimType = Literal["spec", "measurement", "price", "attribution", "prediction"]
Confidence = Literal["high", "medium", "low", "disputed"]
# RTX PRO 6000 有 WS / MQ / SE 三个 SKU；unspecified 表示来源没写明，
# 是一个需要偿还的欠账状态，不是一个中性的默认值。
Sku = Literal[
    "ws", "mq", "se", "all", "na", "unspecified",
    "mq+ws", "se+ws", "mq+se", "mq+se+ws",
]
Stance = Literal["supports", "refutes", "context"]
QuestionStatus = Literal["answered", "partial", "unanswered"]
StopReason = Literal["answered", "budget_exhausted", "gap_remaining", "error"]
TraceKind = Literal[
    "search",
    "fetch",
    "fetch_failed",
    "extract",
    "claim_added",
    "claim_revised",
    "claim_dropped",
    "gap_declared",
    "section_written",
    "validate",
]
TraceOutcome = Literal["ok", "partial", "blocked", "superseded"]


@dataclass(slots=True)
class Source:
    source_id: str
    url: str
    source_type: SourceType
    trust_tier: TrustTier
    fetched_at: datetime
    publisher: str = ""
    title: str = ""
    published_at: Optional[date] = None
    updated_at: Optional[date] = None
    language: str = "en"
    access: Access = "open"
    license: Optional[str] = None
    doi: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.source_id.startswith("src-"):
            raise ValueError(f"source_id must start with 'src-': {self.source_id}")
        if self.fetched_at.tzinfo is None:
            raise ValueError(f"{self.source_id}: fetched_at must be timezone-aware (invariant S1)")


@dataclass(slots=True)
class Evidence:
    evidence_id: str
    document_id: str
    quote: str
    locator: str
    stance: Stance = "supports"
    extracted_by: str = "manual"

    def __post_init__(self) -> None:
        if not self.evidence_id.startswith("e-"):
            raise ValueError(f"evidence_id must start with 'e-': {self.evidence_id}")
        if not self.quote.strip():
            raise ValueError(f"{self.evidence_id}: quote must be a verbatim non-empty excerpt")


@dataclass(slots=True)
class Claim:
    claim_id: str
    statement: str
    claim_type: ClaimType
    as_of: date
    confidence: Confidence
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_ids: list[str] = field(default_factory=list)
    derivation: Optional[str] = None
    notes: Optional[str] = None
    sku: Sku = "na"

    def __post_init__(self) -> None:
        if not self.claim_id.startswith("c-"):
            raise ValueError(f"claim_id must start with 'c-': {self.claim_id}")
        if not self.evidence_ids:
            raise ValueError(f"{self.claim_id}: at least one evidence_id is required")
        if self.claim_type == "prediction" and not self.derivation:
            raise ValueError(f"{self.claim_id}: prediction claims require a derivation (invariant C2)")


@dataclass(slots=True)
class SubQuestion:
    id: str
    question: str
    done_when: str
    expected_evidence: str = ""
    status: QuestionStatus = "unanswered"


@dataclass(slots=True)
class Brief:
    question: str
    as_of: date
    deliverable: str
    subquestions: list[SubQuestion]
    scope: dict[str, str] = field(default_factory=dict)
    freshness: str = "30d"
    constraints: dict = field(default_factory=dict)
    exclusions: list[str] = field(default_factory=list)

    def coverage(self) -> dict[str, int]:
        """按状态统计子问题覆盖率，供报告页与评测使用。"""
        counts = {"answered": 0, "partial": 0, "unanswered": 0}
        for sq in self.subquestions:
            counts[sq.status] += 1
        return counts


@dataclass(slots=True)
class TraceEvent:
    """一次可观察的动作及其后果。seq 必须在同一 run 内唯一且递增。"""

    seq: int
    kind: TraceKind
    summary: str
    target: Optional[str] = None
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    outcome: Optional[TraceOutcome] = None
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if self.seq < 1:
            raise ValueError(f"trace seq must be >= 1: {self.seq}")
        if not self.summary.strip():
            raise ValueError(f"trace seq={self.seq}: summary must not be empty")
        for sid in self.source_ids:
            if not sid.startswith("src-"):
                raise ValueError(f"trace seq={self.seq}: bad source_id {sid!r}")
        for eid in self.evidence_ids:
            if not eid.startswith("e-"):
                raise ValueError(f"trace seq={self.seq}: bad evidence_id {eid!r}")
        for cid in self.claim_ids:
            if not cid.startswith("c-"):
                raise ValueError(f"trace seq={self.seq}: bad claim_id {cid!r}")


@dataclass(slots=True)
class Budget:
    limits: dict[str, int] = field(default_factory=dict)
    used: dict[str, float] = field(default_factory=dict)

    def exhausted(self) -> bool:
        """任一受限维度达到上限即视为耗尽。未设上限的维度不参与判断。"""
        for key, limit in self.limits.items():
            if key == "max_tool_calls" and self.used.get("tool_calls", 0) >= limit:
                return True
            if key == "max_minutes" and self.used.get("minutes", 0) >= limit:
                return True
        return False


@dataclass(slots=True)
class ResearchRun:
    """一次研究运行的完整记录（阶段 1 验收门槛「轨迹可看」的载体）。

    不变量 R1：stop_reason 必填；budget_exhausted / gap_remaining 时
    stop_note 必须说明未解决的部分，不得静默截断。
    """

    run_id: str
    as_of: date
    stop_reason: StopReason
    budget: Budget
    trace: list[TraceEvent]
    slug: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    plan_version: int = 1
    report_version: int = 1
    stop_note: Optional[str] = None
    eval: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.startswith("run-"):
            raise ValueError(f"run_id must start with 'run-': {self.run_id}")
        if self.stop_reason in ("budget_exhausted", "gap_remaining") and not self.stop_note:
            raise ValueError(
                f"{self.run_id}: stop_reason={self.stop_reason} requires stop_note "
                "listing what remains unresolved (invariant R1)"
            )
        seqs = [e.seq for e in self.trace]
        if seqs != sorted(seqs):
            raise ValueError(f"{self.run_id}: trace seq must be ascending")
        if len(seqs) != len(set(seqs)):
            raise ValueError(f"{self.run_id}: trace seq must be unique")

    def counts_by_kind(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.trace:
            out[e.kind] = out.get(e.kind, 0) + 1
        return out
