from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from koru.cli_goal import goal_main
from koru.goal_workspace import GoalProjectResolutionError, resolve_goal_project


def _git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return path


def test_direct_git_repository_is_selected(tmp_path: Path) -> None:
    repository = _git_repo(tmp_path / "repo")

    assert resolve_goal_project(repository) == repository.resolve()


def test_missing_project_fails_with_resolution_error(tmp_path: Path) -> None:
    with pytest.raises(GoalProjectResolutionError) as caught:
        resolve_goal_project(tmp_path / "missing")

    assert "not a directory" in caught.value.reason


def test_umbrella_selects_its_only_dirty_immediate_repository(tmp_path: Path) -> None:
    clean = _git_repo(tmp_path / "clean")
    dirty = _git_repo(tmp_path / "dirty")
    (dirty / "new.txt").write_text("untracked\n", encoding="utf-8")

    assert resolve_goal_project(tmp_path) == dirty.resolve()
    assert clean.is_dir()


def test_umbrella_with_multiple_dirty_repositories_fails_closed(tmp_path: Path) -> None:
    first = _git_repo(tmp_path / "a")
    second = _git_repo(tmp_path / "b")
    (first / "one.txt").write_text("one\n", encoding="utf-8")
    (second / "two.txt").write_text("two\n", encoding="utf-8")

    with pytest.raises(GoalProjectResolutionError) as caught:
        resolve_goal_project(tmp_path)

    assert caught.value.candidates == ("a", "b")
    assert "multiple dirty" in caught.value.reason


def test_umbrella_with_no_dirty_repository_requires_explicit_repo(tmp_path: Path) -> None:
    _git_repo(tmp_path / "a")

    with pytest.raises(GoalProjectResolutionError) as caught:
        resolve_goal_project(tmp_path)

    assert caught.value.candidates == ("a",)
    assert "no dirty" in caught.value.reason


def test_explicit_repo_selects_a_contained_clean_repository(tmp_path: Path) -> None:
    repository = _git_repo(tmp_path / "selected")

    assert resolve_goal_project(tmp_path, "selected") == repository.resolve()


def test_automatic_selection_ignores_symlinked_external_repository(
    tmp_path: Path,
) -> None:
    outside = _git_repo(tmp_path.parent / f"{tmp_path.name}-outside")
    (outside / "new.txt").write_text("outside\n", encoding="utf-8")
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(GoalProjectResolutionError) as caught:
        resolve_goal_project(tmp_path)

    assert "neither a Git repository" in caught.value.reason


@pytest.mark.parametrize("repo", ["../outside", "/tmp/outside"])
def test_explicit_repo_rejects_paths_outside_workspace(tmp_path: Path, repo: str) -> None:
    with pytest.raises(GoalProjectResolutionError):
        resolve_goal_project(tmp_path, repo)


def test_ambiguous_cli_starts_neither_goal_nor_agent(tmp_path: Path) -> None:
    first = _git_repo(tmp_path / "a")
    second = _git_repo(tmp_path / "b")
    (first / "one.txt").write_text("one\n", encoding="utf-8")
    (second / "two.txt").write_text("two\n", encoding="utf-8")

    with mock.patch("koru.cli_goal.supervise_goal") as supervise:
        with mock.patch("koru.cli_goal._agent_remediator") as remediator:
            result = goal_main(["--project", str(tmp_path), "--format", "json"])

    assert result == 2
    supervise.assert_not_called()
    remediator.assert_not_called()
