"""Real-Git checks for evidence retention and governed staging refusal."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from koru.queue import workspace
from koru.queue.patch_mode import PROMOTION_FAILED
from koru.queue.transaction import build_patch_plan
from koru.queue.transaction.staging import stage_patch
from koru.queue.workspace import StagingAdmissionRequired, prune_stale_worktrees, staging_worktree
from tests import _repolab


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _repolab.git_repo(root)
    _repolab.commit_file(root, "a.txt", "old\n")
    return root


@pytest.mark.parametrize("content", ["tracked", "untracked", "commit", "branch"])
def test_changed_staging_survives_next_run(repo: Path, content: str) -> None:
    with staging_worktree(repo, ("a.txt",)) as staged:
        assert staged is not None
        if content == "tracked":
            (staged / "a.txt").write_text("repair\n")
        elif content == "untracked":
            (staged / "evidence.txt").write_text("verification output")
        elif content == "commit":
            _repolab.commit_file(staged, "a.txt", "committed repair\n")
        else:
            git(staged, "switch", "-qc", "repair-pending-review")
        head = git(staged, "rev-parse", "HEAD")
        status = git(staged, "status", "--porcelain=v1", "--ignored", "--untracked-files=all")
    assert staged.is_dir()
    prune_stale_worktrees(repo)
    with staging_worktree(repo, ()) as fresh:
        assert fresh is not None and fresh != staged
    assert staged.is_dir()
    assert git(staged, "rev-parse", "HEAD") == head
    assert git(staged, "status", "--porcelain=v1", "--ignored", "--untracked-files=all") == status
    assert (repo / "a.txt").read_text() == "old\n"


def test_ignored_output_alone_survives(repo: Path) -> None:
    _repolab.commit_file(repo, ".gitignore", "*.log\n")
    with staging_worktree(repo, ()) as staged:
        assert staged is not None
        (staged / "verify.log").write_bytes(b"retain\x00raw output")
        assert not git(staged, "status", "--porcelain")
    assert (staged / "verify.log").read_bytes() == b"retain\x00raw output"


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_interrupted_dirty_staging_is_not_removed(repo: Path, failure: type[BaseException]) -> None:
    with pytest.raises(failure):
        with staging_worktree(repo, ()) as staged:
            assert staged is not None
            (staged / "a.txt").write_text("unfinished repair\n")
            raise failure()
    assert (staged / "a.txt").read_text() == "unfinished repair\n"
    assert str(staged) in git(repo, "worktree", "list", "--porcelain")


def test_pruning_has_no_git_or_filesystem_effects(repo: Path) -> None:
    orphan = repo.parent / ".koru-run-orphan"
    orphan.mkdir()
    (orphan / "unique.txt").write_text("only copy")
    nested = repo / ".koru/worktrees/run-orphan"
    nested.mkdir(parents=True)
    (nested / "unique.txt").write_text("another only copy")
    with patch("koru.queue.workspace._git", side_effect=AssertionError("no pruning")):
        prune_stale_worktrees(repo)
    assert (orphan / "unique.txt").read_text() == "only copy"
    assert (nested / "unique.txt").read_text() == "another only copy"


def test_clean_staging_can_be_removed_normally(repo: Path) -> None:
    with staging_worktree(repo, ()) as staged:
        assert staged is not None
    assert not staged.exists()
    assert str(staged) not in git(repo, "worktree", "list", "--porcelain")


def test_locked_staging_is_not_force_removed(repo: Path) -> None:
    with staging_worktree(repo, ()) as staged:
        assert staged is not None
        git(repo, "worktree", "lock", "--reason", "owner reconciliation", str(staged))
    assert staged.is_dir()
    assert "locked owner reconciliation" in git(repo, "worktree", "list", "--porcelain")


def test_already_removed_staging_does_not_mask_result(repo: Path) -> None:
    with staging_worktree(repo, ()) as staged:
        assert staged is not None
        git(repo, "worktree", "remove", str(staged))
    assert not staged.exists()


def test_removal_during_cleanup_observation_does_not_mask_result(repo: Path) -> None:
    original_git = workspace._git
    paths: dict[str, Path] = {}

    def concurrent_removal(project: Path, *args: str, **kwargs):
        if project == paths.get("staged") and args == ("rev-parse", "--absolute-git-dir"):
            git(repo, "worktree", "remove", str(project))
        return original_git(project, *args, **kwargs)

    with patch("koru.queue.workspace._git", side_effect=concurrent_removal):
        with staging_worktree(repo, ()) as staged:
            assert staged is not None
            paths["staged"] = staged
    assert not staged.exists()


@pytest.mark.parametrize("linked", [False, True])
def test_governed_staging_requires_controller(repo: Path, linked: bool) -> None:
    (repo / ".governance").mkdir()
    root = repo
    if linked:
        root = repo.parent / "existing-linked"
        git(repo, "worktree", "add", "--detach", str(root), "HEAD")
    before = git(repo, "worktree", "list", "--porcelain")
    # A locally authored lease is not a controller grant.
    lease = root / ".subactor/leases/ticket-001--fake.json"
    lease.parent.mkdir(parents=True)
    lease.write_text('{"phase":"editing","fencingToken":1}')
    with pytest.raises(StagingAdmissionRequired, match="protected controller"):
        with staging_worktree(root, ("a.txt",)):
            pytest.fail("must not yield an editing workspace")
    assert git(repo, "worktree", "list", "--porcelain") == before
    assert not list(repo.parent.glob(".koru-run-*"))


@pytest.mark.parametrize("mode", ["branch", "apply"])
def test_governed_refusal_does_not_run_verifier_or_apply(repo: Path, mode: str) -> None:
    (repo / ".governance").mkdir()
    diff = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
    plan = build_patch_plan(repo, {"id": "T-1", "inputs": {"promotion_mode": mode}}, diff)
    runner = Mock(side_effect=AssertionError("verifier must not run"))
    result = stage_patch(plan, runner)
    assert result.isolated and result.outcome is not None
    assert result.outcome.code == PROMOTION_FAILED
    assert "protected controller" in result.outcome.message
    runner.assert_not_called()
    assert (repo / "a.txt").read_text() == "old\n"


def test_symlink_staging_is_refused(repo: Path) -> None:
    alias = repo.parent / "alias"
    alias.symlink_to(repo, target_is_directory=True)
    with pytest.raises(StagingAdmissionRequired, match="symlink"):
        with staging_worktree(alias, ()):
            pytest.fail("symlink workspace admitted")


def test_symlink_location_override_is_refused(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = repo.parent / "elsewhere"
    target.mkdir()
    alias = repo.parent / "alias"
    alias.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("KORU_QUEUE_WORKTREE_DIR", str(alias))
    with pytest.raises(StagingAdmissionRequired, match="symlink"):
        with staging_worktree(repo, ()):
            pytest.fail("symlink staging location admitted")
    assert not list(target.iterdir())


def test_git_override_is_refused_before_any_git_effect(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_WORK_TREE", str(repo.parent))
    with patch("koru.queue.workspace._git", side_effect=AssertionError("Git must not run")):
        with pytest.raises(StagingAdmissionRequired, match="overrides"):
            with staging_worktree(repo, ()):
                pytest.fail("redirected workspace admitted")
