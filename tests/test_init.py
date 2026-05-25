"""Tests for ``koru --init`` (one-command project bootstrap).

Contract:
- A fresh directory becomes a working koru project after one call.
- The starter scaffold imports cleanly and yields ≥1 runnable ticket.
- The policy stub is valid YAML and parses to safe defaults.
- ``.gitignore`` gets an entry for ``.planfile/.koru/`` exactly once.
- Re-running on an initialised project errors unless ``force=True``.
- ``--from <yaml>`` honours an externally-provided pipeline.
"""

from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

from koru.init import (
    GITIGNORE_LINE,
    POLICY_STUB,
    init_project,
    refresh_init_agent_lane,
    resolve_project_agent_lane,
)
from koru.policy import load_policy
from koru.runtime import planfile_dir, runtime_dir


def _detach_ci_env() -> dict[str, str]:
    """Remove CI markers so IDE folder detection is deterministic in tests."""
    backup: dict[str, str] = {}
    for key in ("CI", "GITHUB_ACTIONS"):
        if key in os.environ:
            backup[key] = os.environ[key]
            del os.environ[key]
    return backup


def _reattach_ci_env(backup: dict[str, str]) -> None:
    os.environ.update(backup)


class TestStarterInit(unittest.TestCase):
    def test_creates_planfile_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project)
            self.assertTrue((planfile_dir(project) / "config.yaml").exists())
            self.assertTrue(
                (planfile_dir(project) / "sprints" / "current.yaml").exists(),
            )
            self.assertGreaterEqual(report.sprint_imported, 2)
            self.assertTrue(report.used_starter_pipeline)

    def test_writes_policy_stub_and_loads_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            policy_file = runtime_dir(project) / "policy.yaml"
            self.assertTrue(policy_file.is_file())
            # The stub is valid YAML.
            data = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
            self.assertIsInstance(data, dict)
            # And load_policy resolves to safe defaults (no gates flipped).
            policy = load_policy(project)
            self.assertFalse(policy.allow_commit)
            self.assertFalse(policy.allow_push)
            self.assertFalse(policy.allow_branch_create)
            self.assertTrue(policy.require_planfile_lifecycle)

    def test_policy_stub_constant_is_valid_yaml(self) -> None:
        """The shipped POLICY_STUB string must always parse."""
        data = yaml.safe_load(POLICY_STUB)
        self.assertIsInstance(data, dict)
        self.assertIn("llm", data)

    def test_appends_gitignore_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            gi = (project / ".gitignore").read_text(encoding="utf-8")
            self.assertIn(GITIGNORE_LINE, gi)

    def test_gitignore_idempotent(self) -> None:
        """Re-running --init must not duplicate the gitignore line."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            init_project(project, force=True)
            gi = (project / ".gitignore").read_text(encoding="utf-8")
            self.assertEqual(gi.count(GITIGNORE_LINE), 1)

    def test_preserves_existing_gitignore_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
            init_project(project)
            gi = (project / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("__pycache__/", gi)
            self.assertIn(GITIGNORE_LINE, gi)

    def test_policy_stub_not_overwritten_on_force(self) -> None:
        """User edits to policy.yaml survive a re-init."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            policy_file = runtime_dir(project) / "policy.yaml"
            policy_file.write_text("USER EDIT — keep me", encoding="utf-8")
            init_project(project, force=True)
            self.assertEqual(
                policy_file.read_text(encoding="utf-8"),
                "USER EDIT — keep me",
            )

    def test_no_starter_yaml_left_behind(self) -> None:
        """The internal _starter.planfile.yaml is cleaned up after import."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            self.assertFalse(
                (planfile_dir(project) / "_starter.planfile.yaml").exists(),
            )

    def test_writes_koru_yaml_on_first_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project)
            kf = project / "koru.yaml"
            self.assertTrue(kf.is_file())
            self.assertTrue(report.koru_project_pipeline_yaml_written)
            data = yaml.safe_load(kf.read_text(encoding="utf-8"))
            self.assertEqual(data.get("schema"), "1.0")
            self.assertIn("when", data)
            self.assertEqual(
                data["autonomy"]["strategy"]["id"],
                "accordion_detail_to_general",
            )

    def test_host_environment_bundle_written_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project)
            self.assertTrue(report.host_environment_written)
            rt = runtime_dir(project)
            self.assertTrue((rt / "host-environment.json").is_file())
            self.assertTrue((rt / "host-environment.md").is_file())

    def test_host_environment_skipped_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project, prepare_host_environment=False)
            self.assertFalse(report.host_environment_written)
            self.assertFalse(
                (runtime_dir(project) / "host-environment.json").exists(),
            )

    def test_force_init_preserves_existing_koru_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            kf = project / "koru.yaml"
            kf.write_text("schema: '1.0'\nproject: kept\nwhen: {}\n", encoding="utf-8")
            report = init_project(project, force=True)
            self.assertFalse(report.koru_project_pipeline_yaml_written)
            self.assertEqual(yaml.safe_load(kf.read_text())["project"], "kept")


class TestForceAndConflicts(unittest.TestCase):
    def test_re_init_without_force_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            with self.assertRaises(FileExistsError):
                init_project(project)

    def test_re_init_with_force_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            report = init_project(project, force=True)
            self.assertGreaterEqual(report.sprint_imported, 2)


class TestFromExternalPipeline(unittest.TestCase):
    def test_imports_user_supplied_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            pipeline = project.parent / "pipeline.yaml"
            pipeline.write_text(
                textwrap.dedent("""\
                schema: '1.1'
                project: ext
                tasks:
                  - id: EXT-001
                    name: External task
                    executor:
                      kind: shell
                      handler: 'true'
                    execution:
                      queue: default
                      state: ready
                    priority: high
            """),
                encoding="utf-8",
            )
            report = init_project(project, from_file=pipeline)
            self.assertFalse(report.used_starter_pipeline)
            self.assertEqual(report.sprint_imported, 1)
            self.assertTrue((project / "koru.yaml").is_file())


class TestRuntimeContract(unittest.TestCase):
    def test_init_does_not_leave_files_outside_planfile(self) -> None:
        """Koru-owned state lives under .planfile/; root may have .gitignore + koru.yaml."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            entries = sorted(p.name for p in project.iterdir())
            # Allowed at project root: .planfile/, .gitignore, koru.yaml.
            self.assertEqual(entries, [".gitignore", ".planfile", "koru.yaml"])


class TestAgentLaneArtifacts(unittest.TestCase):
    def test_auto_local_writes_shell_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project)
            self.assertEqual(report.agent_lane, "local")
            self.assertTrue(report.agent_lane_files_written)
            self.assertTrue(report.autopilot_host_setup_written)
            rt = runtime_dir(project)
            self.assertTrue((rt / "shell-env.sh").is_file())
            self.assertTrue((rt / "run-autonomous.sh").is_file())
            self.assertTrue((rt / "setup-autopilot-host.sh").is_file())
            self.assertTrue(os.access(rt / "run-autonomous.sh", os.X_OK))
            self.assertTrue(os.access(rt / "setup-autopilot-host.sh", os.X_OK))

    def test_auto_cursor_when_dot_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".cursor").mkdir()
            ci_backup = _detach_ci_env()
            try:
                report = init_project(project)
            finally:
                _reattach_ci_env(ci_backup)
            self.assertEqual(report.agent_lane, "cursor")
            shell = (runtime_dir(project) / "shell-env.sh").read_text(
                encoding="utf-8",
            )
            self.assertIn("KORU_AUTOPILOT_INSTANCE='cursor'", shell)

    def test_auto_vscode_when_dot_vscode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".vscode").mkdir()
            ci_backup = _detach_ci_env()
            try:
                report = init_project(project)
            finally:
                _reattach_ci_env(ci_backup)
            self.assertEqual(report.agent_lane, "vscode")

    def test_auto_cursor_beats_vscode_when_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".cursor").mkdir()
            (project / ".vscode").mkdir()
            ci_backup = _detach_ci_env()
            try:
                report = init_project(project)
            finally:
                _reattach_ci_env(ci_backup)
            self.assertEqual(report.agent_lane, "cursor")

    def test_auto_prefers_persisted_shell_env_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".cursor").mkdir()
            (project / ".windsurf").mkdir()
            ci_backup = _detach_ci_env()
            try:
                init_project(project, agent_lane="windsurf")
                lane = resolve_project_agent_lane(project, "auto")
            finally:
                _reattach_ci_env(ci_backup)
            self.assertEqual(lane, "windsurf")

    def test_auto_ci_forces_local_even_with_dot_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".cursor").mkdir()
            old_ci = os.environ.get("CI")
            os.environ["CI"] = "true"
            try:
                report = init_project(project)
            finally:
                if old_ci is None:
                    os.environ.pop("CI", None)
                else:
                    os.environ["CI"] = old_ci
            self.assertEqual(report.agent_lane, "local")

    def test_none_skips_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = init_project(project, agent_lane="none")
            self.assertIsNone(report.agent_lane)
            self.assertFalse(report.agent_lane_files_written)
            rt = runtime_dir(project)
            self.assertFalse((rt / "shell-env.sh").exists())
            self.assertFalse((rt / "run-autonomous.sh").exists())


class TestRefreshInitAgentLane(unittest.TestCase):
    def test_requires_planfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            with self.assertRaises(FileNotFoundError) as ctx:
                refresh_init_agent_lane(project)
            self.assertIn("koru --init", str(ctx.exception))

    def test_writes_after_init_with_agent_lane_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project, agent_lane="none")
            rt = runtime_dir(project)
            self.assertFalse((rt / "shell-env.sh").exists())
            report = refresh_init_agent_lane(project)
            self.assertTrue(report.agent_lane_files_written)
            self.assertEqual(report.agent_lane, "local")
            self.assertTrue((rt / "shell-env.sh").is_file())


if __name__ == "__main__":
    unittest.main()
