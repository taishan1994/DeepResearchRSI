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
Stance = Literal["supports", "refutes", "context"]
QuestionStatus = Literal["answered", "partial", "unanswered"]


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
