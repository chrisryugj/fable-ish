# fable-ish

**Don't say "done" until it's verified.**

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![platform](https://img.shields.io/badge/platform-Claude%20Code-7c3aed.svg)](https://claude.com/claude-code)

> *When the AI says "tests pass," did it actually run them?*

`fable-ish` reproduces, as **Claude Code** hooks, the *verification discipline* shown by **Fable** — Anthropic's recent coding model. Fable's strength isn't "a smart model writes good code"; it's the **loop**: it resets its exit criteria to match each task's risk, and refuses to call work done until those criteria pass an *observable* proof. fable-ish imitates that discipline with three lightweight hooks (hence the `-ish`).

[한국어](./README.md)

> **Origin & port.** The original `fable-ish` was built for **Codex** by **플라잉따릉이 (Agent Korea)**, who reverse-engineered Fable's behavior into a plugin. This repository is a port of that plugin to **Claude Code** (port by chrisryugj). The plugin name, skill, and workflow are preserved from the original.

---

## 🔁 The Fable loop, in one line

> Set the goal → gather evidence → define the work unit → **set exit criteria** → implement → **verify** → hunt for counter-examples → re-tune the criteria → exit if they pass, else repeat.

The point isn't a *fixed checklist* ("tests pass") — it's **dynamic exit criteria**. Low risk? One static check is enough. High risk (auth, DB, deploy)? A stronger proof becomes the exit bar.

> The loop as a whole is **guidance the skill provides**. What the hooks *mechanically enforce* is just the last part — **refusing a "done" with no verification evidence** (the Stop gate), plus re-engaging a turn that only promised work. The other steps (inspect context, name the work unit, hunt counter-examples, …) are advised, not enforced.

---

## 💡 What it does

LLMs often report "all done" without verifying. fable-ish adds **friction** to that habit using lifecycle hooks:

- **🏷️ Task classification** — sorts each incoming request into `quick` / `normal` / `deep` / `blocked` and injects the matching verification expectation. Destructive / secret-exposing prompts are stopped at the *input* stage, not at the end.
- **🛡️ Risky-action blocking** — denies dangerous operations before they run: `rm -rf`, `git push`, `npm publish`, DB migrations, and edits to secret files (`.env`/`.pem`/`id_rsa`). This is a heuristic first line — back it with `permissions.deny` for hard enforcement (see the [design note](#️-design-note--guardrails-and-hard-enforcement)).
- **📒 Evidence tracking** — records which files changed, which verification commands ran, and whether anything failed, in a small JSON ledger. It even tracks whether a proof actually *covered the changed files* (`direct` / `generic` / `uncertain`).
- **🚦 Completion gate** — if code changed but no successful verification was observed, it sends Claude back to verify at stop time (capped at two blocks to avoid loops).

One core rule: **never claim verification that was not observed.**

---

## ⚡ Installation

This repository is both a single plugin and its marketplace (`.claude-plugin/marketplace.json`).

**Locally, right now (just clone it):**

```text
/plugin marketplace add /path/to/fable-ish
/plugin install fable-ish
```

**After it's on GitHub (once you push the repo):**

```text
/plugin marketplace add chrisryugj/fable-ish
/plugin install fable-ish
```

After installing, **restart Claude Code**. Plugin-bundled hooks are **not trusted automatically** — open `/hooks`, review the definitions, and trust them before relying on the gate.

> **Requirements**: the hooks are standard-library Python scripts; `python3` must be on PATH. On Windows, use `python` if `python3` is unavailable, or adjust the `command` entries in `hooks/hooks.json`.

---

## ▶️ Usage — install once, then it just flows

Once installed and trusted via `/hooks`, it's **automatic** — there's nothing to turn on.

- **Automatic (hooks):** every prompt is classified `quick`/`normal`/`deep`/`blocked`, and if code changed without verification, the Stop gate sends Claude back. You do nothing.
- **Explicit (skill):** invoke it directly with the `/fable-ish <task>` slash command, with natural language like *"implement this end-to-end with fable-ish"*, or let Claude call the skill on its own for complex/verification-heavy work. (The `fablish` typo resolves to the same skill.)

If hooks are disabled or untrusted, the skill still works as reusable instructions, but the mechanical gate won't run.

> **Note**: the blocking hooks are heuristic (bypassable), so treat them as a *first line*. For unbypassable hard enforcement, also set native `permissions.deny` — example in [`examples/claude-permissions.example.json`](./examples/claude-permissions.example.json), explained in the [design note](#️-design-note--guardrails-and-hard-enforcement).

---

## 🔧 How it works

| Hook | Role |
|------|------|
| `UserPromptSubmit` | Classifies the request as `quick`/`normal`/`deep`/`blocked` and injects short context. `blocked` (secret/destructive requests) is stopped with `decision:block` |
| `PreToolUse` / `PermissionRequest` | Deny risky Bash/PowerShell commands (`rm -rf`, `git push`, `npm publish`, DB migrations …) and secret-file edits (`.env`/`.pem`/`id_rsa`) before they run or are approved |
| `PostToolUse` (+ `PostToolUseFailure`) | On **both success and failure** of Bash/PowerShell/edit tools, records changed files/paths, verification commands, a coverage relation (`direct`/`generic`/`uncertain`), and failures in a JSON ledger (under `CLAUDE_PLUGIN_DATA`, OS-temp fallback). A verification that arrives via the failure event is never logged as a pass |
| `Stop` | Re-engages when work changed files without successful verification, or when the turn only *promised* work without doing it (capped at two blocks; yields immediately when `stop_hook_active` is set) |

The skill (`skills/fable-ish/SKILL.md`) is the human-readable workflow layer: mode-by-mode work loops, the verification ladder, and the final-report format.

---

## 🛡️ Design note — guardrails and hard enforcement

fable-ish ports the original's `PreToolUse` / `PermissionRequest` hooks that block risky commands and secret-file edits. **But this is a heuristic first line, not a security boundary.**

Judging shell *intent* with regex is inherently incomplete. Variable expansion, quoting, globs, and encoding can slip past the surface pattern (e.g. `rm -r -f` split flags, `$VAR -rf`, base64-piped `eval`), and it can also over-block legitimate work. So treat this layer as a *tripwire for accidental mistakes*.

For **unbypassable hard enforcement**, also set Claude Code's native `permissions.deny`, where commands are parsed and a user approval step applies. A ready-to-use example is in [`examples/claude-permissions.example.json`](./examples/claude-permissions.example.json):

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Write(./.env)",
      "Bash(rm -rf:*)",
      "Bash(git push:*)",
      "Bash(npm publish:*)"
    ]
  }
}
```

For real isolation, add sandboxing / permission modes (avoid `bypassPermissions`) / approvals / review. In short: fable-ish's blocking is the *first line*, `permissions.deny` is the *hard enforcement*, and the core is still making sure work is **verified before it's reported done**.

For real isolation, rely on sandboxing, permission modes (avoid `bypassPermissions`), approvals, and review — not string matching. fable-ish focuses on the part a hook is actually good at: making sure work is *verified* before it's reported done.

---

## ⚠️ Limits

The hooks are guardrails and a discipline aid, not a complete security boundary.

- Multiple matching hooks can run concurrently.
- `PreToolUse` blocking does not intercept every possible shell path — it's a heuristic that variables, quoting, and encoding can bypass.
- `PostToolUse` cannot undo side effects from a completed command.
- Task classification is heuristic; treat the mode as a hint, not a guarantee.
- Hooks require review and trust before running.
- Stop blocking is intentionally capped (two blocks) to avoid infinite loops.
- The `permissions.deny` profile is provided as an example only; this plugin does not silently install it.

For stronger enforcement, add sandboxing, approvals, tests, linters, and review policies.

---

## 🚫 Excluded by design

- No MCP server.
- No app integration.
- No external API.
- No web server or UI.
- No database.
- No background worker.
- No LLM classifier (classification is regex heuristics).
- No GitHub, Slack, Gmail, or Notion integration.
- No complex policy engine.

---

## 🧪 Development / Verification

From the plugin root:

```bash
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool hooks/hooks.json
python3 -m py_compile hooks/*.py scripts/*.py
python3 tests/test_hooks.py
```

Sample hook inputs can be piped into each hook script with `CLAUDE_PLUGIN_DATA` set to a temporary directory.

---

## 🙏 Credits

- **Original author (Codex plugin):** [플라잉따릉이 (Agent Korea)](https://github.com/) — verification-gate design and original implementation
- **Claude Code port:** chrisryugj

The original was built as a Codex plugin; this repository adapts it to Claude Code (hooks, manifest, tooling) without renaming the plugin or its workflow.

---

## 📄 License

[MIT](./LICENSE) — © 플라잉따릉이 (Agent Korea) and contributors.
