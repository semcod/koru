"""Tests for ``koru --doctor`` (project diagnostics).

Each probe is exercised in at least one pass and one non-pass state.
The renderer and the JSON shape are also verified — the LLM consumer
relies on stable keys and order.
"""

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from koru.doctor import (
    FAIL,
    PASS,
    SKIP,
    WARN,
    Check,
    DoctorReport,
    detected_problems,
    problem_catalog,
    render_problem_catalog_text,
    render_text,
    run_diagnostics,
)

# These tests use subprocess and are slow; skip by default
pytestmark = pytest.mark.slow

_AUTOPILOT_ENV_KEYS = (
    "KORU_AUTOPILOT_IDE",
    "KORU_AUTOPILOT_INSTANCE",
    "KORU_AUTOPILOT_SOCKET",
)


def _without_autopilot_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _AUTOPILOT_ENV_KEYS}


def _scaffold(project: Path, *, write_koru_yaml: bool = True) -> None:
    """Build a minimally valid koru project so individual probes pass."""
    pf = project / ".planfile"
    (pf / "sprints").mkdir(parents=True)
    (pf / ".koru").mkdir()
    (pf / "config.yaml").write_text("project: t\n", encoding="utf-8")
    (pf / "sprints" / "current.yaml").write_text(
        textwrap.dedent("""\
            sprint:
              id: current
              tickets:
                T-1:
                  id: T-1
                  name: x
                  executor: {kind: shell, handler: 'true'}
            """),
        encoding="utf-8",
    )
    (project / ".gitignore").write_text(".planfile/.koru/\n", encoding="utf-8")
    (project / ".git").mkdir()
    if write_koru_yaml:
        (project / "koru.yaml").write_text(
            textwrap.dedent("""\
                schema: "1.0"
                project: t
                when:
                  smoke:
                    description: test
                    commands:
                      - "true"
                """),
            encoding="utf-8",
        )


def _run(project: Path) -> DoctorReport:
    return run_diagnostics(project)


def _named(report: DoctorReport, name: str) -> Check:
    for c in report.checks:
        if c.name == name:
            return c
    raise AssertionError(f"check {name!r} not in {[c.name for c in report.checks]}")


class TestHappyPath(unittest.TestCase):
    def test_full_scaffold_passes_all_required_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch.dict(os.environ, _without_autopilot_env(), clear=True),
                patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}"),
                patch(
                    "koru.doctor_autopilot_checks.detect_terminal_host_ide_id",
                    return_value=None,
                ),
            ):
                report = _run(project)
            # No failures on a properly-set-up project.
            self.assertFalse(report.has_failures, msg=str(report.to_dict()))
            self.assertEqual(_named(report, "git_repo").status, PASS)
            self.assertEqual(_named(report, "planfile_config").status, PASS)
            self.assertEqual(_named(report, "planfile_sprints").status, PASS)
            self.assertEqual(_named(report, "runtime_dir").status, PASS)
            self.assertEqual(_named(report, "policy_yaml").status, PASS)
            self.assertEqual(_named(report, "gitignore").status, PASS)
            self.assertEqual(_named(report, "koru_project_pipeline").status, PASS)
            self.assertEqual(_named(report, "agent_backends_registry").status, PASS)
            self.assertEqual(_named(report, "interface_registry").status, PASS)
            self.assertIn(_named(report, "koru_package_version").status, (PASS, WARN))
            self.assertIn(_named(report, "planfile_cli_version").status, (PASS, WARN, SKIP))


class TestKoruProjectPipelineProbe(unittest.TestCase):
    def test_warns_when_planfile_ok_but_koru_yaml_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project, write_koru_yaml=False)
            with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}"):
                report = _run(project)
            self.assertEqual(_named(report, "koru_project_pipeline").status, WARN)


class TestAutonomousServiceStreamProbe(unittest.TestCase):
    def test_autonomous_service_stream_passes_when_idle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch("koru.autonomous_processes._find_existing_autonomous_processes", return_value=[]),
                patch("koru.autonomous_processes._find_existing_wup_processes", return_value=[]),
                patch("koru.doctor._autopilot_stream_socket_summary", return_value=([], 0, 0)),
            ):
                report = _run(project)
            check = _named(report, "autonomous_service_stream")
            self.assertEqual(check.status, PASS)
            self.assertIn("stream=single_or_idle", check.detail)

    def test_autonomous_service_stream_warns_on_duplicate_data_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            auto = [
                SimpleNamespace(pid=111, command=f"koru auto --project {project}"),
                SimpleNamespace(pid=222, command=f"koru autonomous up --project {project}"),
            ]
            wup = [
                SimpleNamespace(pid=333, command=f"wup watch {project}"),
                SimpleNamespace(pid=444, command=f"wup watch {project} --mode testql"),
            ]
            with (
                patch("koru.autonomous_processes._find_existing_autonomous_processes", return_value=auto),
                patch("koru.autonomous_processes._find_existing_wup_processes", return_value=wup),
                patch(
                    "koru.doctor._autopilot_stream_socket_summary",
                    return_value=(
                        [
                            "koru-autopilot-vscodium.sock:listening",
                            "koru-autopilot-vscode.sock:listening",
                        ],
                        2,
                        0,
                    ),
                ),
            ):
                report = _run(project)
            check = _named(report, "autonomous_service_stream")
            self.assertEqual(check.status, WARN)
            self.assertIn("multiple_autonomous_loops", check.detail)
            self.assertIn("multiple_wup_watchers", check.detail)
            self.assertIn("multiple_autopilot_socket_listeners", check.detail)
            self.assertIn("pid=111", check.detail)


class TestPlanfileCliVersionProbe(unittest.TestCase):
    def test_parses_version_from_stderr(self) -> None:
        from koru.doctor import _check_planfile_cli_version

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            with (
                patch(
                    "koru.doctor.subprocess.run",
                    return_value=SimpleNamespace(
                        stdout="",
                        stderr="Planfile CLI version: 9.8.7\n",
                        returncode=0,
                    ),
                ),
                patch(
                    "koru.doctor._planfile_version_argv",
                    return_value=["planfile", "--version"],
                ),
            ):
                status, detail = _check_planfile_cli_version(project)
            self.assertEqual(status, PASS)
            self.assertIn("9.8.7", detail)


class TestAutonomousEnvironDoctorIntegration(unittest.TestCase):
    def test_doctor_includes_autonomous_environ_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}"):
                with patch.dict(os.environ, {"TICKET_SOURCES": "scan"}, clear=False):
                    report = _run(project)
            check = _named(report, "autonomous_environ")
            self.assertEqual(check.status, PASS)
            self.assertIn("TICKET_SOURCES=scan", check.detail)

    def test_doctor_fails_on_invalid_ticket_sources_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}"):
                with patch.dict(os.environ, {"TICKET_SOURCES": "bogus"}, clear=False):
                    report = _run(project)
            self.assertEqual(_named(report, "autonomous_environ").status, FAIL)
            self.assertTrue(report.has_failures)

    def test_warns_when_no_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            shutil.rmtree(project / ".git")
            report = _run(project)
            self.assertEqual(_named(report, "git_repo").status, WARN)
            # gitignore probe is skipped without git.
            with self.assertRaises(AssertionError):
                _named(report, "gitignore")


class TestAutopilotDoctorChecks(unittest.TestCase):
    def test_autopilot_checks_skip_when_env_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch.dict(os.environ, _without_autopilot_env(), clear=True),
                patch(
                    "koru.doctor_autopilot_checks.detect_terminal_host_ide_id",
                    return_value=None,
                ),
                patch("koru.doctor_autopilot_checks.detect_running_ides", return_value=[]),
            ):
                report = _run(project)
            self.assertEqual(_named(report, "autopilot_env").status, SKIP)
            self.assertEqual(_named(report, "autopilot_socket").status, SKIP)
            self.assertEqual(_named(report, "autopilot_manage").status, SKIP)
            self.assertEqual(_named(report, "autopilot_debug_log").status, SKIP)
            self.assertEqual(_named(report, "plugin_console_logs").status, SKIP)
            self.assertEqual(_named(report, "ide_console_log").status, SKIP)

    def test_autopilot_env_warns_on_lane_ide_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            env = {
                **_without_autopilot_env(),
                "KORU_AUTOPILOT_INSTANCE": "windsurf",
                "KORU_AUTOPILOT_IDE": "antigravity",
            }
            with patch.dict(os.environ, env, clear=True):
                report = _run(project)
            check = _named(report, "autopilot_env")
            self.assertEqual(check.status, WARN)
            self.assertIn("instance_ide_mismatch=true", check.detail)

    def test_autopilot_env_shows_lane_matrix_when_multiple_ides_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            fake_vscode = SimpleNamespace(id="vscode")
            fake_vscodium = SimpleNamespace(id="vscodium")
            reports = {
                "vscode": SimpleNamespace(
                    daemon={"running": False},
                    plugin={"connected": False},
                ),
                "vscodium": SimpleNamespace(
                    daemon={"running": True},
                    plugin={"connected": True},
                ),
            }
            with (
                patch.dict(os.environ, _without_autopilot_env(), clear=True),
                patch(
                    "koru.doctor_autopilot_checks.detect_terminal_host_ide_id",
                    return_value="vscode",
                ),
                patch(
                    "koru.doctor_autopilot_checks.detect_running_ides",
                    return_value=[fake_vscode, fake_vscodium],
                ),
                patch(
                    "koru.doctor_autopilot_checks.collect_install_manager_report",
                    side_effect=lambda ide, socket_path=None: reports[ide],
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_env")
            self.assertEqual(check.status, WARN)
            self.assertIn("explicit_env_required_when_multiple=true", check.detail)
            self.assertIn("lane_matrix=vscode*:stopped/disconnected,vscodium:running/connected", check.detail)

    def test_python_venv_alignment_warns_on_stale_virtual_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".venv" / "bin").mkdir(parents=True)
            with (
                patch.dict(os.environ, {"VIRTUAL_ENV": str(project / "venv")}, clear=False),
                patch("sys.executable", str(project / ".venv" / "bin" / "python")),
                patch("shutil.which", return_value=str(project / ".venv" / "bin" / "koru")),
            ):
                report = _run(project)
            check = _named(report, "python_venv_alignment")
            self.assertEqual(check.status, PASS)
            self.assertIn("virtual_env_stale_label=true", check.detail)

    def test_python_venv_alignment_allows_unset_virtual_env_when_python_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".venv" / "bin").mkdir(parents=True)
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("sys.executable", str(project / ".venv" / "bin" / "python")),
                patch("shutil.which", return_value=str(project / ".venv" / "bin" / "koru")),
            ):
                report = _run(project)
            check = _named(report, "python_venv_alignment")
            self.assertEqual(check.status, PASS)
            self.assertIn("virtual_env_unset=true", check.detail)

    def test_autopilot_plugin_bundle_warns_on_expected_version_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            plugin = project / "plugins" / "koru-autopilot-vscode"
            plugin.mkdir(parents=True)
            (plugin / "package.json").write_text(
                json.dumps({"version": "9.9.9"}),
                encoding="utf-8",
            )
            (plugin / "package-lock.json").write_text(
                json.dumps({"version": "9.9.9", "packages": {"": {"version": "9.9.9"}}}),
                encoding="utf-8",
            )
            report = _run(project)
            check = _named(report, "autopilot_plugin_bundle")
            self.assertEqual(check.status, WARN)
            self.assertIn("package_version_mismatch", check.detail)
            self.assertIn("asset_vsix_missing", check.detail)

    def test_windsurf_chat_column_control_warns_on_post_send_keep_open_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        "2026-05-22T14:27:48Z WINDSURF_FASTPATH_EXECUTE_SEND_OK "
                        '{"attempt":1}',
                        "2026-05-22T14:27:49Z WINDSURF_KEEP_OPEN_OK "
                        '{"cmd":"windsurf.cascadePanel.open","reason":"after-sendTextToChat"}',
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "windsurf_chat_column_control")
            self.assertEqual(check.status, WARN)
            self.assertIn("risk=post_send_cascade_open", check.detail)

    def test_windsurf_chat_column_control_passes_when_keep_open_guard_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        '2026-05-22T14:27:48Z WINDSURF_FASTPATH_EXECUTE_SEND_OK {"attempt":1}',
                        (
                            "2026-05-22T14:27:49Z WINDSURF_KEEP_OPEN_DISABLED "
                            '{"reason":"after-sendTextToChat"}'
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "windsurf_chat_column_control")
            self.assertEqual(check.status, PASS)
            self.assertIn("post_send_keep_open_guard=disabled", check.detail)

    def test_autopilot_manage_maps_manager_error_to_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            fake_report = SimpleNamespace(
                issues=[
                    SimpleNamespace(
                        to_dict=lambda: {
                            "code": "plugin_not_connected",
                            "severity": "error",
                            "message": "not connected",
                        }
                    )
                ],
                plugin={
                    "ide": "antigravity",
                    "connected": False,
                    "connected_version": None,
                    "installed_version": "0.1.40",
                    "expected_version": "0.1.40",
                },
                daemon={"running": True},
                socket="/run/user/1000/koru-autopilot-antigravity.sock",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "antigravity",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor_autopilot_checks.collect_install_manager_report",
                    return_value=fake_report,
                ),
                patch(
                    "koru.doctor_autopilot_checks._resolve_autopilot_socket_for_doctor",
                    return_value=Path("/tmp/a.sock"),
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_manage")
            self.assertEqual(check.status, FAIL)
            self.assertIn("plugin_not_connected", check.detail)

    def test_autopilot_runtime_status_surfaces_live_plugin_build_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            fake_report = SimpleNamespace(
                issues=[],
                plugin={
                    "ide": "vscodium",
                    "supported": True,
                    "connected": True,
                    "connected_version": "0.2.7",
                    "connected_build_sha": "341728a18cd90915",
                    "installed_version": "0.2.7",
                    "expected_version": "0.2.7",
                    "expected_build_sha": "341728a18cd90915",
                },
                daemon={
                    "running": True,
                    "plugins": [
                        {"ide": "vscodium", "version": "0.2.7", "buildSha": "341728a18cd90915"}
                    ],
                },
                socket="/run/user/1000/koru-autopilot-vscodium.sock",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "vscodium",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor_autopilot_checks.collect_install_manager_report",
                    return_value=fake_report,
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_runtime_status")
            self.assertEqual(check.status, PASS)
            self.assertIn("connected_build=341728a18cd90915", check.detail)
            self.assertIn("expected_build=341728a18cd90915", check.detail)
            self.assertIn("runtime_status=healthy", check.detail)

    def test_autopilot_runtime_status_shows_alternate_lane_health(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            fake_vscode = SimpleNamespace(id="vscode")
            fake_vscodium = SimpleNamespace(id="vscodium")
            fake_reports = {
                "vscode": SimpleNamespace(
                    issues=[SimpleNamespace(to_dict=lambda: {"code": "daemon_not_running", "severity": "error"})],
                    plugin={
                        "ide": "vscode",
                        "supported": True,
                        "connected": False,
                        "connected_version": None,
                        "connected_build_sha": None,
                        "installed_version": "0.1.57",
                        "expected_version": "0.2.0",
                        "expected_build_sha": "caf883516b28b913",
                    },
                    daemon={"running": False, "plugins": []},
                    socket="/run/user/1000/koru-autopilot-vscode.sock",
                ),
                "vscodium": SimpleNamespace(
                    daemon={"running": True},
                    plugin={"connected": True},
                ),
            }
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "vscode",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor_autopilot_checks.detect_running_ides",
                    return_value=[fake_vscode, fake_vscodium],
                ),
                patch(
                    "koru.doctor_autopilot_checks.collect_install_manager_report",
                    side_effect=lambda ide, socket_path=None: fake_reports[ide],
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_runtime_status")
            self.assertEqual(check.status, FAIL)
            self.assertIn("lane_matrix=vscode*:stopped/disconnected,vscodium:running/connected", check.detail)

    def test_autopilot_chat_control_warns_on_submit_unverified_and_includes_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        (
                            '2026-05-27T06:36:27Z OUT {"ide":"vscodium",'
                            '"verification":"submit_unverified"}'
                        ),
                        (
                            '2026-05-27T06:36:30Z OUT {"ide":"vscodium",'
                            '"message":"host-key submit candidates ran but chat input still contains pasted text"}'
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "vscodium",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "autopilot_chat_control")
            self.assertEqual(check.status, WARN)
            self.assertIn("submit_unverified=", check.detail)
            self.assertIn("status_command=koru autopilot status --ide vscodium --explain", check.detail)
            self.assertIn("probe_command=koru autopilot drive --ide vscodium --require-plugin 'probe test'", check.detail)
            self.assertIn("validate_command=koru autopilot trace --project", check.detail)

    def test_autopilot_debug_log_warns_when_selected_ide_has_no_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                (
                    "2026-05-22T12:00:00Z CONNECT_CANDIDATES "
                    '{"ide":"windsurf","candidates":[]}\n'
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "antigravity",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "autopilot_debug_log")
            self.assertEqual(check.status, WARN)
            self.assertIn("no recent entries", check.detail)

    def test_autopilot_chat_control_warns_on_windsurf_fast_path_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        (
                            '2026-05-22T13:35:25.100Z CONNECT_OK '
                            '{"path":"/run/user/1000/koru-autopilot-windsurf.sock","ide":"windsurf"}'
                        ),
                        (
                            '2026-05-22T13:35:25.500Z WINDSURF_FASTPATH_CHECK_COMMAND '
                            '{"hasSendCmd":true}'
                        ),
                        (
                            '2026-05-22T13:35:26.000Z WINDSURF_FASTPATH_EXECUTE_SEND_ERROR '
                            '{"attempt":1,"error":"chat input not ready"}'
                        ),
                        (
                            '2026-05-22T13:35:33.000Z WINDSURF_FASTPATH_EXECUTE_SEND_OK '
                            '{"attempt":2}'
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                        "KORU_PLUGIN_DEBUG_LOG": str(log),
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._resolve_autopilot_socket_for_doctor",
                    return_value=Path("/run/user/1000/koru-autopilot-windsurf.sock"),
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_chat_control")
            self.assertEqual(check.status, WARN)
            self.assertIn("fast_send_errors=1", check.detail)
            self.assertIn("recovered_after_retry=true", check.detail)

    def test_autopilot_chat_control_warns_on_latest_paste_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                (
                    '2026-05-22T13:35:26.000Z OUT {"ok":false,'
                    '"ide":"windsurf","message":"chat opened but paste command failed '
                    '(fast path failed)"}\n'
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "autopilot_chat_control")
            self.assertEqual(check.status, WARN)
            self.assertIn("paste_failures=1", check.detail)
            self.assertIn("latest_chat_control_failure=true", check.detail)

    def test_autopilot_chat_control_passes_on_clean_native_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        (
                            "2026-05-22T13:35:25.500Z WINDSURF_FASTPATH_CHECK_COMMAND "
                            '{"hasSendCmd":true}'
                        ),
                        '2026-05-22T13:35:26.000Z WINDSURF_FASTPATH_EXECUTE_SEND_OK {"attempt":1}',
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "autopilot_chat_control")
            self.assertEqual(check.status, PASS)
            self.assertIn("chat_control=stable", check.detail)

    def test_autopilot_chat_control_uses_daemon_activity_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        (
                            '2026-05-22T13:45:01.340Z CONNECT_CANDIDATES '
                            '{"ide":"windsurf","candidates":[]}'
                        ),
                        (
                            '2026-05-22T13:45:01.340Z CONNECT_ERROR '
                            '{"path":"/run/user/1000/koru-autopilot-windsurf.sock"}'
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            nfo = project / ".planfile" / ".koru" / "nfo-events.jsonl"
            nfo.write_text(
                json.dumps(
                    {
                        "extra": {
                            "activity_message": (
                                "CHAT: autopilot: ok "
                                "(ticket=STARTER-183, ide=windsurf, backend=plugin)"
                            )
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_PLUGIN_DEBUG_LOG": str(log),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "autopilot_chat_control")
            self.assertEqual(check.status, PASS)
            self.assertIn("daemon_successes=1", check.detail)

    def test_plugin_console_logs_reads_daemon_status_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._resolve_autopilot_socket_for_doctor",
                    return_value=Path("/run/user/1000/koru-autopilot-windsurf.sock"),
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=(
                        [
                            {
                                "timestamp": "2026-05-22T12:00:00Z",
                                "ide": "antigravity",
                                "message": "ANTIGRAVITY_FASTPATH_START",
                            },
                            {
                                "timestamp": "2026-05-22T12:00:01Z",
                                "ide": "windsurf",
                                "version": "0.1.45",
                                "message": "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
                                "data": {"attempt": 1},
                            },
                        ],
                        None,
                    ),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, PASS)
            self.assertIn("source=daemon", check.detail)
            self.assertIn("WINDSURF_FASTPATH_EXECUTE_SEND_OK", check.detail)
            self.assertNotIn("ANTIGRAVITY_FASTPATH_START", check.detail)

    def test_plugin_console_logs_falls_back_to_debug_log_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        '2026-05-22T12:00:00Z WINDSURF_FASTPATH_START {"attempt":1}',
                        '2026-05-22T12:00:01Z WINDSURF_FASTPATH_EXECUTE_SEND_OK {"attempt":1}',
                    ]
                ),
                encoding="utf-8",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                        "KORU_PLUGIN_DEBUG_LOG": str(log),
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=([], "daemon unreachable"),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, WARN)
            self.assertIn("source=plugin_debug_log", check.detail)
            self.assertIn("WINDSURF_FASTPATH_EXECUTE_SEND_OK", check.detail)
            self.assertIn("daemon_status_error=daemon unreachable", check.detail)

    def test_plugin_console_logs_treats_stopped_daemon_connect_tail_as_informational(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            socket = Path("/run/user/1000/koru-autopilot-windsurf.sock")
            log = project / "plugin.log"
            log.write_text(
                "\n".join(
                    [
                        (
                            '2026-05-22T12:00:00Z CONNECT_CANDIDATES '
                            '{"ide":"windsurf","candidates":["'
                            f'{socket}"]}}'
                        ),
                        f'2026-05-22T12:00:01Z CONNECT_TRY {{"path":"{socket}"}}',
                        (
                            '2026-05-22T12:00:02Z CONNECT_ERROR '
                            f'{{"path":"{socket}","message":"connect ENOENT {socket}"}}'
                        ),
                        f'2026-05-22T12:00:03Z CONNECT_CLOSE {{"path":"{socket}"}}',
                    ]
                ),
                encoding="utf-8",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                        "KORU_PLUGIN_DEBUG_LOG": str(log),
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._resolve_autopilot_socket_for_doctor",
                    return_value=socket,
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=([], "[Errno 2] No such file or directory"),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, PASS)
            self.assertIn("daemon_offline_expected_after_stop=true", check.detail)
            self.assertIn("daemon_status_error=", check.detail)

    def test_plugin_console_logs_respects_tail_limit_and_filters_selected_ide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                        "KORU_DOCTOR_CONSOLE_LOG_LINES": "2",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._resolve_autopilot_socket_for_doctor",
                    return_value=Path("/run/user/1000/koru-autopilot-windsurf.sock"),
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=(
                        [
                            {"ide": "windsurf", "message": "WINDSURF_FIRST"},
                            {"ide": "antigravity", "message": "ANTIGRAVITY_IGNORED"},
                            {"ide": "windsurf", "message": "WINDSURF_SECOND"},
                            {"ide": "windsurf", "message": "WINDSURF_THIRD"},
                        ],
                        None,
                    ),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, PASS)
            self.assertIn("entries=3", check.detail)
            self.assertNotIn("WINDSURF_FIRST", check.detail)
            self.assertNotIn("ANTIGRAVITY_IGNORED", check.detail)
            self.assertIn("WINDSURF_SECOND", check.detail)
            self.assertIn("WINDSURF_THIRD", check.detail)

    def test_plugin_console_logs_matches_ide_nested_in_data_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=(
                        [
                            {
                                "timestamp": "2026-05-22T12:00:00Z",
                                "message": "WINDSURF_KEEP_OPEN_OK",
                                "data": {"ide": "windsurf", "cmd": "windsurf.cascadePanel.open"},
                            }
                        ],
                        None,
                    ),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, PASS)
            self.assertIn("WINDSURF_KEEP_OPEN_OK", check.detail)
            self.assertIn("windsurf.cascadePanel.open", check.detail)

    def test_plugin_console_logs_warns_when_no_daemon_or_debug_log_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            missing_log = project / "missing-plugin.log"
            with (
                patch.dict(
                    os.environ,
                    {
                        **_without_autopilot_env(),
                        "KORU_AUTOPILOT_INSTANCE": "windsurf",
                        "KORU_PLUGIN_DEBUG_LOG": str(missing_log),
                    },
                    clear=True,
                ),
                patch(
                    "koru.doctor._daemon_console_logs_for_doctor",
                    return_value=([], "daemon unreachable"),
                ),
            ):
                report = _run(project)
            check = _named(report, "plugin_console_logs")
            self.assertEqual(check.status, WARN)
            self.assertIn("daemon_status_error=daemon unreachable", check.detail)

    def test_ide_console_log_warns_with_recent_windsurf_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            logs = Path(tmp) / "logs"
            session = logs / "20260522T130000"
            session.mkdir(parents=True)
            (session / "window.log").write_text(
                "\n".join(
                    [
                        "2026-05-22 info started",
                        "[Extension Host] rejected promise not handled within 1 second",
                        "[codeium.windsurf] Error: Language server has not been started!",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, WARN)
            self.assertIn("interesting=2", check.detail)
            self.assertIn("Language server has not been started", check.detail)
            self.assertIn("language_server_not_started=1", check.detail)

    def test_ide_console_log_passes_without_recent_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            logs = Path(tmp) / "logs"
            session = logs / "20260522T130000"
            session.mkdir(parents=True)
            (session / "window.log").write_text(
                "2026-05-22 info workbench ready\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, PASS)
            self.assertIn("no recent warnings/errors", check.detail)

    def test_ide_console_log_warns_when_log_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            missing_logs = Path(tmp) / "missing-logs"
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(missing_logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, WARN)
            self.assertIn("log root missing", check.detail)

    def test_ide_console_log_prefers_error_headlines_over_stack_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            logs = Path(tmp) / "logs"
            session = logs / "20260522T130000" / "window1" / "exthost"
            session.mkdir(parents=True)
            (session / "app.log").write_text(
                "\n".join(
                    [
                        (
                            "[Extension Host] stack trace: Error: "
                            "Language server has not been started!"
                        ),
                        (
                            "    at get client "
                            "(/usr/share/windsurf/resources/app/extensions/windsurf/dist/"
                            "extension.js:2:1)"
                        ),
                        "    at async runNextTicks (node:internal/process/task_queues:65:5)",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, WARN)
            self.assertIn("Language server has not been started", check.detail)
            self.assertNotIn("at async", check.detail)

    def test_ide_console_log_reads_nested_extension_host_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            logs = Path(tmp) / "logs"
            nested = logs / "20260522T130000" / "window1" / "exthost" / "codeium.windsurf"
            nested.mkdir(parents=True)
            (nested / "Windsurf.log").write_text(
                "Creating a TrustedTypePolicy named 'lexical' violates CSP\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, WARN)
            self.assertIn("TrustedTypePolicy", check.detail)

    def test_ide_console_log_classifies_windsurf_startup_and_cascade_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _scaffold(project)
            logs = Path(tmp) / "logs"
            session = logs / "20260522T145552"
            session.mkdir(parents=True)
            (session / "window.log").write_text(
                "\n".join(
                    [
                        (
                            "This document requires 'TrustedScript' assignment. "
                            "The action has been blocked."
                        ),
                        (
                            "WARN IWorkbenchContributionsRegistry#getContribution"
                            "('windsurf.cascadePanel'): contribution instantiated before "
                            "LifecyclePhase.Restored!"
                        ),
                        (
                            "WARN [codeium.windsurf]: Cannot register "
                            "'windsurf.marketplaceGalleryItemURL'. "
                            "This property is already registered."
                        ),
                        (
                            "Overwriting grammar scope name to file mapping for scope source.ts."
                        ),
                        (
                            "GET https://marketplace.windsurf.com/vscode/gallery/"
                            "semcod/koru-autopilot-vscode/latest 404 (Not Found)"
                        ),
                        (
                            "POST http://k.localhost:35697/"
                            "exa.language_server_pb.LanguageServerService/"
                            "AcknowledgeCascadeCodeEdit 500 (Internal Server Error)"
                        ),
                        (
                            "File or directory "
                            '"/home/tom/github/maskservice/c2004/app" does not exist.'
                        ),
                        "ERR App icon customization is not supported on this OS",
                        (
                            "[Extension Host] failed to find pyright executable, "
                            "falling back to bundled"
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    **_without_autopilot_env(),
                    "KORU_AUTOPILOT_INSTANCE": "windsurf",
                    "KORU_IDE_CONSOLE_LOG_DIR": str(logs),
                },
                clear=True,
            ):
                report = _run(project)
            check = _named(report, "ide_console_log")
            self.assertEqual(check.status, WARN)
            for category in (
                "trusted_types=1",
                "extension_registration=1",
                "grammar_scope_overwrite=1",
                "missing_workspace_path=1",
                "marketplace_404=1",
                "cascade_rpc_500=1",
                "cascade_panel_early_restore=1",
                "app_icon_unsupported=1",
                "pyright_fallback=1",
            ):
                self.assertIn(category, check.detail)


class TestPlanfileBinary(unittest.TestCase):
    def test_explicit_env_var_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            fake = project / "fakebin"
            fake.write_text("#!/bin/sh\n", encoding="utf-8")
            fake.chmod(0o755)
            with patch.dict(os.environ, {"KORU_PLANFILE_CMD": str(fake)}, clear=False):
                report = _run(project)
            self.assertEqual(_named(report, "planfile_binary").status, PASS)

    def test_missing_binary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            env = {k: v for k, v in os.environ.items() if k != "KORU_PLANFILE_CMD"}
            with patch.dict(os.environ, env, clear=True), patch("shutil.which", return_value=None):
                report = _run(project)
            self.assertEqual(_named(report, "planfile_binary").status, FAIL)


class TestPlanfileConfigCheck(unittest.TestCase):
    def test_missing_config_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / "config.yaml").unlink()
            report = _run(project)
            self.assertEqual(_named(report, "planfile_config").status, FAIL)
            self.assertIn("missing", _named(report, "planfile_config").detail)

    def test_malformed_config_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / "config.yaml").write_text(
                "this: is: not: valid",
                encoding="utf-8",
            )
            report = _run(project)
            self.assertEqual(_named(report, "planfile_config").status, FAIL)


class TestSprintsCheck(unittest.TestCase):
    def test_empty_sprint_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / "sprints" / "current.yaml").write_text(
                "sprint:\n  id: current\n  tickets: {}\n",
                encoding="utf-8",
            )
            report = _run(project)
            self.assertEqual(_named(report, "planfile_sprints").status, WARN)

    def test_no_sprints_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            shutil.rmtree(project / ".planfile" / "sprints")
            report = _run(project)
            self.assertEqual(_named(report, "planfile_sprints").status, FAIL)


class TestPolicyYamlCheck(unittest.TestCase):
    def test_absent_policy_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            report = _run(project)
            self.assertEqual(_named(report, "policy_yaml").status, PASS)

    def test_malformed_policy_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / ".koru" / "policy.yaml").write_text(
                "this: is: not: valid",
                encoding="utf-8",
            )
            report = _run(project)
            self.assertEqual(_named(report, "policy_yaml").status, FAIL)

    def test_string_truthy_value_warns(self) -> None:
        """`allow_commit: "true"` is rejected by load_policy — doctor surfaces it."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / ".koru" / "policy.yaml").write_text(
                'llm:\n  allow_commit: "true"\n',
                encoding="utf-8",
            )
            report = _run(project)
            self.assertEqual(_named(report, "policy_yaml").status, WARN)
            self.assertIn("allow_commit", _named(report, "policy_yaml").detail)


class TestGitignoreCheck(unittest.TestCase):
    def test_warns_when_runtime_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
            report = _run(project)
            self.assertEqual(_named(report, "gitignore").status, WARN)


class TestCiCommandCheck(unittest.TestCase):
    def test_empty_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            report = _run(project)
            # Default policy has empty ci_command.
            self.assertEqual(_named(report, "ci_command").status, WARN)

    def test_resolved_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / ".koru" / "policy.yaml").write_text(
                'ci:\n  command: "echo hi"\n',
                encoding="utf-8",
            )
            report = _run(project)
            self.assertEqual(_named(report, "ci_command").status, PASS)


class TestPytestCollectProbe(unittest.TestCase):
    """Behaviour of the ``pytest_collect`` doctor probe.

    The probe maps real subprocess outcomes to the four doctor states
    (PASS/WARN/FAIL/SKIP). The mapping is the contract — we mock
    ``subprocess.run`` directly to keep tests deterministic and fast.
    """

    def _scaffold_with_pyproject(self, project: Path) -> None:
        _scaffold(project)
        # The probe only registers when pyproject.toml or tests/ exists,
        # so we always provide one.
        (project / "pyproject.toml").write_text(
            "[project]\nname = 'test'\n",
            encoding="utf-8",
        )

    def test_pass_when_collection_succeeds_with_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(
                returncode=0,
                stdout="42 tests collected in 0.13s",
                stderr="",
            )
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, PASS)
            self.assertIn("42", check.detail)

    def test_pass_when_count_not_parseable(self) -> None:
        """rc==0 but no parseable count line — still pass, just no number."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            self.assertEqual(_named(report, "pytest_collect").status, PASS)

    def test_warn_when_zero_tests_collected(self) -> None:
        """Empty test suite is suspicious — warn but don't fail."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(
                returncode=0,
                stdout="collected 0 items",
                stderr="",
            )
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, WARN)
            self.assertIn("0 tests collected", check.detail)

    def test_warn_when_collection_errors(self) -> None:
        """Non-zero exit means errors — include one useful headline."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(
                returncode=2,
                stdout="",
                stderr="ImportError: foo",
            )
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, WARN)
            self.assertIn("koru scan", check.detail)
            self.assertIn("ImportError: foo", check.detail)

    def test_warn_when_collection_error_is_reported_on_stdout(self) -> None:
        """Some pytest failures put the collection headline on stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(
                returncode=2,
                stdout=(
                    "============================= test session starts "
                    "=============================\n"
                    "ERROR collecting tests/test_plugin.py\n"
                    "ModuleNotFoundError: No module named 'windsurf'\n"
                ),
                stderr="",
            )
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, WARN)
            self.assertIn("ERROR collecting tests/test_plugin.py", check.detail)

    def test_warn_when_collection_failure_output_is_empty(self) -> None:
        """Empty subprocess output still reports a clean actionable hint."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)
            fake = SimpleNamespace(returncode=1, stdout="", stderr="")
            with patch("subprocess.run", return_value=fake):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, WARN)
            self.assertIn("koru scan", check.detail)
            self.assertNotIn("first_error=", check.detail)

    def test_fail_when_collection_times_out(self) -> None:
        """Hangs are the strongest signal — promote to FAIL.

        This is the doctor counterpart of the scan timeout fix
        (PLF-093 post-mortem, 2026-05-11). Both surfaces must agree:
        a hung pytest is a real, blocking problem.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)

            def boom(*_args, **_kwargs):
                raise subprocess.TimeoutExpired(cmd="pytest", timeout=15)

            with patch("subprocess.run", side_effect=boom):
                report = _run(project)
            check = _named(report, "pytest_collect")
            self.assertEqual(check.status, FAIL)
            self.assertIn("hung", check.detail.lower())
            self.assertIn("koru scan", check.detail)

    def test_skip_when_pytest_not_installed(self) -> None:
        """Missing pytest binary is environmental, not actionable here."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self._scaffold_with_pyproject(project)

            def missing(*_a, **_kw):
                raise FileNotFoundError("python3 not found")

            with patch("subprocess.run", side_effect=missing):
                report = _run(project)
            self.assertEqual(_named(report, "pytest_collect").status, SKIP)

    def test_probe_skipped_entirely_when_no_pyproject_and_no_tests(self) -> None:
        """Bare project (no pyproject, no tests dir) — probe not even run."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)  # scaffold only, no pyproject, no tests/
            report = _run(project)
            names = [c.name for c in report.checks]
            self.assertNotIn("pytest_collect", names)

    def test_env_var_overrides_timeout(self) -> None:
        """KORU_DOCTOR_PYTEST_TIMEOUT lets ops tighten/extend the limit."""
        from koru.doctor import _resolve_pytest_collect_timeout

        with patch.dict(os.environ, {"KORU_DOCTOR_PYTEST_TIMEOUT": "3"}):
            self.assertEqual(_resolve_pytest_collect_timeout(), 3.0)
        # Garbage values fall back silently — no surprises for typos.
        with patch.dict(os.environ, {"KORU_DOCTOR_PYTEST_TIMEOUT": "not-a-num"}):
            self.assertEqual(_resolve_pytest_collect_timeout(), 15.0)
        # Negative / zero also falls back to default.
        with patch.dict(os.environ, {"KORU_DOCTOR_PYTEST_TIMEOUT": "-5"}):
            self.assertEqual(_resolve_pytest_collect_timeout(), 15.0)


class TestReportShape(unittest.TestCase):
    def test_to_dict_keys_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            d = _run(project).to_dict()
            self.assertEqual(
                set(d),
                {
                    "schema_version",
                    "project",
                    "summary",
                    "has_failures",
                    "checks",
                },
            )
            for check in d["checks"]:
                self.assertEqual(set(check), {"name", "status", "detail"})

    def test_render_text_groups_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            text = render_text(_run(project))
            self.assertIn("koru doctor", text)
            self.assertIn("[OK ]", text)
            self.assertIn("planfile_config", text)
            self.assertIn("checks", text.lower())

    def test_summary_counts_match_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            report = _run(project)
            counts = report.summary()
            self.assertEqual(
                sum(counts.values()),
                len(report.checks),
            )


class TestWupAndInotifyProbes(unittest.TestCase):
    def test_inotify_watches_non_linux_skipped(self) -> None:
        from koru.doctor import _check_inotify_watches
        with patch("sys.platform", "darwin"):
            status, detail = _check_inotify_watches(Path("."))
            self.assertEqual(status, SKIP)
            self.assertIn("only applicable", detail)

    def test_inotify_watches_linux_low_limit_fails(self) -> None:
        from koru.doctor import _check_inotify_watches
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="16384"):
                    status, detail = _check_inotify_watches(Path("."))
                    self.assertEqual(status, FAIL)
                    self.assertIn("too low", detail)

    def test_inotify_watches_linux_high_limit_passes(self) -> None:
        from koru.doctor import _check_inotify_watches
        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="1048576"):
                    status, detail = _check_inotify_watches(Path("."))
                    self.assertEqual(status, PASS)
                    self.assertIn("sufficient", detail)

    def test_wup_binary_missing_warns(self) -> None:
        from koru.doctor import _check_wup_binary
        with patch("shutil.which", return_value=None):
            status, detail = _check_wup_binary(Path("."))
            self.assertEqual(status, WARN)
            self.assertIn("not on PATH", detail)

    def test_wup_binary_present_passes(self) -> None:
        from koru.doctor import _check_wup_binary
        with patch("shutil.which", return_value="/usr/bin/wup"):
            status, detail = _check_wup_binary(Path("."))
            self.assertEqual(status, PASS)
            self.assertIn("/usr/bin/wup", detail)


class TestProblemCatalogAndDetectedProblems(unittest.TestCase):
    def test_problem_catalog_has_entries(self) -> None:
        catalog = problem_catalog()
        self.assertTrue(catalog)
        self.assertTrue(any(item.get("check") == "planfile_config" for item in catalog))

    def test_detected_problems_only_warn_or_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            report = _run(project)
            problems = detected_problems(report)
            self.assertTrue(problems)
            self.assertTrue(all(p["status"] in {WARN, FAIL} for p in problems))

    def test_render_problem_catalog_text_mentions_detection(self) -> None:
        text = render_problem_catalog_text()
        self.assertIn("Known problems", text)
        self.assertIn("detection:", text)


if __name__ == "__main__":
    unittest.main()
