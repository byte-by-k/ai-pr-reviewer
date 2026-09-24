import pytest
from pydantic import ValidationError

from src.multi_agent.models import ReviewFinding


def test_finding_rejects_unknown_severity():
    with pytest.raises(ValidationError):
        ReviewFinding(
            agent="security", category="security", severity="urgent", confidence="high",
            title="Secret", explanation="A secret is present", file_path="app.py",
            evidence="token = x", recommendation="Use an environment variable",
        )
