# Week 3 Project Documentation

## Project overview

AI PR Reviewer is a LangGraph-based multi-agent code review system built for Project 3E. It helps software engineers review GitHub pull requests by delegating the same diff to three specialists: a correctness reviewer, a security reviewer, and a testing reviewer. A deterministic orchestrator combines their validated findings, removes exact duplicates, assigns an overall risk level, and writes a prioritized report. After generating the report, the CLI asks whether to publish and defaults to No. Supplying `--publish` bypasses the prompt and publishes immediately. A published review always leaves a visible result.

**Project one-liner:** My agent helps software engineering teams review pull requests in a command-line workflow, replacing repetitive manual bug, security, and test-coverage analysis. It retrieves code and project rules autonomously, hands off the final report to a human before any GitHub write, and succeeds when it produces a useful prioritized report across three representative pull requests.

## User and problem

The primary user is a software engineer, QA engineer, DevSecOps engineer, or technical lead. Manual pull-request review is time-consuming and inconsistent: reviewers can overlook boundary cases, security weaknesses, or missing tests while focusing on implementation details. The system supplies a consistent first pass while preserving human responsibility for accepting, rejecting, or publishing findings.

## Architecture and control flow

The CLI retrieves pull-request metadata and changed-file patches from GitHub. Chroma retrieves relevant rules from `codereviewrules.yaml`. LangGraph stores the pull-request context and runs three specialist nodes. The graph then aggregates their Pydantic-validated results into one severity-ranked report.

```text
GitHub pull request
        |
        v
Retrieve metadata and diff ---- Chroma rule retrieval
        |                              |
        +--------------+---------------+
                       v
              LangGraph review state
                 /      |      \
        correctness  security  testing
                 \      |      /
                  aggregate results
                       |
           deduplicate and prioritize
                       |
              Markdown or JSON report
                       |
              human approval boundary
                       |
             optional GitHub publishing
```

## Agent responsibilities

The correctness specialist finds concrete bugs, edge-case failures, performance defects, resilience problems, and maintainability anti-patterns. The security specialist finds secrets, injection weaknesses, unsafe trust boundaries, and sensitive-data risks. The testing specialist evaluates the complete pull request, including implementation and test files together, and recommends missing happy-path, boundary, regression, failure-path, and security tests.

The orchestrator is deterministic rather than another unconstrained model call. It merges exact duplicate findings, preserves contributing agents, sorts by severity, calculates overall risk, and chooses `approve`, `comment`, or `request_changes`.

## Tools and state

The GitHub adapter reads pull-request metadata and patches and can optionally publish review comments. Chroma performs dense similarity retrieval over project review rules using the local `all-MiniLM-L6-v2` embedding model. Anthropic Claude performs the three specialist analyses. LangGraph maintains the review context, the list of agent reviews, and the final report across nodes. Pydantic validates every agent response and the combined report.

No long-term conversational memory is required. Persistent state consists of the Chroma rule index and saved JSON or Markdown reports. API keys are loaded from `.env` and are excluded from version control.

## Human in the loop and safety limits

Report generation is read-only until the user approves the publishing step. Without `--publish`, the CLI asks `Post the review comments to the pull request?` and defaults to No. With `--publish`, it posts without prompting, which is suitable for an intentionally configured automation. When publishing, each supported violation is posted as an inline comment and the system adds an overall review summary. A clean review posts the exact message `No issues to report - Recommended for Approval`. If the pull-request author is also the reviewer, GitHub blocks formal approval and request-changes verdicts; the adapter preserves the result as a normal review comment. The system never merges code, modifies source branches, or deletes records.

Prompt-injection resistance is included in every specialist system prompt: code, comments, filenames, rule text, and PR descriptions are treated as untrusted review material rather than instructions. Findings are advisory and do not replace human review, automated tests, SAST, dependency scanning, or professional security assessment.

## Prompt and agent instructions

Each specialist receives the same structured system policy with a different role and focus. The system instruction requires evidence from the supplied diff, prohibits invented context and line numbers, restricts severity and confidence values, treats repository content as untrusted, and demands JSON only. The human prompt includes pull-request metadata, file or PR-level diff context, retrieved project rules, and an explicit `AgentReview` JSON example.

The structured contract requires an agent name, summary, and findings. Each finding contains category, severity, confidence, title, explanation, file, line, evidence, recommendation, suggested test, and matched rule IDs. The adapter parses one JSON object and validates it with Pydantic before the result can enter graph state.

During vibe coding, I used AI coding assistance to inspect the original repository, preserve the existing provider and RAG design, introduce the three specialist roles, build the LangGraph fan-out and aggregation flow, add Pydantic contracts, create evaluation samples, diagnose invalid JSON responses, and improve the testing agent after evaluating a clean PR.

## Code samples used

Three public GitHub pull requests form the evaluation set:

1. [PR 1 mixed intentional defects](https://github.com/byte-by-k/ai-pr-reviewer/pull/1) contains SQL injection, command injection, a dummy hardcoded credential, division-by-zero behavior, mutable default state, resource handling problems, and missing tests.
2. [PR 2 clean validated change](https://github.com/byte-by-k/ai-pr-reviewer/pull/2) contains Decimal-based shipping calculation, input validation, happy-path testing, and parameterized boundary tests. It evaluates false-positive behavior.
3. [PR 3 correctness and resilience defects](https://github.com/byte-by-k/ai-pr-reviewer/pull/3) contains an off-by-one error, quadratic duplicate detection, overly broad exception handling, and no tests.

The project rule dataset is `codereviewrules.yaml`. It contains human-authored security, correctness, resilience, performance, design, style, and testing rules embedded in Chroma and retrieved by specialist category.

## Iterations

The first iteration used the original single reviewer and directly generated comments. The Week 3 iteration separated responsibilities into three specialists and introduced LangGraph state and deterministic aggregation. The next iteration added Pydantic structured output, but the correctness and testing agents occasionally returned invalid JSON. I added a schema-explicit prompt, robust JSON extraction, exact agent validation, and one bounded repair retry.

Evaluation of the clean PR then revealed a workflow defect: the testing specialist reviewed the production file before seeing the test file and produced a contradictory missing-tests finding. I changed the testing node to evaluate the complete pull-request diff as one unit. On rerun, the clean PR received `approve` with no findings. The final publishing iteration made the outcome visible for every review: violations produce inline comments plus a summary, while clean changes receive a clear approval recommendation. The CLI now confirms publishing interactively unless `--publish` is supplied.

## Evaluation results

| Sample | Expected outcome | Actual outcome | Findings | Observation |
|---|---|---|---:|---|
| PR 1 mixed defects | Request changes | Request changes | 15 | All three specialists returned useful findings |
| PR 2 clean and tested | Approve | Approve | 0 | No false positives after PR-level testing review fix |
| PR 3 correctness defects | Request changes | Request changes | 9 | Correctness and missing-test risks were detected |

All three expected verdicts matched. All nine specialist executions produced valid structured summaries in the final evaluation. Seventeen automated tests cover model validation, retry behavior, graph execution, orchestration, reporting, evaluation metrics, PR-level testing context, self-authored PR fallback, publishing outcomes, and CLI confirmation behavior.

## Failure behavior

Anthropic requests use a bounded timeout and retry configuration. If a specialist response is invalid, the model receives one repair request; a second failure produces a safe empty specialist result with a visible failure summary rather than unvalidated content. GitHub requests use a configurable timeout. Empty Chroma state stops the command with setup guidance. Publishing handles GitHub's self-review restriction by falling back to a non-blocking review comment. The CLI defaults the interactive publishing confirmation to No.

## Learnings and observations

Multi-agent value came primarily from separation of concerns and explicit control flow, not from using more prompts. Structured output is essential because orchestration cannot safely combine arbitrary prose. Evaluation must include a clean sample: only then did the file-by-file test-coverage flaw become visible. Specialist context should match the task; correctness can often reason about a hunk, while test coverage requires seeing implementation and tests together.

Model severity still requires human judgment. A syntactically hardcoded dummy password can be classified as critical even when it is not a live secret. Similarly, different agents can describe related risks with different titles, so exact deduplication does not remove every semantic overlap. These are appropriate areas for future calibration and semantic deduplication.

## Limitations and future work

The system reviews changed patches rather than the entire repository, so it can miss relevant unchanged context. GitHub truncates some large patches. Review quality depends on model behavior and the rulebook. Future improvements include semantic duplicate clustering, repository-context retrieval, changed-line validation before publishing comments, LangSmith tracing, calibrated severity evaluation, and an explicit interactive approval interrupt before GitHub writes.
