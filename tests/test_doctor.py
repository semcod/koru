"""Tests for ``koru --doctor`` (project diagnostics).

Each probe is exercised in at least one pass and one non-pass state.
The renderer and the JSON shape are also verified — the LLM consumer
relies on stable keys and order.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.doctor import (
    FAIL,
    PASS,
    WARN,
    Check,
    DoctorReport,
    render_text,
    run_diagnostics,
)


def _scaffold(project: Path) -> None:
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
            with patch("shutil.which", side_effect=lambda x: f"/usr/bin/{x}"):
                report = _run(project)
            # No failures on a properly-set-up project.
            self.assertFalse(report.has_failures, msg=str(report.to_dict()))
            self.assertEqual(_named(report, "git_repo").status, PASS)
            self.assertEqual(_named(report, "planfile_config").status, PASS)
            self.assertEqual(_named(report, "planfile_sprints").status, PASS)
            self.assertEqual(_named(report, "runtime_dir").status, PASS)
            self.assertEqual(_named(report, "policy_yaml").status, PASS)
            self.assertEqual(_named(report, "gitignore").status, PASS)


class TestGitRepoCheck(unittest.TestCase):
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
            with patch.dict(os.environ, env, clear=True), \
                 patch("shutil.which", return_value=None):
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
                "this: is: not: valid", encoding="utf-8"
            )
            report = _run(project)
            self.assertEqual(_named(report, "planfile_config").status, FAIL)


class TestSprintsCheck(unittest.TestCase):
    def test_empty_sprint_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / "sprints" / "current.yaml").write_text(
                "sprint:\n  id: current\n  tickets: {}\n", encoding="utf-8"
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
                "this: is: not: valid", encoding="utf-8"
            )
            report = _run(project)
            self.assertEqual(_named(report, "policy_yaml").status, FAIL)

    def test_string_truthy_value_warns(self) -> None:
        """`allow_commit: "true"` is rejected by load_policy — doctor surfaces it."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            (project / ".planfile" / ".koru" / "policy.yaml").write_text(
                'llm:\n  allow_commit: "true"\n', encoding="utf-8"
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
                'ci:\n  command: "echo hi"\n', encoding="utf-8"
            )
            report = _run(project)
            self.assertEqual(_named(report, "ci_command").status, PASS)


class TestReportShape(unittest.TestCase):
    def test_to_dict_keys_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _scaffold(project)
            d = _run(project).to_dict()
            self.assertEqual(set(d), {
                "schema_version", "project", "summary",
                "has_failures", "checks",
            })
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
                sum(counts.values()), len(report.checks)
            )


if __name__ == "__main__":
    unittest.main()
