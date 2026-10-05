"""Real Git regression checks for protected admission on every patch write path."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from koru.queue.patch_mode import PROMOTION_FAILED
from koru.queue.transaction import execute_patch_transaction
from koru.queue.transaction.result import StagingResult
from tests import _repolab

DIFF = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "KORU_QUEUE_WORKTREE", "KORU_QUEUE_PROMOTION_MODE",
    ):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "repo"
    root.mkdir()
    _repolab.git_repo(root)
    _repolab.commit_file(root, "a.txt", "old\n")
    return root


def governed_root(repo: Path, linked: bool) -> Path:
    (repo / ".governance").mkdir()
    if not linked:
        return repo
    # Only the registered primary has the marker: linked lookup must find it.
    root = repo / ".worktrees/ticket-001--fixture"
    git(repo, "worktree", "add", "--relative-paths", "-b", "ticket/001-fixture", str(root), "HEAD")
    return root


def assert_refused(result, root: Path, runner: Mock) -> None:
    assert result.outcome is not None
    assert result.outcome.code == PROMOTION_FAILED
    assert "protected controller" in result.outcome.message
    assert not result.outcome.retryable
    assert result.outcome.workspace_left_untouched
    assert (root / "a.txt").read_text() == "old\n"
    runner.assert_not_called()


@pytest.mark.parametrize("linked", [False, True])
@pytest.mark.parametrize("mode", ["apply", "commit"])
@pytest.mark.parametrize("verify", [False, True])
@pytest.mark.parametrize("isolation", [False, True])
@pytest.mark.parametrize("callback", [False, True])
def test_governed_mutation_requires_independent_admission(
    repo: Path, monkeypatch: pytest.MonkeyPatch, linked: bool,
    mode: str, verify: bool, isolation: bool, callback: bool,
) -> None:
    root = governed_root(repo, linked)
    lease = root / ".subactor/leases/ticket-001--fixture.json"
    lease.parent.mkdir(parents=True)
    lease.write_text('{"phase":"editing","fencingToken":999,"capability":"workspace_write"}')
    head = git(root, "rev-parse", "HEAD")
    registrations = git(repo, "worktree", "list", "--porcelain")
    monkeypatch.setenv("KORU_QUEUE_WORKTREE", "1" if isolation else "0")
    runner = Mock(return_value=_repolab.reply())
    authorizer = Mock(return_value=None)
    inputs = {"promotion_mode": mode, "worktree": isolation}
    if verify:
        inputs["verify_command"] = "fixture-verify"
    result = execute_patch_transaction(
        root, _repolab.reply(stdout=DIFF), {"id": "T-1", "inputs": inputs}, runner,
        authorize=authorizer if callback else None,
    )
    assert_refused(result, root, runner)
    authorizer.assert_not_called()
    assert git(root, "rev-parse", "HEAD") == head
    assert git(repo, "worktree", "list", "--porcelain") == registrations


@pytest.mark.parametrize("linked", [False, True])
def test_governed_artifact_remains_available(repo: Path, linked: bool) -> None:
    root = governed_root(repo, linked)
    head = git(root, "rev-parse", "HEAD")
    runner = Mock()
    result = execute_patch_transaction(
        root, _repolab.reply(stdout=DIFF),
        {"id": "T-1", "inputs": {"promotion_mode": "artifact"}}, runner,
    )
    assert result.outcome is None
    assert result.plan is not None and result.plan.mode == "artifact"
    assert (root / "a.txt").read_text() == "old\n"
    assert git(root, "rev-parse", "HEAD") == head
    runner.assert_not_called()


@pytest.mark.parametrize("verify", [False, True])
def test_unmanaged_direct_apply_keeps_legacy_behavior(
    repo: Path, monkeypatch: pytest.MonkeyPatch, verify: bool,
) -> None:
    monkeypatch.setenv("KORU_QUEUE_WORKTREE", "0")
    runner = Mock(return_value=_repolab.reply())
    inputs = {"promotion_mode": "apply"}
    if verify:
        inputs["verify_command"] = "fixture-verify"
    result = execute_patch_transaction(
        repo, _repolab.reply(stdout=DIFF), {"id": "T-1", "inputs": inputs}, runner,
    )
    assert result.outcome is None
    assert (repo / "a.txt").read_text() == "new\n"
    assert runner.call_count == int(verify)


def test_recheck_after_local_authorizer(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_QUEUE_WORKTREE", "0")
    runner = Mock(return_value=_repolab.reply())

    def local_callback(plan, frozen):
        (repo / ".governance").mkdir()
        return None

    result = execute_patch_transaction(
        repo, _repolab.reply(stdout=DIFF),
        {"id": "T-1", "inputs": {"promotion_mode": "apply", "verify_command": "fixture-verify"}},
        runner, authorize=local_callback,
    )
    assert_refused(result, repo, runner)


@pytest.mark.parametrize("staged", [False, True])
def test_recheck_after_staging_before_fallback_or_promotion(repo: Path, staged: bool) -> None:
    runner = Mock(return_value=_repolab.reply())

    def stage_then_change_authority(plan, shell_runner):
        (repo / ".governance").mkdir()
        return StagingResult.verified() if staged else StagingResult.unavailable()

    with patch("koru.queue.transaction.service.stage_patch", side_effect=stage_then_change_authority):
        result = execute_patch_transaction(
            repo, _repolab.reply(stdout=DIFF),
            {"id": "T-1", "inputs": {"promotion_mode": "apply", "verify_command": "fixture-verify"}},
            runner,
        )
    assert_refused(result, repo, runner)


def test_symlink_workspace_is_refused(repo: Path) -> None:
    alias = repo.parent / "alias"
    alias.symlink_to(repo, target_is_directory=True)
    runner = Mock(return_value=_repolab.reply())
    result = execute_patch_transaction(
        alias, _repolab.reply(stdout=DIFF),
        {"id": "T-1", "inputs": {"promotion_mode": "apply"}}, runner,
    )
    assert result.outcome is not None and result.outcome.code == PROMOTION_FAILED
    assert "symlink" in result.outcome.message
    assert (repo / "a.txt").read_text() == "old\n"
    runner.assert_not_called()


@pytest.mark.parametrize("key", [
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
])
def test_git_redirection_is_refused_before_git_reads_or_effects(
    repo: Path, monkeypatch: pytest.MonkeyPatch, key: str,
) -> None:
    monkeypatch.setenv(key, str(repo.parent / "redirected"))
    runner = Mock(return_value=_repolab.reply())
    with patch("koru.queue.workspace._git", side_effect=AssertionError("no redirected Git reads")):
        result = execute_patch_transaction(
            repo, _repolab.reply(stdout=DIFF),
            {"id": "T-1", "inputs": {"promotion_mode": "apply"}}, runner,
        )
    assert result.outcome is not None and result.outcome.code == PROMOTION_FAILED
    assert "overrides" in result.outcome.message
    assert (repo / "a.txt").read_text() == "old\n"
    runner.assert_not_called()
