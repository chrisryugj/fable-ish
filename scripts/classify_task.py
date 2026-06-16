#!/usr/bin/env python3
"""Heuristics for fable-ish task and tool-risk classification."""

from __future__ import annotations

import re
from typing import Any

from ledger import redact


QUICK_RE = re.compile(
    r"(?i)\b(quick|brief|briefly|simple|simply|just explain|explain only|review only|direction|"
    r"check only|no edits|do not edit|read only|analysis only)\b|"
    r"간단히|빠르게|설명만|검토만|리뷰만|분석만|읽어만|방향|확인만|"
    r"수정하지\s*말고|건드리지\s*말고|파일\s*수정하지\s*말고|아직\s*수정"
)
DEEP_RE = re.compile(
    r"(?i)\b(deep|thorough|exhaustive|end-to-end|production-ready|deploy|deployment|"
    r"migration|database|auth|security|refactor|large|complex|implement the plan)\b|"
    r"끝까지|철저|전부|전체|완성본|상용화|배포\s*전|배포|마이그레이션|인증|보안|리팩터"
)
NORMAL_RE = re.compile(
    r"(?i)\b(implement|fix|debug|change|edit|create|build|test|lint|review|update)\b|"
    r"구현|수정|고쳐|디버그|작성|생성|테스트|검증"
)

SECRET_REQUEST_RE = re.compile(
    r"(?i)(print|show|dump|cat|echo|exfiltrate|leak).{0,40}(secret|token|api[_ -]?key|password|\.env)"
)
DESTRUCTIVE_REQUEST_RE = re.compile(
    r"(?i)(rm\s+-rf\s+/|delete\s+everything|drop\s+database|git\s+reset\s+--hard|"
    r"wipe\s+(the\s+)?repo|destroy\s+production)"
)
SAMPLE_RE = re.compile(r"(?i)\b(sample|example|test case|fixture|dry[- ]run|검증|샘플|예시)\b")

# Risky shell commands blocked before they run (Bash / PowerShell).
COMMAND_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("destructive-delete", re.compile(r"(?i)(^|[;&|]\s*)rm\s+-[A-Za-z]*r[A-Za-z]*f|rm\s+-[A-Za-z]*f[A-Za-z]*r"), "rm -rf is blocked."),
    ("destructive-delete", re.compile(r"(?i)\bfind\b.+\b-delete\b"), "Bulk find -delete is blocked."),
    ("destructive-delete", re.compile(r"(?i)\bxargs\b.+\brm\b"), "Bulk xargs rm is blocked."),
    ("destructive-delete", re.compile(r"(?i)\b(Remove-Item|ri|rd|rmdir)\b.+(-Recurse|-Force)"), "Recursive PowerShell deletion is blocked."),
    ("destructive-git", re.compile(r"(?i)\bgit\s+reset\s+--hard\b"), "git reset --hard is blocked."),
    ("destructive-git", re.compile(r"(?i)\bgit\s+clean\s+-[A-Za-z]*f"), "git clean -f is blocked."),
    ("remote-write", re.compile(r"(?i)\bgit\s+push\b"), "git push requires an explicit release workflow."),
    ("infra-destroy", re.compile(r"(?i)\b(terraform\s+destroy|pulumi\s+destroy)\b"), "Infrastructure destruction commands are blocked."),
    ("secret-output", re.compile(r"(?i)\b(cat|less|more|grep|rg|awk|sed|Get-Content|gc|type)\b.+(\.env|id_rsa|\.pem|secret|token|api[_-]?key|password)"), "Secret-bearing file or token output is blocked."),
    ("secret-output", re.compile(r"(?i)\b(printenv|env|set|Get-ChildItem\s+Env:|gci\s+env:)\b(\s*$|\s*[;&|])"), "Bulk environment output is blocked."),
    ("secret-output", re.compile(r"(?i)\becho\s+\$[A-Za-z0-9_]*(SECRET|TOKEN|KEY|PASSWORD)[A-Za-z0-9_]*|\$Env:[A-Za-z0-9_]*(SECRET|TOKEN|KEY|PASSWORD)"), "Secret environment variable output is blocked."),
]

# Secret-bearing file paths blocked from edits (Edit / Write / MultiEdit / NotebookEdit).
SECRET_PATH_RE = re.compile(
    r"(?i)("
    r"(^|[/\\])\.env($|[./\\])"
    r"|id_rsa|id_ed25519"
    r"|\.(pem|pfx|p12|key)$"
    r"|(^|[/\\])(\.npmrc|\.git-credentials|credentials|secrets?)($|[./\\])"
    r")"
)

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
COMMAND_TOOLS = {"Bash", "PowerShell"}


def classify_prompt(prompt: str) -> tuple[str, list[str], str]:
    text = prompt or ""
    lowered = text.lower()
    risks: list[str] = []
    if "production" in lowered or "배포" in text:
        risks.append("production")
    if re.search(r"(?i)\b(db|database|migration|migrate|schema)\b|데이터베이스|마이그레이션", text):
        risks.append("database")
    if re.search(r"(?i)\b(auth|secret|token|api[_ -]?key|password)\b|인증|비밀|토큰", text):
        risks.append("secret-or-auth")
    if re.search(r"(?i)\b(git\s+push|release|publish)\b|릴리즈|배포", text):
        risks.append("remote-write")
    if re.search(r"(?i)\b(rm\s+-rf|delete|drop|destroy|wipe)\b|삭제", text):
        risks.append("destructive")

    sample_context = bool(SAMPLE_RE.search(text))
    blocked = (SECRET_REQUEST_RE.search(text) or DESTRUCTIVE_REQUEST_RE.search(text)) and not sample_context
    if blocked:
        return "blocked", risks or ["blocked-risk"], redact(text, 180)
    if DEEP_RE.search(text) or any(flag in risks for flag in ("production", "database", "remote-write")):
        return "deep", risks, redact(text, 180)
    if QUICK_RE.search(text) and not risks:
        return "quick", risks, redact(text, 180)
    if NORMAL_RE.search(text):
        return "normal", risks, redact(text, 180)
    return "quick", risks, redact(text, 180)


def classify_command(command: str) -> tuple[bool, list[str], str]:
    text = command or ""
    flags: list[str] = []
    reasons: list[str] = []
    for flag, pattern, reason in COMMAND_RULES:
        if pattern.search(text):
            flags.append(flag)
            reasons.append(reason)
    if flags:
        return True, sorted(set(flags)), " ".join(reasons)
    return False, [], ""


def edit_target_path(input_data: dict[str, Any]) -> str:
    tool_input = input_data.get("tool_input")
    if isinstance(tool_input, dict):
        return str(
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
            or ""
        )
    return ""


def classify_file_edit(input_data: dict[str, Any]) -> tuple[bool, list[str], str]:
    path = edit_target_path(input_data)
    if path and SECRET_PATH_RE.search(path):
        return True, ["secret-file-edit"], "Edits to secret-bearing files are blocked."
    return False, [], ""


def tool_command(input_data: dict[str, Any]) -> str:
    tool_input = input_data.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if command is not None:
            return str(command)
        if "description" in tool_input:
            return str(tool_input.get("description") or "")
    if isinstance(tool_input, str):
        return tool_input
    return ""


def classify_tool_risk(input_data: dict[str, Any]) -> tuple[bool, list[str], str]:
    tool_name = str(input_data.get("tool_name") or "")
    if tool_name in EDIT_TOOLS:
        return classify_file_edit(input_data)
    if tool_name in COMMAND_TOOLS:
        return classify_command(tool_command(input_data))
    return False, [], ""


def context_for_mode(mode: str, risk_flags: list[str]) -> str:
    lines = [f"fable-ish task mode: {mode}."]
    if risk_flags:
        lines.append("Risk flags: " + ", ".join(risk_flags) + ".")
    if mode == "quick":
        lines.append("Keep the response concise; do not force deep planning or broad verification.")
    elif mode == "normal":
        lines.append("If files change, run one relevant verification command or state why none applies.")
    elif mode == "deep":
        lines.append("Define the exit proof before completion and verify changed behavior before final.")
    elif mode == "blocked":
        lines.append("Do not proceed until the risky request is narrowed or explicitly confirmed.")
    lines.append("Never claim verification that was not actually observed.")
    return "\n".join(lines[:10])
