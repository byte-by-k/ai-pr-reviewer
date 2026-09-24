"""Load and validate code-review rules from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class RuleExample:
    violation: Optional[str] = None
    compliant: Optional[str] = None


@dataclass
class Rule:
    id: str
    name: str
    category: str
    severity: str
    description: str
    examples: Optional[RuleExample] = None
    tags: List[str] = field(default_factory=list)

    def to_embedding_text(self) -> str:
        parts = [
            f"Rule: {self.name}",
            f"Category: {self.category}",
            f"Severity: {self.severity}",
            f"Description: {self.description.strip()}",
        ]
        if self.tags:
            parts.append(f"Tags: {', '.join(self.tags)}")
        if self.examples:
            if self.examples.violation:
                parts.append(f"Violation example:\n{self.examples.violation.strip()}")
            if self.examples.compliant:
                parts.append(f"Compliant example:\n{self.examples.compliant.strip()}")
        return "\n".join(parts)

    def to_prompt_text(self) -> str:
        lines = [f"[{self.id}] {self.name} (severity: {self.severity})"]
        lines.append(f"  {self.description.strip()}")
        if self.examples and self.examples.violation:
            lines.append(f"  Bad: {self.examples.violation.strip()[:200]}")
        return "\n".join(lines)


def load_rules(yaml_path: str | Path) -> List[Rule]:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules: List[Rule] = []
    for item in data.get("rules", []):
        raw_examples = item.get("examples")
        examples = None
        if raw_examples:
            examples = RuleExample(
                violation=raw_examples.get("violation"),
                compliant=raw_examples.get("compliant"),
            )
        rules.append(
            Rule(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                severity=item["severity"],
                description=item["description"],
                examples=examples,
                tags=item.get("tags", []),
            )
        )
    return rules
