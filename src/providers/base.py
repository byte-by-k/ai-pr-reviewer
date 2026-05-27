"""
Abstract PR provider — platform-agnostic interface for fetching diffs
and posting review comments.

Implement this for any DevOps platform: Azure DevOps, GitHub, GitLab, Bitbucket.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FileDiff:
    """Represents a single changed file in a PR."""
    path: str
    hunks: List[str]          # raw unified diff hunks
    is_new_file: bool = False
    is_deleted: bool = False


@dataclass
class PRMetadata:
    pr_id: str
    title: str
    description: Optional[str]
    author: str
    target_branch: str
    source_branch: str


@dataclass
class ReviewComment:
    file_path: str
    line: int
    rule_id: str
    severity: str
    comment: str


class PRProvider(ABC):
    """
    Abstract interface every platform adapter must implement.
    The review agent calls only these methods — it never imports
    platform-specific code directly.
    """

    @abstractmethod
    def get_metadata(self, pr_id: str) -> PRMetadata:
        """Return title, author, branches for the given PR."""

    @abstractmethod
    def get_diff(self, pr_id: str) -> List[FileDiff]:
        """Return a list of file diffs for the given PR."""

    @abstractmethod
    def post_comments(self, pr_id: str, comments: List[ReviewComment]) -> None:
        """Post review comments back to the PR."""

    @abstractmethod
    def approve(self, pr_id: str) -> None:
        """Approve the PR (called when no issues found)."""

    @abstractmethod
    def request_changes(self, pr_id: str, summary: str) -> None:
        """Request changes with an overall summary comment."""
