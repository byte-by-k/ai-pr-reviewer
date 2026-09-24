from src.multi_agent.models import ReviewReport
from src.multi_agent.service import MultiAgentReviewService


class PublishingProvider:
    def __init__(self):
        self.actions = []

    def post_comments(self, pr_id, comments):
        self.actions.append(("findings", pr_id, len(comments)))

    def approve(self, pr_id):
        self.actions.append(("approve", pr_id))

    def request_changes(self, pr_id, summary):
        self.actions.append(("request_changes", pr_id, summary))

    def comment(self, pr_id, summary):
        self.actions.append(("comment", pr_id, summary))


def report(verdict: str) -> ReviewReport:
    return ReviewReport(
        pr_id="1",
        title="Sample",
        overall_risk="none" if verdict == "approve" else "medium",
        verdict=verdict,
        executive_summary="Review summary",
    )


def service_with(provider):
    service = MultiAgentReviewService.__new__(MultiAgentReviewService)
    service.provider = provider
    return service


def test_clean_report_publishes_approval_recommendation():
    provider = PublishingProvider()
    service_with(provider).publish("1", report("approve"))
    assert provider.actions == [("approve", "1")]


def test_non_blocking_violations_publish_summary_comment():
    provider = PublishingProvider()
    service_with(provider).publish("1", report("comment"))
    assert provider.actions == [("comment", "1", "Review summary")]


def test_blocking_violations_publish_request_changes_summary():
    provider = PublishingProvider()
    service_with(provider).publish("1", report("request_changes"))
    assert provider.actions == [("request_changes", "1", "Review summary")]
