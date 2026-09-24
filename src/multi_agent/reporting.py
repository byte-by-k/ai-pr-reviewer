"""Human-readable report rendering."""

from __future__ import annotations

from src.multi_agent.models import ReviewReport


def render_markdown(report: ReviewReport) -> str:
    counts = report.counts_by_severity
    lines = [
        "# Multi-Agent Code Review",
        "",
        f"**Pull request:** #{report.pr_id} — {report.title}",
        f"**Overall risk:** {report.overall_risk.upper()}",
        f"**Recommended verdict:** {report.verdict.replace('_', ' ').title()}",
        "",
        "## Executive summary",
        "",
        report.executive_summary,
        "",
        "| Critical | High | Medium | Low |",
        "|---:|---:|---:|---:|",
        f"| {counts['critical']} | {counts['high']} | {counts['medium']} | {counts['low']} |",
        "",
    ]
    for severity in ("critical", "high", "medium", "low"):
        findings = [finding for finding in report.findings if finding.severity.value == severity]
        if not findings:
            continue
        lines.extend([f"## {severity.title()} findings", ""])
        for finding in findings:
            location = finding.file_path + (f":{finding.line}" if finding.line else "")
            agents = ", ".join(finding.contributing_agents or [finding.agent])
            lines.extend(
                [
                    f"### {finding.title}",
                    "",
                    f"- **Location:** `{location}`",
                    f"- **Reviewer:** {agents}",
                    f"- **Confidence:** {finding.confidence.value.title()}",
                    f"- **Rules:** {', '.join(finding.matched_rule_ids) or 'No rule ID supplied'}",
                    "",
                    finding.explanation,
                    "",
                    f"**Evidence:** `{finding.evidence}`",
                    "",
                    f"**Recommendation:** {finding.recommendation}",
                    "",
                ]
            )
            if finding.suggested_test:
                lines.extend([f"**Suggested test:** {finding.suggested_test}", ""])

    lines.extend(["## Agent summaries", ""])
    for agent, summary in report.agent_summaries.items():
        lines.append(f"- **{agent.title()}:** {summary}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    return "\n".join(lines).rstrip() + "\n"
