"""Query objects for the local manager bounded context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthSnapshotQuery:
    koru_version: str


@dataclass(frozen=True)
class QueueSnapshotQuery:
    pass


@dataclass(frozen=True)
class WorkersSnapshotQuery:
    pass


@dataclass(frozen=True)
class StateSnapshotQuery:
    pass


__all__ = [
    "HealthSnapshotQuery",
    "QueueSnapshotQuery",
    "StateSnapshotQuery",
    "WorkersSnapshotQuery",
]
