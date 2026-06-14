#!/usr/bin/env python3
"""Approval-time guardrails for fable-ish."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from classify_task import classify_tool_risk
from ledger import add_unique, emit_json, read_stdin_json, update_ledger


def main() -> int:
    input_data = read_stdin_json()
    blocked, flags, reason = classify_tool_risk(input_data)
    if flags:
        update_ledger(input_data, lambda ledger: add_unique(ledger, "risk_flags", flags))
    if blocked:
        emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {
                        "behavior": "deny",
                        "message": f"fable-ish denied approval request: {reason}",
                    },
                }
            }
        )
    else:
        emit_json({})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit_json({"systemMessage": f"fable-ish permission hook failed open: {exc}"})
        raise SystemExit(0)
