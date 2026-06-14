#!/usr/bin/env python3
"""Heuristics for fable-ish task classification."""

from __future__ import annotations

from ledger import redact
import re


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
    sensitive = (SECRET_REQUEST_RE.search(text) or DESTRUCTIVE_REQUEST_RE.search(text)) and not sample_context
    if sensitive:
        return "blocked", risks or ["sensitive-request"], redact(text, 180)
    if DEEP_RE.search(text) or any(flag in risks for flag in ("production", "database", "remote-write")):
        return "deep", risks, redact(text, 180)
    if QUICK_RE.search(text) and not risks:
        return "quick", risks, redact(text, 180)
    if NORMAL_RE.search(text):
        return "normal", risks, redact(text, 180)
    return "quick", risks, redact(text, 180)


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
        lines.append(
            "This request touches a sensitive or destructive boundary. Confirm scope, prefer the safest "
            "reversible action, and stop for user confirmation when the next step needs credentials, "
            "irreversible remote writes, or destructive deletes. Rely on Claude Code permissions for hard enforcement."
        )
    lines.append("Never claim verification that was not actually observed.")
    return "\n".join(lines[:10])
