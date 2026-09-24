from types import SimpleNamespace

from src.multi_agent.client import AnthropicReviewModel
from src.multi_agent.prompts import REVIEWER_SPECS
from src.providers.base import PRMetadata


VALID_CORRECTNESS_REVIEW = """{
  "agent": "correctness",
  "summary": "Found a division-by-zero risk.",
  "findings": [{
    "agent": "correctness",
    "category": "correctness",
    "severity": "high",
    "confidence": "high",
    "title": "Division by zero",
    "explanation": "Zero orders cause a runtime exception.",
    "file_path": "sample.py",
    "line": 4,
    "evidence": "return total / count",
    "recommendation": "Reject a zero count.",
    "suggested_test": "Test count equal to zero.",
    "matched_rule_ids": []
  }]
}"""


class FakeMessages:
    def __init__(self, responses: list[str]):
        self.responses = iter(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=next(self.responses))]
        )


def metadata() -> PRMetadata:
    return PRMetadata("1", "Sample", None, "dev", "main", "feature")


def test_parser_accepts_json_inside_markdown_fence():
    parsed = AnthropicReviewModel._parse_review(
        f"```json\n{VALID_CORRECTNESS_REVIEW}\n```",
        "correctness",
    )
    assert parsed.agent == "correctness"
    assert parsed.findings[0].title == "Division by zero"


def test_invalid_response_is_retried_once():
    messages = FakeMessages(["not json", VALID_CORRECTNESS_REVIEW])
    client = SimpleNamespace(messages=messages)
    model = AnthropicReviewModel(client=client)

    review = model.review_hunk(
        REVIEWER_SPECS["correctness"],
        metadata(),
        "sample.py",
        "+return total / count",
        [],
    )

    assert messages.calls == 2
    assert review.findings[0].title == "Division by zero"


def test_two_invalid_responses_return_safe_empty_review():
    messages = FakeMessages(["not json", "still not json"])
    client = SimpleNamespace(messages=messages)
    model = AnthropicReviewModel(client=client)

    review = model.review_hunk(
        REVIEWER_SPECS["testing"],
        metadata(),
        "sample.py",
        "+return total / count",
        [],
    )

    assert messages.calls == 2
    assert review.agent == "testing"
    assert review.findings == []
    assert "after one retry" in review.summary
