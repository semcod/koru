"""Fleet scan orchestration: observe, scope, select and evaluate repositories."""

from __future__ import annotations

import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from koru.standard_fleet.discovery import (
    _lock_standard,
    discover_governed_repositories,
    load_standard_release,
)
from koru.standard_fleet.git_observation import (
    GitRunner,
    _observe_repository,
    _RepositoryObservation,
    _subprocess_git,
)
from koru.standard_fleet.models import (
    StandardCandidate,
    StandardExcluded,
    StandardFleetReport,
    StandardRelease,
)

DEFAULT_WORKERS = 8
MAX_WORKERS = 32
DEFAULT_ORGANIZATIONS = ("autogrammar", "semcod", "subactor", "wellmanifest")


def _candidate_from_observation(
    observation: _RepositoryObservation,
    release: StandardRelease,
) -> StandardCandidate | None:
    pinned_version, pinned_revision, lock_error = _lock_standard(observation.path)
    reasons: list[str] = []
    if lock_error:
        reasons.append(lock_error)
    if observation.git_error:
        reasons.append(observation.git_error)
    if pinned_version != release.version:
        reasons.append("version-mismatch")
    if pinned_revision != release.revision:
        reasons.append("revision-mismatch")
    if not reasons:
        return None
    return StandardCandidate(
        path=observation.path,
        identity=observation.identity,
        pinned_version=pinned_version,
        pinned_revision=pinned_revision,
        latest_version=release.version,
        latest_revision=release.revision,
        reasons=tuple(dict.fromkeys(reasons)),
        dirty=observation.dirty,
        linked_worktrees=observation.linked_worktrees,
    )


def inspect_repository(
    repo: Path,
    release: StandardRelease,
    *,
    git_runner: GitRunner = _subprocess_git,
) -> StandardCandidate | None:
    """Return a stale candidate, or None when its pin is current."""
    return _candidate_from_observation(_observe_repository(repo, git_runner=git_runner), release)


def _normalise_organizations(organizations: Sequence[str] | None) -> tuple[str, ...]:
    values = organizations if organizations is not None else DEFAULT_ORGANIZATIONS
    normalised = tuple(dict.fromkeys(value.strip().lower() for value in values if value.strip()))
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) for value in normalised):
        raise ValueError("organizations must contain GitHub organization names")
    return normalised


def _identity_organization(identity: str) -> str | None:
    if identity.startswith("local:"):
        return None
    organization, separator, _repository = identity.partition("/")
    return organization.lower() if separator else None


def _expected_repository_path(workspace: Path, identity: str) -> Path | None:
    organization, separator, repository = identity.partition("/")
    if not separator or not organization or not repository:
        return None
    return (workspace / organization / repository).resolve()


def _primary_paths_by_identity(
    workspace: Path,
    observations: Sequence[_RepositoryObservation],
) -> dict[str, Path]:
    grouped: dict[str, list[_RepositoryObservation]] = {}
    for observation in observations:
        if observation.identity.startswith("local:"):
            continue
        grouped.setdefault(observation.identity.lower(), []).append(observation)
    primary: dict[str, Path] = {}
    for identity, items in grouped.items():
        expected = _expected_repository_path(workspace, identity)
        chosen = min(
            items,
            key=lambda item: (
                0 if expected is not None and item.path == expected else 1,
                len(item.path.relative_to(workspace).parts),
                str(item.path),
            ),
        )
        primary[identity] = chosen.path
    return primary


def _exclusion_reasons(
    observation: _RepositoryObservation,
    *,
    organizations: tuple[str, ...],
    include_external: bool,
    include_local: bool,
    include_worktrees: bool,
    include_duplicates: bool,
    primary_paths: dict[str, Path],
) -> tuple[str, ...]:
    reasons: list[str] = []
    organization = _identity_organization(observation.identity)
    if organization is None and not include_local:
        reasons.append("local-origin")
    elif organization is not None and not include_external and organization not in organizations:
        reasons.append("organization-not-allowed")
    if observation.linked_worktree and not include_worktrees:
        reasons.append("linked-worktree")
    primary_path = primary_paths.get(observation.identity.lower())
    if primary_path is not None and primary_path != observation.path and not include_duplicates:
        reasons.append("duplicate-clone")
    return tuple(reasons)


def scan_standard_fleet(
    workspace: Path,
    standard_root: Path,
    *,
    workers: int = DEFAULT_WORKERS,
    git_runner: GitRunner = _subprocess_git,
    organizations: Sequence[str] | None = None,
    include_external: bool = False,
    include_local: bool = False,
    include_worktrees: bool = False,
    include_duplicates: bool = False,
) -> StandardFleetReport:
    """Scan the selected governed repositories; observations run in parallel.

    The default scope is the primary checkout for the four organizations that
    own the current fleet. Local-only checkouts, linked worktrees and duplicate
    clones remain visible in ``excluded`` but cannot create adoption tickets
    unless explicitly included.
    """
    if workers < 1 or workers > MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
    workspace = workspace.resolve()
    release = load_standard_release(standard_root, git_runner=git_runner)
    allowed_organizations = _normalise_organizations(organizations)
    repositories = discover_governed_repositories(workspace)
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(repositories)))) as pool:
        observations = tuple(pool.map(lambda repo: _observe_repository(repo, git_runner=git_runner), repositories))
    primary_paths = _primary_paths_by_identity(workspace, observations)
    selected: list[_RepositoryObservation] = []
    excluded: list[StandardExcluded] = []
    for observation in observations:
        reasons = _exclusion_reasons(
            observation,
            organizations=allowed_organizations,
            include_external=include_external,
            include_local=include_local,
            include_worktrees=include_worktrees,
            include_duplicates=include_duplicates,
            primary_paths=primary_paths,
        )
        if reasons:
            excluded.append(
                StandardExcluded(
                    path=observation.path,
                    identity=observation.identity,
                    reasons=reasons,
                    dirty=observation.dirty,
                    linked_worktrees=observation.linked_worktrees,
                )
            )
        else:
            selected.append(observation)
    candidates = tuple(
        item
        for item in (_candidate_from_observation(observation, release) for observation in selected)
        if item is not None
    )
    return StandardFleetReport(
        workspace=workspace,
        standard=release,
        repositories=len(selected),
        current=len(selected) - len(candidates),
        candidates=candidates,
        excluded=tuple(excluded),
        discovered=len(repositories),
    )
