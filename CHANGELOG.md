# Changelog

> Original `fable-ish` Codex plugin by 플라잉따릉이 (Agent Korea).
> This changelog tracks the Claude Code port by chrisryugj.

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
