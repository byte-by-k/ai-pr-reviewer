from unittest.mock import Mock

from src.providers.github_provider import GitHubPRProvider


def test_self_review_verdict_falls_back_to_comment():
    provider = GitHubPRProvider(
        token="test-token", owner="owner", repo="repo", timeout=1
    )
    rejected = Mock(status_code=422, text="Can not request changes on your own pull request")
    accepted = Mock(status_code=200, text="")
    provider._session.post = Mock(side_effect=[rejected, accepted])

    provider.request_changes("7", "Blocking findings were detected.")

    assert provider._session.post.call_count == 2
    fallback_payload = provider._session.post.call_args_list[1].kwargs["json"]
    assert fallback_payload["event"] == "COMMENT"
    accepted.raise_for_status.assert_called_once()
