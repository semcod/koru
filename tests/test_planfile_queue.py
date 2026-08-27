from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from koru.cqrs.event_store import JsonlEventStore
from koru.queue import run_next_planfile_task
from koru.queue.ticket import (
    _configured_planfile_cmd_usable,
    _planfile_supports_structured_queue_json,
    parse_next_ticket,
    planfile_command,
)
from tests import _repolab


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


class TestPlanfileCommand(unittest.TestCase):
    def test_structured_queue_probe_handles_non_utf8_bytes(self) -> None:
        _planfile_supports_structured_queue_json.cache_clear()
        with patch(
            "koru.queue.ticket.subprocess.run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout=b"planfile wersja \xf3 0.1.101",
                stderr=b"",
            ),
        ) as run:
            self.assertTrue(_planfile_supports_structured_queue_json("/tmp/planfile"))
        self.assertFalse(run.call_args.kwargs["text"])
        _planfile_supports_structured_queue_json.cache_clear()
        with patch(
            "koru.queue.ticket.subprocess.run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout=b"planfile wersja \xf3 0.1.99",
                stderr=b"",
            ),
        ):
            self.assertFalse(_planfile_supports_structured_queue_json("/tmp/planfile-old"))

    def test_configured_command_probe_handles_non_utf8_module_missing_marker(self) -> None:
        _configured_planfile_cmd_usable.cache_clear()
        with patch(
            "koru.queue.ticket.subprocess.run",
            return_value=SimpleNamespace(
                returncode=1,
                stdout=b"",
                stderr=b"\xf3 no module named 'planfile.cli'",
            ),
        ) as run:
            self.assertFalse(_configured_planfile_cmd_usable("/tmp/venv/bin/python -m planfile.cli"))
        self.assertFalse(run.call_args.kwargs["text"])
        _configured_planfile_cmd_usable.cache_clear()
        with patch(
            "koru.queue.ticket.subprocess.run",
            return_value=SimpleNamespace(
                returncode=0,
                stdout=b"\xf3 planfile 0.1.101",
                stderr=b"",
            ),
        ):
            self.assertTrue(_configured_planfile_cmd_usable("/tmp/venv/bin/python -m planfile.cli"))

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

            with (
                patch("koru.queue.ticket.find_spec", return_value=object()),
                patch(
                    "koru.queue.ticket.shutil.which",
                    return_value="/tmp/other-venv/bin/planfile",
                ),
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

            with (
                patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec),
                patch(
                    "koru.queue.ticket.shutil.which",
                    return_value="/tmp/other-venv/bin/planfile",
                ),
            ):
                planfile_command(project, ["ticket", "list"], runner=runner)

            self.assertEqual(calls[0], [str(local), "ticket", "list"])

    def test_skips_local_planfile_too_old_for_structured_queue_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project = root / "koru"
            old_local = project / "venv" / "bin" / "planfile"
            old_local.parent.mkdir(parents=True)
            old_local.write_text("#!/bin/sh\n", encoding="utf-8")
            old_local.chmod(0o755)
            calls: list[list[str]] = []

            def runner(command, _project):
                calls.append(list(command))
                return _ok()

            with (
                patch(
                    "koru.queue.ticket._planfile_executable_candidates",
                    return_value=(old_local,),
                ),
                patch(
                    "koru.queue.ticket._planfile_supports_structured_queue_json",
                    side_effect=lambda executable: executable == "/usr/bin/planfile",
                ),
                patch("koru.queue.ticket._module_cli_command_for_project", return_value=None),
                patch(
                    "koru.queue.ticket.shutil.which",
                    return_value="/usr/bin/planfile",
                ),
            ):
                planfile_command(project, ["ticket", "list"], runner=runner)

            self.assertEqual(calls[0], ["/usr/bin/planfile", "ticket", "list"])

    def test_prefers_planfile_checkout_near_koru_source_for_external_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project = root / "maskservice" / "c2004"
            checkout_root = root / "semcod"
            local = checkout_root / "planfile" / "venv" / "bin" / "planfile"
            local.parent.mkdir(parents=True)
            local.write_text("#!/bin/sh\n", encoding="utf-8")
            local.chmod(0o755)
            calls: list[list[str]] = []

            def runner(command, _project):
                calls.append(list(command))
                return _ok()

            with (
                patch(
                    "koru.queue.ticket._source_planfile_search_roots",
                    return_value=(checkout_root,),
                ),
                patch("koru.queue.ticket.find_spec", return_value=None),
                patch(
                    "koru.queue.ticket.shutil.which",
                    return_value="/tmp/old/bin/planfile",
                ),
            ):
                planfile_command(project, ["ticket", "done", "PLF-1"], runner=runner)

            self.assertEqual(calls[0], [str(local), "ticket", "done", "PLF-1"])

    def test_prefers_project_venv_python_before_sys_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            venv_python = project / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("#!/bin/sh\n", encoding="utf-8")
            venv_python.chmod(0o755)
            calls: list[list[str]] = []

            def runner(command, _project):
                calls.append(list(command))
                return _ok()

            with (
                patch(
                    "koru.queue.ticket._python_has_planfile_cli",
                    side_effect=lambda python: python == str(venv_python),
                ),
                patch("koru.queue.ticket._local_planfile_executable", return_value=None),
                patch(
                    "koru.queue.ticket._has_planfile_cli_module",
                    return_value=True,
                ),
                patch(
                    "koru.queue.ticket.shutil.which",
                    return_value=None,
                ),
            ):
                planfile_command(project, ["ticket", "list"], runner=runner)

            self.assertEqual(
                calls[0],
                [str(venv_python), "-m", "planfile.cli", "ticket", "list"],
            )

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

        with (
            patch("koru.queue.ticket._local_planfile_executable", return_value=None),
            patch(
                "koru.queue.ticket._module_cli_command_for_project",
                return_value=None,
            ),
            patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec),
            patch(
                "koru.queue.ticket.shutil.which",
                return_value="/usr/bin/planfile",
            ),
        ):
            planfile_command(Path("/tmp"), ["ticket", "list"], runner=runner)

        self.assertEqual(calls[0], ["/usr/bin/planfile", "ticket", "list"])

    def test_retries_planfile_file_lock_timeout(self) -> None:
        calls: list[list[str]] = []

        def runner(command, _project):
            calls.append(list(command))
            if len(calls) < 3:
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr=(
                        "Timeout: The file lock "
                        "'/repo/.planfile/sprints/current.yaml.lock' could not be acquired."
                    ),
                )
            return _ok("[]")

        with (
            patch.dict(os.environ, {"KORU_PLANFILE_CMD": "/good/planfile"}),
            patch("koru.queue.ticket.time.sleep") as sleep,
        ):
            result = planfile_command(Path("/tmp"), ["ticket", "list"], runner=runner)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0], ["/good/planfile", "ticket", "list"])
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.25, 0.5])

    def test_module_cli_probe_treats_missing_parent_as_missing(self) -> None:
        calls: list[list[str]] = []

        def runner(command, _project):
            calls.append(list(command))
            return _ok()

        def fake_find_spec(name: str):
            if name == "planfile.cli":
                raise ModuleNotFoundError("No module named 'planfile'")
            return None

        with (
            patch("koru.queue.ticket._local_planfile_executable", return_value=None),
            patch(
                "koru.queue.ticket._module_cli_command_for_project",
                return_value=None,
            ),
            patch("koru.queue.ticket.find_spec", side_effect=fake_find_spec),
            patch(
                "koru.queue.ticket.shutil.which",
                return_value="/usr/bin/planfile",
            ),
        ):
            planfile_command(Path("/tmp"), ["ticket", "list"], runner=runner)

        self.assertEqual(calls[0], ["/usr/bin/planfile", "ticket", "list"])


class TestPlanfileQueue(unittest.TestCase):
    def test_exact_target_executes_requested_open_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            tickets = [
                {
                    "id": "PLF-FIRST",
                    "name": "Higher priority task",
                    "status": "open",
                    "priority": "critical",
                    "executor": {"kind": "shell", "handler": "echo first"},
                },
                {
                    "id": "PLF-TARGET",
                    "name": "Requested task",
                    "status": "open",
                    "priority": "normal",
                    "executor": {"kind": "shell", "handler": "echo target"},
                },
            ]
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                if _ticket_args(command)[:5] == [
                    "ticket",
                    "list",
                    "--status",
                    "open",
                    "--format",
                ]:
                    return _ok(json.dumps(tickets))
                return _ok()

            def shell_runner(command: str, _project: Path) -> SimpleNamespace:
                self.assertEqual(command, "echo target")
                return SimpleNamespace(returncode=0, stdout="target\n", stderr="")

            result = run_next_planfile_task(
                project=project,
                target_ticket_id="PLF-TARGET",
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-TARGET")
            lifecycle = [_ticket_args(call) for call in planfile_calls]
            self.assertNotIn(["ticket", "start", "PLF-FIRST"], lifecycle)
            self.assertIn(["ticket", "start", "PLF-TARGET"], lifecycle)

    def test_missing_exact_target_does_not_run_next_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-NEXT",
                "name": "Next task",
                "status": "open",
                "executor": {"kind": "shell", "handler": "echo next"},
            }
            planfile_calls: list[list[str]] = []
            shell_calls: list[str] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                return _ok(json.dumps([ticket]))

            def shell_runner(command: str, _project: Path) -> SimpleNamespace:
                shell_calls.append(command)
                return _ok()

            result = run_next_planfile_task(
                project=project,
                target_ticket_id="PLF-MISSING",
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )

            self.assertEqual(result.status, "target_not_runnable")
            self.assertEqual(result.ticket_id, "PLF-MISSING")
            self.assertEqual(shell_calls, [])
            self.assertEqual(len(planfile_calls), 1)

    def test_llm_preflight_failure_precedes_ticket_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-LLM",
                "name": "Refactor safely",
                "status": "open",
                "executor": {"kind": "llm"},
                "inputs": {"prompt": "Refactor the declared module"},
            }
            planfile_calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                planfile_calls.append(command)
                return _ok(json.dumps([ticket]))

            with patch(
                "koru.queue.runner.preflight_llm_request",
                return_value=(False, "SubLLM route unavailable"),
            ):
                result = run_next_planfile_task(
                    project=project,
                    target_ticket_id="PLF-LLM",
                    planfile_runner=planfile_runner,
                )

            self.assertEqual(result.status, "infrastructure_error")
            self.assertEqual(result.ticket_id, "PLF-LLM")
            lifecycle = [_ticket_args(call) for call in planfile_calls]
            self.assertEqual(
                lifecycle,
                [["ticket", "list", "--status", "open", "--format", "json"]],
            )

    def test_shell_ticket_runs_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-001",
                "name": "Run bootstrap",
                "executor": {"kind": "shell", "handler": "echo ok"},
                "execution": {"queue": "c2004-refactor", "state": "ready"},
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

    def test_queue_name_filters_open_tickets_before_priority_sort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            tickets = [
                {
                    "id": "PLF-OP",
                    "name": "Operator calibration",
                    "status": "open",
                    "priority": "critical",
                    "executor": {"kind": "human"},
                    "execution": {"queue": "operator", "state": "ready"},
                    "inputs": {"prompt": "Do operator work"},
                },
                {
                    "id": "PLF-DEF",
                    "name": "Default queue shell",
                    "status": "open",
                    "priority": "normal",
                    "executor": {"kind": "shell", "handler": "echo ok"},
                    "execution": {"queue": "default", "state": "ready"},
                },
            ]

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(tickets))
                return _ok()

            def shell_runner(command: str, _project: Path) -> SimpleNamespace:
                self.assertEqual(command, "echo ok")
                return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
                queue_name="default",
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticket_id, "PLF-DEF")

    def test_queue_name_returns_idle_when_no_ticket_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            tickets = [
                {
                    "id": "PLF-OP",
                    "name": "Operator calibration",
                    "status": "open",
                    "priority": "critical",
                    "executor": {"kind": "human"},
                    "execution": {"queue": "operator", "state": "ready"},
                    "inputs": {"prompt": "Do operator work"},
                }
            ]

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(tickets))
                return _ok()

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                queue_name="default",
            )

            self.assertEqual(result.status, "idle")
            self.assertIsNone(result.ticket_id)

    def test_default_queue_skips_implicit_wup_auto_diag_ticket(self) -> None:
        tickets = [
            {
                "id": "PLF-WUP",
                "name": "[AUTO-DIAG] wup-frontend visual down",
                "status": "open",
                "priority": "critical",
                "labels": ["wup", "auto-diag", "llm-ready"],
                "source": {"tool": "wup"},
            },
            {
                "id": "PLF-DEF",
                "name": "Default queue shell",
                "status": "open",
                "priority": "normal",
                "executor": {"kind": "shell", "handler": "echo ok"},
                "execution": {"queue": "default", "state": "ready"},
            },
        ]

        ticket = parse_next_ticket(json.dumps(tickets), queue_name="default")

        self.assertIsNotNone(ticket)
        self.assertEqual(ticket["id"], "PLF-DEF")

    def test_default_queue_accepts_explicit_wup_auto_diag_ticket(self) -> None:
        ticket = {
            "id": "PLF-WUP",
            "name": "[AUTO-DIAG] wup-frontend visual down",
            "status": "open",
            "priority": "critical",
            "labels": ["wup", "auto-diag", "llm-ready"],
            "source": {"tool": "wup"},
            "execution": {"queue": "default", "state": "ready"},
        }

        picked = parse_next_ticket(json.dumps(ticket), queue_name="default")

        self.assertIsNotNone(picked)
        self.assertEqual(picked["id"], "PLF-WUP")

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

    def test_shell_failure_is_reopened_while_attempt_budget_remains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-003R",
                "name": "Retry transient failure",
                "executor": {"kind": "shell", "handler": "false"},
                "execution": {"attempt": 0, "max_attempts": 3, "state": "ready"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=lambda *_args: SimpleNamespace(
                    returncode=1, stdout="", stderr="temporary failure",
                ),
            )

            tail = [_ticket_args(call) for call in calls]
            assert result.status == "failed"
            assert ["ticket", "fail", "PLF-003R", "--error", "FAIL: temporary failure"] in tail
            ready = next(args for args in tail if args[:3] == ["ticket", "ready", "PLF-003R"])
            assert "retry 2/3" in ready[4].lower()
            assert ["ticket", "update", "PLF-003R", "--status", "open"] in tail
            assert not any(args[:3] == ["ticket", "block", "PLF-003R"] for args in tail)

    def test_shell_failure_blocks_after_last_allowed_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project = Path(tmp_dir)
            ticket = {
                "id": "PLF-003X",
                "name": "Exhaust retries",
                "executor": {"kind": "shell", "handler": "false"},
                "execution": {"attempt": 2, "max_attempts": 3, "state": "ready"},
            }
            calls: list[list[str]] = []

            def planfile_runner(command: list[str], _project: Path) -> SimpleNamespace:
                calls.append(command)
                if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                    return _ok(json.dumps(ticket))
                return _ok()

            result = run_next_planfile_task(
                project=project,
                planfile_runner=planfile_runner,
                shell_runner=lambda *_args: SimpleNamespace(
                    returncode=1, stdout="", stderr="permanent failure",
                ),
            )

            tail = [_ticket_args(call) for call in calls]
            assert result.status == "failed"
            assert ["ticket", "fail", "PLF-003X", "--error", "FAIL: permanent failure"] in tail
            assert any(args[:3] == ["ticket", "block", "PLF-003X"] for args in tail)
            assert not any(args[:3] == ["ticket", "ready", "PLF-003X"] for args in tail)

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
            # Model selection is owned by the strict SubLLM route.
            self.assertEqual(
                captured["request"]["prompt"],
                "Should we move only reusable code to packages/?",
            )
            self.assertNotIn("model", captured["request"])
            self.assertNotIn("max_tokens", captured["request"])
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

    def test_llm_answer_persisted_as_ticket_note(self) -> None:
        """The model answer must land on the ticket, not be discarded."""
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
                    returncode=0,
                    stdout="Move only reusable code to packages/.",
                    stderr="",
                    status_code=200,
                    model="openai/gpt-4o-mini",
                    usage={},
                )

            result = run_next_planfile_task(
                project=project,
                actor="koru-llm",
                planfile_runner=planfile_runner,
                llm_runner=llm_runner,
            )

            self.assertEqual(result.status, "completed")
            notes = [
                _ticket_args(c)
                for c in calls
                if _ticket_args(c)[:3] == ["ticket", "update", "LLM-001"]
            ]
            self.assertTrue(notes, "expected a ticket update --note call with the answer")
            note_text = notes[0][4]
            self.assertTrue(note_text.startswith("KORU-LLM-RUN"), note_text[:60])
            self.assertIn("Move only reusable code to packages/.", note_text)
            # note lands before the ticket is marked done
            tail = [_ticket_args(c) for c in calls]
            self.assertLess(tail.index(notes[0]), tail.index(["ticket", "done", "LLM-001"]))

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
            self.assertNotIn("model", payload)
            self.assertNotIn("max_tokens", payload)
            self.assertEqual(
                payload["prompt"],
                "Should we move only reusable code to packages/?",
            )

    _LLM_ENV_KEYS = (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "KORU_LLM_ENDPOINT",
        "KORU_LLM_PROVIDER",
        "KORU_LLM_SHELL_FALLBACK",
        "KORU_TILLM_CLIENT",
    )

    @contextlib.contextmanager
    def _clean_llm_env(self, **overrides: str):
        """Run with every LLM-selecting env var cleared, plus overrides."""
        backup = {k: os.environ.pop(k, None) for k in self._LLM_ENV_KEYS}
        os.environ.update(overrides)
        try:
            yield
        finally:
            for key in overrides:
                os.environ.pop(key, None)
            for key, value in backup.items():
                if value is not None:
                    os.environ[key] = value

    def test_llm_default_runner_requires_central_subllm_transport(self) -> None:
        from koru.queue import runners as runners_mod

        with self._clean_llm_env():
            request = {"prompt": "hi"}
            result = runners_mod.run_llm_request(request, Path("/tmp"))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.status_code, 0)
        self.assertTrue(
            "SubLLM transport is unavailable" in result.stderr
            or "SubLLM refused or failed" in result.stderr,
        )

    def test_llm_does_not_fallback_to_vendor_cli(self) -> None:
        from koru.queue import runners as runners_mod

        captured: dict[str, object] = {}

        def fake_drive(**kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {"ok": True, "exit_code": 0, "stdout": "done", "stderr": ""}

        with self._clean_llm_env(), patch.object(
            runners_mod.shutil, "which", side_effect=lambda cmd: cmd == "claude",
        ), patch("koru.tillm_bridge.drive_shell_chat", fake_drive):
            result = runners_mod.run_llm_request({"prompt": "hi"}, Path("/tmp"))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(captured, {})

    def test_llm_ignores_legacy_provider_override(self) -> None:
        from koru.queue import runners as runners_mod

        captured: dict[str, object] = {}

        def fake_drive(**kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {"ok": True, "exit_code": 0, "stdout": "ok", "stderr": ""}

        with self._clean_llm_env(), patch(
            "koru.tillm_bridge.drive_shell_chat", fake_drive,
        ):
            result = runners_mod.run_llm_request(
                {"prompt": "hi", "provider": "claude"}, Path("/tmp"),
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(captured, {})

    def test_normalize_openrouter_model_strips_registry_prefix(self) -> None:
        from koru.queue import runners as runners_mod

        normalized = runners_mod._normalize_llm_model(
            "openrouter/qwen/qwen3.7-plus",
            "https://openrouter.ai/api/v1/chat/completions",
        )
        self.assertEqual(normalized, "qwen/qwen3.7-plus")


class TestQueueEditVerification(unittest.TestCase):
    """An agent that exits 0 without editing anything must not close a ticket.

    Reproduces the real failure: `claude -p` hit a permission prompt, refused,
    described the change instead of making it, and exited 0 — and the queue
    marked the refactor done while the file was untouched."""

    def _ticket(self, **overrides: object) -> dict:
        ticket = {
            "id": "SBX-001",
            "labels": ["koru", "llm-ready", "refactor"],
            "files": ["src/router.mjs"],
            "inputs": {"prompt": "refactor it"},
        }
        ticket.update(overrides)
        return ticket

    def test_refactor_ticket_expects_edits_by_default(self) -> None:
        from koru.queue.runner import _ticket_expects_edits

        self.assertTrue(_ticket_expects_edits(self._ticket()))
        self.assertTrue(_ticket_expects_edits(self._ticket(labels=["todo2code", "code-change"])))
        self.assertFalse(_ticket_expects_edits(self._ticket(labels=["deploy"])))

    def test_explicit_flag_overrides_label_heuristic(self) -> None:
        from koru.queue.runner import _ticket_expects_edits

        opted_out = self._ticket(inputs={"expect_files_changed": False})
        self.assertFalse(_ticket_expects_edits(opted_out))
        opted_in = self._ticket(labels=["deploy"], inputs={"expect_files_changed": True})
        self.assertTrue(_ticket_expects_edits(opted_in))

    def test_unchanged_file_is_reported_as_failure(self) -> None:
        from koru.queue.runner import (
            _snapshot_declared_files,
            _verify_declared_files_changed,
        )

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = project / "src" / "router.mjs"
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")
            ticket = self._ticket()

            before = _snapshot_declared_files(project, ticket)
            reason = _verify_declared_files_changed(project, ticket, before)
            self.assertIsNotNone(reason)
            self.assertIn("src/router.mjs", reason or "")

            target.write_text("refactored", encoding="utf-8")
            self.assertIsNone(_verify_declared_files_changed(project, ticket, before))

    def test_creating_a_missing_declared_file_counts_as_a_change(self) -> None:
        from koru.queue.runner import (
            _snapshot_declared_files,
            _verify_declared_files_changed,
        )

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ticket = self._ticket(files=["src/new-module.mjs"])
            before = _snapshot_declared_files(project, ticket)

            created = project / "src" / "new-module.mjs"
            created.parent.mkdir(parents=True)
            created.write_text("export const x = 1;\n", encoding="utf-8")
            self.assertIsNone(_verify_declared_files_changed(project, ticket, before))


from koru.queue.patch_mode import (  # noqa: E402
    MANIFEST_MISMATCH,
    MANIFEST_NOT_PERSISTED,
    NO_PATCH_EMITTED,
    PATCH_INTRODUCES_SYMLINK,
    PROMOTION_CONFLICT,
    PROMOTION_REFUSED_DIRTY_REPO,
    UNSAFE_DIRTY_WORKSPACE,
    VERIFY_BASELINE_FAILED,
    VERIFY_FAILED_ISOLATED,
    VERIFY_FAILED_ROLLED_BACK,
    load_persisted_manifest,
)


class TestPatchMode(unittest.TestCase):
    """Patch mode: the agent proposes a diff, koru applies it deterministically.

    This is what lets an edit ticket run without granting the agent CLI write
    access to the workspace.

    The apply/direct pipeline is pinned explicitly here: the *default*
    promotion mode is ``branch``, and these tests exercise the apply mechanics
    (in-place write, rollback, dirty guards), which tickets now have to opt
    into. Tests with an explicit ``promotion_mode`` input override the pin."""

    def setUp(self) -> None:
        patcher = patch.dict(os.environ, {"KORU_QUEUE_PROMOTION_MODE": "apply"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _git_repo(self, tmp: str) -> Path:
        return _repolab.git_repo(tmp)

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        _repolab.commit_file(project, rel, body)

    def test_extracts_diff_from_fenced_reply(self) -> None:
        from koru.queue.patch_mode import extract_unified_diff

        reply = (
            "Here is the change you asked for:\n\n"
            "```diff\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "```\n\n"
            "Let me know if you want anything adjusted."
        )
        diff = extract_unified_diff(reply)
        self.assertIsNotNone(diff)
        self.assertIn("diff --git a/a.txt b/a.txt", diff or "")
        self.assertNotIn("Let me know", diff or "")
        self.assertTrue((diff or "").endswith("\n"))

    def test_refusal_and_prose_yield_no_diff(self) -> None:
        from koru.queue.patch_mode import extract_unified_diff

        self.assertIsNone(extract_unified_diff("NO-PATCH: the file does not exist"))
        self.assertIsNone(extract_unified_diff("I would restructure the module like this..."))
        self.assertIsNone(extract_unified_diff(""))

    def test_applies_a_valid_patch(self) -> None:
        from koru.queue.patch_mode import apply_unified_diff

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            diff = (
                "diff --git a/a.txt b/a.txt\n"
                "--- a/a.txt\n"
                "+++ b/a.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )
            result = apply_unified_diff(project, diff)
            self.assertTrue(result.ok, result.detail)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")
            self.assertIn("a.txt", result.changed_files)

    def test_stale_patch_is_refused_without_touching_the_tree(self) -> None:
        from koru.queue.patch_mode import apply_unified_diff

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "actual content\n")
            stale = (
                "diff --git a/a.txt b/a.txt\n"
                "--- a/a.txt\n"
                "+++ b/a.txt\n"
                "@@ -1 +1 @@\n"
                "-something else entirely\n"
                "+new\n"
            )
            result = apply_unified_diff(project, stale)
            self.assertFalse(result.ok)
            self.assertIn("does not apply cleanly", result.detail)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "actual content\n")

    def test_missing_file_headers_are_repaired_and_apply(self) -> None:
        """Agents often emit `diff --git` straight into `@@`, which git rejects
        as "patch fragment without header". The paths are already known, so the
        headers are reconstructed instead of failing the run."""
        from koru.queue.patch_mode import apply_unified_diff, extract_unified_diff

        reply = (
            "```diff\n"
            "diff --git a/a.txt b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "```\n"
        )
        diff = extract_unified_diff(reply)
        self.assertIsNotNone(diff)
        self.assertIn("--- a/a.txt", diff or "")
        self.assertIn("+++ b/a.txt", diff or "")

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            result = apply_unified_diff(project, diff or "")
            self.assertTrue(result.ok, result.detail)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")

    def test_existing_file_headers_are_left_alone(self) -> None:
        from koru.queue.patch_mode import extract_unified_diff

        reply = (
            "```diff\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "```\n"
        )
        diff = extract_unified_diff(reply) or ""
        self.assertEqual(diff.count("--- a/a.txt"), 1)
        self.assertEqual(diff.count("+++ b/a.txt"), 1)

    def test_miscounted_hunk_header_is_recomputed_and_applies(self) -> None:
        """Models miscount `@@` lengths, which git rejects as a corrupt patch.
        The body is authoritative, so the counts are recomputed from it."""
        from koru.queue.patch_mode import apply_unified_diff, extract_unified_diff

        reply = (
            "```diff\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1,3 +1,99 @@\n"  # deliberately wrong new-length
            " one\n"
            "+inserted\n"
            " two\n"
            " three\n"
            "```\n"
        )
        diff = extract_unified_diff(reply) or ""
        self.assertIn("@@ -1,3 +1,4 @@", diff)

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "one\ntwo\nthree\n")
            result = apply_unified_diff(project, diff)
            self.assertTrue(result.ok, result.detail)
            self.assertEqual(
                (project / "a.txt").read_text(encoding="utf-8"),
                "one\ninserted\ntwo\nthree\n",
            )

    _PATCH_REPLY = (
        "```diff\n"
        "diff --git a/a.txt b/a.txt\n"
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "```\n"
    )

    def _gate_ok(self, command: str, cwd: Path):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def test_branch_mode_commits_the_result_without_touching_the_workspace(self) -> None:
        """On a shared checkout the verified result lands on its own ref, so a
        concurrent `git add -A` elsewhere cannot absorb it into another commit."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {
                "id": "SBX-9",
                "inputs": {"verify_command": "true", "promotion_mode": "branch"},
            }

            _result, outcome = apply_proposed_patch(project, reply, ticket, self._gate_ok)

            self.assertIsNone(outcome, outcome)
            # Working tree untouched...
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            # ...but the verified change exists on its own branch.
            branches = subprocess.run(
                ["git", "branch", "--list", "koru/run-*"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout
            self.assertIn("koru/run-", branches)
            branch = branches.split()[-1]
            committed = subprocess.run(
                ["git", "show", f"{branch}:a.txt"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout
            self.assertEqual(committed, "new\n")
            # Only the patch's file is in the commit — not koru's own run
            # artifacts, which `git add -A` would otherwise sweep in.
            files = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", branch],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout.split()
            self.assertEqual(files, ["a.txt"])

    def test_artifact_mode_writes_the_patch_and_changes_nothing(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"id": "SBX-9", "inputs": {"promotion_mode": "artifact"}}

            def unused_gate(command: str, cwd: Path):
                raise AssertionError("artifact mode must not run a gate")

            _result, outcome = apply_proposed_patch(project, reply, ticket, unused_gate)

            self.assertIsNone(outcome, outcome)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            runs = list((project / ".koru" / "runs").glob("*/patch.diff"))
            self.assertEqual(len(runs), 1)
            self.assertIn("+new", runs[0].read_text(encoding="utf-8"))
            evidence = json.loads(
                (runs[0].parent / "evidence.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(evidence["ticket_id"], "SBX-9")
            self.assertEqual(evidence["targets"], ["a.txt"])

    def test_commit_mode_refuses_a_dirty_repository(self) -> None:
        """A commit must contain only this patch, which a dirty tree cannot promise."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "unrelated.txt").write_text("someone else's work\n", encoding="utf-8")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"inputs": {"verify_command": "true", "promotion_mode": "commit"}}

            _result, outcome = apply_proposed_patch(project, reply, ticket, self._gate_ok)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, PROMOTION_REFUSED_DIRTY_REPO)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_commit_mode_commits_on_clean_main_after_verify(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {
                "id": "SBX-10",
                "inputs": {"verify_command": "true", "promotion_mode": "commit"},
            }

            _result, outcome = apply_proposed_patch(project, reply, ticket, self._gate_ok)

            self.assertIsNone(outcome, outcome)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")
            log = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertIn("koru(SBX-10)", log)
            committed = subprocess.run(
                ["git", "show", "HEAD:a.txt"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout
            self.assertEqual(committed, "new\n")

    def test_manifest_is_persisted_for_patch_runs(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"id": "SBX-11", "inputs": {"verify_command": "true"}}

            _result, outcome = apply_proposed_patch(project, reply, ticket, self._gate_ok)

            self.assertIsNone(outcome, outcome)
            runs = list((project / ".koru" / "runs").glob("*/manifest.json"))
            self.assertEqual(len(runs), 1)
            manifest = json.loads(runs[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["ticket_id"], "SBX-11")
            self.assertEqual(manifest["touched_files"], ["a.txt"])
            self.assertIn("manifest_hash", manifest)
            self.assertIn("workspace_snapshot_sha256", manifest)
            self.assertIn("patch_sha256", manifest)
            self.assertEqual(manifest["dirty_files"], [])
            self.assertEqual(
                load_persisted_manifest(project, manifest["run_id"]),
                manifest,
            )

    def test_promotion_refuses_when_persisted_manifest_is_tampered(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"inputs": {"verify_command": "true"}}
            calls = {"n": 0}

            def gate_then_tamper(command: str, cwd: Path):
                calls["n"] += 1
                if calls["n"] == 2:
                    runs = list((project / ".koru" / "runs").glob("*/manifest.json"))
                    self.assertEqual(len(runs), 1)
                    tampered = json.loads(runs[0].read_text(encoding="utf-8"))
                    tampered["base_head"] = "0" * 40
                    runs[0].write_text(json.dumps(tampered), encoding="utf-8")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome = apply_proposed_patch(project, reply, ticket, gate_then_tamper)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, MANIFEST_NOT_PERSISTED)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_promotion_mode_falls_back_to_env_then_branch(self) -> None:
        """Branch-first is the default: with nothing said, the result lands on
        its own ref and the shared working tree stays untouched."""
        from koru.queue.patch_mode import PROMOTION_APPLY, PROMOTION_BRANCH, promotion_mode

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(promotion_mode({"inputs": {}}), PROMOTION_BRANCH)
        self.assertEqual(
            promotion_mode({"inputs": {"promotion_mode": "apply"}}), PROMOTION_APPLY,
        )
        with patch.dict(os.environ, {"KORU_QUEUE_PROMOTION_MODE": "commit"}):
            self.assertEqual(promotion_mode({"inputs": {}}), "commit")
            # An unknown ticket value must not silently inherit the env default.
            self.assertEqual(
                promotion_mode({"inputs": {"promotion_mode": "nonsense"}}), "commit",
            )

    def test_worktree_keeps_the_repository_depth_on_disk(self) -> None:
        """Suites resolve fixtures relative to the repo's parent in a monorepo
        (`resolve(__dirname, "../..")`). A worktree nested inside the project
        silently breaks every one of them, so it is staged as a sibling."""
        from koru.queue.patch_mode import staging_worktree

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            project = parent / "repo"
            project.mkdir()
            for args in (
                ["init", "-q"],
                ["config", "user.email", "koru@test"],
                ["config", "user.name", "koru"],
            ):
                subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
            self._commit_file(project, "a.txt", "old\n")
            # A fixture that lives beside the repo, as in a monorepo checkout.
            (parent / "fixture.json").write_text("{}", encoding="utf-8")

            with staging_worktree(project, ("a.txt",)) as staged:
                self.assertIsNotNone(staged)
                assert staged is not None
                # Same depth as the project, so "../.." lands where it normally would.
                self.assertEqual(staged.parent, project.parent)
                self.assertTrue((staged / ".." / "fixture.json").resolve().is_file())

            self.assertFalse(list(parent.glob(".koru-run-*")))

    def test_stale_worktrees_from_a_killed_run_are_reclaimed(self) -> None:
        """A killed process never runs its cleanup. The next run must reclaim
        both the abandoned directory and git's registration of it."""
        from koru.queue.patch_mode import prune_stale_worktrees, staging_worktree

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            project = parent / "repo"
            project.mkdir()
            for args in (
                ["init", "-q"],
                ["config", "user.email", "koru@test"],
                ["config", "user.name", "koru"],
            ):
                subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
            self._commit_file(project, "a.txt", "old\n")

            # A registration whose directory vanished, and a directory git no
            # longer knows about — the two ways a killed run leaves debris.
            subprocess.run(
                ["git", "worktree", "add", "--detach", "--quiet", str(parent / ".koru-run-gone"), "HEAD"],
                cwd=project, check=True, capture_output=True,
            )
            shutil.rmtree(parent / ".koru-run-gone")
            orphan_dir = parent / ".koru-run-orphaned"
            orphan_dir.mkdir()
            (orphan_dir / "leftover.txt").write_text("debris", encoding="utf-8")

            # Reclaimed as a side effect of starting the next run, not only
            # when called directly — that wiring is the part that matters.
            with staging_worktree(project, ("a.txt",)) as fresh:
                self.assertIsNotNone(fresh)

            self.assertFalse(orphan_dir.exists())
            listed = subprocess.run(
                ["git", "worktree", "list"], cwd=project, capture_output=True, text=True, check=True,
            ).stdout
            self.assertNotIn(".koru-run-gone", listed)

            # A live worktree must survive pruning — concurrent runs rely on it.
            with staging_worktree(project, ("a.txt",)) as staged:
                self.assertIsNotNone(staged)
                assert staged is not None
                prune_stale_worktrees(project)
                self.assertTrue(staged.is_dir())

    def test_worktree_is_cleaned_up_on_keyboard_interrupt(self) -> None:
        """Ctrl-C during verification must not leave a worktree behind."""
        from koru.queue.patch_mode import staging_worktree

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            project = parent / "repo"
            project.mkdir()
            for args in (
                ["init", "-q"],
                ["config", "user.email", "koru@test"],
                ["config", "user.name", "koru"],
            ):
                subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
            self._commit_file(project, "a.txt", "old\n")

            with self.assertRaises(KeyboardInterrupt):
                with staging_worktree(project, ("a.txt",)) as staged:
                    self.assertIsNotNone(staged)
                    raise KeyboardInterrupt

            self.assertFalse(list(parent.glob(".koru-run-*")))

    def test_conflict_on_one_file_promotes_none_of_them(self) -> None:
        """Promotion is all-or-nothing: a concurrent edit to one target must not
        leave the patch's other files half-applied."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            (project / "a.txt").write_text("a1\n", encoding="utf-8")
            (project / "b.txt").write_text("b1\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-qm", "base"], cwd=project, check=True, capture_output=True,
            )
            reply = SimpleNamespace(
                returncode=0,
                stdout=(
                    "```diff\n"
                    "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n"
                    "@@ -1 +1 @@\n-a1\n+a2\n"
                    "diff --git a/b.txt b/b.txt\n--- a/b.txt\n+++ b/b.txt\n"
                    "@@ -1 +1 @@\n-b1\n+b2\n"
                    "```\n"
                ),
                stderr="",
            )
            calls = {"n": 0}

            def gate(command: str, cwd: Path):
                calls["n"] += 1
                if calls["n"] == 2:  # after the worktree baseline, before promotion
                    (project / "b.txt").write_text("touched by someone else\n", encoding="utf-8")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "true"}}, gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, PROMOTION_CONFLICT)
            # Neither file moved: a.txt was not promoted just because it was clean.
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "a1\n")
            self.assertEqual(
                (project / "b.txt").read_text(encoding="utf-8"), "touched by someone else\n",
            )

    def test_binary_targets_are_named_not_dumped_into_the_prompt(self) -> None:
        """A binary file quoted into a retry prompt is mojibake the model cannot
        act on, and it cannot express a binary change as a unified diff anyway."""
        from koru.queue.patch_mode import current_file_excerpt

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01\x02payload\xff")
            (project / "notes.txt").write_text("readable text\n", encoding="utf-8")

            excerpt = current_file_excerpt(project, ("logo.png", "notes.txt"))

            self.assertIn("logo.png", excerpt)
            self.assertIn("binary file, contents not shown", excerpt)
            self.assertNotIn("\ufffd", excerpt)
            self.assertIn("readable text", excerpt)

    def test_read_only_checkout_degrades_instead_of_crashing(self) -> None:
        """Containers and CI mount repos read-only — koru's own noVNC image
        uses /opt/koru:ro. Staging must decline, not raise."""
        from koru.queue.patch_mode import staging_worktree

        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            project = parent / "repo"
            project.mkdir()
            for args in (
                ["init", "-q"],
                ["config", "user.email", "koru@test"],
                ["config", "user.name", "koru"],
            ):
                subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
            self._commit_file(project, "a.txt", "old\n")

            project.chmod(0o555)
            parent.chmod(0o555)
            try:
                with staging_worktree(project, ("a.txt",)) as staged:
                    # No writable location anywhere: decline so the caller can
                    # fall back to in-place execution and its dirty-file guard.
                    self.assertIsNone(staged)
            finally:
                parent.chmod(0o755)
                project.chmod(0o755)

    def test_symlink_creating_patch_is_refused(self) -> None:
        """git apply blocks `../` traversal but not a link pointing anywhere on
        the filesystem, which would let a scoped patch reach outside it."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(
                returncode=0,
                stdout=(
                    "```diff\n"
                    "diff --git a/link b/link\n"
                    "new file mode 120000\n"
                    "--- /dev/null\n"
                    "+++ b/link\n"
                    "@@ -0,0 +1 @@\n"
                    "+/etc/passwd\n"
                    "```\n"
                ),
                stderr="",
            )

            def unused_gate(command: str, cwd: Path):
                raise AssertionError("a refused patch must not reach the gate")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "true"}}, unused_gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, PATCH_INTRODUCES_SYMLINK)
            self.assertFalse(outcome.retryable)
            self.assertFalse((project / "link").exists())

    def test_symlinks_can_be_opted_into(self) -> None:
        from koru.queue.patch_mode import symlink_creations, symlinks_allowed

        symlink_diff = "diff --git a/l b/l\nnew file mode 120000\n"
        self.assertTrue(symlink_creations(symlink_diff))
        self.assertFalse(symlink_creations("diff --git a/f b/f\nnew file mode 100644\n"))
        self.assertFalse(symlinks_allowed())
        with patch.dict(os.environ, {"KORU_QUEUE_ALLOW_SYMLINKS": "1"}):
            self.assertTrue(symlinks_allowed())

    def test_multi_file_patch_is_all_or_nothing(self) -> None:
        """One bad file must not leave the others half-applied."""
        from koru.queue.patch_mode import apply_unified_diff

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            partial = (
                "diff --git a/a.txt b/a.txt\n"
                "--- a/a.txt\n"
                "+++ b/a.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
                "diff --git a/missing.txt b/missing.txt\n"
                "--- a/missing.txt\n"
                "+++ b/missing.txt\n"
                "@@ -1 +1 @@\n"
                "-nope\n"
                "+new\n"
            )
            result = apply_unified_diff(project, partial)

            self.assertFalse(result.ok)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_rename_and_mode_change_are_allowed(self) -> None:
        """Renames and the executable bit are ordinary refactoring output."""
        from koru.queue.patch_mode import apply_unified_diff

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "old-name.sh", "echo hi\n")
            rename = (
                "diff --git a/old-name.sh b/new-name.sh\n"
                "old mode 100644\n"
                "new mode 100755\n"
                "similarity index 100%\n"
                "rename from old-name.sh\n"
                "rename to new-name.sh\n"
            )
            result = apply_unified_diff(project, rename)

            self.assertTrue(result.ok, result.detail)
            self.assertFalse((project / "old-name.sh").exists())
            self.assertTrue((project / "new-name.sh").exists())
            self.assertTrue(os.access(project / "new-name.sh", os.X_OK))

    def test_manifest_hash_is_stable_and_content_sensitive(self) -> None:
        """The hash must depend only on the decision, so identical inputs always
        produce the same manifest — otherwise it cannot pin anything."""
        from koru.queue.patch_mode import build_manifest, manifest_hash

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            kwargs = dict(
                run_id="fixed-run",
                ticket={"id": "T-1"},
                diff="a diff",
                targets=("a.txt",),
                verify_command="true",
                mode="apply",
                attempt=1,
                max_attempts=2,
            )
            first = build_manifest(project, **kwargs)
            second = build_manifest(project, **kwargs)
            self.assertEqual(first["manifest_hash"], second["manifest_hash"])
            self.assertEqual(first, second)

            other = build_manifest(project, **{**kwargs, "diff": "a different diff"})
            self.assertNotEqual(first["manifest_hash"], other["manifest_hash"])
            # The recorded hash is not itself part of the hashed payload.
            self.assertEqual(manifest_hash(first), first["manifest_hash"])

    def test_manifest_detects_content_and_head_drift(self) -> None:
        from koru.queue.patch_mode import build_manifest, manifest_drift

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            manifest = build_manifest(
                project,
                run_id="r",
                ticket={"id": "T-1"},
                diff="d",
                targets=("a.txt",),
                verify_command="true",
                mode="apply",
                attempt=1,
                max_attempts=1,
            )
            self.assertEqual(manifest_drift(project, manifest), "")

            (project / "a.txt").write_text("someone else edited this\n", encoding="utf-8")
            self.assertIn("a.txt", manifest_drift(project, manifest))

    def test_retry_does_not_silently_rebase_after_workspace_changed(self) -> None:
        """A retry must target the base it was pinned to. If another session
        moves the workspace between attempts, abandon rather than rebase."""
        from koru.queue.patch_retry import apply_patch_with_retry

        corrupt = SimpleNamespace(
            returncode=0,
            stdout=(
                "```diff\ndiff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n"
                "@@ -1 +1 @@\nno marker here\n```\n"
            ),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"KORU_QUEUE_PATCH_RETRIES": "3"},
        ):
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            def moving_target(request, cwd):
                # Simulate a second session editing the file between attempts.
                (project / "a.txt").write_text("moved by another session\n", encoding="utf-8")
                return corrupt

            def gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome, _evidence = apply_patch_with_retry(
                project,
                corrupt,
                {"inputs": {}, "files": ["a.txt"]},
                {"prompt": "x"},
                moving_target,
                gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, MANIFEST_MISMATCH)
            self.assertEqual(
                (project / "a.txt").read_text(encoding="utf-8"), "moved by another session\n",
            )

    def test_context_excerpt_is_bounded_and_redacted(self) -> None:
        from koru.queue.patch_mode import current_file_excerpt

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "cfg.py").write_text(
                'API_' + 'KEY = "sk-' + 'must-not-leak-abcdefgh"\n' + ("filler\n" * 5000),
                encoding="utf-8",
            )
            excerpt = current_file_excerpt(project, ("cfg.py",), max_chars=500)

            self.assertIn("cfg.py", excerpt)
            self.assertNotIn("sk-must-not-leak-abcdefgh", excerpt)
            self.assertLess(len(excerpt), 1500)
            self.assertEqual(current_file_excerpt(project, ("missing.py",)), "")

    def test_gate_failing_before_the_patch_is_not_blamed_on_the_agent(self) -> None:
        """Found by the first real pilot: a suite that resolves fixtures relative
        to the repo root fails inside a worktree regardless of the patch. Judging
        the agent on that is a false negative, so the baseline is checked first."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            calls = {"n": 0}

            def broken_environment(command: str, cwd: Path):
                calls["n"] += 1
                return SimpleNamespace(returncode=1, stdout="", stderr="cannot find fixture")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "node --test"}}, broken_environment,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, VERIFY_BASELINE_FAILED)
            self.assertFalse(outcome.retryable)  # re-asking cannot fix the environment
            self.assertIn("already failed in a clean worktree", outcome.message)
            # Red before and red after: the gate ran on both sides so the two
            # cases could be told apart, and nothing reached the workspace.
            self.assertEqual(calls["n"], 2)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_a_patch_that_turns_the_gate_green_is_a_repair_not_a_failure(self) -> None:
        """A red baseline is also what a repair ticket looks like before its fix.
        Deciding on the baseline alone threw away correct patches whenever the
        ticket was not labelled type:development-defect."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            calls = {"n": 0}

            def gate(command: str, cwd: Path):
                # Fails on "old", passes on "new" — the patch is the fix.
                calls["n"] += 1
                fixed = (Path(cwd) / "a.txt").read_text(encoding="utf-8").strip() == "new"
                return SimpleNamespace(
                    returncode=0 if fixed else 1, stdout="", stderr="" if fixed else "still broken",
                )

            # Deliberately unlabelled: no type:development-defect, no opt-out flag.
            _result, outcome = apply_proposed_patch(
                project,
                reply,
                {"labels": ["refactor"], "inputs": {"verify_command": "node --test"}},
                gate,
            )

            self.assertIsNone(outcome, outcome)
            self.assertEqual(calls["n"], 2)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")

    def test_development_defect_skips_verify_baseline_in_worktree(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            calls = {"n": 0}

            def gate(command: str, cwd: Path):
                calls["n"] += 1
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            ticket = {
                "labels": ["type:development-defect"],
                "inputs": {
                    "verify_command": "node --test",
                    "promotion_mode": "branch",
                },
            }
            with patch.dict(os.environ, {"KORU_QUEUE_WORKTREE": "1"}):
                _result, outcome = apply_proposed_patch(project, reply, ticket, gate)

            self.assertIsNone(outcome)
            self.assertEqual(calls["n"], 1)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_retry_feedback_redacts_credentials(self) -> None:
        """Diagnostics travel back to the model, so anything credential-shaped
        in git or test output must not go with them."""
        from koru.queue.patch_mode import redact_secrets

        leaky = (
            'error: patch failed: config.py:3\n'
            'ANTHROPIC_API_' 'KEY="sk-ant-' 'abcdefghijklmnop"\n'
            "db_" "password = 'hunter2-" "very-secret'\n"
            "Author" "ization: Bearer eyJhbGciOiJIUzI1NiJ9.payloadpayload.signature\n"
            "AKIAIOSFODNN7EXAMPLE\n"
        )
        cleaned = redact_secrets(leaky)

        for secret in (
            "sk-ant-abcdefghijklmnop",
            "hunter2-very-secret",
            "eyJhbGciOiJIUzI1NiJ9.payloadpayload.signature",
            "AKIAIOSFODNN7EXAMPLE",
        ):
            self.assertNotIn(secret, cleaned)
        # The part the agent actually needs survives.
        self.assertIn("patch failed: config.py:3", cleaned)

    def test_retry_feedback_is_length_bounded(self) -> None:
        from koru.queue.patch_mode import redact_secrets

        cleaned = redact_secrets("x" * 10_000)
        self.assertLess(len(cleaned), 2_200)
        self.assertIn("truncated", cleaned)

    def test_patch_creating_a_new_file_is_promoted(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            creation = (
                "```diff\n"
                "diff --git a/new.txt b/new.txt\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                "+++ b/new.txt\n"
                "@@ -0,0 +1 @@\n"
                "+created\n"
                "```\n"
            )
            reply = SimpleNamespace(returncode=0, stdout=creation, stderr="")

            def gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "true"}}, gate,
            )

            self.assertIsNone(outcome, outcome)
            self.assertEqual((project / "new.txt").read_text(encoding="utf-8"), "created\n")

    def test_patch_deleting_a_file_is_promoted(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "gone.txt", "bye\n")
            deletion = (
                "```diff\n"
                "diff --git a/gone.txt b/gone.txt\n"
                "deleted file mode 100644\n"
                "--- a/gone.txt\n"
                "+++ /dev/null\n"
                "@@ -1 +0,0 @@\n"
                "-bye\n"
                "```\n"
            )
            reply = SimpleNamespace(returncode=0, stdout=deletion, stderr="")

            def gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "true"}}, gate,
            )

            self.assertIsNone(outcome, outcome)
            self.assertFalse((project / "gone.txt").exists())

    def test_worktree_is_cleaned_up_when_the_gate_raises(self) -> None:
        """A crashing verify command must not leak a worktree directory."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def exploding_gate(command: str, cwd: Path):
                raise RuntimeError("gate blew up")

            with self.assertRaises(RuntimeError):
                apply_proposed_patch(
                    project, reply, {"inputs": {"verify_command": "true"}}, exploding_gate,
                )

            self.assertFalse(list(project.parent.glob(".koru-run-*")))
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_untracked_file_counts_as_dirty_in_direct_mode(self) -> None:
        """An untracked file has no index version at all, so `git checkout --`
        could not restore it either — it must block direct apply too."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"KORU_QUEUE_WORKTREE": "0"},
        ):
            project = self._git_repo(tmp)
            self._commit_file(project, "seed.txt", "seed\n")
            (project / "a.txt").write_text("old\n", encoding="utf-8")  # untracked

            reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def unused_gate(command: str, cwd: Path):
                raise AssertionError("verify must not run when the patch was refused")

            _result, outcome = apply_proposed_patch(
                project, reply, {"inputs": {"verify_command": "true"}}, unused_gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, UNSAFE_DIRTY_WORKSPACE)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_direct_mode_refuses_to_touch_a_dirty_file(self) -> None:
        """Regression: `git checkout --` restores from the index, so rolling a
        patch back off a file that already held unstaged work would destroy
        that work. Direct mode must refuse rather than promise a rollback it
        cannot honour."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"KORU_QUEUE_WORKTREE": "0"},
        ):
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "committed\n")
            (project / "a.txt").write_text("old\n", encoding="utf-8")  # the user's WIP

            agent_reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def unused_gate(command: str, cwd: Path):
                raise AssertionError("verify must not run when the patch was refused")

            _result, outcome = apply_proposed_patch(
                project, agent_reply, {"inputs": {"verify_command": "true"}}, unused_gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, UNSAFE_DIRTY_WORKSPACE)
            self.assertFalse(outcome.retryable)
            # The user's uncommitted edit survives untouched.
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_promotion_is_rejected_when_workspace_changes_during_verification(self) -> None:
        """Another session editing the same file mid-verification must not be
        silently overwritten by the promotion."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            agent_reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def concurrent_editor(command: str, cwd: Path):
                # Simulate a second session writing to the main tree while the
                # patch is being verified inside the worktree.
                (project / "a.txt").write_text("another session was here\n", encoding="utf-8")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome = apply_proposed_patch(
                project, agent_reply, {"inputs": {"verify_command": "true"}}, concurrent_editor,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, PROMOTION_CONFLICT)
            self.assertTrue(outcome.workspace_left_untouched)
            self.assertFalse(outcome.retryable)
            # The other session's work is intact; no half-applied patch.
            self.assertEqual(
                (project / "a.txt").read_text(encoding="utf-8"),
                "another session was here\n",
            )

    def test_unapplicable_patch_is_retried_with_the_git_error(self) -> None:
        """A malformed diff is a mechanical failure the agent can fix — but only
        if it is told exactly what git objected to."""
        from koru.queue.patch_retry import apply_patch_with_retry

        corrupt = (
            "```diff\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "this line has no marker\n"
            "```\n"
        )
        prompts: list[str] = []

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            action = {"prompt": "Rename the thing."}
            first = SimpleNamespace(returncode=0, stdout=corrupt, stderr="")

            def retry_agent(request, cwd):
                prompts.append(str(request.get("prompt")))
                return SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome, _evidence = apply_patch_with_retry(
                project, first, {"inputs": {}}, action, retry_agent, gate,
            )

            self.assertIsNone(outcome, outcome)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")
            self.assertEqual(len(prompts), 1)
            self.assertIn("Previous attempt was rejected", prompts[0])
            self.assertIn("Rename the thing.", prompts[0])

    def test_verification_failure_is_not_retried(self) -> None:
        """A patch that applies but fails its gate is wrong on the merits, so
        re-asking would just spend another agent run on the same idea."""
        from koru.queue.patch_retry import apply_patch_with_retry

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            first = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")

            def never_called(request, cwd):
                raise AssertionError("a substantive failure must not be retried")

            calls = {"n": 0}

            def failing_gate(command: str, cwd: Path):
                calls["n"] += 1
                if calls["n"] == 1:  # clean-worktree baseline
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="tests failed")

            _result, outcome, _evidence = apply_patch_with_retry(
                project,
                first,
                {"inputs": {"verify_command": "false"}},
                {"prompt": "x"},
                never_called,
                failing_gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, VERIFY_FAILED_ISOLATED)
            self.assertFalse(outcome.retryable)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_retry_budget_is_bounded(self) -> None:
        """An agent that keeps emitting junk must not loop forever."""
        from koru.queue.patch_retry import apply_patch_with_retry

        calls = {"n": 0}
        junk = SimpleNamespace(returncode=0, stdout="I cannot do that.", stderr="")

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"KORU_QUEUE_PATCH_RETRIES": "2"},
        ):
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            def junk_agent(request, cwd):
                calls["n"] += 1
                return junk

            def gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            _result, outcome, _evidence = apply_patch_with_retry(
                project, junk, {"inputs": {}}, {"prompt": "x"}, junk_agent, gate,
            )

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, NO_PATCH_EMITTED)
            self.assertEqual(calls["n"], 1)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_failing_verify_never_reaches_the_workspace(self) -> None:
        """With worktree staging, a patch that fails its gate is proven bad in
        isolation and the real workspace is never modified at all."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            agent_reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"inputs": {"verify_command": "false"}}
            seen: list[Path] = []

            def failing_gate(command: str, cwd: Path):
                seen.append(Path(cwd))
                # First call is the clean-worktree baseline; it must pass so the
                # failure below is attributed to the patch, not the environment.
                if len(seen) == 1:
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(returncode=1, stdout="", stderr="2 tests failed")

            _result, outcome = apply_proposed_patch(project, agent_reply, ticket, failing_gate)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, VERIFY_FAILED_ISOLATED)
            self.assertTrue(outcome.workspace_left_untouched)
            self.assertIn("2 tests failed", outcome.message)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            # The gate ran against the worktree, not the project itself.
            self.assertTrue(seen and seen[0] != project, seen)
            self.assertFalse(list(project.parent.glob(".koru-run-*")))

    def test_failing_verify_rolls_back_when_worktree_is_disabled(self) -> None:
        """Without isolation the patch does land, so it must be reverted."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"KORU_QUEUE_WORKTREE": "0"},
        ):
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            agent_reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"inputs": {"verify_command": "false"}}

            def failing_gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=1, stdout="", stderr="2 tests failed")

            _result, outcome = apply_proposed_patch(project, agent_reply, ticket, failing_gate)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, VERIFY_FAILED_ROLLED_BACK)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_worktree_staging_sees_uncommitted_workspace_edits(self) -> None:
        """The agent diffs the working tree, so the worktree must be seeded
        with uncommitted content — otherwise every patch against a dirty file
        would be rejected as not applying."""
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "committed\n")
            (project / "a.txt").write_text("old\n", encoding="utf-8")  # uncommitted edit
            agent_reply = SimpleNamespace(returncode=0, stdout=self._PATCH_REPLY, stderr="")
            ticket = {"inputs": {"verify_command": "true"}}

            def passing_gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            _result, outcome = apply_proposed_patch(project, agent_reply, ticket, passing_gate)

            self.assertIsNone(outcome)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")

    def test_passing_verify_keeps_the_patch(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            agent_reply = SimpleNamespace(
                returncode=0,
                stdout=(
                    "```diff\n"
                    "diff --git a/a.txt b/a.txt\n"
                    "--- a/a.txt\n"
                    "+++ b/a.txt\n"
                    "@@ -1 +1 @@\n"
                    "-old\n"
                    "+new\n"
                    "```\n"
                ),
                stderr="",
            )
            ticket = {"inputs": {"verify_command": "true"}}

            def passing_gate(command: str, cwd: Path):
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            _result, outcome = apply_proposed_patch(project, agent_reply, ticket, passing_gate)

            self.assertIsNone(outcome)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")

    def test_reply_without_a_diff_is_not_treated_as_work(self) -> None:
        from koru.queue.patch_transaction import apply_proposed_patch

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            agent_reply = SimpleNamespace(
                returncode=0,
                stdout="NO-PATCH: the function is already simple enough",
                stderr="",
            )

            def unused_gate(command: str, cwd: Path):
                raise AssertionError("verify must not run when no patch was applied")

            _result, outcome = apply_proposed_patch(project, agent_reply, {}, unused_gate)

            self.assertIsNotNone(outcome)
            self.assertEqual(outcome.code, NO_PATCH_EMITTED)
            self.assertTrue(outcome.retryable)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")

    def test_patch_mode_defaults_on_and_is_overridable(self) -> None:
        from koru.queue.patch_mode import patch_mode_enabled

        self.assertTrue(patch_mode_enabled({"inputs": {}}))
        self.assertFalse(patch_mode_enabled({"inputs": {"patch_mode": False}}))
        with patch.dict(os.environ, {"KORU_LLM_PATCH_MODE": "0"}):
            self.assertFalse(patch_mode_enabled({"inputs": {}}))
            self.assertTrue(patch_mode_enabled({"inputs": {"patch_mode": True}}))

    def test_prompt_carries_the_diff_only_contract(self) -> None:
        from koru.queue.patch_mode import build_patch_prompt

        prompt = build_patch_prompt("Refactor applyRoute.")
        self.assertIn("Refactor applyRoute.", prompt)
        self.assertIn("Do NOT edit any file", prompt)
        self.assertIn("NO-PATCH", prompt)


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


def test_planfile_error_message_actionable_on_module_missing(tmp_path: Path) -> None:
    """Module-missing failures must tell the operator how to fix them."""
    from types import SimpleNamespace

    from koru.queue.runner import run_next_planfile_task

    def planfile_runner(_command: list[str], _project: Path) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="/x/.venv/bin/python: Error while finding module specification for 'planfile.cli' (ModuleNotFoundError: No module named 'planfile')",  # noqa: E501
        )

    result = run_next_planfile_task(project=tmp_path, planfile_runner=planfile_runner)

    assert result.status == "planfile_error"
    assert "pip install planfile" in result.message
