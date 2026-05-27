"""
CLI entrypoint for ai-pr-reviewer.

Usage:
    # Embed rules into ChromaDB (run once, or when rules change)
    python -m src.cli embed-rules

    # Review a PR
    python -m src.cli review --provider azure --pr-id 42
    python -m src.cli review --provider github --pr-id 123
"""

import logging
import click
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


RULES_FILE = Path(__file__).parent.parent / "codereviewrules.yaml"
CHROMA_DIR = ".chroma"


@click.group()
def cli():
    """AI-powered, DevOps-agnostic PR code reviewer."""


@cli.command("embed-rules")
@click.option("--rules-file", default=str(RULES_FILE), show_default=True)
@click.option("--chroma-dir", default=CHROMA_DIR, show_default=True)
@click.option("--force", is_flag=True, help="Re-embed even if rules already exist.")
def embed_rules(rules_file: str, chroma_dir: str, force: bool):
    """Parse codereviewrules.yaml and embed rules into ChromaDB."""
    from src.rules.loader import load_rules
    from src.vector_store.chroma_store import RuleVectorStore

    rules = load_rules(rules_file)
    click.echo(f"Loaded {len(rules)} rules from {rules_file}")

    store = RuleVectorStore(persist_dir=chroma_dir)
    store.embed_rules(rules, force_refresh=force)
    click.echo(f"ChromaDB now contains {store.count()} embedded rules.")


@cli.command("review")
@click.option("--provider", type=click.Choice(["azure", "github", "gitlab"]), required=True)
@click.option("--pr-id", required=True, help="PR / MR number")
@click.option("--rules-file", default=str(RULES_FILE), show_default=True)
@click.option("--chroma-dir", default=CHROMA_DIR, show_default=True)
@click.option("--model", default="claude-sonnet-4-5", show_default=True)
@click.option("--top-k", default=5, show_default=True, help="Rules retrieved per diff chunk.")
def review(provider: str, pr_id: str, rules_file: str, chroma_dir: str, model: str, top_k: int):
    """Run an AI code review on a pull request."""
    from src.rules.loader import load_rules
    from src.vector_store.chroma_store import RuleVectorStore
    from src.agent.reviewer import PRReviewAgent

    rules = load_rules(rules_file)
    store = RuleVectorStore(persist_dir=chroma_dir)

    if store.count() == 0:
        click.echo("ChromaDB is empty. Run `embed-rules` first.", err=True)
        raise SystemExit(1)

    pr_provider = _build_provider(provider)
    agent = PRReviewAgent(
        provider=pr_provider,
        vector_store=store,
        rules=rules,
        model=model,
        top_k_rules=top_k,
    )

    click.echo(f"Reviewing PR #{pr_id} via {provider}...")
    agent.review(pr_id)
    click.echo("Done.")


def _build_provider(name: str):
    if name == "azure":
        from src.providers.azure_devops import AzureDevOpsPRProvider
        return AzureDevOpsPRProvider()
    elif name == "github":
        from src.providers.github_provider import GitHubPRProvider
        return GitHubPRProvider()
    else:
        raise ValueError(f"Provider '{name}' not yet implemented.")


if __name__ == "__main__":
    cli()
