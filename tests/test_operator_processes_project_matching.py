"""Tests for koru.autonomy.operator.operator_processes's project-matching.

Covers the bug reproduced live 2026-07-05: `_command_project` resolved a
relative `--project .` argument against the *checking* process's own cwd
(`Path(".").resolve()`) instead of the *target* process's cwd. Two
completely unrelated koru-autonomous processes, each started with a
relative `--project .` from a different directory, could be treated as
"the same project" whenever the checking process's cwd happened to equal
the other process's original cwd -- causing `--replace-existing` to kill
an unrelated project's long-running autonomous loop.
"""

from __future__ import annotations

from pathlib import Path

from koru.autonomy.operator.operator_processes import (
    _autonomous_process_matches_project,
    _command_project,
    _PsRow,
)


class TestCommandProject:
    def test_absolute_project_arg_parsed_directly(self, tmp_path: Path) -> None:
        cmd = f"koru autonomous up --project {tmp_path} --replace-existing"
        assert _command_project(cmd) == tmp_path.resolve()

    def test_absolute_project_eq_form(self, tmp_path: Path) -> None:
        cmd = f"koru autonomous up --project={tmp_path} --replace-existing"
        assert _command_project(cmd) == tmp_path.resolve()

    def test_no_project_flag_returns_none(self) -> None:
        assert _command_project("koru autonomous up --replace-existing") is None

    def test_relative_project_resolves_against_relative_to_not_cwd(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The core regression: a relative `--project .` must resolve
        against the target process's own directory, not whatever directory
        happens to be the *checking* process's current working directory.
        """
        project_a = tmp_path / "project-a"
        project_a.mkdir()
        checker_cwd = tmp_path / "unrelated-checker-cwd"
        checker_cwd.mkdir()
        monkeypatch.chdir(checker_cwd)

        cmd = "koru autonomous up --project . --replace-existing"

        # Correct: resolves relative to the target process's own cwd.
        assert _command_project(cmd, relative_to=project_a) == project_a.resolve()
        # And it must NOT silently resolve to the checker's own cwd.
        assert _command_project(cmd, relative_to=project_a) != checker_cwd.resolve()

    def test_relative_project_falls_back_to_process_cwd_when_no_relative_to_given(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        cmd = "koru autonomous up --project . --replace-existing"
        assert _command_project(cmd) == tmp_path.resolve()


class TestAutonomousProcessMatchesProject:
    def test_two_different_relative_dot_projects_do_not_match(self, tmp_path: Path, monkeypatch) -> None:
        """Direct reproduction of the live incident: project A's checker
        must not identify project B's relative `--project .` process as
        belonging to project A, even though both used the literal string
        ``--project .`` on their command lines.

        ``_process_cwd`` can't be faked for a real PID here, so this drives
        the regression through ``_command_project`` directly with an
        explicit ``relative_to`` standing in for "process B's own cwd" --
        the exact value ``_autonomous_process_matches_project`` would have
        passed through from ``_process_cwd(row.pid)``.
        """
        project_a = tmp_path / "project-a"
        project_a.mkdir()
        project_b = tmp_path / "project-b"
        project_b.mkdir()
        monkeypatch.chdir(project_a)  # the *checker* happens to be running from project A

        # Process B was started with a relative "." from its own directory (project_b).
        cmd = "koru autonomous up --project . --replace-existing"
        resolved = _command_project(cmd, relative_to=project_b)

        assert resolved == project_b.resolve()
        assert resolved != project_a.resolve()

    def test_absolute_project_match_succeeds(self, tmp_path: Path) -> None:
        row = _PsRow(
            pid=99999,
            ppid=1,
            command=f"koru autonomous up --project {tmp_path} --replace-existing",
        )
        match = _autonomous_process_matches_project(
            row,
            tmp_path,
            any_project=False,
            excluded=set(),
        )
        assert match is not None
        assert match.pid == 99999

    def test_absolute_project_mismatch_excluded(self, tmp_path: Path) -> None:
        other = tmp_path / "other"
        other.mkdir()
        row = _PsRow(
            pid=99999,
            ppid=1,
            command=f"koru autonomous up --project {other} --replace-existing",
        )
        match = _autonomous_process_matches_project(
            row,
            tmp_path,
            any_project=False,
            excluded=set(),
        )
        assert match is None

    def test_excluded_pid_never_matches(self, tmp_path: Path) -> None:
        row = _PsRow(
            pid=42,
            ppid=1,
            command=f"koru autonomous up --project {tmp_path} --replace-existing",
        )
        match = _autonomous_process_matches_project(
            row,
            tmp_path,
            any_project=False,
            excluded={42},
        )
        assert match is None

    def test_any_project_matches_regardless_of_path(self, tmp_path: Path) -> None:
        other = tmp_path / "other"
        other.mkdir()
        row = _PsRow(
            pid=99999,
            ppid=1,
            command=f"koru autonomous up --project {other} --replace-existing",
        )
        match = _autonomous_process_matches_project(
            row,
            tmp_path,
            any_project=True,
            excluded=set(),
        )
        assert match is not None

    def test_non_autonomous_command_never_matches(self, tmp_path: Path) -> None:
        row = _PsRow(pid=99999, ppid=1, command="vim some_file.py")
        match = _autonomous_process_matches_project(
            row,
            tmp_path,
            any_project=True,
            excluded=set(),
        )
        assert match is None
