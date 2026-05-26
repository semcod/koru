from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from koru import cli_scan
from koru.scan import (
    ScanResult,
    Suggestion,
    _suggestion_dedupe_key,
    run_scan,
    scan_gitignore_drift,
    scan_missing_gates,
    scan_missing_tools,
    scan_pytest_collect,
    scan_semcod_quality_artifacts,
    scan_todo_markers,
)


def _ok(stdout: str = "", returncode: int = 0, stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _marker_fixture(*names: str) -> str:
    return "".join(f"# {name}: marker\n" for name in names)


_MARK_A = "TO" + "DO"
_MARK_B = "FIX" + "ME"
_MARK_C = "X" * 3
_MARK_D = "HA" + "CK"


class TestScanCLI(unittest.TestCase):
    def test_json_output_uses_scan_result_dict_and_semcod_flag(self) -> None:
        result = ScanResult(
            suggestions=[
                Suggestion(
                    signal="semcod",
                    title="Read semcod exports",
                    description="ok",
                ),
            ],
        )

        with mock.patch("koru.cli_scan.run_scan", return_value=result) as run:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_scan.scan_main(
                    [
                        "--project",
                        "/tmp/project",
                        "--skip-pytest",
                        "--semcod-artifacts",
                        "--format",
                        "json",
                    ],
                )

        self.assertEqual(rc, 0)
        run.assert_called_once()
        self.assertTrue(run.call_args.kwargs["include_semcod_artifacts"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["suggestions"][0]["signal"], "semcod")

    def test_cli_passes_path_filters_to_run_scan(self) -> None:
        with mock.patch("koru.cli_scan.run_scan", return_value=ScanResult(suggestions=[])) as run:
            rc = cli_scan.scan_main(
                [
                    "--project",
                    "/tmp/project",
                    "--path",
                    "src/koru",
                    "--path",
                    "tests/test_scan.py",
                    "--format",
                    "json",
                ],
            )

        self.assertEqual(rc, 0)
        self.assertEqual(run.call_args.kwargs["paths"], ["src/koru", "tests/test_scan.py"])

    def test_code2llm_god_and_refactor_share_file_dedupe_key(self) -> None:
        god = Suggestion(
            signal="code2llm_god",
            title="Split god module: src/koru/autonomous.py",
            description="god",
            files=("src/koru/autonomous.py",),
        )
        refactor = Suggestion(
            signal="code2llm_refactor",
            title="code2llm refactor: split src/koru/autonomous.py",
            description="refactor",
            files=("src/koru/autonomous.py",),
        )

        self.assertEqual(
            _suggestion_dedupe_key("koru-scan", god),
            _suggestion_dedupe_key("prefact", refactor),
        )

    def test_render_scan_text_colors_signal_in_tty(self) -> None:
        result = ScanResult(
            suggestions=[
                Suggestion(
                    signal="code2llm_cc",
                    title="Reduce CC",
                    description="desc",
                    priority="high",
                ),
            ],
        )

        with mock.patch.dict("os.environ", {"CLICOLOR_FORCE": "1", "NO_COLOR": ""}, clear=False):
            with mock.patch("sys.stdout.isatty", return_value=True):
                text = cli_scan.render_scan_text(result)

        self.assertIn("\033[", text)
        self.assertIn("code2llm_cc", text)

    def test_render_scan_text_respects_no_color(self) -> None:
        result = ScanResult(
            suggestions=[
                Suggestion(
                    signal="code2llm_cc",
                    title="Reduce CC",
                    description="desc",
                    priority="high",
                ),
            ],
        )

        with mock.patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            with mock.patch("sys.stdout.isatty", return_value=True):
                text = cli_scan.render_scan_text(result)

        self.assertNotIn("\033[", text)

    def test_render_scan_text_uses_distinct_signal_colors(self) -> None:
        result = ScanResult(
            suggestions=[
                Suggestion(
                    signal="code2llm_cc",
                    title="Reduce CC",
                    description="desc",
                    priority="normal",
                ),
                Suggestion(
                    signal="redup_overlap",
                    title="Remove duplicate",
                    description="desc",
                    priority="normal",
                ),
                Suggestion(
                    signal="pytest_flaky",
                    title="Stabilize test",
                    description="desc",
                    priority="normal",
                ),
            ],
        )

        with mock.patch.dict("os.environ", {"CLICOLOR_FORCE": "1", "NO_COLOR": ""}, clear=False):
            with mock.patch("sys.stdout.isatty", return_value=True):
                text = cli_scan.render_scan_text(result)

        self.assertIn("\033[36mcode2llm_cc", text)
        self.assertIn("\033[35mredup_overlap", text)
        self.assertIn("\033[33mpytest_flaky", text)


class TestScanPytestCollect(unittest.TestCase):
    def test_returns_empty_when_no_tests_and_no_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(scan_pytest_collect(Path(tmp)), [])

    def test_empty_on_clean_collect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")
            result = scan_pytest_collect(
                project,
                runner=lambda _c, _p: _ok("4 tests collected"),
            )
            self.assertEqual(result, [])

    def test_parses_per_file_collection_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")
            output = (
                "ERROR tests/test_foo.py - ImportError: No module named 'foo'\n"
                "ERROR tests/test_bar.py::TestBar - ModuleNotFoundError: bar\n"
            )
            result = scan_pytest_collect(
                project,
                runner=lambda _c, _p: _ok(output, returncode=2),
            )
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].signal, "pytest_collect")
            self.assertEqual(result[0].priority, "high")
            self.assertIn("tests/test_foo.py", result[0].title)
            self.assertEqual(result[0].files, ("tests/test_foo.py",))
            self.assertIn("tests/test_bar.py", result[1].title)

    def test_falls_back_to_umbrella_import_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")
            output = "E   ModuleNotFoundError: No module named 'goal'\n--- collection errors ---\n"
            result = scan_pytest_collect(
                project,
                runner=lambda _c, _p: _ok(output, returncode=2),
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].signal, "pytest_collect")
            self.assertIn("Fix package import path", result[0].title)
            self.assertIn("pythonpath", result[0].description)

    def test_collection_timeout_emits_diagnostic_ticket(self) -> None:
        """A timeout is a *real* problem — koru must NOT swallow it.

        Historical bug (PLF-093 post-mortem, 2026-05-11): timeouts were
        treated as silent success ("no suggestions — repo looks clean").
        That produced false-positive green lights when pytest collection
        actually hung. Pin the corrected behavior: surface the timeout
        as its own actionable ticket.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")

            def boom(_cmd, _proj):
                raise subprocess.TimeoutExpired(cmd="pytest", timeout=30)

            result = scan_pytest_collect(
                project,
                runner=boom,
                timeout_seconds=30.0,
            )
            self.assertEqual(len(result), 1)
            ticket = result[0]
            self.assertEqual(ticket.signal, "pytest_collect_timeout")
            self.assertEqual(ticket.priority, "high")
            self.assertIn("timeout", ticket.labels)
            self.assertIn("ci", ticket.labels)
            # The description must be actionable — not just "it hung".
            self.assertIn("conftest", ticket.description)
            self.assertIn("norecursedirs", ticket.description)
            self.assertIn("30", ticket.description)  # the actual timeout value

    def test_timeout_value_is_reflected_in_ticket(self) -> None:
        """If the operator overrides timeout_seconds, the ticket says so."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")

            def boom(_cmd, _proj):
                raise subprocess.TimeoutExpired(cmd="pytest", timeout=5)

            result = scan_pytest_collect(
                project,
                runner=boom,
                timeout_seconds=5.0,
            )
            self.assertEqual(len(result), 1)
            self.assertIn("5s", result[0].description)

    def test_pytest_not_installed_stays_silent(self) -> None:
        """Missing pytest binary is environmental, not a project bug.

        We deliberately do *not* create a ticket here — the operator
        cannot act on it from inside the repo. Distinguish carefully
        from the timeout case above.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")

            def missing(_cmd, _proj):
                raise FileNotFoundError("python3: command not found")

            self.assertEqual(scan_pytest_collect(project, runner=missing), [])


class TestScanTodoMarkers(unittest.TestCase):
    def test_filters_files_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "low.py").write_text(_marker_fixture(_MARK_A))
            self.assertEqual(scan_todo_markers(project, min_per_file=3), [])

    def test_groups_markers_per_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "hot.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C, _MARK_D),
            )
            (project / "warm.py").write_text(_marker_fixture(_MARK_A, _MARK_B, _MARK_C))
            result = scan_todo_markers(project, min_per_file=3)
            titles = {s.title for s in result}
            self.assertEqual(len(result), 2)
            self.assertTrue(any("hot.py" in t for t in titles))
            self.assertTrue(any("warm.py" in t for t in titles))
            for s in result:
                self.assertEqual(s.priority, "low")
                self.assertIn("scan", s.labels)

    def test_respects_koruignore_file_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".koruignore").write_text(".koru_scan_*.py\n")
            (project / ".koru_scan_probe.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )
            (project / "normal.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )

            result = scan_todo_markers(project, min_per_file=3)
            self.assertEqual(len(result), 1)
            self.assertIn("normal.py", result[0].title)

    def test_respects_koruignore_directory_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".koruignore").write_text("generated/\n")
            generated = project / "generated"
            generated.mkdir(parents=True)
            (generated / "noise.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )
            (project / "src.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )

            result = scan_todo_markers(project, min_per_file=3)
            self.assertEqual(len(result), 1)
            self.assertIn("src.py", result[0].title)

    def test_ignores_common_virtualenv_dirs_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            venv_test = project / "connect-scenario" / "backend" / ".venv-test"
            venv_test.mkdir(parents=True)
            (venv_test / "noise.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )
            (project / "src.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )

            result = scan_todo_markers(project, min_per_file=3)
            self.assertEqual(len(result), 1)
            self.assertIn("src.py", result[0].title)


class TestScanMissingGates(unittest.TestCase):
    def test_no_suggestions_when_tool_missing(self) -> None:
        # If neither `wup` nor `regix` is installed, scan returns []
        # for them — we can't reliably stub PATH here, so we only assert
        # the structure: suggestions, if any, target known gates.
        with tempfile.TemporaryDirectory() as tmp:
            for s in scan_missing_gates(Path(tmp)):
                self.assertEqual(s.signal, "missing_gate")
                self.assertIn(s.labels[0], {"bootstrap"})

    def test_skips_when_config_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "wup.yaml").write_text("# present")
            (project / "regix.yaml").write_text("# present")
            for s in scan_missing_gates(project):
                # If installed, wup/regix should NOT appear (config present)
                self.assertNotIn("wup", s.title)
                self.assertNotIn("regix", s.title)


class TestScanMissingTools(unittest.TestCase):
    def test_no_pyproject_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(scan_missing_tools(Path(tmp)), [])

    def test_skips_tools_not_in_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text(
                "[project]\nname='x'\ndependencies = ['requests>=2.0', 'urllib3']\n",
            )
            # Neither requests nor urllib3 are in the semcod tool registry.
            self.assertEqual(scan_missing_tools(project), [])


class TestScanGitignoreDrift(unittest.TestCase):
    def test_no_gitignore_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(scan_gitignore_drift(Path(tmp)), [])

    def test_present_entry_skips_suggestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text(".planfile/.koru/\n")
            self.assertEqual(scan_gitignore_drift(project), [])

    def test_missing_entry_suggests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing relevant\n")
            result = scan_gitignore_drift(project)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].signal, "gitignore_drift")
            self.assertEqual(result[0].priority, "low")
            self.assertEqual(result[0].files, (".gitignore",))


class TestRunScan(unittest.TestCase):
    def test_dry_run_returns_suggestions_no_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")
            (project / "lots.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C, _MARK_D),
            )
            result = run_scan(project, skip_pytest=True, include_semcod_artifacts=False)
            self.assertGreater(len(result.suggestions), 0)
            self.assertEqual(result.applied, [])
            self.assertEqual(result.skipped, [])

    def test_apply_creates_tickets_and_skips_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")

            captured: list[list[str]] = []
            existing_titles = [
                "Gitignore `.planfile/.koru/` runtime directory",  # duplicate
            ]

            def runner(cmd, _proj) -> SimpleNamespace:
                captured.append(list(cmd))
                if cmd[:4] == ["planfile", "ticket", "list", "--source"]:
                    return _ok(json.dumps([{"name": existing_titles[0]}]))
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    return _ok("OK")
                return _ok()

            result = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
                runner=runner,
            )
            # Duplicate is skipped, no create call for it
            self.assertIn(existing_titles[0], result.skipped)
            for cmd in captured:
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    self.assertNotIn(existing_titles[0], cmd)

    def test_code2llm_suggestions_include_artifact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            analysis = project / "project" / "analysis.toon.yaml"
            analysis.parent.mkdir()
            analysis.write_text("HEALTH\n  🔴 DUP   2 classes duplicated\n", encoding="utf-8")

            suggestions = run_scan(
                project,
                skip_pytest=True,
                include_semcod_artifacts=True,
            ).suggestions

            dup = next(item for item in suggestions if item.signal == "code2llm_dup")
            evidence = dup.source_context["evidence"]
            self.assertEqual(evidence["schema"], "koru.ticket_evidence.v1")
            self.assertEqual(evidence["kind"], "code2llm_analysis")
            artifact = evidence["artifact"]
            self.assertEqual(artifact["path"], "project/analysis.toon.yaml")
            self.assertEqual(artifact["size_bytes"], analysis.stat().st_size)
            self.assertEqual(artifact["mtime_ns"], analysis.stat().st_mtime_ns)
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("code2llm", evidence["regenerate_command"])
            self.assertIn("--planfile-apply", evidence["regenerate_command"])

    def test_apply_create_failure_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd[:4] == ["planfile", "ticket", "list", "--source"]:
                    return _ok("[]")
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    return _ok("err", returncode=2, stderr="boom")
                return _ok()

            result = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
                runner=runner,
            )
            # Failed create -> skipped, never applied
            self.assertEqual(result.applied, [])
            self.assertGreater(len(result.skipped), 0)

    def test_apply_logs_all_scan_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            suggestions = [
                Suggestion(
                    signal="dup-title",
                    title="Duplicate by title",
                    description="dup-title desc",
                    priority="normal",
                ),
                Suggestion(
                    signal="dup-signal",
                    title="Duplicate by signal",
                    description="dup-signal desc",
                    priority="high",
                ),
                Suggestion(
                    signal="create-fail",
                    title="Create fails",
                    description="create-fail desc",
                    priority="high",
                ),
                Suggestion(
                    signal="create-ok",
                    title="Create succeeds",
                    description="create-ok desc",
                    priority="normal",
                ),
            ]

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd[:4] == ["planfile", "ticket", "list", "--source"]:
                    return _ok(
                        json.dumps(
                            [
                                {"name": "Duplicate by title"},
                                {
                                    "name": "Something else",
                                    "source": {"context": {"signal": "dup-signal"}},
                                },
                            ],
                        ),
                    )
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    title = cmd[3]
                    if title == "Create fails":
                        return SimpleNamespace(returncode=2, stdout="", stderr="lock busy")
                    return _ok("ok")
                return _ok()

            with mock.patch("koru.scan.collect_suggestions", return_value=suggestions):
                with mock.patch("koru.scan._record_scan_activity") as activity:
                    result = run_scan(
                        project,
                        apply=True,
                        skip_pytest=True,
                        include_semcod_artifacts=False,
                        runner=runner,
                    )

            self.assertEqual(result.applied, ["Create succeeds"])
            self.assertCountEqual(
                result.skipped,
                ["Duplicate by title", "Duplicate by signal", "Create fails"],
            )

            decision_payloads = [
                call.kwargs.get("data", {})
                for call in activity.call_args_list
            ]
            self.assertEqual(len(decision_payloads), 4)
            by_signal = {
                str(payload.get("signal")): payload
                for payload in decision_payloads
            }
            self.assertEqual(by_signal["dup-title"].get("decision"), "skipped")
            self.assertEqual(by_signal["dup-title"].get("reason"), "duplicate_title")
            self.assertEqual(by_signal["dup-signal"].get("decision"), "skipped")
            self.assertEqual(by_signal["dup-signal"].get("reason"), "duplicate_signal")
            self.assertEqual(by_signal["create-fail"].get("decision"), "skipped")
            self.assertEqual(by_signal["create-fail"].get("reason"), "create_failed")
            self.assertEqual(result.skipped_create_failed_details, ["Create fails: lock busy"])
            create_fail_message = next(
                str(call.args[0])
                for call in activity.call_args_list
                if "Create fails" in str(call.args[0])
            )
            self.assertIn("lock busy", create_fail_message)
            self.assertEqual(by_signal["create-ok"].get("decision"), "applied")
            self.assertNotIn("reason", by_signal["create-ok"])

    def test_apply_treats_reused_create_as_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            suggestions = [
                Suggestion(
                    signal="create-reused",
                    title="Create reused",
                    description="desc",
                    priority="normal",
                ),
            ]

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd[:3] == ["planfile", "ticket", "list"]:
                    return _ok("[]")
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    return SimpleNamespace(
                        returncode=1,
                        stdout="",
                        stderr="task already exists (reused)",
                    )
                return _ok()

            with mock.patch("koru.scan.collect_suggestions", return_value=suggestions):
                with mock.patch("koru.scan._record_scan_activity") as activity:
                    result = run_scan(
                        project,
                        apply=True,
                        skip_pytest=True,
                        include_semcod_artifacts=False,
                        runner=runner,
                    )

            self.assertEqual(result.applied, [])
            self.assertEqual(result.skipped, ["Create reused"])
            self.assertEqual(result.skipped_as_duplicate, ["Create reused"])
            self.assertEqual(result.skipped_create_failed, [])
            self.assertEqual(result.skipped_create_failed_details, [])
            payload = activity.call_args.kwargs.get("data", {})
            self.assertEqual(payload.get("decision"), "skipped")
            self.assertEqual(payload.get("reason"), "duplicate_reused")

    def test_apply_creates_human_executor_tickets_without_custom_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")
            (project / ".planfile" / "sprints").mkdir(parents=True)
            (project / ".planfile" / "config.yaml").write_text(
                "prefix: PLF\nnext_id: 1\n",
                encoding="utf-8",
            )
            (project / ".planfile" / "sprints" / "current.yaml").write_text(
                "sprint:\n  name: current\n  tickets: {}\n",
                encoding="utf-8",
            )

            result = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
            )

            self.assertTrue(result.applied)
            raw = (project / ".planfile" / "sprints" / "current.yaml").read_text(
                encoding="utf-8",
            )
            self.assertIn("kind: human", raw)
            self.assertIn("mode: interactive", raw)
            self.assertIn("tool: koru-scan", raw)

    def test_apply_surfaces_runtime_create_failure_detail_without_custom_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            suggestions = [
                Suggestion(
                    signal="create-fail-runtime",
                    title="Create fails at runtime",
                    description="desc",
                    priority="normal",
                ),
            ]

            with mock.patch("koru.scan.collect_suggestions", return_value=suggestions):
                with mock.patch(
                    "koru.scan.create_nl_task",
                    side_effect=RuntimeError("cqrs store lock busy"),
                ):
                    with mock.patch("koru.scan._record_scan_activity") as activity:
                        result = run_scan(
                            project,
                            apply=True,
                            skip_pytest=True,
                            include_semcod_artifacts=False,
                        )

            self.assertEqual(result.applied, [])
            self.assertEqual(result.skipped_create_failed, ["Create fails at runtime"])
            self.assertEqual(
                result.skipped_create_failed_details,
                ["Create fails at runtime: cqrs store lock busy"],
            )
            message = str(activity.call_args.args[0])
            self.assertIn("cqrs store lock busy", message)

    def test_apply_surfaces_runtime_create_failure_class_when_message_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            suggestions = [
                Suggestion(
                    signal="create-fail-empty",
                    title="Create fails silently",
                    description="desc",
                    priority="normal",
                ),
            ]

            with mock.patch("koru.scan.collect_suggestions", return_value=suggestions):
                with mock.patch(
                    "koru.scan.create_nl_task",
                    side_effect=RuntimeError(),
                ):
                    result = run_scan(
                        project,
                        apply=True,
                        skip_pytest=True,
                        include_semcod_artifacts=False,
                    )

            self.assertEqual(
                result.skipped_create_failed_details,
                ["Create fails silently: RuntimeError"],
            )

    def test_apply_uses_stable_title_and_deduplicates_by_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")
            (project / ".planfile" / "sprints").mkdir(parents=True)
            (project / ".planfile" / "config.yaml").write_text(
                "prefix: PLF\nnext_id: 1\n",
                encoding="utf-8",
            )
            (project / ".planfile" / "sprints" / "current.yaml").write_text(
                "sprint:\n  name: current\n  tickets: {}\n",
                encoding="utf-8",
            )

            first = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
            )
            second = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
            )

            self.assertTrue(first.applied)
            self.assertEqual(second.applied, [])
            self.assertGreater(len(second.skipped), 0)
            raw = (project / ".planfile" / "sprints" / "current.yaml").read_text(
                encoding="utf-8",
            )
            self.assertIn("Gitignore `.planfile/.koru/` runtime directory", raw)
            self.assertEqual(raw.count("Gitignore `.planfile/.koru/` runtime directory"), 1)

    def test_apply_deduplicates_planfile_source_tool_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")
            existing = "Gitignore `.planfile/.koru/` runtime directory"
            created: list[list[str]] = []

            def runner(cmd, _proj) -> SimpleNamespace:
                source_list_cmd = [
                    "planfile",
                    "ticket",
                    "list",
                    "--source",
                    "koru-scan",
                    "--format",
                    "json",
                ]
                if cmd == source_list_cmd:
                    return _ok("[]")
                if cmd == ["planfile", "ticket", "list", "--format", "json"]:
                    return _ok(json.dumps([{"name": existing, "source": {"tool": "koru-scan"}}]))
                if cmd[:3] == ["planfile", "ticket", "create"]:
                    created.append(list(cmd))
                    return _ok("OK")
                return _ok()

            result = run_scan(
                project,
                apply=True,
                skip_pytest=True,
                include_semcod_artifacts=False,
                runner=runner,
            )

            self.assertIn(existing, result.skipped)
            for cmd in created:
                self.assertNotIn(existing, cmd)

    def test_existing_scan_titles_ignores_done_tickets(self) -> None:
        from koru.scan import _existing_scan_titles

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            title = "Fix package import path for pytest collection"

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd[:3] == ["planfile", "ticket", "list"]:
                    return _ok(
                        json.dumps(
                            [
                                {
                                    "name": title,
                                    "status": "done",
                                    "source": {"tool": "koru-scan"},
                                },
                                {
                                    "name": "Still open",
                                    "status": "open",
                                    "source": {"tool": "koru-scan"},
                                },
                            ],
                        ),
                    )
                return _ok()

            titles = _existing_scan_titles(project, source="koru-scan", runner=runner)
            self.assertNotIn(title, titles)
            self.assertIn("Still open", titles)

    def test_limit_caps_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for i in range(5):
                (project / f"f{i}.py").write_text(
                    _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
                )
            result = run_scan(project, skip_pytest=True, limit=2, include_semcod_artifacts=False)
            self.assertLessEqual(len(result.suggestions), 2)

    def test_priority_ordering_critical_first(self) -> None:
        # Hand-build a result by calling collect then sorting via run_scan.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")  # low-priority signal
            (project / "many.py").write_text(
                _marker_fixture(_MARK_A, _MARK_B, _MARK_C),
            )
            result = run_scan(project, skip_pytest=True, include_semcod_artifacts=False)
            priorities = [s.priority for s in result.suggestions]
            ranks = {"critical": 0, "high": 1, "normal": 2, "low": 3}
            self.assertEqual(
                priorities,
                sorted(priorities, key=lambda p: ranks.get(p, 99)),
            )


class TestScanSemcodArtifacts(unittest.TestCase):
    def test_jscpd_report_emits_when_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".jscpd").mkdir()
            (project / ".jscpd" / "jscpd-report.json").write_text(
                json.dumps(
                    {
                        "statistics": {
                            "total": {
                                "duplicatedLines": 100,
                                "percentage": 5.0,
                                "clones": 12,
                            },
                        },
                    },
                ),
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "jscpd_report" for s in out))

    def test_code2llm_analysis_emits_when_god_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "HEALTH[1]:\n  🔴 GOD   big.py = 900L, 5 classes, 16m, max CC=11\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "code2llm_god" for s in out))

    def test_code2llm_analysis_emits_dup_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "HEALTH[1]:\n  🔴 DUP   28 classes duplicated\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "code2llm_dup" for s in out))

    def test_code2llm_analysis_emits_cc_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "HEALTH[1]:\n  🟡 CC    my_func CC=18 (limit:15)\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "code2llm_cc" for s in out))

    def test_code2llm_analysis_emits_refactor_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "REFACTOR[2]:\n"
                "  1. rm duplicates  (-28 dup classes)\n"
                "  2. split big.py  (god module)\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            refactor_tickets = [s for s in out if s.signal == "code2llm_refactor"]
            self.assertEqual(len(refactor_tickets), 2)

    def test_code2llm_analysis_emits_layer_hotspots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "HEALTH[0]: ok\n"
                "REFACTOR[0]: none needed\n\n"
                "LAYERS:\n"
                "  src/                            CC̄=4.0    ←in:0  →out:0\n"
                "  │ !! autonomous_cycle          2163L  1C   73m  CC=14     ←0\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            hotspots = [s for s in out if s.signal == "code2llm_layer_hotspot"]
            self.assertEqual(len(hotspots), 1)
            self.assertEqual(hotspots[0].priority, "high")
            self.assertIn("autonomous_cycle", hotspots[0].title)

    def test_path_filter_limits_semcod_artifact_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "project").mkdir()
            (project / "project" / "analysis.toon.yaml").write_text(
                "HEALTH[2]:\n"
                "  🔴 GOD src/foo.py = 900L, 2 classes, 40m\n"
                "  🔴 GOD src/bar.py = 900L, 2 classes, 40m\n",
                encoding="utf-8",
            )
            result = run_scan(
                project,
                skip_pytest=True,
                include_semcod_artifacts=True,
                paths=("src/foo.py",),
            )

            self.assertEqual(len(result.suggestions), 1)
            self.assertIn("src/foo.py", result.suggestions[0].title)

    def test_testql_export_emits_when_many_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            body = "\n".join(
                [f"❌ scenario-{i}.yaml: 0/1 passed, 1 failed" for i in range(5)],
            )
            (project / "testql_api_results.json").write_text(body, encoding="utf-8")
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "testql_export" for s in out))

    def test_redup_filtered_emits_when_many_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".redup").mkdir()
            groups = [{"id": i, "files": [f"m{i}.py"]} for i in range(20)]
            (project / ".redup" / "check.filtered.json").write_text(
                json.dumps(groups),
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "redup_filtered" for s in out))

    def test_redup_changed_emits_when_wup_scan_has_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".redup").mkdir()
            (project / ".redup" / "wup-changed.json").write_text(
                json.dumps({"groups": [{"id": "D1", "files": ["changed.py"]}]}),
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "redup_changed" for s in out))

    def test_vallm_validation_emits_when_errors_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "validation.toon.yaml").write_text(
                "# vallm batch | 12✓ 3⚠ 2✗\n"
                "WARNINGS[3]:\n"
                "ERRORS[2]:\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            ticket = next(s for s in out if s.signal == "vallm_validation")
            self.assertEqual(ticket.priority, "high")

    def test_pyqual_report_emits_when_failed_checks_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".pyqual").mkdir()
            (project / ".pyqual" / "report.yaml").write_text(
                "summary:\n  failed_checks: 2\n  passed: 10\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "pyqual_report" for s in out))

    def test_prefact_report_emits_when_findings_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "prefact-report.json").write_text(
                json.dumps({"findings": [{"id": "P1"}, {"id": "P2"}]}),
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "prefact_report" for s in out))

    def test_regix_report_emits_when_regressions_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "regix-gates.json").write_text(
                json.dumps({"regressions": 1}),
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "regix_report" for s in out))

    def test_redsl_report_emits_when_gate_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "redsl-report.yaml").write_text(
                "gate:\n  status: failed\n",
                encoding="utf-8",
            )
            out = scan_semcod_quality_artifacts(project)
            self.assertTrue(any(s.signal == "redsl_report" for s in out))


if __name__ == "__main__":
    unittest.main()
