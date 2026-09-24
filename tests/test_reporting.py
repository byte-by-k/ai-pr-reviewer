import json

from src.multi_agent.models import AgentReview
from src.multi_agent.service import MultiAgentReviewService
from src.providers.base import FileDiff, PRMetadata


class Provider:
    def get_metadata(self, pr_id):
        return PRMetadata(pr_id, "Sample", None, "dev", "main", "feature")

    def get_diff(self, pr_id):
        return [FileDiff("app.py", ["+print('hello')"])]


class Store:
    def query(self, *args, **kwargs):
        return []


class Model:
    def review_hunk(self, *args, **kwargs):
        raise AssertionError("No rules means no model request")


def test_service_writes_json_report(tmp_path):
    service = MultiAgentReviewService(Provider(), Store(), [], Model())
    output = tmp_path / "report.json"
    report = service.review_to_file("3", output)
    saved = json.loads(output.read_text())
    assert report.verdict == "approve"
    assert saved["pr_id"] == "3"
    assert set(saved["agent_summaries"]) == {"correctness", "security", "testing"}
