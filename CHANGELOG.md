# Changelog

> Original `fable-ish` Codex plugin by 플라잉따릉이 (Agent Korea).
> This changelog tracks the Claude Code port by chrisryugj.

## 0.1.2 - 2026-06-14

Parity with upstream fable-ish 0.1.2.

- Fixed new-prompt ledger reset to clear `changed_paths` and reset
  `coverage_relation` to `none`, so per-task coverage tracking no longer leaks
  across unrelated prompts in the same session. (Independently caught by this
  port's adversarial review before the upstream fix landed.)
- Added a regression test asserting the reset.
- Manifest description/keywords no longer advertise the removed command-checking
  hooks; dropped a dead `user_prompt` input fallback from the original platform.

## 0.1.1 - 2026-06-14

Parity with upstream fable-ish 0.1.1, adapted to this Claude Code port.

- Stop hook now honors `stop_hook_active` and skips re-blocking to avoid a
  continuation loop.
- Expanded Korean prompt classification (review-only / no-edit / pre-release phrasing).
- Ledger now records changed paths and a coarse verification coverage relation
  (`direct` / `generic` / `uncertain`) linking proofs to the files that changed.
- Documented `fablish` as a common typo alias for `fable-ish`.
- Hardened hook subprocess tests with a timeout.
- Upstream 0.1.1 added regex command-rule and permission examples (`rules/`,
  `examples/`). This port intentionally keeps hard enforcement in native
  `permissions.deny` and does **not** ship regex command-blocking hooks; see the
  README design note.

## 0.1.0 - 2026-06-14

Initial Claude Code port of the `fable-ish` verification-gate plugin (originally a
Codex plugin).

- Ported the plugin to Claude Code: `.claude-plugin/plugin.json` manifest,
  `${CLAUDE_PLUGIN_ROOT}` hook paths, and `CLAUDE_PLUGIN_DATA` ledger location.
- Preserved the `fable-ish` plugin name, skill name, and skill directory name.
- Kept the verification gate: prompt classification (`UserPromptSubmit`),
  evidence tracking (`PostToolUse`), and stop-time review (`Stop`).
- **Removed the regex command/patch guardrail hooks** (`PreToolUse`,
  `PermissionRequest`). Regex cannot reliably judge shell intent — it under-blocks
  real danger (`dd`, `mkfs`, split flags, variable/quote/base64 bypasses) and
  over-blocks legitimate work. Hard enforcement now defers to Claude Code's native
  `permissions.deny`; see the README design note for a sample.
- Softened sensitive-prompt handling: `blocked` mode no longer hard-rejects the
  prompt. It is now a "more careful" mode that injects guidance and lets the
  Stop gate emphasize verification, while leaving hard limits to permissions.
- Replaced Codex-specific tool handling (`apply_patch`, `*** … File:` patches)
  with Claude Code edit tools (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`) and
  `file_path`-based signals.
- Updated tests to run hooks with `sys.executable` (cross-platform) and to cover
  the verification-gate behavior on Claude Code wire shapes.

### Notes

- Plugin-bundled hooks require trust. Review and trust them with `/hooks` after
  install.
- The verification gate is a discipline aid, not a sandbox or security boundary.
