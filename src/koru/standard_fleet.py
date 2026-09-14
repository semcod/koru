"""Read-only Wellmanifest freshness scan with bounded ticket emission.

The scanner compares each adopted governance lock with one already-fetched,
clean checkout of wellmanifest/new-project. It never edits an adopter.
When explicitly requested, it emits one waiting-input Planfile ticket per
stale repository; the stable source key makes repeated scheduler cycles safe.
Actual adoption remains a repository-owned ticket and protected delivery
operation.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from koru.tasks import create_nl_task

REPORT_SCHEMA = "koru.standard-fleet-report/v1"
SOURCE_TOOL = "koru-standard-fleet-watcher"
DEDUPE_PREFIX = "koru:wellmanifest-standard-adoption:"
DEFAULT_WORKERS = 8
MAX_WORKERS = 32
_REMOTE_IDENTITY = re.compile(r"(?:git@|https://|ssh://git@)(?:[^/:]+)[/:]([^/]+)/(.+?)(?:\.git)?/?$")
_PRUNE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".worktrees",
    "worktrees",
    "build",
    "dist",
    "__pycache__",
}


@dataclass(frozen=True)
class GitObservation:
    returncode: int
    stdout: str = ""
    stderr: str = ""


GitRunner = Callable[[Path, Sequence[str]], GitObservation]


@dataclass(frozen=True)
class StandardRelease:
    version: str
    revision: str
    source_root: Path


@dataclass(frozen=True)
class StandardCandidate:
    path: Path
    identity: str
    pinned_version: str | None
    pinned_revision: str | None
    latest_version: str
    latest_revision: str
    reasons: tuple[str, ...]
    dirty: bool
    linked_worktrees: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["reasons"] = list(self.reasons)
        payload["dedupe_key"] = adoption_dedupe_key(self)
        return payload


@dataclass(frozen=True)
class StandardFleetReport:
    workspace: Path
    standard: StandardRelease
    repositories: int
    current: int
    candidates: tuple[StandardCandidate, ...]
    emitted: int = 0
    reused: int = 0
    emission_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "workspace": str(self.workspace),
            "standard": {
                "version": self.standard.version,
                "revision": self.standard.revision,
                "sourceRoot": str(self.standard.source_root),
            },
            "repositories": self.repositories,
            "current": self.current,
            "stale": len(self.candidates),
            "candidates": [item.to_dict() for item in self.candidates],
            "tickets": {
                "emitted": self.emitted,
                "reused": self.reused,
                "errors": list(self.emission_errors),
            },
        }


def _subprocess_git(repo: Path, args: Sequence[str]) -> GitObservation:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return GitObservation(127, stderr=str(exc))
    return GitObservation(completed.returncode, completed.stdout, completed.stderr)


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_standard_release(
    source_root: Path,
    *,
    git_runner: GitRunner = _subprocess_git,
) -> StandardRelease:
    """Load a clean, immutable local standard source observation."""
    source_root = source_root.resolve()
    version = _read_text(source_root / "VERSION")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("standard source VERSION is not a semantic version")
    dirty = git_runner(source_root, ["status", "--porcelain"])
    if dirty.returncode != 0:
        raise ValueError("standard source Git status could not be observed")
    if dirty.stdout.strip():
        raise ValueError("standard source checkout is dirty")
    revision_result = git_runner(source_root, ["rev-parse", "--verify", "HEAD"])
    revision = _clean_text(revision_result.stdout).lower()
    if revision_result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("standard source HEAD is not a full commit SHA")
    return StandardRelease(version, revision, source_root)


def discover_governed_repositories(workspace: Path) -> list[Path]:
    """Find repositories with an adopted governance lock, without worktrees."""
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise NotADirectoryError(workspace)
    found: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(workspace):
        dirnames[:] = [name for name in dirnames if name not in _PRUNE_DIRS]
        candidate = Path(dirpath)
        if (candidate / ".governance" / "manifest.lock.json").is_file():
            found.append(candidate)
            dirnames[:] = []
    return sorted(found)


def _origin_identity(repo: Path, *, git_runner: GitRunner) -> str:
    observed = git_runner(repo, ["remote", "get-url", "origin"])
    remote = _clean_text(observed.stdout)
    match = _REMOTE_IDENTITY.match(remote)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return f"local:{repo}"


def _lock_standard(repo: Path) -> tuple[str | None, str | None, str | None]:
    path = repo / ".governance" / "manifest.lock.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None, "invalid-standard-lock"
    standard = data.get("standard") if isinstance(data, dict) else None
    if not isinstance(standard, dict):
        return None, None, "invalid-standard-lock"
    version = standard.get("version")
    revision = standard.get("sourceRevision")
    if not isinstance(version, str) or not isinstance(revision, str):
        return None, None, "invalid-standard-lock"
    return version.strip(), revision.strip().lower(), None


def _git_state(repo: Path, *, git_runner: GitRunner) -> tuple[bool, int, str | None]:
    dirty_result = git_runner(repo, ["status", "--porcelain"])
    if dirty_result.returncode != 0:
        return False, 0, "git-status-unavailable"
    worktrees_result = git_runner(repo, ["worktree", "list", "--porcelain"])
    if worktrees_result.returncode != 0:
        return bool(worktrees_result.stdout.strip()), 0, "git-worktree-unavailable"
    worktree_lines = [line for line in worktrees_result.stdout.splitlines() if line.startswith("worktree ")]
    return bool(dirty_result.stdout.strip()), max(0, len(worktree_lines) - 1), None


def inspect_repository(
    repo: Path,
    release: StandardRelease,
    *,
    git_runner: GitRunner = _subprocess_git,
) -> StandardCandidate | None:
    """Return a stale candidate, or None when its pin is current."""
    pinned_version, pinned_revision, lock_error = _lock_standard(repo)
    dirty, linked_worktrees, git_error = _git_state(repo, git_runner=git_runner)
    reasons: list[str] = []
    if lock_error:
        reasons.append(lock_error)
    if git_error:
        reasons.append(git_error)
    if pinned_version != release.version:
        reasons.append("version-mismatch")
    if pinned_revision != release.revision:
        reasons.append("revision-mismatch")
    if not reasons:
        return None
    return StandardCandidate(
        path=repo.resolve(),
        identity=_origin_identity(repo, git_runner=git_runner),
        pinned_version=pinned_version,
        pinned_revision=pinned_revision,
        latest_version=release.version,
        latest_revision=release.revision,
        reasons=tuple(dict.fromkeys(reasons)),
        dirty=dirty,
        linked_worktrees=linked_worktrees,
    )


def scan_standard_fleet(
    workspace: Path,
    standard_root: Path,
    *,
    workers: int = DEFAULT_WORKERS,
    git_runner: GitRunner = _subprocess_git,
) -> StandardFleetReport:
    """Scan all governed repositories; Git observations may run in parallel."""
    if workers < 1 or workers > MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
    workspace = workspace.resolve()
    release = load_standard_release(standard_root, git_runner=git_runner)
    repositories = discover_governed_repositories(workspace)
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(repositories)))) as pool:
        candidates = tuple(
            item
            for item in pool.map(
                lambda repo: inspect_repository(repo, release, git_runner=git_runner),
                repositories,
            )
            if item is not None
        )
    return StandardFleetReport(
        workspace=workspace,
        standard=release,
        repositories=len(repositories),
        current=len(repositories) - len(candidates),
        candidates=candidates,
    )


def adoption_dedupe_key(candidate: StandardCandidate) -> str:
    """Return a new key only when this repository or target revision changes."""
    identity = re.sub(r"[^a-zA-Z0-9._/-]+", "-", candidate.identity).strip("-").lower()
    return f"{DEDUPE_PREFIX}{identity}:{candidate.latest_revision}"


def _ticket_description(candidate: StandardCandidate) -> str:
    blockers: list[str] = []
    if candidate.dirty:
        blockers.append("target primary checkout is dirty")
    if candidate.linked_worktrees:
        blockers.append(f"{candidate.linked_worktrees} linked worktree(s) exist")
    blocker_text = "; ".join(blockers) if blockers else "no local blocker observed"
    return (
        f"Wellmanifest standard update is due for {candidate.identity}.\n\n"
        f"Target checkout: {candidate.path}\n"
        f"Pinned version/revision: {candidate.pinned_version or 'invalid'} / "
        f"{candidate.pinned_revision or 'invalid'}\n"
        f"Available version/revision: {candidate.latest_version} / "
        f"{candidate.latest_revision}\n"
        f"Detected: {', '.join(candidate.reasons)}; {blocker_text}.\n\n"
        "Use one target-owned governance adoption ticket and its canonical "
        "worktree. First re-read AGENTS.md, active tickets, dirty state and "
        "linked worktrees. Run 'goal governance adopt --latest --check' for "
        "evidence, then perform the reviewed adoption only inside that ticket. "
        "Do not reset, overwrite or delete unknown work. Commit, test, PR and "
        "protected Validator merge remain required; this notice grants no "
        "write or merge authority."
    )


def emit_adoption_tickets(
    planfile_project: Path,
    candidates: Sequence[StandardCandidate],
    *,
    create_task: Callable[..., Any] = create_nl_task,
) -> tuple[int, int, tuple[str, ...]]:
    """Emit idempotent waiting-input tickets through the single Planfile writer."""
    emitted = 0
    reused = 0
    errors: list[str] = []
    for candidate in candidates:
        try:
            created = create_task(
                planfile_project,
                _ticket_description(candidate),
                queue_name="governance-handoff",
                priority="high",
                scaffold={
                    "title": (f"[STANDARD-UPDATE] {candidate.identity} -> {candidate.latest_version}"),
                    "labels": ["standard-update", "wellmanifest", "waiting-input"],
                    "source_tool": SOURCE_TOOL,
                    "source_context": {
                        "signal": "wellmanifest_standard_stale",
                        "dedupe_key": adoption_dedupe_key(candidate),
                        "repository": candidate.identity,
                        "target_root": str(candidate.path),
                        "latest_version": candidate.latest_version,
                        "latest_revision": candidate.latest_revision,
                        "authority_required": "target-governance-adoption/v1",
                    },
                    "executor_kind": "human",
                    "executor_mode": "interactive",
                    "execution_state": "waiting_input",
                    "files": [],
                },
            )
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"{candidate.identity}: {exc}")
            continue
        if getattr(created, "reused", False):
            reused += 1
        else:
            emitted += 1
    return emitted, reused, tuple(errors)


def render_report(report: StandardFleetReport) -> str:
    lines = [
        f"Wellmanifest fleet: {report.repositories} repositories, "
        f"{report.current} current, {len(report.candidates)} stale",
        f"Standard: {report.standard.version} @ {report.standard.revision}",
    ]
    for candidate in report.candidates:
        blockers = []
        if candidate.dirty:
            blockers.append("dirty")
        if candidate.linked_worktrees:
            blockers.append(f"worktrees={candidate.linked_worktrees}")
        suffix = f" [{', '.join(blockers)}]" if blockers else ""
        lines.append(f"  {candidate.identity}: {', '.join(candidate.reasons)}{suffix}")
    if report.emitted or report.reused or report.emission_errors:
        lines.append(f"Tickets: emitted={report.emitted} reused={report.reused} errors={len(report.emission_errors)}")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_WORKERS",
    "MAX_WORKERS",
    "REPORT_SCHEMA",
    "SOURCE_TOOL",
    "StandardCandidate",
    "StandardFleetReport",
    "StandardRelease",
    "adoption_dedupe_key",
    "discover_governed_repositories",
    "emit_adoption_tickets",
    "inspect_repository",
    "load_standard_release",
    "render_report",
    "scan_standard_fleet",
]
