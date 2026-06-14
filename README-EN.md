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

LLMs often report "all done" without verifying. fable-ish adds **friction** to that habit using just three lifecycle hooks:

- **🏷️ Task classification** — sorts each incoming request into `quick` / `normal` / `deep` / `blocked` and injects the matching verification expectation as context.
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

> **Note**: *hard* blocking of secret files and dangerous commands belongs in native `permissions.deny`, not this plugin (see the [design note](#️-design-note--why-theres-no-command-blocking-hook) below).

---

## 🔧 How it works

| Hook | Role |
|------|------|
| `UserPromptSubmit` | Classifies the request as `quick`/`normal`/`deep`/`blocked` and injects short context for the expected verification depth |
| `PostToolUse` (+ `PostToolUseFailure`) | On **both success and failure** of Bash/PowerShell/edit tools, records changed files/paths, verification commands, a coverage relation (`direct`/`generic`/`uncertain`), and failures in a JSON ledger (under `CLAUDE_PLUGIN_DATA`, OS-temp fallback). A verification that arrives via the failure event is never logged as a pass |
| `Stop` | Re-engages when work changed files without successful verification, or when the turn only *promised* work without doing it (capped at two blocks; yields immediately when `stop_hook_active` is set) |

The skill (`skills/fable-ish/SKILL.md`) is the human-readable workflow layer: mode-by-mode work loops, the verification ladder, and the final-report format.

---

## 🛡️ Design note — why there's no command-blocking hook

fable-ish does **not** block risky shell commands or secret-file edits — by design.

Matching shell *intent* with regex is a losing game. A regex ruleset for this blocks only **4 of 16** dangerous commands — `rm -r -f` (split flags), `rm --recursive --force`, `$VAR -rf`, base64-piped `eval`, `git -C . push`, and genuinely destructive `dd` / `mkfs` / fork-bombs all slip through — while it *over-blocks* legitimate work like clearing a build cache or `npm publish` during a release. Variable expansion, quoting, globs, and encoding defeat any surface pattern, so hardening the regex only trades false negatives for more false positives.

Claude Code already has a stronger native mechanism. Enforce hard limits with `permissions.deny` in your settings, where commands are parsed and a user approval step still applies:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Write(./.env)",
      "Bash(rm -rf:*)",
      "Bash(dd:*)",
      "Bash(mkfs:*)",
      "Bash(git push:*)"
    ]
  }
}
```

For real isolation, rely on sandboxing, permission modes (avoid `bypassPermissions`), approvals, and review — not string matching. fable-ish focuses on the part a hook is actually good at: making sure work is *verified* before it's reported done.

---

## ⚠️ Limits

The verification gate is a discipline aid, not a security boundary.

- The classifier is heuristic; treat the mode as a hint, not a guarantee.
- `PostToolUse` cannot undo side effects from a completed command.
- Hooks require review and trust before running.
- Stop blocking is intentionally capped at two to avoid infinite loops.

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
