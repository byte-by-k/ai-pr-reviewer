from src.multi_agent.graph import build_review_graph
from src.multi_agent.models import AgentReview, ReviewContext
from src.providers.base import FileDiff, PRMetadata


class FakeReviewer:
    def __init__(self, name):
        self.name = name

    def review(self, context):
        return AgentReview(agent=self.name, summary=f"{self.name} complete")


def test_graph_runs_all_three_reviewers():
    graph = build_review_graph({name: FakeReviewer(name) for name in ("correctness", "security", "testing")})
    context = ReviewContext(
        metadata=PRMetadata("1", "PR", None, "dev", "main", "feature"),
        diffs=[FileDiff(path="app.py", hunks=["+print('x')"])],
    )
    result = graph.invoke({"context": context, "agent_reviews": []})
    assert set(result["report"].agent_summaries) == {"correctness", "security", "testing"}
