"""
GitHub PR provider.

Required env vars:
    GITHUB_TOKEN    Personal Access Token with repo scope
    GITHUB_OWNER    e.g. my-org or my-username
    GITHUB_REPO     e.g. my-repo
"""

from __future__ import annotations
import os
from typing import List
import requests
from src.providers.base import PRProvider, PRMetadata, FileDiff, ReviewComment


class GitHubPRProvider(PRProvider):

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        timeout: float | None = None,
    ):
        self._token = token or os.environ["GITHUB_TOKEN"]
        self._owner = owner or os.environ["GITHUB_OWNER"]
        self._repo = repo or os.environ["GITHUB_REPO"]
        self._timeout = timeout or float(os.getenv("GITHUB_TIMEOUT", "30"))
        self._base = "https://api.github.com"
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get_metadata(self, pr_id: str) -> PRMetadata:
        data = self._get(f"/repos/{self._owner}/{self._repo}/pulls/{pr_id}")
        return PRMetadata(
            pr_id=pr_id,
            title=data["title"],
            description=data.get("body"),
            author=data["user"]["login"],
            target_branch=data["base"]["ref"],
            source_branch=data["head"]["ref"],
        )

    def get_diff(self, pr_id: str) -> List[FileDiff]:
        files = self._get(f"/repos/{self._owner}/{self._repo}/pulls/{pr_id}/files")
        diffs: List[FileDiff] = []
        for f in files:
            patch = f.get("patch", "")
            diffs.append(
                FileDiff(
                    path=f["filename"],
                    hunks=[patch] if patch else [],
                    is_new_file=(f["status"] == "added"),
                    is_deleted=(f["status"] == "removed"),
                )
            )
        return diffs

    def post_comments(self, pr_id: str, comments: List[ReviewComment]) -> None:
        pr_data = self._get(f"/repos/{self._owner}/{self._repo}/pulls/{pr_id}")
        commit_id = pr_data["head"]["sha"]
        for c in comments:
            url = f"/repos/{self._owner}/{self._repo}/pulls/{pr_id}/comments"
            self._session.post(
                self._base + url,
                json={
                    "body": self._format(c),
                    "commit_id": commit_id,
                    "path": c.file_path,
                    "line": c.line,
                    "side": "RIGHT",
                },
                timeout=self._timeout,
            ).raise_for_status()

    def approve(self, pr_id: str) -> None:
        # Always leave a visible clean-review result. A COMMENT event works for
        # both self-authored and third-party pull requests.
        self._submit_review(
            pr_id,
            event="COMMENT",
            body="No issues to report - Recommended for Approval",
        )

    def request_changes(self, pr_id: str, summary: str) -> None:
        self._submit_review(
            pr_id,
            event="REQUEST_CHANGES",
            body=f"**AI Review Summary**\n\n{summary}",
        )

    def comment(self, pr_id: str, summary: str) -> None:
        self._submit_review(
            pr_id,
            event="COMMENT",
            body=f"**AI Review Summary**\n\n{summary}",
        )

    def _submit_review(self, pr_id: str, event: str, body: str) -> None:
        """Submit a verdict, falling back to a comment for self-authored PRs."""
        url = f"{self._base}/repos/{self._owner}/{self._repo}/pulls/{pr_id}/reviews"
        response = self._session.post(
            url,
            json={"body": body, "event": event},
            timeout=self._timeout,
        )
        if response.status_code == 422 and "own pull request" in response.text.lower():
            fallback = self._session.post(
                url,
                json={
                    "body": f"{body}\n\n*GitHub does not allow authors to submit "
                    f"a `{event}` verdict on their own pull request, so this was "
                    "published as a non-blocking review comment.*",
                    "event": "COMMENT",
                },
                timeout=self._timeout,
            )
            fallback.raise_for_status()
            return
        response.raise_for_status()

    def _get(self, path: str) -> dict | list:
        resp = self._session.get(self._base + path, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _format(c: ReviewComment) -> str:
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(c.severity, "⚪")
        return f"{emoji} **[{c.rule_id}] {c.severity.upper()}**\n\n{c.comment}"
