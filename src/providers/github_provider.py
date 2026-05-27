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
    ):
        self._token = token or os.environ["GITHUB_TOKEN"]
        self._owner = owner or os.environ["GITHUB_OWNER"]
        self._repo = repo or os.environ["GITHUB_REPO"]
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
            ).raise_for_status()

    def approve(self, pr_id: str) -> None:
        self._session.post(
            f"{self._base}/repos/{self._owner}/{self._repo}/pulls/{pr_id}/reviews",
            json={"event": "APPROVE"},
        ).raise_for_status()

    def request_changes(self, pr_id: str, summary: str) -> None:
        self._session.post(
            f"{self._base}/repos/{self._owner}/{self._repo}/pulls/{pr_id}/reviews",
            json={"body": f"**AI Review Summary**\n\n{summary}", "event": "REQUEST_CHANGES"},
        ).raise_for_status()

    def _get(self, path: str) -> dict | list:
        resp = self._session.get(self._base + path)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _format(c: ReviewComment) -> str:
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(c.severity, "⚪")
        return f"{emoji} **[{c.rule_id}] {c.severity.upper()}**\n\n{c.comment}"
