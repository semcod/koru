"""Unit tests for koru.cli — dispatch, bare invocation, flags."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import koru.cli as cli_module
from koru.cli import _SUBCOMMANDS, _build_parser, _dispatch_auto_alias, _is_bare_invocation, main
from koru.cqrs import runtime_for_project


def _tmp_git_project(prefix: str = "koru-cli-test-") -> Path:
    td = tempfile.mkdtemp(prefix=prefix)
    p = Path(td)
    subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    return p


def _run_main(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch("sys.argv", ["koru", *argv]):
        with mock.patch("sys.stdout", new=buf):
            with mock.patch("koru.cli._maybe_reexec_for_project_venv"):
                code = main()
    return code, buf.getvalue()


def test_cli_shim_reloads_partial_legacy_module() -> None:
    """Collection must survive a stale synthetic legacy module in sys.modules."""
    module_name = "koru._legacy_cli_impl"
    original = sys.modules.get(module_name)
    partial = types.ModuleType(module_name)
    sys.modules[module_name] = partial
    try:
        loaded = cli_module._load_legacy_cli_module()
        assert loaded is not partial
        assert loaded is sys.modules[module_name]
        assert hasattr(loaded, "main")
        assert hasattr(loaded, "_SUBCOMMANDS")
    finally:
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original


class TestBareInvocation(unittest.TestCase):
    """``koru`` with no action flag should route to markdown brief."""

    def _parse(self, *argv: str) -> object:
        return _build_parser().parse_args(list(argv))

    def test_no_args_is_bare(self) -> None:
        args = self._parse()
        self.assertTrue(_is_bare_invocation(args))

    def test_project_only_is_bare(self) -> None:
        args = self._parse("--project", "/tmp/p")
        self.assertTrue(_is_bare_invocation(args))

    def test_init_is_not_bare(self) -> None:
        args = self._parse("--init")
        self.assertFalse(_is_bare_invocation(args))

    def test_init_skip_host_environment_flag(self) -> None:
        args = self._parse("--init", "--skip-host-environment")
        self.assertTrue(args.skip_host_environment)
        args2 = self._parse("--init")
        self.assertFalse(args2.skip_host_environment)

    def test_init_agent_lane_is_not_bare(self) -> None:
        args = self._parse("--init-agent-lane")
        self.assertFalse(_is_bare_invocation(args))

    def test_doctor_is_not_bare(self) -> None:
        args = self._parse("--doctor")
        self.assertFalse(_is_bare_invocation(args))

    def test_context_is_not_bare(self) -> None:
        args = self._parse("--context")
        self.assertFalse(_is_bare_invocation(args))

    def test_queue_is_not_bare(self) -> None:
        args = self._parse("--queue")
        self.assertFalse(_is_bare_invocation(args))

    def test_watch_is_not_bare(self) -> None:
        args = self._parse("--watch")
        self.assertFalse(_is_bare_invocation(args))

    def test_bootstrap_is_not_bare(self) -> None:
        args = self._parse("--bootstrap")
        self.assertFalse(_is_bare_invocation(args))

    def test_command_is_not_bare(self) -> None:
        args = self._parse("--command", "echo hi")
        self.assertFalse(_is_bare_invocation(args))


class TestDoctorDispatch(unittest.TestCase):
    """--doctor uses text by default, json when --format json."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-doc-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_doctor_default_is_text(self) -> None:
        code, output = _run_main("--doctor", "--project", str(self.project))
        self.assertIn("koru doctor", output)
        self.assertTrue(
            any(m in output for m in ("[OK ]", "[WARN]", "[FAIL]")),
            f"Expected text markers in output:\n{output}",
        )

    def test_doctor_json(self) -> None:
        code, output = _run_main(
            "--doctor",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        data = json.loads(output)
        self.assertIn("checks", data)
        self.assertIn("project", data)

    def test_doctor_subcommand_text(self) -> None:
        code, output = _run_main("doctor", "--project", str(self.project))
        self.assertIn("koru doctor", output)
        self.assertTrue(
            any(m in output for m in ("[OK ]", "[WARN]", "[FAIL]")),
            f"Expected text markers in output:\n{output}",
        )
        self.assertIsInstance(code, int)

    def test_doctor_subcommand_catalog_json(self) -> None:
        code, output = _run_main(
            "doctor",
            "--project",
            str(self.project),
            "--format",
            "json",
            "--catalog",
        )
        data = json.loads(output)
        self.assertIn("detected_problems", data)
        self.assertIn("problem_catalog", data)
        self.assertIsInstance(data["problem_catalog"], list)
        self.assertIsInstance(code, int)

    def test_doctor_fix_text_is_guidance_only(self) -> None:
        code, output = _run_main("--doctor", "--fix", "--project", str(self.project))
        self.assertIn("Guided repair (--fix):", output)
        self.assertIn("koru --doctor --repair --project", output)
        self.assertIn("koru autopilot doctor --fix", output)
        self.assertIn("KORU_AUTOPILOT_INSTANCE=", output)
        self.assertIn("koru autopilot daemon --project", output)
        self.assertIn("koru autopilot status --ide", output)
        self.assertIn("koru autopilot trace --project", output)
        self.assertIn("koru ide doctor --ide", output)
        self.assertIn("--gc-sockets", output)
        self.assertIn("koru autonomous safe-up --project", output)
        self.assertIsInstance(code, int)

    def test_doctor_fix_json(self) -> None:
        code, output = _run_main(
            "--doctor",
            "--fix",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        data = json.loads(output)
        self.assertIn("fix", data)
        self.assertFalse(data["fix"]["writes_by_default"])
        self.assertIn("commands", data["fix"])
        self.assertIsInstance(code, int)

    def test_doctor_repair_text_applies_safe_actions(self) -> None:
        fake_report = types.SimpleNamespace(ok=True, issues=[], actions=[])
        fake_start = {
            "action": "start_daemon",
            "status": "started",
            "pid": 123,
            "socket": "/tmp/koru-autopilot-vscodium.sock",
            "log": "/tmp/doctor-autopilot-vscodium.log",
        }
        with mock.patch("koru.cli_doctor.repair_installation", return_value=fake_report):
            with mock.patch(
                "koru.cli_doctor._start_autopilot_daemon_for_repair",
                return_value=fake_start,
            ):
                code, output = _run_main(
                    "--doctor",
                    "--repair",
                    "--project",
                    str(self.project),
                )
        self.assertIn("Applied repair (--repair):", output)
        self.assertIn("repair_installation: True", output)
        self.assertIn("start_daemon: started", output)
        self.assertIn("pid=123", output)
        self.assertIsInstance(code, int)

    def test_doctor_exit_0_on_no_failures(self) -> None:
        code, _ = _run_main("--doctor", "--project", str(self.project))
        self.assertIsInstance(code, int)


class TestInitDispatch(unittest.TestCase):
    """--init creates project scaffold."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-init-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_init_creates_planfile(self) -> None:
        code, output = _run_main("--init", "--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertTrue((self.project / ".planfile" / "config.yaml").exists())
        self.assertTrue((self.project / ".planfile" / ".koru" / "policy.yaml").exists())
        helper = self.project / ".planfile" / ".koru" / "run-autonomous.sh"
        self.assertTrue(helper.is_file(), "default --agent-lane auto writes runner")

    def test_init_duplicate_rejected(self) -> None:
        _run_main("--init", "--project", str(self.project))
        code, _ = _run_main("--init", "--project", str(self.project))
        self.assertEqual(code, 1)

    def test_init_agent_lane_none_skips_helpers(self) -> None:
        p2 = _tmp_git_project("koru-cli-init-none-")
        try:
            code, out = _run_main(
                "--init",
                "--project",
                str(p2),
                "--agent-lane",
                "none",
            )
            self.assertEqual(code, 0, out)
            self.assertFalse((p2 / ".planfile" / ".koru" / "shell-env.sh").exists())
            self.assertFalse((p2 / ".planfile" / ".koru" / "run-autonomous.sh").exists())
        finally:
            shutil.rmtree(p2, ignore_errors=True)


class TestInitAgentLaneDispatch(unittest.TestCase):
    """--init-agent-lane refreshes shell helpers without full re-init."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-ial-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_fails_without_planfile(self) -> None:
        code, output = _run_main(
            "--init-agent-lane",
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 2)
        self.assertIn("not found", output)

    def test_ok_when_planfile_exists(self) -> None:
        code, _ = _run_main("--init", "--project", str(self.project))
        self.assertEqual(code, 0)
        code, output = _run_main(
            "--init-agent-lane",
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 0, output)
        runner = self.project / ".planfile" / ".koru" / "run-autonomous.sh"
        self.assertTrue(runner.is_file())


class TestContextDispatch(unittest.TestCase):
    """--context emits JSON or markdown."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-ctx-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_context_json_default(self) -> None:
        code, output = _run_main(
            "--context",
            "--project",
            str(self.project),
        )
        data = json.loads(output)
        self.assertIn("policy", data)
        self.assertEqual(code, 0)

    def test_context_markdown(self) -> None:
        code, output = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "markdown",
        )
        self.assertIn("# koru handoff", output)
        self.assertEqual(code, 0)


class TestBareEmitsMarkdown(unittest.TestCase):
    """Bare ``koru`` should produce a markdown brief."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-bare-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_bare_produces_markdown(self) -> None:
        code, output = _run_main("--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertIn("# koru handoff", output)


class TestTopologySubcommand(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="koru-cli-topology-")
        self.project = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_topology_json_lists_components_and_pipelines(self) -> None:
        code, output = _run_main("topology", "--project", str(self.project), "--format", "json")
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertIn("components", data)
        self.assertIn("pipelines", data)
        self.assertIn("regix", data["components"])

    def test_topology_disable_then_is_enabled_false(self) -> None:
        code1, _ = _run_main("topology", "--project", str(self.project), "--disable", "regix")
        self.assertEqual(code1, 0)

        code2, output2 = _run_main(
            "topology",
            "--project",
            str(self.project),
            "--is-enabled",
            "regix",
        )
        self.assertEqual(code2, 1)
        self.assertEqual(output2.strip(), "false")

    def test_topology_enabled_components_for_pipeline(self) -> None:
        _run_main("topology", "--project", str(self.project), "--disable", "wup")
        code, output = _run_main(
            "topology",
            "--project",
            str(self.project),
            "--enabled-components-for",
            "idle-diagnostics",
        )
        self.assertEqual(code, 0)
        self.assertIn("regix", output)
        self.assertNotIn("wup", output)


class TestInitCiSubcommand(unittest.TestCase):
    def test_init_ci_exits_zero_with_paths(self) -> None:
        code, out = _run_main("init-ci")
        self.assertEqual(code, 0)
        self.assertIn(".github/workflows/koru-ci.yml", out)
        self.assertIn("ci-github.md", out)


class TestAutoMain(unittest.TestCase):
    """``koru auto`` stops prior loops and forwards ``--replace-existing`` without a full run."""

    def tearDown(self) -> None:
        for key in ("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", "KORU_AUTOPILOT_NEW_WINDOW_RELOAD"):
            os.environ.pop(key, None)

    def test_auto_main_stops_prior_and_injects_replace_existing(self) -> None:
        from koru.cli_auto import _auto_main

        stopped: list[Path] = []
        calls: list[tuple[list[str], bool]] = []

        def fake_stop(project: Path, **kwargs: object) -> None:
            stopped.append(project)

        def fake_autonomous(argv: list[str], *, invoked_as_auto: bool = False) -> int:
            calls.append((list(argv), invoked_as_auto))
            return 0

        with (
            mock.patch(
                "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
                side_effect=fake_stop,
            ),
            mock.patch(
                "koru._legacy_cli_impl.autonomous_main",
                side_effect=fake_autonomous,
            ),
            mock.patch("koruide.ide.detect_terminal_host_ide_id", return_value=None),
            mock.patch.dict(os.environ, {"KORU_AUTO_SKIP_WIZARD": "1"}, clear=False),
        ):
            os.environ.pop("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", None)
            os.environ.pop("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", None)
            code = _auto_main(["--project", "/tmp/proj"])
            reuse_reload = os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD")
            new_window_reload = os.environ.get("KORU_AUTOPILOT_NEW_WINDOW_RELOAD")

        self.assertEqual(code, 0)
        self.assertEqual(len(stopped), 1)
        self.assertEqual(stopped[0], Path("/tmp/proj").resolve())
        self.assertEqual(len(calls), 1)
        self.assertIn("--replace-existing", calls[0][0])
        self.assertNotIn("--no-autopilot", calls[0][0])
        self.assertNotIn("--stop-on-waiting-input", calls[0][0])
        self.assertNotIn("--no-wup-watch", calls[0][0])
        self.assertNotIn("--max-cycles", calls[0][0])
        self.assertNotIn("--max-iterations", calls[0][0])
        self.assertTrue(calls[0][1])
        self.assertEqual(reuse_reload, "1")
        self.assertIsNone(new_window_reload)

    def test_auto_main_skips_reuse_window_from_integrated_terminal(self) -> None:
        from koru.cli_auto import _auto_main

        with (
            mock.patch(
                "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
                return_value=None,
            ),
            mock.patch(
                "koru._legacy_cli_impl.autonomous_main",
                return_value=0,
            ),
            mock.patch("koruide.ide.detect_terminal_host_ide_id", return_value="cursor"),
            mock.patch.dict(os.environ, {"KORU_AUTO_SKIP_WIZARD": "1"}, clear=False),
        ):
            os.environ.pop("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", None)
            code = _auto_main(["--project", "/tmp/proj"])
            reuse_reload = os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD")

        self.assertEqual(code, 0)
        self.assertIsNone(reuse_reload)

    def test_auto_main_preserves_explicit_reuse_window_reload_setting(self) -> None:
        from koru.cli_auto import _auto_main

        calls: list[list[str]] = []
        with (
            mock.patch(
                "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
                return_value=None,
            ),
            mock.patch(
                "koru._legacy_cli_impl.autonomous_main",
                side_effect=lambda argv, **kw: calls.append(list(argv)) or 0,
            ),
            mock.patch.dict(
                os.environ,
                {
                    "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD": "0",
                    "KORU_AUTOPILOT_NEW_WINDOW_RELOAD": "0",
                    "KORU_AUTO_SKIP_WIZARD": "1",
                },
                clear=False,
            ),
        ):
            code = _auto_main(["--project", "/tmp/proj"])
            reuse_reload = os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD")
            new_window_reload = os.environ.get("KORU_AUTOPILOT_NEW_WINDOW_RELOAD")

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(reuse_reload, "0")
        self.assertEqual(new_window_reload, "0")

    def test_auto_main_allow_duplicate_skips_stop_and_replace_flag(self) -> None:
        from koru.cli_auto import _auto_main

        calls: list[list[str]] = []

        with mock.patch(
            "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
            side_effect=AssertionError("stop should not run"),
        ):
            with mock.patch(
                "koru._legacy_cli_impl.autonomous_main",
                side_effect=lambda argv, **kw: calls.append(list(argv)) or 0,
            ):
                code = _auto_main(["--allow-duplicate", "--project", "/tmp/x"])

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("--replace-existing", calls[0])

    def test_subcommand_auto_routes_to_auto_main(self) -> None:
        with mock.patch("koru.cli_auto._auto_main", return_value=7) as auto_main:
            with mock.patch("sys.argv", ["koru", "auto", "--project", "/tmp/p"]):
                code = main()
        auto_main.assert_called_once_with(["--project", "/tmp/p"])
        self.assertEqual(code, 7)

    def test_auto_main_help_does_not_stop_existing_loop(self) -> None:
        from koru.cli_auto import _auto_main

        with mock.patch("koru.cli_auto.autonomous_main", return_value=0) as autonomous:
            with mock.patch("koru.cli_auto.stop_prior_autonomous_for_auto_start") as stop:
                code = _auto_main(["--help"])

        self.assertEqual(code, 0)
        stop.assert_not_called()
        autonomous.assert_called_once_with(["--help"], invoked_as_auto=True)

    def test_auto_main_strips_redundant_up_subcommand(self) -> None:
        from koru.cli_auto import _auto_main

        calls: list[list[str]] = []

        with mock.patch(
            "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
        ):
            with mock.patch(
                "koru._legacy_cli_impl.autonomous_main",
                side_effect=lambda argv, **kw: calls.append(list(argv)) or 0,
            ):
                code = _auto_main(["up", "--project", "/tmp/proj"])

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("up", calls[0])
        self.assertIn("--replace-existing", calls[0])
        self.assertIn("--project", calls[0])


class TestEventsSubcommand(unittest.TestCase):
    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-events-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_events_json_reports_context_history(self) -> None:
        runtime = runtime_for_project(self.project)
        runtime.append_event(
            context="tasks",
            event_type="tasks.created",
            payload={"ticket_id": "PLF-001"},
            aggregate_id="PLF-001",
        )

        code, output = _run_main(
            "events",
            "--project",
            str(self.project),
            "--context",
            "tasks",
            "--format",
            "json",
        )

        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["context"], "tasks")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["events"][0]["event_type"], "tasks.created")

    def test_events_filters_by_aggregate_id(self) -> None:
        runtime = runtime_for_project(self.project)
        runtime.append_event(
            context="tasks",
            event_type="tasks.created",
            payload={"ticket_id": "PLF-001"},
            aggregate_id="PLF-001",
        )
        runtime.append_event(
            context="tasks",
            event_type="tasks.created",
            payload={"ticket_id": "PLF-002"},
            aggregate_id="PLF-002",
        )

        code, output = _run_main(
            "events",
            "--project",
            str(self.project),
            "--context",
            "tasks",
            "--aggregate-id",
            "PLF-002",
            "--format",
            "json",
        )

        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["events"][0]["aggregate_id"], "PLF-002")

    def test_events_text_format(self) -> None:
        runtime = runtime_for_project(self.project)
        runtime.append_event(
            context="planfile_queue",
            event_type="planfile_queue.task_completed",
            payload={"ticket_id": "PLF-900"},
            aggregate_id="PLF-900",
        )

        code, output = _run_main(
            "events",
            "--project",
            str(self.project),
            "--context",
            "planfile_queue",
            "--format",
            "text",
        )

        self.assertEqual(code, 0)
        self.assertIn("koru events context=planfile_queue", output)
        self.assertIn("planfile_queue.task_completed", output)


class TestAutopilotReexecToProjectVenv(unittest.TestCase):
    def test_autopilot_subcommand_reexecs_when_interpreter_is_outside_project_venv(self) -> None:
        project = _tmp_git_project("koru-cli-autopilot-reexec-")
        try:
            local_koru = TestDoctorReexecToProjectVenv()._prepare_local_koru(project)
            with mock.patch(
                "sys.argv",
                ["koru", "autopilot", "drive", "--ide", "cursor", "--project", str(project)],
            ):
                with mock.patch("koru._legacy_cli_impl.sys.executable", "/usr/bin/python3"):
                    with mock.patch("koru._legacy_cli_impl.sys.prefix", "/usr"):
                        with mock.patch(
                            "koru._legacy_cli_impl.os.execvpe",
                            side_effect=RuntimeError("reexec"),
                        ) as execvpe:
                            with self.assertRaises(RuntimeError):
                                main()

            execvpe.assert_called_once()
            called_argv = execvpe.call_args.args[1]
            self.assertEqual(Path(called_argv[0]).resolve(), local_koru)
            self.assertEqual(
                called_argv[1:],
                ["autopilot", "drive", "--ide", "cursor", "--project", str(project)],
            )
        finally:
            shutil.rmtree(project, ignore_errors=True)


class TestDoctorReexecToProjectVenv(unittest.TestCase):
    def _prepare_local_koru(self, project: Path) -> Path:
        local_koru = project / ".venv" / "bin" / "koru"
        local_koru.parent.mkdir(parents=True, exist_ok=True)
        local_koru.write_text("#!/bin/sh\n", encoding="utf-8")
        local_koru.chmod(0o755)
        return local_koru.resolve()

    def test_doctor_subcommand_reexecs_when_interpreter_is_outside_project_venv(self) -> None:
        project = _tmp_git_project("koru-cli-doc-reexec-sub-")
        try:
            local_koru = self._prepare_local_koru(project)
            with mock.patch("sys.argv", ["koru", "doctor", "--project", str(project)]):
                with mock.patch("koru._legacy_cli_impl.sys.executable", "/usr/bin/python3"):
                    with mock.patch("koru._legacy_cli_impl.sys.prefix", "/usr"):
                        with mock.patch(
                            "koru._legacy_cli_impl.os.execvpe",
                            side_effect=RuntimeError("reexec"),
                        ) as execvpe:
                            with self.assertRaises(RuntimeError):
                                main()

            execvpe.assert_called_once()
            called_argv = execvpe.call_args.args[1]
            called_env = execvpe.call_args.args[2]
            self.assertEqual(Path(called_argv[0]).resolve(), local_koru)
            self.assertEqual(called_argv[1:], ["doctor", "--project", str(project)])
            self.assertEqual(called_env["VIRTUAL_ENV"], str((project / ".venv").resolve()))
            self.assertEqual(
                called_env["PATH"].split(os.pathsep)[0],
                str((project / ".venv" / "bin").resolve()),
            )
        finally:
            shutil.rmtree(project, ignore_errors=True)

    def test_doctor_flag_reexecs_when_interpreter_is_outside_project_venv(self) -> None:
        project = _tmp_git_project("koru-cli-doc-reexec-flag-")
        try:
            local_koru = self._prepare_local_koru(project)
            with mock.patch("sys.argv", ["koru", "--doctor", "--project", str(project)]):
                with mock.patch("koru._legacy_cli_impl.sys.executable", "/usr/bin/python3"):
                    with mock.patch("koru._legacy_cli_impl.sys.prefix", "/usr"):
                        with mock.patch(
                            "koru._legacy_cli_impl.os.execvpe",
                            side_effect=RuntimeError("reexec"),
                        ) as execvpe:
                            with self.assertRaises(RuntimeError):
                                main()

            execvpe.assert_called_once()
            called_argv = execvpe.call_args.args[1]
            called_env = execvpe.call_args.args[2]
            self.assertEqual(Path(called_argv[0]).resolve(), local_koru)
            self.assertEqual(called_argv[1:], ["--doctor", "--project", str(project)])
            self.assertEqual(called_env["VIRTUAL_ENV"], str((project / ".venv").resolve()))
            self.assertEqual(
                called_env["PATH"].split(os.pathsep)[0],
                str((project / ".venv" / "bin").resolve()),
            )
        finally:
            shutil.rmtree(project, ignore_errors=True)


class TestSubcommandDispatch(unittest.TestCase):
    """R6: routing through ``_SUBCOMMANDS`` dispatch table.

    We verify (a) the table contains every documented subcommand, and
    (b) routing dispatches to exactly the handler bound under each key,
    with the residual argv (``raw_args[1:]``) forwarded as-is.
    """

    EXPECTED_KEYS = frozenset(
        {
            "init-ci",
            "init-ide",
            "ide",
            "ide-router",
            "configure",
            "mesh",
            "vision",
            "observe",
            "agent-backends",
            "task",
            "agent",
            "local-serve",
            "serve",
            "scan",
            "gate",
            "queue",
            "replay",
            "gc",
            "doctor",
            "git",
            "tools",
            "mcp-serve",
            "autopilot",
            "autoloop",
            "autonomous",
            "auto",
            "wizard",
            "dsl",
            "api",
            "topology",
            "strategy",
            "runtime-context",
            "refactor-planfile-handoff",
            "tagi",
            "dev",
            "events",
            "self",
        },
    )

    def test_table_contains_all_documented_subcommands(self) -> None:
        self.assertEqual(self.EXPECTED_KEYS, set(_SUBCOMMANDS.keys()))

    def test_table_values_are_callables(self) -> None:
        for name, fn in _SUBCOMMANDS.items():
            self.assertTrue(callable(fn), f"{name!r} → {fn!r} is not callable")

    def test_each_subcommand_routes_to_its_handler(self) -> None:
        """``koru <name> a b c`` must call ``_SUBCOMMANDS[<name>](['a','b','c'])``."""
        for name in self.EXPECTED_KEYS:
            with self.subTest(subcommand=name):
                fake = mock.Mock(return_value=0)
                with mock.patch.dict(_SUBCOMMANDS, {name: fake}):
                    with mock.patch("koru._legacy_cli_impl._maybe_reexec_for_project_venv"):
                        with mock.patch("sys.argv", ["koru", name, "a", "b", "c"]):
                            code = main()
                        # Assert INSIDE the patch context so the mock is still bound.
                        fake.assert_called_once_with(["a", "b", "c"])
                    self.assertEqual(code, 0)

    def test_unknown_first_arg_falls_through_to_argparse(self) -> None:
        """A non-subcommand argv MUST NOT trigger any handler."""
        sentinels = {name: mock.Mock(side_effect=AssertionError) for name in self.EXPECTED_KEYS}
        with mock.patch.dict(_SUBCOMMANDS, sentinels):
            with mock.patch("koru.cli_doctor.doctor_main", return_value=0):
                code, _ = _run_main("--doctor", "--project", ".")
        self.assertEqual(code, 0)
        for handler in sentinels.values():
            handler.assert_not_called()

    def test_empty_argv_does_not_call_any_handler(self) -> None:
        project = _tmp_git_project("koru-cli-empty-")
        try:
            sentinels = {name: mock.Mock(side_effect=AssertionError) for name in self.EXPECTED_KEYS}
            with mock.patch.dict(_SUBCOMMANDS, sentinels):
                _run_main("--project", str(project))
        finally:
            shutil.rmtree(project, ignore_errors=True)


class TestAutoAliasBackwardCompat(unittest.TestCase):
    """Legacy installs expose ``autonomous`` but not ``auto`` (pyenv 3.12 wheels)."""

    def test_dispatch_auto_alias_routes_to_autonomous_when_auto_missing(self) -> None:
        called: list[tuple] = []

        def fake_autonomous(argv: list[str], *, invoked_as_auto: bool = False) -> int:
            called.append((list(argv), invoked_as_auto))
            return 0

        trimmed = {k: v for k, v in _SUBCOMMANDS.items() if k != "auto"}
        trimmed["autonomous"] = fake_autonomous
        stub = types.ModuleType("koru.cli_auto")
        with mock.patch.dict(_SUBCOMMANDS, trimmed, clear=True):
            with mock.patch.dict(sys.modules, {"koru.cli_auto": stub}):
                rc = _dispatch_auto_alias(["auto", "doctor"])
        self.assertEqual(rc, 0)
        self.assertEqual(called, [(["doctor"], True)])

    def test_dispatch_auto_alias_returns_none_when_auto_registered(self) -> None:
        self.assertIsNone(_dispatch_auto_alias(["auto", "--help"]))

    def test_suggest_auto_maps_to_autonomous_on_legacy_table(self) -> None:
        from koru.cli import _suggest_subcommand

        trimmed = {k: v for k, v in _SUBCOMMANDS.items() if k != "auto"}
        with mock.patch.dict(_SUBCOMMANDS, trimmed, clear=True):
            self.assertEqual(_suggest_subcommand("auto"), "autonomous")


class TestUnknownSubcommandHint(unittest.TestCase):
    """Regression: ``koru autox`` must print a ``Did you mean 'koru auto'?`` hint.

    Earlier `koru` builds shipped without the ``auto`` alias of ``autonomous``;
    users who upgraded the source tree but kept an older `koru` on PATH would
    just see ``koru: error: unrecognized arguments: auto`` with no hint. The
    suggestion engine in `main()` now points at the closest match.
    """

    def _run_capture_stderr(self, *argv: str) -> tuple[int, str]:
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with mock.patch("sys.argv", ["koru", *argv]):
            with mock.patch("sys.stdout", new=buf_out):
                with mock.patch("sys.stderr", new=buf_err):
                    with mock.patch(
                        "koru._legacy_cli_impl._maybe_reexec_for_project_venv"
                    ):
                        code = main()
        return code, buf_err.getvalue()

    def test_typo_close_to_auto_suggests_auto(self) -> None:
        code, stderr = self._run_capture_stderr("autox")
        self.assertEqual(code, 2)
        self.assertIn("'autox' is not a known subcommand", stderr)
        self.assertIn("Did you mean 'koru auto'", stderr)

    def test_typo_close_to_autoloop_suggests_autoloop(self) -> None:
        code, stderr = self._run_capture_stderr("floop")
        self.assertEqual(code, 2)
        self.assertIn("Did you mean 'koru autoloop'", stderr)

    def test_unrelated_token_lists_known_subcommands(self) -> None:
        code, stderr = self._run_capture_stderr("zzzzzzzzz")
        self.assertEqual(code, 2)
        self.assertIn("'zzzzzzzzz' is not a known subcommand", stderr)
        self.assertIn("Known subcommands:", stderr)
        self.assertIn("autonomous", stderr)
        self.assertIn("autopilot", stderr)
