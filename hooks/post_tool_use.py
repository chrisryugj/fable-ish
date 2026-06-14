#!/usr/bin/env python3
"""Record fable-ish tool evidence after supported tool calls."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ledger import add_unique, emit_json, read_stdin_json, redact, update_ledger
from parse_tool_result import (
    changed_kinds,
    changed_paths,
    command_from_input,
    detect_failure,
    verification_coverage,
    verification_record,
)


def main() -> int:
    input_data = read_stdin_json()
    event = str(input_data.get("hook_event_name") or "PostToolUse")
    failure_event = event == "PostToolUseFailure"
    kinds = changed_kinds(input_data)
    paths = changed_paths(input_data)
    failure = detect_failure(input_data)
    verification = verification_record(input_data)
    command = command_from_input(input_data)

    # An explicit failure event means the tool did not succeed: never let it be
    # recorded as a passing verification, and record a failure even if the
    # heuristic could not parse one from the (schema-uncertain) failure payload.
    if failure_event:
        if verification and verification.get("success") is not False:
            verification["success"] = False
        if not failure:
            failure = {
                "kind": "tool-failure",
                "summary": redact(command, 240) or "tool reported a failure",
                "baseline": "uncertain",
            }

    def apply(ledger):
        if kinds:
            ledger["changed_files_seen"] = True
            add_unique(ledger, "change_kinds", kinds)
            add_unique(ledger, "changed_paths", [path.strip() for path in paths if path])
        if verification:
            verification["coverage_relation"] = verification_coverage(command, ledger.get("changed_paths", []))
            ledger["verification_results"].append(verification)
            if command:
                ledger["verification_commands"].append(verification["command"])
            coverage_order = {"none": 0, "uncertain": 1, "generic": 2, "direct": 3}
            current = ledger.get("coverage_relation") or "none"
            observed = verification.get("coverage_relation") or "uncertain"
            if coverage_order.get(observed, 0) > coverage_order.get(current, 0):
                ledger["coverage_relation"] = observed
        if failure:
            ledger["failures"].append(failure)

    update_ledger(input_data, apply)

    if failure:
        emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": "fable-ish observed a tool failure. Do not report completion until it is fixed, isolated as baseline, or explicitly documented.",
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
        emit_json({"systemMessage": f"fable-ish post-tool hook failed open: {exc}"})
        raise SystemExit(0)
