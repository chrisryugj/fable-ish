#!/usr/bin/env python3
"""Parse tool inputs and outputs into compact fable-ish ledger facts."""

from __future__ import annotations

import re
from typing import Any

from ledger import classify_path_kind, redact


VERIFY_RE = re.compile(
    r"(?i)\b("
    r"pytest|unittest|go\s+test|cargo\s+test|npm\s+test|pnpm\s+test|yarn\s+test|bun\s+test|"
    r"mvn\s+test|gradle\s+test|rspec|vitest|jest|playwright|cypress|"
    r"lint|eslint|ruff|flake8|mypy|pyright|tsc|typecheck|"
    r"build|check|validate|verify|json\.tool|py_compile|curl"
    r")\b"
)
FAILURE_RE = re.compile(
    r"(?i)(command not found|no such file or directory|traceback|syntaxerror|failed|failure|"
    r"\berror:|\b[1-9][0-9]*\s+errors?\b|exit code [1-9]|exited with code [1-9]|"
    r"tests? failed|build failed|lint failed)"
)
SUCCESS_RE = re.compile(r"(?i)\b(passed|success|succeeded|0 failed|build completed|done|valid)\b")
DIRECT_TEST_RE = re.compile(r"(?i)(pytest|unittest|vitest|jest|playwright|cypress|rspec|go\s+test|cargo\s+test)")
MUTATING_BASH_RE = re.compile(r"(?i)\b(python\s+.*\s+-m\s+compileall|chmod|mkdir|mv|cp|rm|touch|npm\s+run\s+build|pnpm\s+build|yarn\s+build)\b")


def response_text(value: Any, limit: int = 4000) -> str:
    parts: list[str] = []

    def walk(item: Any) -> None:
        if len(" ".join(parts)) > limit:
            return
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            for key in ("stdout", "stderr", "output", "message", "text", "content", "error", "summary"):
                if key in item:
                    walk(item[key])
            if not parts:
                for child in item.values():
                    walk(child)
        elif isinstance(item, list):
            for child in item[:20]:
                walk(child)

    walk(value)
    return redact(" ".join(parts), limit)


def command_from_input(input_data: dict[str, Any]) -> str:
    tool_input = input_data.get("tool_input")
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or tool_input.get("description") or "")
    if isinstance(tool_input, str):
        return tool_input
    return ""


def exit_success(input_data: dict[str, Any], text: str) -> bool | None:
    candidates = [input_data, input_data.get("tool_response")]
    for candidate in candidates:
        if isinstance(candidate, dict):
            for key in ("success", "ok"):
                if isinstance(candidate.get(key), bool):
                    return bool(candidate[key])
            for key in ("exit_code", "exitCode", "returncode", "status"):
                value = candidate.get(key)
                if isinstance(value, int):
                    return value == 0
                if isinstance(value, str) and value.isdigit():
                    return int(value) == 0
    if FAILURE_RE.search(text):
        return False
    if SUCCESS_RE.search(text):
        return True
    return None


def is_verification_command(command: str) -> bool:
    return bool(VERIFY_RE.search(command or ""))


def detect_failure(input_data: dict[str, Any]) -> dict[str, Any] | None:
    text = response_text(input_data.get("tool_response", input_data))
    success = exit_success(input_data, text)
    if success is False or (success is None and FAILURE_RE.search(text)):
        return {
            "kind": "tool-result",
            "summary": redact(text or command_from_input(input_data), 240),
            "baseline": "uncertain",
        }
    return None


def changed_paths(input_data: dict[str, Any]) -> list[str]:
    tool_name = str(input_data.get("tool_name") or "")
    tool_input = input_data.get("tool_input")
    paths: list[str] = []
    if isinstance(tool_input, dict):
        target = tool_input.get("file_path") or tool_input.get("notebook_path")
        if target:
            paths.append(str(target))
    if tool_name in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        return paths or ["edit"]
    return paths


def changed_kinds(input_data: dict[str, Any]) -> list[str]:
    paths = changed_paths(input_data)
    if paths:
        return sorted({classify_path_kind(path.strip()) for path in paths})
    tool_name = str(input_data.get("tool_name") or "")
    command = command_from_input(input_data)
    if tool_name == "Bash" and MUTATING_BASH_RE.search(command):
        return ["other"]
    return []


def verification_coverage(command: str, changed: list[str]) -> str:
    if not command:
        return "none"
    clean_paths = [path.strip() for path in changed if path and path not in {"patch", "edit"}]
    if clean_paths and any(path in command for path in clean_paths):
        return "direct"
    if DIRECT_TEST_RE.search(command) and re.search(r"(?i)(test|spec|__tests__)", command):
        return "direct"
    if re.search(r"(?i)\b(test|lint|typecheck|tsc|build|check|validate|verify)\b", command):
        return "generic"
    return "uncertain"


def verification_record(input_data: dict[str, Any]) -> dict[str, Any] | None:
    command = command_from_input(input_data)
    if not command or not is_verification_command(command):
        return None
    text = response_text(input_data.get("tool_response", input_data), 1000)
    success = exit_success(input_data, text)
    return {
        "command": redact(command, 220),
        "success": bool(success) if success is not None else None,
        "summary": redact(text, 220),
        "coverage_relation": verification_coverage(command, []),
    }
