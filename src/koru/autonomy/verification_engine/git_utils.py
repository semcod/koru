"""Git observation helpers for post-drive verification."""

import hashlib
import os
import stat
import subprocess
from pathlib import Path

from koru.autonomy.verification_engine.models import GitEvidence, Snapshot


def _git_bytes(project: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        timeout=10,
        check=True,
    )
    out = result.stdout
    if isinstance(out, str):
        return out.encode("utf-8")
    return out or b""


def _workspace_fingerprints(project: Path) -> dict[str, str] | None:
    """Observe bytes, symlink targets, modes and index entries without staging.

    Ignored runtime files are excluded; tracked and untracked source is included.
    No raw file contents enter a checkpoint. Errors remain unknown evidence.
    """
    try:
        names = _git_bytes(project, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        entries: dict[str, str] = {}
        for raw in set(names.split(b"\0")) - {b""}:
            name = os.fsdecode(raw)
            path = project / name
            try:
                mode = path.lstat().st_mode
            except FileNotFoundError:
                entries[f"worktree:{name}"] = "deleted"
                continue
            if stat.S_ISLNK(mode):
                content = os.fsencode(os.readlink(path))
            elif stat.S_ISREG(mode):
                content = path.read_bytes()
            else:
                raise OSError("unsupported workspace entry")
            entries[f"worktree:{name}"] = f"{mode}:{hashlib.sha256(content).hexdigest()}"
        for raw in _git_bytes(project, "ls-files", "--stage", "-z").split(b"\0"):
            if raw and b"\t" in raw:
                metadata, name = raw.split(b"\t", 1)
                entries[f"index:{os.fsdecode(name)}"] = metadata.decode("ascii", errors="replace")
        return entries
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _workspace_delta(project: Path, before: Snapshot) -> GitEvidence:
    after = _workspace_fingerprints(project)
    if after is None:
        return GitEvidence(observed=False, diff_stat="workspace observation failed")
    prior = before.workspace_fingerprints or {}
    changed = {name.split(":", 1)[1] for name in prior.keys() | after.keys() if prior.get(name) != after.get(name)}
    return GitEvidence(files_changed=len(changed), diff_stat=f"{len(changed)} workspace paths changed")


def _extract_leading_int(token: str) -> int:
    """Extract the first integer from a string like ``' 3 files changed'``."""
    digits = ""
    for ch in token.strip():
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else 0


def _git_head(project: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (result.stdout or "").strip() if result.returncode == 0 else ""
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return ""


def _git_dirty_count(project: Path) -> int:
    return len(_git_dirty_paths(project))


def _git_dirty_paths(project: Path) -> tuple[str, ...]:
    """Repo-relative paths reported dirty/untracked by ``git status --porcelain``."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return ()
    if result.returncode != 0:
        return ()
    paths: list[str] = []
    for line in (result.stdout or "").splitlines():
        if not line.strip():
            continue
        entry = line[3:] if len(line) > 3 else ""
        # Renames come as "old -> new"; the new path is what a commit would contain.
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            paths.append(entry)
    return tuple(paths)
