"""LangGraph fan-out/fan-in workflow for three specialist reviewers."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from src.multi_agent.models import AgentReview, ReviewContext, ReviewReport
from src.multi_agent.orchestrator import combine_reviews


class ReviewState(TypedDict, total=False):
    context: ReviewContext
    agent_reviews: Annotated[list[AgentReview], operator.add]
    report: ReviewReport


def build_review_graph(reviewers: dict[str, object]):
    workflow = StateGraph(ReviewState)

    def prepare(state: ReviewState) -> ReviewState:
        if not state["context"].diffs:
            return {"agent_reviews": []}
        return {}

    def reviewer_node(name: str):
        def run(state: ReviewState) -> ReviewState:
            result = reviewers[name].review(state["context"])
            return {"agent_reviews": [result]}

        return run

    def aggregate(state: ReviewState) -> ReviewState:
        return {
            "report": combine_reviews(
                state["context"].metadata,
                state.get("agent_reviews", []),
            )
        }

    workflow.add_node("prepare_review", prepare)
    for name in ("correctness", "security", "testing"):
        workflow.add_node(f"review_{name}", reviewer_node(name))
    workflow.add_node("aggregate_and_prioritize", aggregate)
    workflow.add_edge(START, "prepare_review")
    specialist_nodes = ["review_correctness", "review_security", "review_testing"]
    for node in specialist_nodes:
        workflow.add_edge("prepare_review", node)
    workflow.add_edge(specialist_nodes, "aggregate_and_prioritize")
    workflow.add_edge("aggregate_and_prioritize", END)
    return workflow.compile()
