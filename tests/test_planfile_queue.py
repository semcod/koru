from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from koru.cqrs.event_store import JsonlEventStore
from koru.queue import run_next_planfile_task
from koru.queue.ticket import planfile_command


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


class TestPlanfileCommand(unittest.TestCase):
    def test_prefers_local_planfile_before_importable_module_from_active_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project = root / "koru"
            local = root / "planfile" / ".venv" / "bin" / "planfile"
            local.parent.mkdir(parents=True)
            local.write_text("#!/bin/sh\n", encoding="utf-8")
            local.chmod(0o755)
            calls: list[list[str]] = []

            def runner(command, _project):
                calls.append(list(command))
                return _ok()

            with patch("koru.queue.ticket.find_spec", return_value=object()), patch(
                "koru.queue.ticket.shutil.which",
                return_value="/tmp/other-venv/bin/planfile",
            ):
                planfile_command(project, ["ticket", "list"], runner=runner)

            self.assertEqual(calls[0], [str(local), "ticket", "list"])

    def test_prefers_local_planfile_before_path_cli_when_module_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project = root / "koru"
            local = root / "planfile" / ".venv" / "bin" / "planfile"
            local.parent.mkdir(parents=True)
            local.write_text("#!/bin/sh\n", encoding="utf-8")
            local.chmod(0o755)
            calls: list[list[str]] = []

            def runner(command, _project):
                calls.append(list(command))
                return _ok()

            def fake_find_spec(name: str):
                if name == "planfile.cli":
                    raise ModuleNotFoundError("No module named 'planfile'")
                return None

            with patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec), patch(
                "koru.queue.ticket.shutil.which",
                return_value="/tmp/other-venv/bin/planfile",
            ):
                planfile_command(project, ["ticket", "list"], runner=runner)

            self.assertEqual(calls[0], [str(local), "ticket", "list"])

    def test_falls_back_to_path_cli_when_module_cli_missing(self) -> None:
        calls: list[list[str]] = []

        def runner(command, _project):
            calls.append(list(command))
            return _ok()

        def fake_find_spec(name: str):
            if name == "planfile.cli":
                return None
            if name == "planfile":
                return object()
            return None

        with patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec), patch(
            "koru.queue.ticket.shutil.which",
            return_value="/usr/bin/planfile",
        ):
            planfile_command(Path("/tmp"), ["ticket", "list"], runner=runner)

        self.assertEqual(calls[0], ["planfile", "ticket", "list"])

    def test_module_cli_probe_treats_missing_parent_as_missing(self) -> None:
        calls: list[list[str]] = []

        def runner(command, _project):
            calls.append(list(command))
            return _ok()

        def fake_find_spec(name: str):
            if name == "planfile.cli":
                raise ModuleNotFoundError("No module named 'planfile'")
            return None

        with patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec), patch(
            "koru.queue.ticket.shutil.which",
            return_value="/usr/bin/planfile",
        ):
            planfile_command(Path("/tmp"), ["ticket", "list"], runner=runner)

        self.assertEqual(calls[0], ["planfile", "ticket", "list"])


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
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
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
                queue_name="c2004-refactor",
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-001")
            tail_args = [_ticket_args(call) for call in planfile_calls]
            claim = [
                "ticket",
                "claim",
                "PLF-001",
                "--assigned-to",
                "koru-test",
                "--lease-seconds",
                "3600",
            ]
            self.assertIn(claim, tail_args)
            self.assertLess(tail_args.index(claim), tail_args.index(["ticket", "start", "PLF-001"]))
            self.assertIn(["ticket", "start", "PLF-001"], tail_args)
            self.assertIn(["ticket", "done", "PLF-001"], tail_args)
            start_i = tail_args.index(["ticket", "start", "PLF-001"])
            done_i = tail_args.index(["ticket", "done", "PLF-001"])
            update_calls = [
                ta
                for ta in tail_args
                if len(ta) >= 5
                and ta[:3] == ["ticket", "update", "PLF-001"]
                and ta[3] in ("--note", "-n")
            ]
            self.assertTrue(update_calls, "expected shell evidence ticket update")
            self.assertGreater(tail_args.index(update_calls[0]), start_i)
            self.assertLess(tail_args.index(update_calls[0]), done_i)
            self.assertIn("KORU-SHELL-RUN", update_calls[0][4])
            self.assertIn("ok", update_calls[0][4])
            for args in tail_args:
                self.assertNotIn(args[1], {"complete", "fail", "input", "next"})

    def test_ticket_claim_failure_returns_claim_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-0X",
                "name": "Run",
                "executor": {"kind": "shell", "handler": "echo ok"},
                "execution": {"state": "ready"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                ta = _ticket_args(command)
                if ta[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                if ta[:3] == ["ticket", "claim", "PLF-0X"]:
                    return SimpleNamespace(returncode=1, stdout="", stderr="already claimed")
                return _ok()

            result = run_next_planfile_task(
                project=project,
                actor="koru-test",
                planfile_runner=planfile_runner,
            )

            self.assertEqual(result.status, "claim_failed")
            self.assertEqual(result.ticket_id, "PLF-0X")
            self.assertEqual(result.message, "already claimed")

    def test_ticket_claim_missing_command_falls_back_to_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-0Y",
                "name": "Run with older planfile",
                "executor": {"kind": "shell", "handler": "echo ok"},
                "execution": {"state": "ready"},
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                ta = _ticket_args(command)
                if ta[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                if ta[:3] == ["ticket", "claim", "PLF-0Y"]:
                    return SimpleNamespace(
                        returncode=2,
                        stdout="",
                        stderr="Usage: planfile ticket [OPTIONS] COMMAND [ARGS]...\n"
                        "Error: No such command 'claim'.",
                    )
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
            tail_args = [_ticket_args(call) for call in planfile_calls]
            self.assertIn(
                [
                    "ticket",
                    "claim",
                    "PLF-0Y",
                    "--assigned-to",
                    "koru-test",
                    "--lease-seconds",
                    "3600",
                ],
                tail_args,
            )
            self.assertIn(["ticket", "start", "PLF-0Y"], tail_args)
            self.assertIn(["ticket", "done", "PLF-0Y"], tail_args)

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
                self.assertEqual(
                    _ticket_args(command),
                    ["ticket", "list", "--status", "open", "--format", "json"],
                )
                return _ok(json.dumps(ticket))

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-002")
            self.assertEqual(result.message, "Provide OPENROUTER_API_KEY")

    def test_missing_executor_kind_defaults_to_human_waiting_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-002B",
                "name": "Split large module: autonomous (fresh discovery)",
                "source": {"tool": "koru-manual-discovery"},
                "executor": {"mode": "interactive"},
                "inputs": {"prompt": "Work this ticket manually"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                self.assertEqual(
                    _ticket_args(command),
                    ["ticket", "list", "--status", "open", "--format", "json"],
                )
                return _ok(json.dumps(ticket))

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-002B")
            self.assertEqual(result.executor_kind, "human")

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
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
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
            # Failed shell ticket → planfile ticket block --reason "FAIL: ...".
            block_call = next(
                _ticket_args(call)
                for call in planfile_calls
                if _ticket_args(call)[:3] == ["ticket", "block", "PLF-003"]
            )
            self.assertEqual(block_call[3], "--reason")
            self.assertIn("FAIL", block_call[4])

    def test_api_ticket_runs_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-004",
                "name": "Call bootstrap API",
                "executor": {"kind": "api"},
                "inputs": {
                    "api_endpoint": "http://service.local/bootstrap",
                    "api_method": "POST",
                    "api_headers": {"authorization": "Bearer test"},
                    "api_body": {"project": "demo"},
                    "api_timeout_seconds": 5,
                },
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def api_runner(request: dict[str, object], _project: Path) -> SimpleNamespace:
                self.assertEqual(request["endpoint"], "http://service.local/bootstrap")
                self.assertEqual(request["method"], "POST")
                self.assertEqual(request["body"], {"project": "demo"})
                return SimpleNamespace(
                    returncode=0,
                    stdout='{"ok":true}',
                    stderr="",
                    status_code=200,
                    headers={},
                )

            result = run_next_planfile_task(
                project=project,
                actor="koru-api",
                planfile_runner=planfile_runner,
                api_runner=api_runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.executor_kind, "api")
            self.assertEqual(result.message, "POST http://service.local/bootstrap")
            tail_args = [_ticket_args(call) for call in planfile_calls]
            claim = [
                "ticket",
                "claim",
                "PLF-004",
                "--assigned-to",
                "koru-api",
                "--lease-seconds",
                "3600",
            ]
            self.assertIn(claim, tail_args)
            self.assertLess(tail_args.index(claim), tail_args.index(["ticket", "start", "PLF-004"]))
            self.assertIn(["ticket", "start", "PLF-004"], tail_args)
            self.assertIn(["ticket", "done", "PLF-004"], tail_args)

    def test_api_failure_marks_ticket_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-005",
                "name": "Call failing API",
                "executor": {"kind": "api", "handler": "http://service.local/fail"},
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def api_runner(_request: dict[str, object], _project: Path) -> SimpleNamespace:
                return SimpleNamespace(
                    returncode=1,
                    stdout='{"ok":false}',
                    stderr="HTTP 500",
                    status_code=500,
                    headers={},
                )

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                api_runner=api_runner,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.stderr, "HTTP 500")
            block_call = next(
                _ticket_args(call)
                for call in planfile_calls
                if _ticket_args(call)[:3] == ["ticket", "block", "PLF-005"]
            )
            self.assertEqual(block_call[3], "--reason")
            self.assertIn("FAIL", block_call[4])
            self.assertIn("HTTP 500", block_call[4])

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


def test_run_next_planfile_task_persists_queue_event(tmp_path: Path) -> None:
    ticket = {
        "id": "PLF-900",
        "name": "Persist queue event",
        "executor": {"kind": "shell", "handler": "echo ok"},
        "execution": {"state": "ready"},
    }

    def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
        if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
            return _ok(json.dumps(ticket))
        return _ok()

    def shell_runner(_command: str, _project: Path) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    result = run_next_planfile_task(
        project=tmp_path,
        planfile_runner=planfile_runner,
        shell_runner=shell_runner,
    )

    events = JsonlEventStore(tmp_path / ".koru" / "event-store.jsonl").all_events(
        context="planfile_queue"
    )

    assert result.status == "completed"
    assert [event.event_type for event in events] == ["planfile_queue.task_completed"]
    assert events[0].aggregate_id == "PLF-900"

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
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
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
                "name": "Future MCP task",
                "executor": {"kind": "mcp", "mode": "automatic"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "unsupported_executor")
            self.assertEqual(result.executor_kind, "mcp")
            self.assertEqual(result.ticket_id, "PLF-020")

    def test_shell_ticket_without_command_auto_completes(self) -> None:
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
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-030")
            # Missing script in non-interactive mode → no-op fallback "true".
            self.assertTrue(
                any(_ticket_args(call)[:3] == ["ticket", "done", "PLF-030"] for call in calls),
            )

    def test_scan_ticket_without_executor_waits_for_ide_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-040",
                "name": "Scan refactor",
                "description": "Refactor this hotspot",
                "source": {"tool": "koru-scan"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-040")
            self.assertEqual(result.executor_kind, "human")
            self.assertIn("Refactor this hotspot", result.message)

    def test_api_ticket_without_endpoint_requests_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-031",
                "name": "API with no endpoint",
                "executor": {"kind": "api"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(project=project, planfile_runner=planfile_runner)

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-031")
            self.assertTrue(
                any(
                    _ticket_args(call)[:3] == ["ticket", "block", "PLF-031"]
                    and "--reason" in _ticket_args(call)
                    for call in calls
                ),
            )

    def test_interactive_human_ticket_completes_with_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-100",
                "name": "Confirm scope",
                "executor": {"kind": "human", "mode": "interactive"},
                "inputs": {"prompt": "Confirm refactor scope"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            captured: dict[str, str] = {}

            def prompt_runner(prompt: str, ticket_id: str) -> str | None:
                captured["prompt"] = prompt
                captured["ticket_id"] = ticket_id
                return "Yes — proceed with reusable-only scope"

            result = run_next_planfile_task(
                project=project,
                actor="koru-i",
                planfile_runner=planfile_runner,
                interactive=True,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-100")
            self.assertEqual(result.executor_kind, "human")
            self.assertEqual(captured["prompt"], "Confirm refactor scope")
            self.assertEqual(captured["ticket_id"], "PLF-100")

            tail_calls = [_ticket_args(c) for c in calls]
            claim = [
                "ticket",
                "claim",
                "PLF-100",
                "--assigned-to",
                "koru-i",
                "--lease-seconds",
                "3600",
            ]
            self.assertIn(claim, tail_calls)
            self.assertLess(
                tail_calls.index(claim),
                tail_calls.index(["ticket", "start", "PLF-100"]),
            )
            self.assertIn(["ticket", "start", "PLF-100"], tail_calls)
            self.assertIn(["ticket", "done", "PLF-100"], tail_calls)
            # Answer is captured by koru's run log (not a planfile flag),
            # but the QueueRunResult.message preserves it for the caller.
            self.assertEqual(result.message, "Yes — proceed with reusable-only scope")

    def test_interactive_human_ticket_cancellation_leaves_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-101",
                "name": "Cancelled prompt",
                "executor": {"kind": "human"},
                "inputs": {"prompt": "Should we proceed?"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def prompt_runner(_prompt: str, _ticket_id: str) -> str | None:
                return None  # user cancelled

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                interactive=True,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.ticket_id, "PLF-101")
            for command in calls:
                args = _ticket_args(command)
                self.assertNotIn(args[1], {"start", "done", "block"})

    def test_interactive_with_dry_run_does_not_prompt(self) -> None:
        """Dry-run takes precedence over --interactive for safety."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-102",
                "name": "No-op",
                "executor": {"kind": "human"},
                "inputs": {"prompt": "Confirm?"},
            }

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            prompt_calls = 0

            def prompt_runner(_prompt: str, _ticket_id: str) -> str | None:
                nonlocal prompt_calls
                prompt_calls += 1
                return "should not be called"

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                interactive=True,
                dry_run=True,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(prompt_calls, 0)


class TestPlanfileQueueLlm(unittest.TestCase):
    """Tests for the executor.kind=llm path."""

    def _llm_ticket(self, **overrides) -> dict:
        ticket = {
            "id": "LLM-001",
            "name": "Decide refactor scope",
            "executor": {"kind": "llm", "mode": "automatic"},
            "inputs": {
                "prompt": "Should we move only reusable code to packages/?",
                "llm_model": "openai/gpt-4o-mini",
            },
        }
        if overrides:
            ticket = {**ticket, **overrides}
        return ticket

    def test_llm_ticket_runs_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = self._llm_ticket()
            calls: list[list[str]] = []

            def planfile_runner(command, _project) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            captured: dict[str, dict] = {}

            def llm_runner(request: dict, _project) -> SimpleNamespace:
                captured["request"] = request
                return SimpleNamespace(
                    returncode=0,
                    stdout="Yes — move only reusable code to packages/.",
                    stderr="",
                    status_code=200,
                    model="openai/gpt-4o-mini",
                    usage={"prompt_tokens": 42, "completion_tokens": 18},
                )

            result = run_next_planfile_task(
                project=project,
                actor="koru-llm",
                planfile_runner=planfile_runner,
                llm_runner=llm_runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.executor_kind, "llm")
            self.assertEqual(result.ticket_id, "LLM-001")
            # llm_runner received the parsed prompt + model
            self.assertEqual(
                captured["request"]["prompt"],
                "Should we move only reusable code to packages/?",
            )
            self.assertEqual(captured["request"]["model"], "openai/gpt-4o-mini")
            tail = [_ticket_args(c) for c in calls]
            claim = [
                "ticket",
                "claim",
                "LLM-001",
                "--assigned-to",
                "koru-llm",
                "--lease-seconds",
                "3600",
            ]
            self.assertIn(claim, tail)
            self.assertLess(tail.index(claim), tail.index(["ticket", "start", "LLM-001"]))
            self.assertIn(["ticket", "start", "LLM-001"], tail)
            self.assertIn(["ticket", "done", "LLM-001"], tail)
            # LLM-specific fields are preserved on QueueRunResult so the
            # run-log writer can persist them.
            self.assertIn("Yes", result.stdout)

    def test_llm_ticket_failure_marks_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = self._llm_ticket()
            calls: list[list[str]] = []

            def planfile_runner(command, _project) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def llm_runner(_request, _project) -> SimpleNamespace:
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="HTTP 401: invalid api key",
                    status_code=401,
                    model="openai/gpt-4o-mini",
                    usage={},
                )

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                llm_runner=llm_runner,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.executor_kind, "llm")
            tail = [_ticket_args(c) for c in calls]
            block_call = next(args for args in tail if args[:3] == ["ticket", "block", "LLM-001"])
            self.assertEqual(block_call[3], "--reason")
            self.assertIn("FAIL", block_call[4])
            self.assertIn("HTTP 401", block_call[4])

    def test_llm_ticket_without_prompt_requests_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "LLM-002",
                # name & description empty -> no prompt at all
                "name": "",
                "description": "",
                "executor": {"kind": "llm"},
                "inputs": {"llm_model": "openai/gpt-4o-mini"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command, _project) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            def llm_runner(_request, _project) -> SimpleNamespace:
                self.fail("llm_runner should NOT be called when prompt is missing")

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                llm_runner=llm_runner,
            )

            self.assertEqual(result.status, "waiting_input")
            self.assertEqual(result.executor_kind, "llm")
            self.assertTrue(
                any(
                    _ticket_args(c)[:3] == ["ticket", "block", "LLM-002"]
                    and "--reason" in _ticket_args(c)
                    for c in calls
                ),
            )

    def test_llm_dry_run_returns_request_without_calling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = self._llm_ticket()

            def planfile_runner(command, _project) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            llm_calls = 0

            def llm_runner(_request, _project) -> SimpleNamespace:
                nonlocal llm_calls
                llm_calls += 1
                return SimpleNamespace(
                    returncode=0,
                    stdout="x",
                    stderr="",
                    status_code=200,
                    model="x",
                    usage={},
                )

            result = run_next_planfile_task(
                project=project,
                dry_run=True,
                planfile_runner=planfile_runner,
                llm_runner=llm_runner,
            )

            self.assertEqual(result.status, "dry_run")
            self.assertEqual(llm_calls, 0)
            payload = json.loads(result.message)
            self.assertEqual(payload["model"], "openai/gpt-4o-mini")
            self.assertEqual(
                payload["prompt"],
                "Should we move only reusable code to packages/?",
            )

    def test_llm_default_runner_without_api_key_returns_clear_error(self) -> None:
        """When OPENROUTER_API_KEY is unset, the default runner must
        refuse to make a network call and return a helpful error."""
        from koru.queue.runners import run_llm_request as _run_llm_request

        env_backup = {
            k: os.environ.pop(k, None)
            for k in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "KORU_LLM_ENDPOINT")
        }
        try:
            request = {"prompt": "hi", "model": "openai/gpt-4o-mini"}
            result = _run_llm_request(request, Path("/tmp"))
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.status_code, 0)
        self.assertIn("OPENROUTER_API_KEY", result.stderr)


class TestPlanfileQueueLoop(unittest.TestCase):
    """Tests for run_planfile_queue_loop — the queue-draining driver."""

    def _make_runner(self, ticket_sequence: list[dict | None]):
        """Build a planfile_runner that returns each ticket in sequence on
        successive 'ticket next' calls, and acks all other commands.
        ``None`` entries cause 'No runnable ticket found'."""
        next_calls = {"i": 0}
        all_calls: list[list[str]] = []

        def planfile_runner(command: list[str], _project) -> SimpleNamespace:
            all_calls.append(command)
            if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                idx = next_calls["i"]
                next_calls["i"] += 1
                if idx >= len(ticket_sequence) or ticket_sequence[idx] is None:
                    return _ok("No runnable ticket found.")
                return _ok(json.dumps(ticket_sequence[idx]))
            return _ok()

        return planfile_runner, all_calls

    def test_loop_drains_three_shell_tickets_to_idle(self) -> None:
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)

            def make_ticket(tid: str) -> dict:
                return {
                    "id": tid,
                    "name": tid,
                    "executor": {"kind": "shell", "handler": "echo " + tid},
                }

            sequence = [make_ticket("L-1"), make_ticket("L-2"), make_ticket("L-3"), None]
            planfile_runner, _ = self._make_runner(sequence)

            def shell_runner(_cmd: str, _project) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, _tid) -> str | None:
                return None

            iterations_seen: list[int] = []
            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
                progress_callback=lambda r, i: iterations_seen.append(i),
            )

            self.assertEqual(result.iterations, 4)
            self.assertEqual(result.completed, ["L-1", "L-2", "L-3"])
            self.assertEqual(result.failed, [])
            self.assertEqual(result.waiting, [])
            self.assertEqual(result.last_status, "idle")
            self.assertEqual(iterations_seen, [1, 2, 3, 4])

    def test_loop_breaks_on_waiting_input_without_interactive(self) -> None:
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            shell_t = {
                "id": "L-10",
                "name": "shell first",
                "executor": {"kind": "shell", "handler": "echo a"},
            }
            human_t = {
                "id": "L-11",
                "name": "human prompt",
                "executor": {"kind": "human"},
                "inputs": {"prompt": "Need decision"},
            }
            never_reached = {
                "id": "L-12",
                "name": "should not run",
                "executor": {"kind": "shell", "handler": "echo c"},
            }
            planfile_runner, _ = self._make_runner([shell_t, human_t, never_reached, None])

            def shell_runner(_cmd, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, _tid) -> str | None:
                return None

            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.completed, ["L-10"])
            self.assertEqual(result.waiting, ["L-11"])
            self.assertEqual(result.last_status, "waiting_input")
            self.assertEqual(result.last_ticket_id, "L-11")
            self.assertEqual(result.ticket_id, "L-11")
            self.assertEqual(result.iterations, 2)  # never_reached not seen

    def test_loop_continues_past_failed_ticket(self) -> None:
        """A failing ticket should not stop the loop — next ticket runs."""
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            failing = {
                "id": "L-20",
                "name": "failing",
                "executor": {"kind": "shell", "handler": "false"},
            }
            ok_one = {
                "id": "L-21",
                "name": "ok",
                "executor": {"kind": "shell", "handler": "true"},
            }
            planfile_runner, _ = self._make_runner([failing, ok_one, None])

            def shell_runner(cmd: str, _proj) -> SimpleNamespace:
                if cmd == "false":
                    return SimpleNamespace(returncode=1, stdout="", stderr="boom")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, _tid) -> str | None:
                return None

            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.failed, ["L-20"])
            self.assertEqual(result.completed, ["L-21"])
            self.assertEqual(result.last_status, "idle")
            self.assertEqual(result.iterations, 3)

    def test_loop_respects_max_iterations_cap(self) -> None:
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            tickets = [
                {
                    "id": f"L-{n}",
                    "name": f"task {n}",
                    "executor": {"kind": "shell", "handler": "echo " + str(n)},
                }
                for n in range(10)
            ]
            planfile_runner, _ = self._make_runner(tickets)

            def shell_runner(_cmd, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, _tid) -> str | None:
                return None

            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
                max_iterations=3,
            )

            self.assertEqual(result.iterations, 3)
            self.assertEqual(len(result.completed), 3)
            self.assertEqual(result.last_status, "completed")
            self.assertEqual(result.last_ticket_id, "L-2")
            self.assertEqual(result.ticket_id, "L-2")

    def test_loop_stop_callback_drains_after_current_iteration(self) -> None:
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            tickets = [
                {
                    "id": "L-40",
                    "name": "first",
                    "executor": {"kind": "shell", "handler": "echo first"},
                },
                {
                    "id": "L-41",
                    "name": "second",
                    "executor": {"kind": "shell", "handler": "echo second"},
                },
            ]
            planfile_runner, _ = self._make_runner(tickets)

            def shell_runner(_cmd, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, _tid) -> str | None:
                return None

            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
                stop_callback=lambda _result, iteration: iteration == 1,
            )

            self.assertEqual(result.iterations, 1)
            self.assertEqual(result.completed, ["L-40"])
            self.assertEqual(result.last_status, "completed")
            self.assertEqual(result.last_ticket_id, "L-40")

    def test_loop_with_interactive_drains_human_tickets(self) -> None:
        from koru.queue import run_planfile_queue_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            sequence = [
                {
                    "id": "L-30",
                    "name": "first human",
                    "executor": {"kind": "human"},
                    "inputs": {"prompt": "decide A?"},
                },
                {
                    "id": "L-31",
                    "name": "second human",
                    "executor": {"kind": "human"},
                    "inputs": {"prompt": "decide B?"},
                },
                None,
            ]
            planfile_runner, _ = self._make_runner(sequence)

            def shell_runner(_cmd, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def api_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def llm_runner(_req, _proj) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            def prompt_runner(_p, tid: str) -> str | None:
                return f"answer for {tid}"

            result = run_planfile_queue_loop(
                project=project,
                planfile_runner=planfile_runner,
                interactive=True,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
            )

            self.assertEqual(result.completed, ["L-30", "L-31"])
            self.assertEqual(result.waiting, [])
            self.assertEqual(result.last_status, "idle")

    def test_loop_validates_max_iterations(self) -> None:
        from koru.queue import run_planfile_queue_loop

        def planfile_runner(_cmd, _proj) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        def shell_runner(_cmd, _proj) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        def api_runner(_req, _proj) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        def llm_runner(_req, _proj) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        def prompt_runner(_p, _tid) -> str | None:
            return None

        with self.assertRaisesRegex(ValueError, "max_iterations"):
            run_planfile_queue_loop(
                project=Path("/tmp"),
                max_iterations=0,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                api_runner=api_runner,
                llm_runner=llm_runner,
                prompt_runner=prompt_runner,
            )


class TestAppendShellEvidenceNote(unittest.TestCase):
    """Regression: planfile CLIs without ``--note`` still persist shell evidence."""

    def test_short_flag_when_long_option_unsupported(self) -> None:
        from koru.queue.planfile_ticket_note import append_shell_evidence_note

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _p: Path) -> SimpleNamespace:
                calls.append(command)
                ta = _ticket_args(command)
                if len(ta) >= 5 and ta[:3] == ["ticket", "update", "PLF-X"] and ta[3] == "--note":
                    return SimpleNamespace(
                        returncode=2,
                        stdout="",
                        stderr="No such option: --note",
                    )
                return _ok()

            res, kind = append_shell_evidence_note(
                project,
                "PLF-X",
                "evidence-body",
                run_id="run1",
                planfile_runner=planfile_runner,
            )
            self.assertEqual(res.returncode, 0)
            self.assertEqual(kind, "cli")
            updates = [
                _ticket_args(c)
                for c in calls
                if _ticket_args(c)[:3] == ["ticket", "update", "PLF-X"]
            ]
            self.assertEqual(len(updates), 2)
            self.assertEqual(updates[0][3], "--note")
            self.assertEqual(updates[1][3], "-n")
            self.assertEqual(updates[1][4], "evidence-body")

    def test_artifact_when_both_note_flags_missing(self) -> None:
        from koru.queue.planfile_ticket_note import append_shell_evidence_note

        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)

            def planfile_runner(command: list[str], _p: Path) -> SimpleNamespace:
                ta = _ticket_args(command)
                if len(ta) >= 5 and ta[:3] == ["ticket", "update", "PLF-Y"]:
                    if ta[3] == "--note":
                        return SimpleNamespace(
                            returncode=2,
                            stdout="",
                            stderr="No such option: --note",
                        )
                    if ta[3] == "-n":
                        return SimpleNamespace(
                            returncode=2,
                            stdout="",
                            stderr="No such option: -n",
                        )
                return _ok()

            res, kind = append_shell_evidence_note(
                project,
                "PLF-Y",
                "artifact-payload",
                run_id="ab12",
                planfile_runner=planfile_runner,
            )
            self.assertEqual(res.returncode, 0)
            self.assertEqual(kind, "artifact")
            path = project / ".planfile" / ".koru" / "runs" / "PLF-Y-ab12.shell-evidence.txt"
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_text(encoding="utf-8"), "artifact-payload")
            self.assertIn(str(path), res.stdout)


if __name__ == "__main__":
    unittest.main()
