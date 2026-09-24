"""Anthropic adapter isolated behind a testable reviewer protocol."""

from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import Protocol

import anthropic

from src.multi_agent.models import AgentReview
from src.multi_agent.prompts import HUMAN_PROMPT, SYSTEM_PROMPT, ReviewerSpec
from src.providers.base import PRMetadata
from src.rules.loader import Rule

log = logging.getLogger(__name__)


class ReviewModel(Protocol):
    def review_hunk(
        self,
        spec: ReviewerSpec,
        metadata: PRMetadata,
        file_path: str,
        diff: str,
        rules: list[Rule],
    ) -> AgentReview: ...


class AnthropicReviewModel:
    def __init__(self, model: str = "claude-sonnet-4-5", client=None):
        self._model = model
        self._client = client or anthropic.Anthropic(timeout=60.0, max_retries=2)

    def review_hunk(
        self,
        spec: ReviewerSpec,
        metadata: PRMetadata,
        file_path: str,
        diff: str,
        rules: list[Rule],
    ) -> AgentReview:
        system = SYSTEM_PROMPT.format(agent_name=spec.name, focus=spec.focus)
        prompt = HUMAN_PROMPT.format(
            title=metadata.title,
            author=metadata.author,
            description=metadata.description or "Not provided",
            file_path=file_path,
            rules="\n\n".join(rule.to_prompt_text() for rule in rules),
            diff=diff[:8000],
            agent_name=spec.name,
        )
        raw = self._request(system, prompt)
        try:
            return self._parse_review(raw, spec.name)
        except (JSONDecodeError, ValueError) as first_error:
            # A single bounded repair attempt handles prose, malformed JSON, and
            # schema drift without silently accepting an unvalidated response.
            log.warning(
                "Invalid %s reviewer response (%s); retrying once.",
                spec.name,
                type(first_error).__name__,
            )
            repair_prompt = (
                f"{prompt}\n\n"
                "CORRECTION: Your previous response did not validate against the required "
                "AgentReview schema. Return a complete corrected JSON object only. Do not "
                "include Markdown or explanatory prose."
            )
            repaired = self._request(system, repair_prompt)
            try:
                return self._parse_review(repaired, spec.name)
            except (JSONDecodeError, ValueError) as final_error:
                log.error(
                    "The %s reviewer returned invalid structured output after one retry (%s).",
                    spec.name,
                    type(final_error).__name__,
                )
                return AgentReview(
                    agent=spec.name,
                    summary="Reviewer returned invalid structured output after one retry.",
                )

    def _request(self, system: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=3000,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", "text") == "text" and hasattr(block, "text")
        ]
        if not text_blocks:
            raise ValueError("Model response did not contain a text block")
        return "\n".join(text_blocks).strip()

    @staticmethod
    def _parse_review(raw: str, expected_agent: str) -> AgentReview:
        """Extract one JSON object and validate its complete Pydantic contract."""
        candidate = raw.strip()
        if candidate.startswith("```"):
            parts = candidate.split("```", 2)
            if len(parts) >= 2:
                candidate = parts[1].removeprefix("json").strip()

        start = candidate.find("{")
        if start < 0:
            raise JSONDecodeError("No JSON object found", candidate, 0)
        payload, _ = json.JSONDecoder().raw_decode(candidate[start:])
        review = AgentReview.model_validate(payload)
        if review.agent != expected_agent:
            raise ValueError(
                f"Expected agent {expected_agent!r}, received {review.agent!r}"
            )
        for finding in review.findings:
            if finding.agent != expected_agent:
                raise ValueError(
                    f"Finding agent {finding.agent!r} does not match {expected_agent!r}"
                )
        return review
