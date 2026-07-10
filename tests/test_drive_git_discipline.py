"""Tests for git discipline in drive prompts and the absorbed-changes guard."""

from __future__ import annotations

import subprocess
from pathlib import Path

from koru.autonomy.planfile_handoff import (
    git_discipline_lines,
    planfile_status_handoff_text,
)
from koru.autonomy.verification_engine import (
    Snapshot,
    absorbed_foreign_paths,
    take_snapshot,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(repo),
        },
    )


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "base.txt").write_text("base\n")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


# ---------------------------------------------------------------------------
# Prompt contract
# ---------------------------------------------------------------------------

def test_git_discipline_forbids_sweeping_commits():
    text = "\n".join(git_discipline_lines())
    assert "git add -A" in text
    assert "git commit -a" in text
    assert "uncommitted file" in text


def test_handoff_text_includes_git_discipline_with_and_without_ticket():
    for ticket in ("PLF-123", ""):
        text = planfile_status_handoff_text(ticket)
        assert "Planfile status handoff:" in text
        assert "Git discipline:" in text


# ---------------------------------------------------------------------------
# Snapshot + absorbed-changes detection
# ---------------------------------------------------------------------------

def test_snapshot_records_dirty_paths(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "base.txt").write_text("operator edit\n")
    (repo / "wip.txt").write_text("untracked wip\n")

    snap = take_snapshot(repo)
    assert set(snap.git_dirty_paths) == {"base.txt", "wip.txt"}
    assert snap.git_dirty_count == 2
    # Round-trips through the state dict (AutoloopState persistence).
    as_dict = snap.to_dict()
    assert isinstance(as_dict["git_dirty_paths"], list)
    restored = Snapshot(**{**as_dict, "git_dirty_paths": tuple(as_dict["git_dirty_paths"])})
    assert restored.git_dirty_paths == snap.git_dirty_paths


def test_absorbed_foreign_paths_detects_swept_operator_work(tmp_path):
    repo = _make_repo(tmp_path)
    # Operator has WIP before the drive.
    (repo / "base.txt").write_text("operator edit\n")
    before = take_snapshot(repo)

    # Agent does a sweeping `git commit -a`-style commit including the WIP
    # plus its own new file.
    (repo / "agent.txt").write_text("agent work\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "refactoring")

    absorbed = absorbed_foreign_paths(repo, before)
    assert absorbed == ["base.txt"]


def test_absorbed_foreign_paths_clean_when_agent_commits_only_its_files(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "base.txt").write_text("operator edit\n")
    before = take_snapshot(repo)

    (repo / "agent.txt").write_text("agent work\n")
    _git(repo, "add", "agent.txt")
    _git(repo, "commit", "-q", "-m", "feat: agent work only")

    assert absorbed_foreign_paths(repo, before) == []
    # Operator WIP is still in the working tree, untouched.
    assert (repo / "base.txt").read_text() == "operator edit\n"


def test_absorbed_foreign_paths_noop_without_new_commits(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "base.txt").write_text("operator edit\n")
    before = take_snapshot(repo)
    assert absorbed_foreign_paths(repo, before) == []
    assert absorbed_foreign_paths(repo, None) == []


def test_warn_absorbed_foreign_changes_emits_event(tmp_path):
    from koru.autonomy.cycle.cycle_post_drive import _warn_absorbed_foreign_changes
    from koru.autonomy.state import AutoloopState

    repo = _make_repo(tmp_path)
    (repo / "base.txt").write_text("operator edit\n")

    state = AutoloopState()
    state.last_drive_snapshot = take_snapshot(repo).to_dict()

    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "refactoring")

    printed: list[str] = []
    events: list[tuple[str, dict]] = []
    _warn_absorbed_foreign_changes(
        repo, state, cycle=7, ticket_id="PLF-1",
        hp=printed.append, emit=lambda name, payload: events.append((name, payload)),
    )
    assert printed and "absorbed pre-existing local changes" in printed[0]
    assert events and events[0][0] == "DriveCommitAbsorbedForeignChanges"
    assert events[0][1]["absorbed_paths"] == ["base.txt"]

    # No warning when nothing was absorbed.
    printed.clear()
    events.clear()
    state.last_drive_snapshot = take_snapshot(repo).to_dict()
    _warn_absorbed_foreign_changes(
        repo, state, cycle=8, ticket_id="PLF-1",
        hp=printed.append, emit=lambda name, payload: events.append((name, payload)),
    )
    assert not printed and not events
