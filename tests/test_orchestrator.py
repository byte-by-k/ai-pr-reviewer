from src.multi_agent.models import AgentReview, ReviewFinding
from src.multi_agent.orchestrator import combine_reviews
from src.providers.base import PRMetadata


def finding(agent="security", severity="high"):
    return ReviewFinding(
        agent=agent, category="security", severity=severity, confidence="high",
        title="Hardcoded secret", explanation="Secret is committed", file_path="app.py",
        line=4, evidence="api_key = 'x'", recommendation="Use a secret manager",
        matched_rule_ids=["SEC-001"], contributing_agents=[agent],
    )


def metadata():
    return PRMetadata("7", "Test PR", None, "dev", "main", "feature")


def test_combines_duplicate_findings_and_preserves_contributors():
    report = combine_reviews(metadata(), [
        AgentReview(agent="security", summary="Security", findings=[finding()]),
        AgentReview(agent="correctness", summary="Correctness", findings=[finding("correctness", "critical")]),
    ])
    assert len(report.findings) == 1
    assert report.findings[0].severity.value == "critical"
    assert set(report.findings[0].contributing_agents) == {"security", "correctness"}
    assert report.verdict == "request_changes"


def test_empty_review_is_approved():
    report = combine_reviews(metadata(), [])
    assert report.overall_risk == "none"
    assert report.verdict == "approve"
