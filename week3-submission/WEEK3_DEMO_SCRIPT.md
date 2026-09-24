# Week 3 Demo Script

Target duration: 4 minutes 30 seconds

## 0:00 to 0:35 Introduction

Hello, this is my Week 3 project, AI PR Reviewer, based on Project 3E. It is a multi-agent code review system for GitHub pull requests. It replaces a repetitive first-pass review by checking correctness, security, and test coverage in parallel, while keeping the final decision with a human reviewer.

## 0:35 to 1:15 Architecture

The CLI retrieves the pull-request metadata and diff from GitHub. Chroma retrieves relevant rules from my YAML code-review rulebook. LangGraph holds the review state and fans the work out to three specialist agents. The correctness agent looks for bugs and anti-patterns, the security agent looks for vulnerabilities, and the testing agent checks implementation and tests together. A deterministic orchestrator combines and prioritizes validated Pydantic findings.

The system is read-only by default. It creates a local report and does not write to GitHub unless I inspect the report and explicitly add the publish flag.

## 1:15 to 2:10 Live run

Show PR 1 in GitHub and explain that it is intentionally flawed and must not be merged.

Run:

```bash
python -m src.cli review --provider github --pr-id 1 --mode multi-agent --output review-report.md
```

While it runs, explain that each specialist receives only its relevant retrieved rules and must return evidence-backed structured JSON.

## 2:10 to 3:05 Report

Open `review-report.md`. Show the overall `Request Changes` verdict, severity table, and representative findings: SQL injection from security, division by zero or mutable default state from correctness, and missing boundary or security tests from testing. Point out the evidence, file location, recommendation, confidence, and suggested test.

Explain that this report is a recommendation. The CLI asks whether to post the review comments and defaults to No, preserving the human approval boundary. Show the existing comments on PR 1: violations appear inline with a final summary. Then show PR 2, where the clean result posts `No issues to report - Recommended for Approval`. Do not publish again during the recording because that would create duplicate comments.

## 3:05 to 3:50 Evaluation and iteration

Show the three evaluation PRs and `evaluation/EVALUATION_SUMMARY.md`. PR 1 contains mixed defects, PR 3 contains correctness and resilience defects, and PR 2 is a clean implementation with tests. The system produced the expected verdict for all three samples, including approving the clean PR.

Explain the iteration: the first testing agent reviewed files separately and incorrectly claimed the clean implementation lacked tests. I changed it to review implementation and tests together at PR level. This removed the false positive.

## 3:50 to 4:30 Reliability and conclusion

The model output is validated by Pydantic. Invalid JSON receives one repair retry, API operations have timeouts, and failure summaries remain visible. Pull-request content is treated as untrusted data to reduce prompt-injection risk. Publishing always leaves a visible result, and `--publish` supports deliberate non-interactive execution while the default path asks for confirmation. Seventeen automated tests pass.

The main limitation is that analysis is diff-only and AI severity still needs human judgment. The project demonstrates multi-agent delegation, LangGraph state, retrieval, structured output, error recovery, evaluation, and a deliberate human approval boundary.

## Recording checklist

- Keep the terminal font large enough to read.
- Hide `.env`, API keys, browser bookmarks, and personal notifications.
- Open PR 1, the architecture section, and the report before recording.
- Activate `.venv` and run `python -m src.cli embed-rules` before recording.
- Do not add `--publish` during the live run; answer No when the CLI asks to post comments.
- Keep the recording under five minutes.
- Upload the video and paste its share link into the submission form.
