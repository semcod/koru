"""Tests for koru.cli_fleet — multi-project autonomous-loop supervisor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru.cli_fleet import (
    _ManagedProject,
    _run_fleet_ls,
    discover_projects,
    fleet_main,
)


def _make_policy_project(root: Path, *parts: str) -> Path:
    project = root.joinpath(*parts) if parts else root
    policy_dir = project / ".planfile" / ".koru"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.yaml").write_text("llm:\n  allow_commit: false\n")
    return project


class TestDiscoverProjects:
    def test_finds_project_with_policy_marker(self, tmp_path: Path) -> None:
        project = _make_policy_project(tmp_path, "myproj")
        found = discover_projects(tmp_path)
        assert found == [project]

    def test_finds_multiple_projects_sorted(self, tmp_path: Path) -> None:
        b = _make_policy_project(tmp_path, "b-project")
        a = _make_policy_project(tmp_path, "a-project")
        found = discover_projects(tmp_path)
        assert found == sorted([a, b])

    def test_ignores_project_without_policy_marker(self, tmp_path: Path) -> None:
        (tmp_path / "unmanaged").mkdir()
        (tmp_path / "unmanaged" / ".planfile").mkdir()
        assert discover_projects(tmp_path) == []

    def test_excludes_test_data_and_plugin_noise(self, tmp_path: Path) -> None:
        real = _make_policy_project(tmp_path, "real-project")
        _make_policy_project(tmp_path, "real-project", "test-data")
        _make_policy_project(tmp_path, "real-project", "plugins", "some-plugin")
        found = discover_projects(tmp_path)
        assert found == [real]

    def test_nested_distinct_projects_both_found(self, tmp_path: Path) -> None:
        """A project nested inside another (e.g. semcod/koru inside semcod)
        is legitimate and should get its own loop -- only known junk
        directory *names* are excluded, not nesting itself."""
        outer = _make_policy_project(tmp_path, "workspace-root")
        inner = _make_policy_project(tmp_path, "workspace-root", "sub-project")
        found = discover_projects(tmp_path)
        assert found == sorted([outer, inner])


class TestManagedProject:
    def test_command_includes_project_and_replace_existing(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=["--ide", "claude"])
        cmd = mp.command()
        assert "--project" in cmd
        assert str(tmp_path) in cmd
        assert "--replace-existing" in cmd
        assert "--ide" in cmd and "claude" in cmd

    def test_is_running_false_before_start(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        assert mp.is_running() is False

    def test_poll_and_maybe_restart_starts_when_not_running_and_due(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        mp.start = MagicMock()
        mp.next_restart_at = 0.0
        mp.poll_and_maybe_restart(now=10.0, backoff_seconds=30.0, log=lambda *_: None)
        mp.start.assert_called_once()

    def test_poll_and_maybe_restart_waits_for_backoff(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        mp.start = MagicMock()
        mp.next_restart_at = 100.0
        mp.poll_and_maybe_restart(now=10.0, backoff_seconds=30.0, log=lambda *_: None)
        mp.start.assert_not_called()

    def test_poll_and_maybe_restart_schedules_restart_after_exit(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        fake_process = MagicMock()
        fake_process.poll.return_value = 1  # exited
        mp.process = fake_process
        logs: list[str] = []
        mp.poll_and_maybe_restart(now=100.0, backoff_seconds=30.0, log=logs.append)
        assert mp.process is None
        assert mp.next_restart_at == 130.0
        assert mp.restart_count == 1
        assert any("exited" in line for line in logs)

    def test_poll_and_maybe_restart_noop_while_running(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        fake_process = MagicMock()
        fake_process.poll.return_value = None  # still running
        mp.process = fake_process
        mp.poll_and_maybe_restart(now=100.0, backoff_seconds=30.0, log=lambda *_: None)
        assert mp.process is fake_process
        assert mp.restart_count == 0

    def test_terminate_noop_when_not_running(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        mp.terminate(log=lambda *_: None)  # must not raise

    def test_terminate_calls_process_terminate(self, tmp_path: Path) -> None:
        mp = _ManagedProject(tmp_path, extra_args=[])
        fake_process = MagicMock()
        fake_process.poll.return_value = None
        fake_process.pid = 1234
        mp.process = fake_process
        mp.terminate(log=lambda *_: None)
        fake_process.terminate.assert_called_once()


class TestFleetLs:
    def test_reports_no_projects(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        import argparse

        args = argparse.Namespace(workspace=tmp_path)
        rc = _run_fleet_ls(args)
        assert rc == 1
        assert "No koru-managed projects" in capsys.readouterr().out

    def test_lists_discovered_projects(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        import argparse

        project = _make_policy_project(tmp_path, "proj-a")
        args = argparse.Namespace(workspace=tmp_path)
        rc = _run_fleet_ls(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert str(project) in out


class TestFleetMain:
    def test_ls_dispatches_correctly(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _make_policy_project(tmp_path, "proj-a")
        rc = fleet_main(["ls", "--workspace", str(tmp_path)])
        assert rc == 0

    def test_missing_subcommand_errors(self) -> None:
        with pytest.raises(SystemExit):
            fleet_main([])
