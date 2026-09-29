"""Evidence and verdict data types for post-drive verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

VerdictOutcome = Literal[
    "completed",
    "in_progress",
    "no_change",
    "submitted_but_no_effect",
    "degraded",
    "unknown",
]


@dataclass(frozen=True)
class GitEvidence:
    """Evidence collected from ``git diff``."""

    files_changed: int = 0
    insertions: int | None = None
    deletions: int | None = None
    diff_stat: str = ""
    observed: bool = True


@dataclass(frozen=True)
class TestEvidence:
    """Evidence collected from WUP / TestQL health."""

    __test__ = False

    status: str = "unknown"  # ok | changed | failing | unknown
    failing_services: tuple[str, ...] = ()
    new_events: int = 0


@dataclass(frozen=True)
class ChatEvidence:
    """Evidence collected from autopilot chat events."""

    events_since_drive: int = 0
    has_message_sent: bool = False
    has_session_ended: bool = False
    last_event_type: str = ""
    last_event_age_seconds: float = -1.0


@dataclass(frozen=True)
class FileEvidence:
    """Evidence from filesystem modification times."""

    modified_files: int = 0
    newest_mtime_delta_seconds: float = -1.0


@dataclass(frozen=True)
class Evidence:
    """Combined evidence from all sources."""

    git: GitEvidence = field(default_factory=GitEvidence)
    tests: TestEvidence = field(default_factory=TestEvidence)
    chat: ChatEvidence = field(default_factory=ChatEvidence)
    files: FileEvidence = field(default_factory=FileEvidence)
    collected_at: float = 0.0
    verification_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Snapshot:
    """Project state snapshot taken before a drive."""

    git_head: str = ""
    git_dirty_count: int = 0
    test_status: str = "unknown"
    timestamp: float = 0.0
    #: Paths dirty/untracked BEFORE the drive — the operator's work in
    #: progress. Used post-drive to detect agent commits that absorbed it.
    git_dirty_paths: tuple[str, ...] = ()
    workspace_fingerprints: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["git_dirty_paths"] = list(self.git_dirty_paths)
        return d


@dataclass(frozen=True)
class Verdict:
    """Heuristic verdict on whether the IDE completed the requested work."""

    outcome: VerdictOutcome
    confidence: float  # 0.0 .. 1.0
    reason: str
    evidence: Evidence = field(default_factory=Evidence)
    ticket_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome
        return d
