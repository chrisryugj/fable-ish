#!/usr/bin/env python3
"""Stop-time decision helper for fable-ish."""

from __future__ import annotations

import json
import re
from typing import Any


MAX_STOP_BLOCKS = 2

# A closing sentence that announces a *next* action — Korean first, English second.
_NEXT_ACTION_RE = re.compile(
    r"(?:이제|다음으로|곧|바로|먼저)\s*[^.!?]*?(?:구현|작성|추가|수정|진행|생성|실행|시작|반영|정리)\s*(?:하겠|할게|하려|예정)"
    r"|(?:구현|작성|추가|수정|진행|생성|실행|시작|반영|정리)\s*(?:하겠습니다|하겠어요|할게요|할\s*게)"
    r"|(?:i'?ll|i will|i'?m going to|let me|next,?\s*i)\s+(?:\w+\s+){0,6}?"
    r"(?:implement|build|add|write|create|fix|run|update|set\s*up|wire|refactor)",
    re.IGNORECASE,
)
# A closing sentence that hands the decision back to the user — then it is a fine place to stop.
_USER_DECISION_RE = re.compile(
    r"(?:할까요|하시겠|드릴까요|선택해|어느\s*쪽|원하시면)"
    r"|(?:shall\s*i|want me to|would you like|which\s*(?:option|one)|let me know)|\?\s*$",
    re.IGNORECASE,
)


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


def _final_assistant_blocks(transcript_path: str) -> list | None:
    """Content blocks of the last assistant turn, scanning the transcript from the end."""
    try:
        with open(transcript_path, encoding="utf-8") as handle:
            rows = [line for line in handle if line.strip()]
    except OSError:
        return None
    for raw in reversed(rows):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        message = obj.get("message", obj)
        if obj.get("type") == "assistant" or message.get("role") == "assistant":
            content = message.get("content")
            if isinstance(content, list):
                return content
    return None


def _closing_line(text: str) -> str:
    parts = [chunk.strip() for chunk in re.split(r"[.!?。\n]+", text) if chunk.strip()]
    return parts[-1] if parts else ""


def stated_but_unstarted(transcript_path: str) -> bool:
    """True when the last turn announces a next action but ends with no tool call and no question."""
    if not transcript_path:
        return False
    blocks = _final_assistant_blocks(transcript_path)
    if not blocks:
        return False
    if any(isinstance(b, dict) and b.get("type") == "tool_use" for b in blocks):
        return False
    spoken = " ".join(
        b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
    ).strip()
    closing = _closing_line(spoken)
    if not closing:
        return False
    return bool(_NEXT_ACTION_RE.search(closing) and not _USER_DECISION_RE.search(closing))
