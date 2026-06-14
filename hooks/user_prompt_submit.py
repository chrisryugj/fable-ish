#!/usr/bin/env python3
"""Classify incoming Claude Code prompts for fable-ish."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from classify_task import classify_prompt, context_for_mode
from ledger import add_unique, emit_json, load_ledger, read_stdin_json, update_ledger


CONTINUATION_PREFIXES = (
    "fable-ish: run ",
    "fable-ish: add ",
    "fable-ish: resolve ",
)


def main() -> int:
    input_data = read_stdin_json()
    prompt = str(input_data.get("prompt") or "")
    normalized_prompt = prompt.lstrip().lower()
    if normalized_prompt.startswith(CONTINUATION_PREFIXES):
        ledger = load_ledger(input_data)
        mode = str(ledger.get("task_mode") or "normal")
        risks = list(ledger.get("risk_flags") or [])
        emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context_for_mode(mode, risks),
                }
            }
        )
        return 0

    mode, risks, goal = classify_prompt(prompt)

    def apply(ledger):
        ledger["task_mode"] = mode
        ledger["goal"] = goal
        ledger["changed_files_seen"] = False
        ledger["changed_paths"] = []
        ledger["change_kinds"] = []
        ledger["risk_flags"] = []
        ledger["verification_commands"] = []
        ledger["verification_results"] = []
        ledger["coverage_relation"] = "none"
        ledger["failures"] = []
        ledger["stop_blocks"] = 0
        add_unique(ledger, "risk_flags", risks)

    update_ledger(input_data, apply)

    if mode == "blocked":
        emit_json(
            {
                "decision": "block",
                "reason": "fable-ish blocked this prompt because it appears to request destructive or secret-exposing action. Narrow the request or provide explicit safe scope.",
            }
        )
        return 0

    emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context_for_mode(mode, risks),
            }
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit_json({"systemMessage": f"fable-ish prompt hook failed open: {exc}"})
        raise SystemExit(0)
