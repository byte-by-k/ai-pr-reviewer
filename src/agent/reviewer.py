"""
Core AI review agent.

Flow:
  1. Load PR diff via PRProvider
  2. For each diff chunk, query ChromaDB for the top-K relevant rules
  3. Send [diff + rules] to Claude and parse structured review comments
  4. Post comments back via PRProvider
"""

from __future__ import annotations
import json
import logging
from typing import List, Dict

import anthropic

from src.providers.base import PRProvider, ReviewComment, FileDiff
from src.rules.loader import Rule
from src.vector_store.chroma_store import RuleVectorStore
from src.agent.prompts import SYSTEM_PROMPT, build_review_prompt

log = logging.getLogger(__name__)


class PRReviewAgent:
    """
    Platform-agnostic AI code review agent.

    Args:
        provider:       Any PRProvider implementation (Azure DevOps, GitHub, ...)
        vector_store:   Populated RuleVectorStore
        rules:          Full list of Rule objects (keyed by id for lookup)
        model:          Anthropic model to use
        top_k_rules:    How many rules to retrieve per diff chunk
    """

    def __init__(
        self,
        provider: PRProvider,
        vector_store: RuleVectorStore,
        rules: List[Rule],
        model: str = "claude-sonnet-4-5",
        top_k_rules: int = 5,
    ):
        self._provider = provider
        self._store = vector_store
        self._rules: Dict[str, Rule] = {r.id: r for r in rules}
        self._model = model
        self._top_k = top_k_rules
        self._client = anthropic.Anthropic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(self, pr_id: str) -> None:
        """
        Run a full review on the given PR and post the results.
        """
        metadata = self._provider.get_metadata(pr_id)
        log.info("Reviewing PR #%s: %s by %s", pr_id, metadata.title, metadata.author)

        diffs = self._provider.get_diff(pr_id)
        if not diffs:
            log.info("No diff found for PR #%s — skipping.", pr_id)
            return

        all_comments: List[ReviewComment] = []
        summary_parts: List[str] = []

        for file_diff in diffs:
            if file_diff.is_deleted:
                continue
            comments, summary = self._review_file(metadata, file_diff)
            all_comments.extend(comments)
            if summary:
                summary_parts.append(f"**{file_diff.path}**: {summary}")

        overall_summary = "\n\n".join(summary_parts) if summary_parts else "No issues found."

        if all_comments:
            self._provider.post_comments(pr_id, all_comments)
            self._provider.request_changes(pr_id, overall_summary)
            log.info("Posted %d comments on PR #%s.", len(all_comments), pr_id)
        else:
            self._provider.approve(pr_id)
            log.info("PR #%s approved — no rule violations found.", pr_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _review_file(
        self, metadata, file_diff: FileDiff
    ) -> tuple[List[ReviewComment], str]:
        """Review all hunks in a single file."""
        all_comments: List[ReviewComment] = []
        summaries: List[str] = []

        for hunk in file_diff.hunks:
            if not hunk.strip():
                continue
            try:
                comments, summary = self._review_hunk(metadata, file_diff.path, hunk)
                all_comments.extend(comments)
                if summary:
                    summaries.append(summary)
            except Exception as e:
                log.warning("Failed to review hunk in %s: %s", file_diff.path, e)

        return all_comments, " ".join(summaries)

    def _review_hunk(
        self, metadata, file_path: str, hunk: str
    ) -> tuple[List[ReviewComment], str]:
        """Query ChromaDB for relevant rules, then ask Claude to review the hunk."""
        # 1. Retrieve relevant rules
        matched_ids = self._store.query(hunk, top_k=self._top_k)
        relevant_rules = [
            self._rules[rule_id]
            for rule_id, _ in matched_ids
            if rule_id in self._rules
        ]

        if not relevant_rules:
            return [], ""

        rules_text = "\n\n".join(r.to_prompt_text() for r in relevant_rules)

        # 2. Build prompt
        prompt = build_review_prompt(
            pr_title=metadata.title,
            author=metadata.author,
            file_path=file_path,
            rules_text=rules_text,
            diff_chunk=hunk,
        )

        # 3. Call Claude
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()

        # 4. Parse structured response
        return self._parse_response(raw, file_path)

    def _parse_response(
        self, raw: str, file_path: str
    ) -> tuple[List[ReviewComment], str]:
        """Parse Claude's JSON response into ReviewComment objects."""
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as e:
            log.warning("Could not parse review JSON: %s\nRaw: %s", e, raw[:500])
            return [], ""

        comments = []
        for item in data.get("comments", []):
            comments.append(
                ReviewComment(
                    file_path=item.get("file_path", file_path),
                    line=int(item.get("line", 1)),
                    rule_id=item.get("rule_id", "UNKNOWN"),
                    severity=item.get("severity", "medium"),
                    comment=item.get("comment", ""),
                )
            )

        return comments, data.get("summary", "")
