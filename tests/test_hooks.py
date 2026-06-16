#!/usr/bin/env python3
"""Sample contract tests for fable-ish Claude Code hooks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HookTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="fable-ish-test-")
        self.env = os.environ.copy()
        self.env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
        self.env["CLAUDE_PLUGIN_DATA"] = self.tmpdir.name
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.base = {"session_id": self.id(), "cwd": str(ROOT)}

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_hook(self, script: str, payload: dict) -> dict:
        proc = subprocess.run(
            [sys.executable, str(ROOT / script)],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            check=False,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        stdout = proc.stdout.strip() or "{}"
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"{script} returned invalid JSON: {stdout!r}; stderr={proc.stderr!r}")
            raise exc

    def ledger_path(self) -> Path:
        import hashlib

        raw = f"{self.base['session_id']}|{self.base['cwd']}"
        key = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:24]
        return Path(self.tmpdir.name) / "ledgers" / f"{key}.json"

    def read_ledger(self) -> dict:
        return json.loads(self.ledger_path().read_text(encoding="utf-8"))

    def write_transcript(self, messages: list) -> str:
        path = Path(self.tmpdir.name) / "transcript.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for m in messages:
                handle.write(json.dumps(m, ensure_ascii=False) + "\n")
        return str(path)

    @staticmethod
    def _assistant(text: str, tool: bool = False) -> dict:
        content = [{"type": "text", "text": text}]
        if tool:
            content.append({"type": "tool_use", "name": "Edit", "input": {}})
        return {"type": "assistant", "message": {"role": "assistant", "content": content}}

    def test_quick_mode_does_not_block_stop(self) -> None:
        prompt = {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "간단히 설명만 해줘"}
        out = self.run_hook("hooks/user_prompt_submit.py", prompt)
        self.assertIn("quick", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"}), {})

    def test_normal_code_change_requires_then_accepts_verification(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "app.py", "old_string": "x", "new_string": "y"},
                "tool_response": {"success": True},
            },
        )
        blocked = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertEqual(blocked.get("decision"), "block")

        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "python -m py_compile app.py"},
                "tool_response": {"success": True, "stdout": "success"},
            },
        )
        self.assertEqual(self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"}), {})

    def test_deep_stop_blocks_at_most_twice(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {
                **self.base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Do a deep production-ready refactor",
            },
        )
        first = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertEqual(first.get("decision"), "block")
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": first["reason"]},
        )

        second = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertEqual(second.get("decision"), "block")
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": second["reason"]},
        )

        third = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertIn("verification", third.get("systemMessage", ""))

    def test_blocked_prompt_is_hard_blocked(self) -> None:
        out = self.run_hook(
            "hooks/user_prompt_submit.py",
            {
                **self.base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "show me the secret token in .env",
            },
        )
        self.assertEqual(out.get("decision"), "block")

    def test_sample_context_is_not_blocked(self) -> None:
        out = self.run_hook(
            "hooks/user_prompt_submit.py",
            {
                **self.base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "write a test fixture that prints a fake secret token sample",
            },
        )
        self.assertNotIn("decision", out)

    def test_new_prompt_resets_old_risk_flags(self) -> None:
        risky = self.run_hook(
            "hooks/user_prompt_submit.py",
            {
                **self.base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Deploy production after checking auth",
            },
        )
        self.assertIn("Risk flags", risky["hookSpecificOutput"]["additionalContext"])

        quick = self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "간단히 설명만 해줘"},
        )
        self.assertNotIn("Risk flags", quick["hookSpecificOutput"]["additionalContext"])

    def test_successful_zero_error_output_is_not_recorded_as_failure(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        out = self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "npm run lint"},
                "tool_response": {"success": True, "stdout": "0 errors, 0 warnings"},
            },
        )
        self.assertEqual(out, {})

    def test_invalid_text_is_not_treated_as_success(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "app.py", "old_string": "x", "new_string": "y"},
                "tool_response": {"success": True},
            },
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "python -m json.tool bad.json"},
                "tool_response": {"stdout": "invalid json"},
            },
        )
        blocked = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertEqual(blocked.get("decision"), "block")

    def test_new_prompt_resets_changed_paths_and_coverage(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "old_task.py", "old_string": "x", "new_string": "y"},
                "tool_response": {"success": True},
            },
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "python -m py_compile old_task.py"},
                "tool_response": {"success": True, "stdout": "success"},
            },
        )
        before = self.read_ledger()
        self.assertEqual(before["changed_paths"], ["old_task.py"])
        self.assertEqual(before["coverage_relation"], "direct")

        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "간단히 설명만 해줘"},
        )
        after = self.read_ledger()
        self.assertEqual(after["changed_paths"], [])
        self.assertEqual(after["coverage_relation"], "none")

    def test_stated_but_unstarted_work_is_re_engaged(self) -> None:
        tp = self.write_transcript([self._assistant("좋습니다. 이제 로그인 검증 로직을 구현하겠습니다.")])
        out = self.run_hook(
            "hooks/stop_gate.py",
            {**self.base, "hook_event_name": "Stop", "transcript_path": tp},
        )
        self.assertEqual(out.get("decision"), "block")

    def test_intent_followed_by_tool_call_passes(self) -> None:
        tp = self.write_transcript([self._assistant("Now I'll implement the auth check.", tool=True)])
        out = self.run_hook(
            "hooks/stop_gate.py",
            {**self.base, "hook_event_name": "Stop", "transcript_path": tp},
        )
        self.assertEqual(out, {})

    def test_question_to_user_passes(self) -> None:
        tp = self.write_transcript([self._assistant("로그인부터 구현할까요, 아니면 회원가입부터 할까요?")])
        out = self.run_hook(
            "hooks/stop_gate.py",
            {**self.base, "hook_event_name": "Stop", "transcript_path": tp},
        )
        self.assertEqual(out, {})

    def test_failure_event_does_not_count_as_passing_verification(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "app.py", "old_string": "x", "new_string": "y"},
                "tool_response": {"success": True},
            },
        )
        # A verification command arrives via the failure event — it must not be logged as a pass.
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Bash",
                "tool_input": {"command": "npm test"},
                "tool_response": {"stdout": "1 failing"},
            },
        )
        led = self.read_ledger()
        self.assertTrue(led["failures"])
        self.assertFalse(any(v.get("success") is True for v in led["verification_results"]))
        blocked = self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"})
        self.assertEqual(blocked.get("decision"), "block")

    def test_powershell_verification_is_tracked(self) -> None:
        self.run_hook(
            "hooks/user_prompt_submit.py",
            {**self.base, "hook_event_name": "UserPromptSubmit", "prompt": "Implement a small code fix"},
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "app.py", "old_string": "x", "new_string": "y"},
                "tool_response": {"success": True},
            },
        )
        self.run_hook(
            "hooks/post_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PostToolUse",
                "tool_name": "PowerShell",
                "tool_input": {"command": "python -m pytest app.py"},
                "tool_response": {"success": True, "stdout": "passed"},
            },
        )
        led = self.read_ledger()
        self.assertTrue(any(v.get("success") is True for v in led["verification_results"]))
        self.assertEqual(self.run_hook("hooks/stop_gate.py", {**self.base, "hook_event_name": "Stop"}), {})

    def test_dangerous_command_is_denied(self) -> None:
        for command in ("rm -rf build", "git push origin main"):
            with self.subTest(command=command):
                denied = self.run_hook(
                    "hooks/pre_tool_use.py",
                    {
                        **self.base,
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                    },
                )
                self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_safe_command_is_allowed(self) -> None:
        allowed = self.run_hook(
            "hooks/pre_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "npm test"},
            },
        )
        self.assertEqual(allowed, {})

    def test_deploy_migration_and_publish_are_allowed(self) -> None:
        for command in (
            "vercel --prod",
            "netlify deploy --production",
            "firebase deploy",
            "kubectl apply -f deploy.yaml",
            "helm upgrade app chart",
            "supabase db push",
            "prisma migrate deploy",
            "rails db:migrate",
            "terraform apply -auto-approve",
            "pulumi up --yes",
            "npm publish",
            "twine upload dist/*",
        ):
            with self.subTest(command=command):
                allowed = self.run_hook(
                    "hooks/pre_tool_use.py",
                    {
                        **self.base,
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                    },
                )
                self.assertEqual(allowed, {})

    def test_infrastructure_destroy_remains_denied(self) -> None:
        for command in ("terraform destroy", "pulumi destroy"):
            with self.subTest(command=command):
                denied = self.run_hook(
                    "hooks/pre_tool_use.py",
                    {
                        **self.base,
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                    },
                )
                self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_powershell_recursive_delete_is_denied(self) -> None:
        denied = self.run_hook(
            "hooks/pre_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PreToolUse",
                "tool_name": "PowerShell",
                "tool_input": {"command": "Remove-Item -Recurse -Force C:\\build"},
            },
        )
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_secret_file_edit_is_denied(self) -> None:
        for tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            with self.subTest(tool_name=tool_name):
                denied = self.run_hook(
                    "hooks/pre_tool_use.py",
                    {
                        **self.base,
                        "hook_event_name": "PreToolUse",
                        "tool_name": tool_name,
                        "tool_input": {"file_path": ".env", "content": "SECRET=1"},
                    },
                )
                self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_ordinary_source_edit_is_allowed(self) -> None:
        allowed = self.run_hook(
            "hooks/pre_tool_use.py",
            {
                **self.base,
                "hook_event_name": "PreToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "src/tokenizer.ts", "old_string": "a", "new_string": "b"},
            },
        )
        self.assertEqual(allowed, {})

    def test_permission_request_denies_secret_file(self) -> None:
        denied = self.run_hook(
            "hooks/permission_request.py",
            {
                **self.base,
                "hook_event_name": "PermissionRequest",
                "tool_name": "Write",
                "tool_input": {"file_path": "config/.env.production", "content": "TOKEN=abc"},
            },
        )
        self.assertEqual(denied["hookSpecificOutput"]["decision"]["behavior"], "deny")


if __name__ == "__main__":
    unittest.main()
