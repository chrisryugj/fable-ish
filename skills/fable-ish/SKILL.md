---
name: fable-ish
description: Apply fable-ish verification discipline to Claude Code coding tasks with risk-proportional workflow, review, and final reporting. Use for fable-ish requests, common typo fablish, complex implementation, debugging, refactoring, deployment preparation, or work where completion needs observable evidence. Do not use for simple explanations or quick low-risk answers unless explicitly requested.
---

# fable-ish

Use this skill as the workflow instruction layer for the fable-ish plugin.
The plugin hooks provide mechanical guardrails and a verification gate (task
classification, risky-action blocking, evidence tracking, stop-time review);
this skill provides the human-readable workflow.
Treat `fablish` as a common typo alias for `fable-ish`; do not rename the plugin, skill, or directory.

## Core Rule

Match verification depth to task risk.

- Quick tasks: answer directly and do not force deep planning.
- Normal coding tasks: inspect relevant context, make a coherent change, and run one relevant proof when files change.
- Deep tasks: define the work unit and observable exit proof before final response.
- Blocked tasks: stop when the next action needs user confirmation, credentials, external state, or unsafe destructive scope.

Do not claim verification that was not observed.

## References

Read only the reference needed for the current task:

- `references/workflow.md`: mode selection, work-unit loop, optional review passes.
- `references/verification.md`: choosing and reporting proof.
- `references/final-report.md`: concise final report format.

## Operating Notes

- Keep small requests small.
- Prefer existing repo commands, tests, validators, and docs.
- If no verifier exists, create a small one only when it is low-risk and clearly useful.
- Use subagents only when they increase recall for broad or risky work; they are optional, not mandatory.
- Stop at a verified boundary or name the concrete remaining blocker.
