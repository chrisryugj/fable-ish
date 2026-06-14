#!/usr/bin/env python3
"""Stop-time decision helper for fable-ish."""

from __future__ import annotations

from typing import Any


MAX_STOP_BLOCKS = 2


def has_successful_verification(ledger: dict[str, Any]) -> bool:
    return any(result.get("success") is True for result in ledger.get("verification_results", []))


def has_any_verification(ledger: dict[str, Any]) -> bool:
    return bool(ledger.get("verification_commands") or ledger.get("verification_results"))


def docs_only(ledger: dict[str, Any]) -> bool:
    kinds = set(ledger.get("change_kinds", []))
    return bool(ledger.get("changed_files_seen")) and kinds and kinds <= {"docs"}


def should_block_stop(ledger: dict[str, Any]) -> tuple[bool, str]:
    mode = ledger.get("task_mode") or "quick"
    stop_blocks = int(ledger.get("stop_blocks") or 0)
    changed = bool(ledger.get("changed_files_seen"))
    verified = has_successful_verification(ledger)

    if stop_blocks >= MAX_STOP_BLOCKS:
        return False, "fable-ish allowed stop after two verification reminders; report any missing verification clearly."
    if mode == "quick":
        return False, ""
    if docs_only(ledger):
        return False, ""
    if mode == "blocked":
        return True, "fable-ish: resolve or narrow the blocked risk before final response."
    if mode == "deep" and not verified:
        if changed:
            return True, "fable-ish: run the narrowest verification command for the changed behavior before final response."
        if not has_any_verification(ledger):
            return True, "fable-ish: add one observable proof or explicitly record why this deep task has no runnable verifier."
    if mode == "normal" and changed and not verified:
        return True, "fable-ish: run one relevant verification command for the changed files, or state why no verifier applies."
    return False, ""


def warning_after_max_blocks(ledger: dict[str, Any]) -> str:
    if int(ledger.get("stop_blocks") or 0) >= MAX_STOP_BLOCKS and not has_successful_verification(ledger):
        return "fable-ish: verification evidence is still missing. Include that gap in the final report."
    return ""
