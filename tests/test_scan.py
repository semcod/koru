from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.scan import (
    Suggestion,
    collect_suggestions,
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


class TestScanPytestCollect(unittest.TestCase):
    def test_returns_empty_when_no_tests_and_no_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(scan_pytest_collect(Path(tmp)), [])

    def test_empty_on_clean_collect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text("[project]\nname='x'\n")
            result = scan_pytest_collect(
                project, runner=lambda _c, _p: _ok("4 tests collected")
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
                project, runner=lambda _c, _p: _ok(output, returncode=2),
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
            output = (
                "E   ModuleNotFoundError: No module named 'goal'\n"
                "--- collection errors ---\n"
            )
            result = scan_pytest_collect(
                project, runner=lambda _c, _p: _ok(output, returncode=2),
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
                project, runner=boom, timeout_seconds=30.0,
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
                project, runner=boom, timeout_seconds=5.0,
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
            (project / "low.py").write_text("# TODO: just one\n")
            self.assertEqual(scan_todo_markers(project, min_per_file=3), [])

    def test_groups_markers_per_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "hot.py").write_text(
                "# TODO: a\n# FIXME: b\n# XXX: c\n# HACK: d\n"
            )
            (project / "warm.py").write_text("# TODO: x\n# FIXME: y\n# XXX: z\n")
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
                "# TODO: a\n# FIXME: b\n# XXX: c\n"
            )
            (project / "normal.py").write_text(
                "# TODO: a\n# FIXME: b\n# XXX: c\n"
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
                "# TODO: a\n# FIXME: b\n# XXX: c\n"
            )
            (project / "src.py").write_text(
                "# TODO: a\n# FIXME: b\n# XXX: c\n"
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
                "[project]\nname='x'\n"
                "dependencies = ['requests>=2.0', 'urllib3']\n"
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
                "# TODO 1\n# FIXME 2\n# XXX 3\n# HACK 4\n"
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

    def test_apply_deduplicates_planfile_source_tool_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")
            existing = "Gitignore `.planfile/.koru/` runtime directory"
            created: list[list[str]] = []

            def runner(cmd, _proj) -> SimpleNamespace:
                if cmd == ["planfile", "ticket", "list", "--source", "koru-scan", "--format", "json"]:
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

    def test_limit_caps_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for i in range(5):
                (project / f"f{i}.py").write_text(
                    "# TODO a\n# FIXME b\n# XXX c\n"
                )
            result = run_scan(project, skip_pytest=True, limit=2, include_semcod_artifacts=False)
            self.assertLessEqual(len(result.suggestions), 2)

    def test_priority_ordering_critical_first(self) -> None:
        # Hand-build a result by calling collect then sorting via run_scan.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("# nothing\n")  # low-priority signal
            (project / "many.py").write_text(
                "# TODO 1\n# FIXME 2\n# XXX 3\n"  # also low
            )
            result = run_scan(project, skip_pytest=True, include_semcod_artifacts=False)
            priorities = [s.priority for s in result.suggestions]
            ranks = {"critical": 0, "high": 1, "normal": 2, "low": 3}
            self.assertEqual(
                priorities, sorted(priorities, key=lambda p: ranks.get(p, 99))
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
                            }
                        }
                    }
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

    def test_testql_export_emits_when_many_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            body = "\n".join(
                [f"❌ scenario-{i}.yaml: 0/1 passed, 1 failed" for i in range(5)]
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


if __name__ == "__main__":
    unittest.main()
