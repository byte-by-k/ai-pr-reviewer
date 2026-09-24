"""Specialized reviewer execution over pull-request diff hunks."""

from __future__ import annotations

import logging

from src.multi_agent.client import ReviewModel
from src.multi_agent.models import AgentReview, ReviewContext
from src.multi_agent.prompts import ReviewerSpec
from src.rules.loader import Rule

log = logging.getLogger(__name__)


class SpecialistReviewer:
    def __init__(self, spec: ReviewerSpec, store, rules: list[Rule], model: ReviewModel, top_k: int = 5):
        self.spec = spec
        self._store = store
        self._rules = {rule.id: rule for rule in rules}
        self._model = model
        self._top_k = top_k

    def review(self, context: ReviewContext) -> AgentReview:
        if self.spec.name == "testing":
            return self._review_test_coverage(context)

        findings = []
        summaries = []
        for file_diff in context.diffs:
            if file_diff.is_deleted:
                continue
            for hunk in file_diff.hunks:
                if not hunk.strip():
                    continue
                matches = self._store.query(
                    hunk,
                    top_k=self._top_k,
                    categories=self.spec.categories,
                )
                relevant = [self._rules[rule_id] for rule_id, _ in matches if rule_id in self._rules]
                if not relevant:
                    continue
                review = self._model.review_hunk(
                    self.spec, context.metadata, file_diff.path, hunk, relevant
                )
                for finding in review.findings:
                    finding.agent = self.spec.name
                    finding.file_path = finding.file_path or file_diff.path
                    finding.contributing_agents = [self.spec.name]
                findings.extend(review.findings)
                if review.summary:
                    summaries.append(review.summary)
        return AgentReview(
            agent=self.spec.name,
            summary=" ".join(dict.fromkeys(summaries)) or "No findings.",
            findings=findings,
        )

    def _review_test_coverage(self, context: ReviewContext) -> AgentReview:
        """Review production changes and their tests together as one PR-level unit."""
        sections = []
        for file_diff in context.diffs:
            if file_diff.is_deleted:
                continue
            for hunk in file_diff.hunks:
                if hunk.strip():
                    sections.append(f"FILE: {file_diff.path}\n{hunk}")
        if not sections:
            return AgentReview(agent=self.spec.name, summary="No reviewable changes.")

        combined_diff = "\n\n".join(sections)
        matches = self._store.query(
            combined_diff,
            top_k=self._top_k,
            categories=self.spec.categories,
        )
        relevant = [self._rules[rule_id] for rule_id, _ in matches if rule_id in self._rules]
        if not relevant:
            return AgentReview(agent=self.spec.name, summary="No applicable testing rules.")

        review = self._model.review_hunk(
            self.spec,
            context.metadata,
            "Multiple changed files",
            combined_diff,
            relevant,
        )
        for finding in review.findings:
            finding.agent = self.spec.name
            finding.contributing_agents = [self.spec.name]
        return review
