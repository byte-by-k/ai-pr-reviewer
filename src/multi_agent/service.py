"""Application service joining providers, reviewers, graph, and publication."""

from __future__ import annotations

import json
from pathlib import Path

from src.multi_agent.client import AnthropicReviewModel, ReviewModel
from src.multi_agent.graph import build_review_graph
from src.multi_agent.models import ReviewContext, ReviewReport
from src.multi_agent.prompts import REVIEWER_SPECS
from src.multi_agent.reporting import render_markdown
from src.multi_agent.reviewers import SpecialistReviewer
from src.providers.base import PRProvider, ReviewComment


class MultiAgentReviewService:
    def __init__(self, provider: PRProvider, store, rules, model: ReviewModel | None = None, top_k: int = 5):
        self.provider = provider
        review_model = model or AnthropicReviewModel()
        reviewers = {
            name: SpecialistReviewer(spec, store, rules, review_model, top_k)
            for name, spec in REVIEWER_SPECS.items()
        }
        self.graph = build_review_graph(reviewers)

    def review(self, pr_id: str) -> ReviewReport:
        context = ReviewContext(
            metadata=self.provider.get_metadata(pr_id),
            diffs=self.provider.get_diff(pr_id),
        )
        result = self.graph.invoke({"context": context, "agent_reviews": []})
        return result["report"]

    def review_to_file(self, pr_id: str, output: str | Path) -> ReviewReport:
        report = self.review(pr_id)
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".json":
            path.write_text(
                json.dumps(report.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
        else:
            path.write_text(render_markdown(report), encoding="utf-8")
        return report

    def publish(self, pr_id: str, report: ReviewReport) -> None:
        comments = [
            ReviewComment(
                file_path=finding.file_path,
                line=finding.line or 1,
                rule_id=",".join(finding.matched_rule_ids) or finding.category,
                severity=finding.severity.value,
                comment=f"{finding.title}\n\n{finding.explanation}\n\nRecommendation: {finding.recommendation}",
            )
            for finding in report.findings
            if finding.line is not None
        ]
        if comments:
            self.provider.post_comments(pr_id, comments)
        if report.verdict == "approve":
            self.provider.approve(pr_id)
        elif report.verdict == "request_changes":
            self.provider.request_changes(pr_id, report.executive_summary)
