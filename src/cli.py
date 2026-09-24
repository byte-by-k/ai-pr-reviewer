"""CLI entry point for legacy and Week 3 multi-agent review modes."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

RULES_FILE = Path(__file__).parent.parent / "codereviewrules.yaml"
CHROMA_DIR = ".chroma"


@click.group()
def cli():
    """AI-powered, DevOps-agnostic pull-request reviewer."""


@cli.command("embed-rules")
@click.option("--rules-file", default=str(RULES_FILE), show_default=True)
@click.option("--chroma-dir", default=CHROMA_DIR, show_default=True)
@click.option("--force", is_flag=True, help="Re-embed even if rules already exist.")
def embed_rules(rules_file: str, chroma_dir: str, force: bool):
    """Parse the YAML rulebook and embed rules in ChromaDB."""
    from src.rules.loader import load_rules
    from src.vector_store.chroma_store import RuleVectorStore

    rules = load_rules(rules_file)
    store = RuleVectorStore(persist_dir=chroma_dir)
    store.embed_rules(rules, force_refresh=force)
    click.echo(f"ChromaDB now contains {store.count()} embedded rules.")


@cli.command("review")
@click.option("--provider", type=click.Choice(["azure", "github"]), required=True)
@click.option("--pr-id", required=True, help="Pull-request number")
@click.option("--mode", type=click.Choice(["multi-agent", "legacy"]), default="multi-agent", show_default=True)
@click.option("--rules-file", default=str(RULES_FILE), show_default=True)
@click.option("--chroma-dir", default=CHROMA_DIR, show_default=True)
@click.option(
    "--model",
    default=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
    show_default="ANTHROPIC_MODEL or claude-sonnet-4-5",
)
@click.option("--top-k", default=5, type=click.IntRange(1, 20), show_default=True)
@click.option("--output", default="review-report.md", show_default=True)
@click.option("--publish", is_flag=True, help="Post comments and verdict. Default is report-only.")
def review(
    provider: str,
    pr_id: str,
    mode: str,
    rules_file: str,
    chroma_dir: str,
    model: str,
    top_k: int,
    output: str,
    publish: bool,
):
    """Review a pull request; report-only is the safe default."""
    from src.rules.loader import load_rules
    from src.vector_store.chroma_store import RuleVectorStore

    rules = load_rules(rules_file)
    store = RuleVectorStore(persist_dir=chroma_dir)
    if store.count() == 0:
        raise click.ClickException("ChromaDB is empty. Run `embed-rules` first.")
    pr_provider = _build_provider(provider)

    if mode == "legacy":
        if not publish:
            raise click.ClickException("Legacy mode posts directly; pass --publish or use multi-agent mode.")
        from src.agent.reviewer import PRReviewAgent

        PRReviewAgent(pr_provider, store, rules, model, top_k).review(pr_id)
        return

    from src.multi_agent.client import AnthropicReviewModel
    from src.multi_agent.service import MultiAgentReviewService

    service = MultiAgentReviewService(
        provider=pr_provider,
        store=store,
        rules=rules,
        model=AnthropicReviewModel(model=model),
        top_k=top_k,
    )
    report = service.review_to_file(pr_id, output)
    click.echo(f"Saved prioritized report to {output}")
    click.echo(f"Verdict: {report.verdict}; risk: {report.overall_risk}")
    if publish:
        service.publish(pr_id, report)
        click.echo("Published review to the pull request.")
    else:
        click.echo("Dry run complete; no pull-request comments or verdict were posted.")


def _build_provider(name: str):
    if name == "azure":
        from src.providers.azure_devops import AzureDevOpsPRProvider

        return AzureDevOpsPRProvider()
    if name == "github":
        from src.providers.github_provider import GitHubPRProvider

        return GitHubPRProvider()
    raise ValueError(f"Unsupported provider: {name}")


if __name__ == "__main__":
    cli()
