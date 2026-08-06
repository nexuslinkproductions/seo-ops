"""Pydantic domain models for the seo-ops MVP.

All timestamps are UTC ISO-8601 strings. JSON-encoded list/dict fields are
kept as Python lists/dicts on the model and serialized by the store layer.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

EVIDENCE_KINDS = {
    "screenshot",
    "html_snapshot",
    "serp_snapshot",
    "llm_answer",
    "export_file",
    "note",
    "measurement",
}
SEVERITIES = {"critical", "high", "medium", "low"}
FINDING_CATEGORIES = {
    "technical",
    "content",
    "structured_data",
    "entity_geo",
    "analytics",
}
FINDING_STATUSES = {"open", "accepted", "dismissed", "resolved"}
CHANGE_STATUSES = {
    "proposed",
    "approved",
    "deployed",
    "verified",
    "rejected",
    "reverted",
}
FAMILIES = {"seo", "aeo", "geo", "analytics"}
SOURCE_FAMILIES = {"seo", "aeo", "geo", "analytics", "evidence", "changes"}


class ClientInfo(BaseModel):
    """Registry entry only: identity, domains, prompt set. No metrics."""

    id: str
    name: str
    created_at: str
    domains: list[str] = []
    geo_prompts: list[str] = []


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    family: Literal["seo", "aeo", "geo", "analytics"]
    name: str
    source: str
    grain: str
    formula: str
    freshness: str = "period"


class ImportBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_family: str
    source_name: str
    file_name: Optional[str] = None
    file_sha256: Optional[str] = None
    imported_at: str
    row_count: int
    rule: str


class RawRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    batch_id: str
    row_sha256: str
    row_date: Optional[str] = None
    source: str
    dimension_key: Optional[str] = None
    dimension_value: Optional[str] = None
    metric: str
    value: float
    payload: str


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    captured_at: str
    captured_by: str
    kind: str
    path: Optional[str] = None
    inline_text: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    source_description: Optional[str] = None
    related_query: Optional[str] = None
    related_url: Optional[str] = None
    related_prompt_id: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in EVIDENCE_KINDS:
            raise ValueError(f"unknown evidence kind: {v}")
        return v


class AuditFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: str
    category: str
    severity: str
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    evidence_ids: list[str] = []
    status: str = "open"

    @field_validator("category", "severity", "status")
    @classmethod
    def _bounded(cls, v: str, info) -> str:
        field = info.field_name
        allowed = {
            "category": FINDING_CATEGORIES,
            "severity": SEVERITIES,
            "status": FINDING_STATUSES,
        }[field]
        if v not in allowed:
            raise ValueError(f"invalid {field}: {v}")
        return v


class MeasurementWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pre_start: str
    pre_end: str
    post_start: str
    post_end: str


class ResultSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    metric: str
    pre_value: Optional[float] = None
    post_value: Optional[float] = None
    abs_delta: Optional[float] = None
    rel_delta: Optional[float] = None
    unit: str = ""


class ChangeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: str
    title: str
    description: Optional[str] = None
    scope_urls: list[str] = []
    status: str = "proposed"
    proposed_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    deployed_at: Optional[str] = None
    verified_at: Optional[str] = None
    pre_evidence_ids: list[str] = []
    post_evidence_ids: list[str] = []
    measurement_window: Optional[MeasurementWindow] = None
    result_summary: Optional[ResultSummary] = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in CHANGE_STATUSES:
            raise ValueError(f"invalid change status: {v}")
        return v


class Scorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    period_start: str
    period_end: str
    generated_at: str
    metrics_snapshot: dict
    highlights: list[str] = []
    changes_in_period: list[str] = []
    export_path: Optional[str] = None


class BacklogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: str
    title: str
    description: Optional[str] = None
    category: str = "content"
    impact: float
    effort: float
    score: float
    status: str = "open"
    evidence_ids: list[str] = []


class IntegrityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    subcommand: str
    checked: int
    clean: bool
    mismatches: list[dict] = []
    missing: list[dict] = []
    extra: list[dict] = []
    errors: list[str] = []

