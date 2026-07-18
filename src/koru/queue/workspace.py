"""Git and filesystem operations behind a patch transaction.

Everything that touches disk lives here: applying and reverting a diff,
fingerprinting files so concurrent edits can be detected, and managing the
throwaway worktree a patch is proven in. Kept separate from policy so the
rules about *whether* a patch may land stay readable on their own.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


def _git(project: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=project,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


@dataclass(frozen=True)
class PatchApplyResult:
    """Outcome of applying an agent-proposed diff."""

    ok: bool
    detail: str
    changed_files: tuple[str, ...] = ()


def apply_unified_diff(project: Path, diff: str) -> PatchApplyResult:
    """Apply a diff to the workspace, refusing anything that does not apply cleanly.

    ``git apply --check`` runs first so a malformed or stale patch changes
    nothing at all, rather than leaving the tree half-edited.
    """
    if not (project / ".git").exists():
        return PatchApplyResult(
            ok=False,
            detail=f"{project} is not a git repository — patch mode needs one to apply and roll back",
        )

    check = _git(project, "apply", "--check", "-", stdin=diff)
    if check.returncode != 0:
        return PatchApplyResult(
            ok=False,
            detail=f"patch does not apply cleanly: {(check.stderr or '').strip()[:400]}",
        )

    listed = _git(project, "apply", "--numstat", "-", stdin=diff)
    changed = tuple(
        line.split("\t")[-1].strip()
        for line in (listed.stdout or "").splitlines()
        if line.strip()
    )

    applied = _git(project, "apply", "-", stdin=diff)
    if applied.returncode != 0:
        return PatchApplyResult(
            ok=False,
            detail=f"git apply failed: {(applied.stderr or '').strip()[:400]}",
        )
    return PatchApplyResult(ok=True, detail="patch applied", changed_files=changed)


def revert_files(project: Path, files: tuple[str, ...]) -> None:
    """Restore tracked files to HEAD — the rollback path for a failed verify."""
    if not files:
        return
    _git(project, "checkout", "--", *files)


def diff_target_files(project: Path, diff: str) -> tuple[str, ...]:
    """List the paths a diff touches, without applying it."""
    listed = _git(project, "apply", "--numstat", "-", stdin=diff)
    return tuple(
        line.split("\t")[-1].strip()
        for line in (listed.stdout or "").splitlines()
        if line.strip()
    )


@dataclass(frozen=True)
class FileFingerprint:
    """Enough of a file's identity to detect that someone else changed it."""

    exists: bool
    sha256: str | None
    mode: int | None
    symlink_target: str | None


def fingerprint_files(project: Path, paths: tuple[str, ...]) -> dict[str, FileFingerprint]:
    """Capture the current state of the files a patch will touch."""
    prints: dict[str, FileFingerprint] = {}
    for rel in paths:
        target = project / rel
        if target.is_symlink():
            prints[rel] = FileFingerprint(True, None, None, os.readlink(target))
            continue
        if not target.is_file():
            prints[rel] = FileFingerprint(False, None, None, None)
            continue
        stat = target.stat()
        prints[rel] = FileFingerprint(
            exists=True,
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            mode=stat.st_mode & 0o777,
            symlink_target=None,
        )
    return prints


def changed_since(project: Path, baseline: dict[str, FileFingerprint]) -> tuple[str, ...]:
    """Paths whose on-disk state no longer matches the captured baseline."""
    current = fingerprint_files(project, tuple(baseline))
    return tuple(sorted(rel for rel, before in baseline.items() if current.get(rel) != before))


def dirty_paths(project: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Which of *paths* carry uncommitted work.

    ``git checkout --`` restores from the index, so reverting a file that
    already held the user's unstaged edits destroys them. Direct-apply mode
    must therefore refuse to touch a dirty file rather than promise a rollback
    it cannot honour.
    """
    if not paths:
        return ()
    status = _git(project, "status", "--porcelain", "--", *paths)
    if status.returncode != 0:
        return paths  # cannot tell — assume the worst rather than risk the edits
    return tuple(
        sorted(
            {
                line[3:].strip().strip('"').split(" -> ")[-1]
                for line in (status.stdout or "").splitlines()
                if line.strip()
            },
        ),
    )


def current_head(project: Path) -> str:
    """The commit a run is based on, or "" outside a git repository."""
    head = _git(project, "rev-parse", "HEAD")
    return (head.stdout or "").strip() if head.returncode == 0 else ""


def repository_is_clean(project: Path) -> bool:
    """Whether the working tree has no uncommitted changes at all."""
    status = _git(project, "status", "--porcelain")
    return status.returncode == 0 and not (status.stdout or "").strip()


def commit_on_main(
    project: Path,
    message: str,
    paths: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Commit only the patch's files on the current branch."""
    if paths:
        staged = _git(project, "add", "--", *paths)
    else:
        staged = _git(project, "add", "-A")
    if staged.returncode != 0:
        return False, (staged.stderr or staged.stdout or "").strip()[:300]
    committed = _git(project, "commit", "--quiet", "-m", message)
    if committed.returncode != 0:
        return False, (committed.stderr or committed.stdout or "").strip()[:300]
    head = _git(project, "rev-parse", "HEAD")
    return True, (head.stdout or "").strip()


def commit_worktree(
    worktree: Path,
    branch: str,
    message: str,
    paths: tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Commit the patch's files in *worktree* onto a fresh *branch*.

    Only *paths* are staged. ``git add -A`` would sweep in whatever else the run
    left behind — koru's own event log, tool caches, test output — and the point
    of this commit is that it contains the reviewed patch and nothing else.
    """
    switched = _git(worktree, "switch", "--quiet", "-c", branch)
    if switched.returncode != 0:
        return False, (switched.stderr or "").strip()[:300]
    _git(worktree, "add", "--", *paths) if paths else _git(worktree, "add", "-A")
    committed = _git(worktree, "commit", "--quiet", "-m", message)
    if committed.returncode != 0:
        return False, (committed.stderr or committed.stdout or "").strip()[:300]
    head = _git(worktree, "rev-parse", "HEAD")
    return True, (head.stdout or "").strip()


def worktree_enabled(project: Path) -> bool:
    """Whether to stage a patch in a throwaway worktree before promoting it.

    Requires a git repository with at least one commit, since the worktree is
    created from HEAD. ``KORU_QUEUE_WORKTREE=0`` opts out.
    """
    if (os.environ.get("KORU_QUEUE_WORKTREE") or "").strip().lower() in {"0", "false", "no", "off"}:
        return False
    if not (project / ".git").exists():
        return False
    return _git(project, "rev-parse", "--verify", "HEAD").returncode == 0


def _worktree_location(project: Path, run_id: str) -> Path:
    """Where to put the staging worktree.

    Placed as a *sibling* of the project rather than inside it, so the checkout
    keeps its usual depth on disk. Suites routinely resolve fixtures relative to
    the repository's parent (``resolve(__dirname, "../..")`` in a monorepo), and
    a worktree nested under ``<project>/.koru/`` silently breaks every one of
    them. Sibling placement keeps those paths resolving as they do normally.
    """
    override = (os.environ.get("KORU_QUEUE_WORKTREE_DIR") or "").strip()
    if override:
        return Path(override).expanduser() / f".koru-run-{run_id}"
    parent = project.parent
    if os.access(parent, os.W_OK):
        return parent / f".koru-run-{run_id}"
    return project / ".koru" / "worktrees" / f"run-{run_id}"


def prune_stale_worktrees(project: Path) -> None:
    """Clear worktrees left behind by an interrupted run.

    A killed process never runs its cleanup, leaving both a directory and a git
    registration. ``git worktree prune`` drops registrations whose directory is
    gone; the reverse case — a surviving directory git no longer tracks — is
    removed here. Only paths matching koru's own naming are touched, and a
    directory git still lists is left alone, so a concurrent run is never
    disturbed.
    """
    _git(project, "worktree", "prune")
    listed = _git(project, "worktree", "list", "--porcelain")
    live = {
        line.split(" ", 1)[1].strip()
        for line in (listed.stdout or "").splitlines()
        if line.startswith("worktree ")
    }
    for candidate in (*project.parent.glob(".koru-run-*"), *(project / ".koru" / "worktrees").glob("run-*")):
        if candidate.is_dir() and str(candidate) not in live:
            shutil.rmtree(candidate, ignore_errors=True)


@contextmanager
def staging_worktree(project: Path, seed_files: tuple[str, ...]) -> Iterator[Path | None]:
    """Yield a disposable worktree seeded with the workspace's current content.

    The agent read the *working tree*, so its diff is written against whatever
    is on disk — including uncommitted edits. A worktree checked out at HEAD
    would therefore reject the patch, so the files the patch touches are copied
    across before it is applied. Yields None when the worktree cannot be
    created, leaving the caller to fall back to in-place execution.
    """
    prune_stale_worktrees(project)
    try:
        path = _worktree_location(project, uuid4().hex[:12])
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only checkouts are normal in containers and CI — koru's own
        # noVNC image mounts the repo at /opt/koru:ro. Degrade to in-place
        # execution, which refuses to touch dirty files, rather than crashing
        # the queue over a directory that cannot be created.
        yield None
        return
    created = _git(project, "worktree", "add", "--detach", "--quiet", str(path), "HEAD")
    if created.returncode != 0:
        yield None
        return
    try:
        for rel in seed_files:
            source = project / rel
            if not source.is_file():
                continue
            destination = path / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        yield path
    finally:
        _git(project, "worktree", "remove", "--force", str(path))


