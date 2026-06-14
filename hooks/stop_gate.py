#!/usr/bin/env python3
"""Stop-time completion gate for fable-ish."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ledger import emit_json, load_ledger, read_stdin_json, save_ledger
from verify_state import should_block_stop, warning_after_max_blocks


def main() -> int:
    input_data = read_stdin_json()
    if input_data.get("stop_hook_active") is True:
        emit_json(
            {
                "systemMessage": "fable-ish stop hook is already active; allowing stop to avoid a continuation loop.",
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": "fable-ish: stop hook was already active, so no additional block was issued.",
                },
            }
        )
        return 0

    ledger = load_ledger(input_data)
    block, reason = should_block_stop(ledger)
    if block:
        ledger["stop_blocks"] = int(ledger.get("stop_blocks") or 0) + 1
        save_ledger(input_data, ledger)
        emit_json({"decision": "block", "reason": reason})
        return 0

    warning = warning_after_max_blocks(ledger)
    if warning:
        emit_json(
            {
                "systemMessage": warning,
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": warning,
                },
            }
        )
    else:
        emit_json({})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit_json({"systemMessage": f"fable-ish stop hook failed open: {exc}"})
        raise SystemExit(0)
