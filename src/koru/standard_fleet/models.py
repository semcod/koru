"""Data models for the Wellmanifest standard-fleet scan.

The models are plain frozen dataclasses with JSON projection helpers so the
scanner, its CLI and the Planfile emission boundary share one shape.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "koru.standard-fleet-report/v1"
SOURCE_TOOL = "koru-standard-fleet-watcher"
DEDUPE_PREFIX = "koru:wellmanifest-standard-adoption:"


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
class StandardExcluded:
    """A governed checkout observed but excluded from the default scope."""

    path: Path
    identity: str
    reasons: tuple[str, ...]
    dirty: bool = False
    linked_worktrees: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["reasons"] = list(self.reasons)
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
    excluded: tuple[StandardExcluded, ...] = ()
    discovered: int | None = None

    def to_dict(self, *, include_excluded: bool = False) -> dict[str, Any]:
        discovered = self.discovered
        if discovered is None:
            discovered = self.repositories + len(self.excluded)
        payload: dict[str, Any] = {
            "schema": REPORT_SCHEMA,
            "workspace": str(self.workspace),
            "standard": {
                "version": self.standard.version,
                "revision": self.standard.revision,
                "sourceRoot": str(self.standard.source_root),
            },
            "repositories": self.repositories,
            "discovered": discovered,
            "current": self.current,
            "stale": len(self.candidates),
            "excluded": len(self.excluded),
            "candidates": [item.to_dict() for item in self.candidates],
            "tickets": {
                "emitted": self.emitted,
                "reused": self.reused,
                "errors": list(self.emission_errors),
            },
        }
        if include_excluded:
            payload["excludedRepositories"] = [item.to_dict() for item in self.excluded]
        return payload


def adoption_dedupe_key(candidate: StandardCandidate) -> str:
    """Return a new key only when this repository or target revision changes."""
    identity = re.sub(r"[^a-zA-Z0-9._/-]+", "-", candidate.identity).strip("-").lower()
    return f"{DEDUPE_PREFIX}{identity}:{candidate.latest_revision}"
