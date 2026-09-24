# Week 3 review samples

These three bounded samples exercise different specialist reviewers. They are
snapshots so evaluation stays reproducible. Sample 1 is derived from the original
Azure DevOps adapter in this repository. Samples 2 and 3 are small application
changes written in normal production style to exercise security and test-review
behavior. Before final course submission, add the URL and commit SHA of at least one
public pull request used in the recorded demo.

Each folder contains a unified diff and human-authored `expected.json`. Run the
multi-agent system against the diff, save the structured report, and use
`python -m evaluation.evaluate` to calculate the simple detection metrics.
