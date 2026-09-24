"""Deterministic aggregation, deduplication, and priority policy."""

from __future__ import annotations

import re

from src.multi_agent.models import AgentReview, ReviewFinding, ReviewReport, Severity
from src.providers.base import PRMetadata


SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def _fingerprint(finding: ReviewFinding) -> tuple[str, int | None, str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", finding.title.lower()).strip()
    return finding.file_path.lower(), finding.line, normalized


def combine_reviews(metadata: PRMetadata, reviews: list[AgentReview]) -> ReviewReport:
    """Merge exact duplicates and apply a transparent severity-first policy."""
    unique: dict[tuple[str, int | None, str], ReviewFinding] = {}
    for review in reviews:
        for finding in review.findings:
            key = _fingerprint(finding)
            existing = unique.get(key)
            if existing is None:
                unique[key] = finding.model_copy(deep=True)
                continue
            existing.contributing_agents = list(
                dict.fromkeys([*existing.contributing_agents, finding.agent])
            )
            existing.matched_rule_ids = list(
                dict.fromkeys([*existing.matched_rule_ids, *finding.matched_rule_ids])
            )
            if SEVERITY_RANK[finding.severity] < SEVERITY_RANK[existing.severity]:
                existing.severity = finding.severity

    findings = sorted(
        unique.values(),
        key=lambda item: (
            SEVERITY_RANK[item.severity],
            item.file_path.lower(),
            item.line or 0,
            item.title.lower(),
        ),
    )
    if findings:
        overall_risk = findings[0].severity.value
        verdict = "request_changes" if findings[0].severity in {Severity.CRITICAL, Severity.HIGH} else "comment"
        summary = (
            f"{len(findings)} distinct finding(s) remained after combining "
            f"{len(reviews)} specialist reviews. Highest severity: {overall_risk}."
        )
    else:
        overall_risk = "none"
        verdict = "approve"
        summary = "The specialist reviewers found no evidence-backed issues in the supplied diff."

    return ReviewReport(
        pr_id=metadata.pr_id,
        title=metadata.title,
        overall_risk=overall_risk,
        verdict=verdict,
        executive_summary=summary,
        findings=findings,
        agent_summaries={review.agent: review.summary for review in reviews},
        limitations=[
            "This is static, diff-only AI review; unchanged repository context may be missing.",
            "Findings require human verification and do not replace security scanners or tests.",
            "Only project rules retrieved for each changed hunk are considered.",
        ],
    )
