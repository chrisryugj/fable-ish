# Changelog

> Original `fable-ish` Codex plugin by 플라잉따릉이 (Agent Korea).
> This changelog tracks the Claude Code port by chrisryugj.

## 0.1.4 - 2026-06-22

Ported the guidance additions from the upstream Codex `fable-ish` 1.0.5 release.
Skill text only — no hook behavior change. (The 1.0.5 `permission_request.py`
no-op and `ship`/`yeet`/`gstack` command exclusions are upstream's move *away*
from guardrails; this port keeps its restored guardrail layer, so they are not
applicable here.)

- **Domain steering** (`SKILL.md`, `references/workflow.md`) — treat
  user-provided rules, edge cases, constraints, and correction criteria as the
  primary steering signal for the work unit, failure scenarios, and exit proof,
  rather than substituting generic coding assumptions.
- **Work-kind selection** (`SKILL.md`, `references/workflow.md`) — after picking
  depth (quick/normal/deep/blocked), also classify work kind
  (build/fix/test/operate/understand/plan/analyze/document) and let the work kind
  choose the proof. Depth picks rigor; work kind picks proof.
- **Broader verification ladder** (`references/verification.md`) — choose proof
  from both domain risk and work kind, and for documentation, data-analysis, or
  operational work use the closest observable proof (fact/link/command checks,
  reproducible calculation, data provenance, process/endpoint/job/deployment
  state, or explicit user confirmation) instead of code-test defaults.

## 0.1.3 - 2026-06-16

Ported improvements from the upstream Codex `fable-ish` 0.1.4 release and its
"allow deployment commands" change.

- **Deployment commands no longer blocked** (`classify_task.py`) — removed the
  `PreToolUse` blocks for production deploy (Vercel/Netlify/Firebase/kubectl/Helm),
  database migrations, package publish, and `terraform apply`/`pulumi up`.
  fable-ish is a verification gate, not a deploy gate; only `terraform`/`pulumi
  destroy` remain blocked under `infra-destroy`. (`rm -rf`, recursive
  `Remove-Item`, `git push`, secret output, and secret-file edits stay blocked.)
- **Stronger verification-evidence recognition** (`parse_tool_result.py`) — now
  reads `exit code: 0` as success, normalizes status strings (`success`/`failed`/
  `timeout`/…), and recognizes build-success output such as `Compiled successfully`
  and `built successfully`. Failure detection also handles the colon form
  (`exit code: 1`).
- **Fail-open Stop hook** (`stop_gate.py`) — captures stray stdout so it can't
  corrupt the hook's JSON contract, and on error emits a message that explicitly
  flags it as a plugin issue ("not evidence that your verification failed") rather
  than an ambiguous failure.

## 0.1.2 - 2026-06-14

Full Claude Code port of the `fable-ish` plugin — feature-equivalent to the Codex
original, adapted to Claude Code's hook model.

- **Verification gate** — prompt classification (`UserPromptSubmit`), an evidence
  ledger with changed-path and coverage tracking (`PostToolUse` +
  `PostToolUseFailure`), and stop-time review (`Stop`): blocks completion without
  verification evidence and re-engages a turn that only *promised* work. Capped at
  two blocks, honors `stop_hook_active`.
- **Risky-action guardrails** — `PreToolUse` / `PermissionRequest` deny dangerous
  Bash/PowerShell commands (`rm -rf`, `git push`, `npm publish`, DB migrations,
  secret output) and secret-file edits (`.env`/`.pem`/`id_rsa`); `blocked` prompts
  are hard-blocked at `UserPromptSubmit`. These are heuristic — a `permissions.deny`
  example under `examples/` adds unbypassable hard enforcement.
- **Failure-aware** — listens on `PostToolUseFailure`, so a failed tool run can't be
  recorded as a passing verification.
- **Claude Code native** — `.claude-plugin` manifest + `marketplace.json`,
  `${CLAUDE_PLUGIN_ROOT}` / `CLAUDE_PLUGIN_DATA`, and Claude tool names (`Bash`,
  `PowerShell`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit`) with `file_path`-based
  signals.
- **Tests** — run the hooks with `sys.executable` (cross-platform); cover the gate,
  the guardrails, and failure handling.
