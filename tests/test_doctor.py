"""Tests for ``koru --doctor`` (project diagnostics).

Each probe is exercised in at least one pass and one non-pass state.
The renderer and the JSON shape are also verified — the LLM consumer
relies on stable keys and order.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
                patch("koru.doctor.detect_terminal_host_ide_id", return_value=None),
                patch("koru.doctor.detect_running_ides", return_value=[]),
            ):
                report = _run(project)
            self.assertEqual(_named(report, "autopilot_env").status, SKIP)
            self.assertEqual(_named(report, "autopilot_socket").status, SKIP)
            self.assertEqual(_named(report, "autopilot_manage").status, SKIP)
            self.assertEqual(_named(report, "autopilot_debug_log").status, SKIP)

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
                patch("koru.doctor.collect_install_manager_report", return_value=fake_report),
                patch(
                    "koru.doctor._resolve_autopilot_socket_for_doctor",
                    return_value=Path("/tmp/a.sock"),
                ),
            ):
                report = _run(project)
            check = _named(report, "autopilot_manage")
            self.assertEqual(check.status, FAIL)
            self.assertIn("plugin_not_connected", check.detail)

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
        """Non-zero exit means errors — point operator at koru scan."""
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
