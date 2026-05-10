from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.planfile_queue import run_next_planfile_task


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


class TestPlanfileQueue(unittest.TestCase):
    def test_shell_ticket_runs_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-001",
                "name": "Run bootstrap",
                "executor": {"kind": "shell", "handler": "echo ok"},
                "execution": {"state": "ready"},
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                if _ticket_args(command)[:4] == ["ticket", "next", "--format", "json"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def shell_runner(command: str, _project: Path) -> SimpleNamespace:
                self.assertEqual(command, "echo ok")
                return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

            result = run_next_planfile_task(
                project=project,
                actor="koru-test",
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-001")
            self.assertIn(
                ["ticket", "claim", "PLF-001", "--assigned-to", "koru-test"],
                [_ticket_args(call) for call in planfile_calls],
            )
            self.assertIn(
                ["ticket", "start", "PLF-001", "--assigned-to", "koru-test"],
                [_ticket_args(call) for call in planfile_calls],
            )
            self.assertTrue(
                any(
                    _ticket_args(call)[:3] == ["ticket", "complete", "PLF-001"]
                    for call in planfile_calls
                )
            )

    def test_human_ticket_returns_waiting_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-002",
                "name": "Provide API key",
                "executor": {"kind": "human", "mode": "interactive"},
                "inputs": {"prompt": "Provide OPENROUTER_API_KEY"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                self.assertEqual(_ticket_args(command), ["ticket", "next", "--format", "json"])
                return _ok(json.dumps(ticket))

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-002")
            self.assertEqual(result.message, "Provide OPENROUTER_API_KEY")

    def test_shell_failure_marks_ticket_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-003",
                "name": "Run failing command",
                "executor": {"kind": "shell"},
                "inputs": {"script": "false"},
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                if _ticket_args(command)[:4] == ["ticket", "next", "--format", "json"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def shell_runner(_command: str, _project: Path) -> SimpleNamespace:
                return SimpleNamespace(returncode=2, stdout="", stderr="boom")

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.exit_code, 2)
            self.assertTrue(
                any(
                    _ticket_args(call)[:3] == ["ticket", "fail", "PLF-003"]
                    for call in planfile_calls
                )
            )


    def test_idle_when_planfile_returns_no_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)

            def planfile_runner(_command: list[str], _project: Path) -> SimpleNamespace:
                return _ok("No runnable ticket found")

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "idle")
            self.assertIsNone(result.ticket_id)

    def test_planfile_error_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)

            def planfile_runner(_command: list[str], _project: Path) -> SimpleNamespace:
                return SimpleNamespace(returncode=2, stdout="", stderr="planfile broken")

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "planfile_error")
            self.assertEqual(result.exit_code, 2)
            self.assertEqual(result.stderr, "planfile broken")

    def test_dry_run_returns_command_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-010",
                "name": "Dry run me",
                "executor": {"kind": "shell", "handler": "echo dry"},
            }
            shell_calls: list[str] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:4] == ["ticket", "next", "--format", "json"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def shell_runner(command: str, _project: Path) -> SimpleNamespace:
                shell_calls.append(command)
                return _ok("should not run")

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                dry_run=True,
            )

            self.assertEqual(result.status, "dry_run")
            self.assertEqual(result.message, "echo dry")
            self.assertEqual(shell_calls, [])

    def test_unsupported_executor_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-020",
                "name": "Future LLM task",
                "executor": {"kind": "llm", "mode": "automatic"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:4] == ["ticket", "next", "--format", "json"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "unsupported_executor")
            self.assertEqual(result.executor_kind, "llm")
            self.assertEqual(result.ticket_id, "PLF-020")

    def test_shell_ticket_without_command_requests_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-030",
                "name": "Shell with no command",
                "executor": {"kind": "shell"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:4] == ["ticket", "next", "--format", "json"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-030")
            self.assertTrue(
                any(
                    _ticket_args(call)[:3] == ["ticket", "input", "PLF-030"]
                    for call in calls
                )
            )


if __name__ == "__main__":
    unittest.main()
