from dataclasses import dataclass

from src.multi_agent.models import AgentReview, ReviewContext
from src.multi_agent.prompts import REVIEWER_SPECS
from src.multi_agent.reviewers import SpecialistReviewer
from src.providers.base import FileDiff, PRMetadata


@dataclass
class Rule:
    id: str = "TST-001"


class Store:
    def query(self, text, **kwargs):
        assert "FILE: src/shipping.py" in text
        assert "FILE: tests/test_shipping.py" in text
        return [("TST-001", 0.1)]


class Model:
    def __init__(self):
        self.calls = 0

    def review_hunk(self, spec, metadata, file_path, diff, rules):
        self.calls += 1
        assert file_path == "Multiple changed files"
        assert len(rules) == 1
        return AgentReview(agent="testing", summary="Coverage is adequate.")


def test_testing_reviewer_sees_implementation_and_tests_together():
    model = Model()
    reviewer = SpecialistReviewer(
        REVIEWER_SPECS["testing"], Store(), [Rule()], model
    )
    context = ReviewContext(
        metadata=PRMetadata("2", "Clean change", None, "dev", "main", "feature"),
        diffs=[
            FileDiff("src/shipping.py", ["+def calculate(): pass"]),
            FileDiff("tests/test_shipping.py", ["+def test_calculate(): pass"]),
        ],
    )

    result = reviewer.review(context)

    assert model.calls == 1
    assert result.summary == "Coverage is adequate."
    assert result.findings == []
