# Changelog

> Original `fable-ish` Codex plugin by 플라잉따릉이 (Agent Korea).
> This changelog tracks the Claude Code port by chrisryugj.

## 0.1.2 - 2026-06-14

Claude Code port of the `fable-ish` verification-gate plugin.

- **Verification gate** — prompt classification (`UserPromptSubmit`), an evidence
  ledger with changed-path and coverage tracking (`PostToolUse`), and stop-time
  review (`Stop`, capped at two blocks, honors `stop_hook_active`).
- **No command-blocking hooks** — hard enforcement of risky commands and secret
  files is delegated to Claude Code's native `permissions.deny` (see the README
  design note for a sample), rather than unreliable regex matching.
- **Sensitive prompts are advised, not hard-rejected** — `blocked` is a
  "more careful" mode that injects guidance and lets the Stop gate emphasize
  verification.
- **Claude Code native** — `.claude-plugin` manifest + `marketplace.json`,
  `${CLAUDE_PLUGIN_ROOT}` / `CLAUDE_PLUGIN_DATA`, and edit tools (`Edit`, `Write`,
  `MultiEdit`, `NotebookEdit`) with `file_path`-based signals.
- **Tests** — run the hooks with `sys.executable` (cross-platform) and cover the
  gate behavior on Claude Code wire shapes.
