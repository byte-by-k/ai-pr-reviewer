"""
Azure DevOps PR provider.

Required env vars:
    ADO_ORG         e.g. my-org
    ADO_PROJECT     e.g. my-project
    ADO_REPO        e.g. my-repo
    ADO_TOKEN       Personal Access Token with Code (Read) + PR (Read & Write)
"""

from __future__ import annotations
import os
import re
from typing import List
import requests
from src.providers.base import PRProvider, PRMetadata, FileDiff, ReviewComment


class AzureDevOpsPRProvider(PRProvider):

    def __init__(
        self,
        org: str | None = None,
        project: str | None = None,
        repo: str | None = None,
        token: str | None = None,
    ):
        self._org = org or os.environ["ADO_ORG"]
        self._project = project or os.environ["ADO_PROJECT"]
        self._repo = repo or os.environ["ADO_REPO"]
        self._token = token or os.environ["ADO_TOKEN"]
        self._base = (
            f"https://dev.azure.com/{self._org}/{self._project}/_apis"
        )
        self._session = requests.Session()
        self._session.auth = ("", self._token)
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # PRProvider interface
    # ------------------------------------------------------------------

    def get_metadata(self, pr_id: str) -> PRMetadata:
        url = f"{self._base}/git/repositories/{self._repo}/pullrequests/{pr_id}?api-version=7.1"
        data = self._get(url)
        return PRMetadata(
            pr_id=pr_id,
            title=data["title"],
            description=data.get("description"),
            author=data["createdBy"]["displayName"],
            target_branch=data["targetRefName"].replace("refs/heads/", ""),
            source_branch=data["sourceRefName"].replace("refs/heads/", ""),
        )

    def get_diff(self, pr_id: str) -> List[FileDiff]:
        url = (
            f"{self._base}/git/repositories/{self._repo}"
            f"/pullrequests/{pr_id}/iterations?api-version=7.1"
        )
        iterations = self._get(url)["value"]
        if not iterations:
            return []
        latest = iterations[-1]["id"]

        changes_url = (
            f"{self._base}/git/repositories/{self._repo}"
            f"/pullrequests/{pr_id}/iterations/{latest}/changes?api-version=7.1"
        )
        changes = self._get(changes_url)["changeEntries"]

        diffs: List[FileDiff] = []
        for change in changes:
            item = change.get("item", {})
            path = item.get("path", "")
            change_type = change.get("changeType", "")
            if not path or change_type == "delete":
                continue
            raw_diff = self._fetch_file_diff(pr_id, latest, path)
            hunks = _parse_hunks(raw_diff)
            diffs.append(
                FileDiff(
                    path=path,
                    hunks=hunks,
                    is_new_file=(change_type == "add"),
                )
            )
        return diffs

    def post_comments(self, pr_id: str, comments: List[ReviewComment]) -> None:
        for c in comments:
            url = (
                f"{self._base}/git/repositories/{self._repo}"
                f"/pullrequests/{pr_id}/threads?api-version=7.1"
            )
            body = {
                "comments": [{"parentCommentId": 0, "content": self._format(c), "commentType": 1}],
                "threadContext": {
                    "filePath": c.file_path,
                    "rightFileEnd": {"line": c.line, "offset": 1},
                    "rightFileStart": {"line": c.line, "offset": 1},
                },
                "status": "active",
            }
            self._session.post(url, json=body).raise_for_status()

    def approve(self, pr_id: str) -> None:
        reviewer_id = self._get_reviewer_id()
        url = (
            f"{self._base}/git/repositories/{self._repo}"
            f"/pullrequests/{pr_id}/reviewers/{reviewer_id}?api-version=7.1"
        )
        self._session.put(url, json={"vote": 10}).raise_for_status()

    def request_changes(self, pr_id: str, summary: str) -> None:
        url = (
            f"{self._base}/git/repositories/{self._repo}"
            f"/pullrequests/{pr_id}/threads?api-version=7.1"
        )
        body = {
            "comments": [{"parentCommentId": 0, "content": f"**AI Review Summary**\n\n{summary}", "commentType": 1}],
            "status": "active",
        }
        self._session.post(url, json=body).raise_for_status()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, url: str) -> dict:
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.json()

    def _get_reviewer_id(self) -> str:
        url = "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1"
        return self._get(url)["id"]

    def _fetch_file_diff(self, pr_id: str, iteration: int, path: str) -> str:
        url = (
            f"{self._base}/git/repositories/{self._repo}"
            f"/pullrequests/{pr_id}/iterations/{iteration}/changes?api-version=7.1"
        )
        # Return raw path for hunk parsing — actual content diff requires additional call
        return path

    @staticmethod
    def _format(c: ReviewComment) -> str:
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(c.severity, "⚪")
        return f"{emoji} **[{c.rule_id}] {c.severity.upper()}**\n\n{c.comment}"


def _parse_hunks(raw: str) -> List[str]:
    """Split a unified diff into individual hunks."""
    if not raw:
        return [raw]
    pattern = re.compile(r"(@@[^@@]+@@[^@@]*)", re.DOTALL)
    hunks = pattern.findall(raw)
    return hunks if hunks else [raw]
