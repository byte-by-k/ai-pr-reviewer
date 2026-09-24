"""Score saved review reports against transparent, human-authored expectations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def score(expected: list[dict], actual: list[dict]) -> dict[str, float | int]:
    matched = 0
    for target in expected:
        if any(
            target["file_path"] == finding.get("file_path")
            and target["category"].lower() == finding.get("category", "").lower()
            and target["severity"] == finding.get("severity")
            for finding in actual
        ):
            matched += 1
    false_positives = max(0, len(actual) - matched)
    return {
        "expected_findings": len(expected),
        "detected_expected_findings": matched,
        "detection_rate": matched / len(expected) if expected else 1.0,
        "false_positive_count": false_positives,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True)
    parser.add_argument("--actual", required=True)
    args = parser.parse_args()
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))["expected_findings"]
    actual = json.loads(Path(args.actual).read_text(encoding="utf-8"))["findings"]
    print(json.dumps(score(expected, actual), indent=2))


if __name__ == "__main__":
    main()
