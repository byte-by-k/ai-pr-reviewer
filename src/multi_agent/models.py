"""Validated contracts shared by reviewers, orchestration, and reporting."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.providers.base import FileDiff, PRMetadata


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewFinding(BaseModel):
    """One evidence-backed issue reported by a specialist reviewer."""

    agent: Literal["correctness", "security", "testing"]
    category: str
    severity: Severity
    confidence: Confidence
    title: str = Field(min_length=3)
    explanation: str = Field(min_length=5)
    file_path: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1)
    recommendation: str = Field(min_length=3)
    suggested_test: str | None = None
    matched_rule_ids: list[str] = Field(default_factory=list)
    contributing_agents: list[str] = Field(default_factory=list)

    @field_validator("matched_rule_ids", "contributing_agents")
    @classmethod
    def unique_values(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class AgentReview(BaseModel):
    agent: Literal["correctness", "security", "testing"]
    summary: str
    findings: list[ReviewFinding] = Field(default_factory=list)


class ReviewContext(BaseModel):
    metadata: PRMetadata
    diffs: list[FileDiff]

    model_config = {"arbitrary_types_allowed": True}


class ReviewReport(BaseModel):
    pr_id: str
    title: str
    overall_risk: Literal["critical", "high", "medium", "low", "none"]
    verdict: Literal["approve", "comment", "request_changes"]
    executive_summary: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    agent_summaries: dict[str, str] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)

    @property
    def counts_by_severity(self) -> dict[str, int]:
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts
