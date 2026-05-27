"""Post-drive verification engine for autonomous cycles.

Collects evidence from multiple sources (git, tests, chat history, file
modifications) and produces a structured ``Verdict`` that the decision
arbiter can act on.  Phase 1 of ADR AUTO-002: zero LLM cost, pure
heuristics.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

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
    insertions: int = 0
    deletions: int = 0
    diff_stat: str = ""


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Snapshot:
    """Project state snapshot taken before a drive."""

    git_head: str = ""
    git_dirty_count: int = 0
    test_status: str = "unknown"
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def collect_git_evidence(project: Path) -> GitEvidence:
    """Run ``git diff --stat`` and parse the summary line."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return GitEvidence()

    if result.returncode != 0:
        return GitEvidence()

    lines = (result.stdout or "").strip().splitlines()
    if not lines:
        return GitEvidence()

    stat_line = lines[-1].strip()
    files_changed = 0
    insertions = 0
    deletions = 0

    for token in stat_line.split(","):
        token = token.strip()
        if "file" in token and "changed" in token:
            files_changed = _extract_leading_int(token)
        elif "insertion" in token:
            insertions = _extract_leading_int(token)
        elif "deletion" in token:
            deletions = _extract_leading_int(token)

    return GitEvidence(
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
        diff_stat=stat_line,
    )


def collect_git_diff_between(
    project: Path,
    before_head: str,
) -> GitEvidence:
    """Compare current HEAD against a prior commit."""
    if not before_head:
        return collect_git_evidence(project)
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", before_head, "HEAD"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return GitEvidence()

    if result.returncode != 0:
        return collect_git_evidence(project)

    lines = (result.stdout or "").strip().splitlines()
    if not lines:
        return GitEvidence()

    stat_line = lines[-1].strip()
    files_changed = 0
    insertions = 0
    deletions = 0
    for token in stat_line.split(","):
        token = token.strip()
        if "file" in token and "changed" in token:
            files_changed = _extract_leading_int(token)
        elif "insertion" in token:
            insertions = _extract_leading_int(token)
        elif "deletion" in token:
            deletions = _extract_leading_int(token)

    return GitEvidence(
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
        diff_stat=stat_line,
    )


def collect_test_evidence(wup_health: Any | None) -> TestEvidence:
    """Extract test evidence from a ``WupHealthResult``."""
    if wup_health is None:
        return TestEvidence()
    status = str(getattr(wup_health, "status", "unknown") or "unknown")
    failing = tuple(getattr(wup_health, "failing_services", ()) or ())
    new_events = int(getattr(wup_health, "new_events", 0) or 0)
    return TestEvidence(
        status=status,
        failing_services=failing,
        new_events=new_events,
    )


def collect_chat_evidence(
    autopilot_events: list[dict[str, Any]],
    drive_timestamp: float,
) -> ChatEvidence:
    """Extract chat evidence from autopilot events since the drive."""
    if not autopilot_events:
        return ChatEvidence()

    events_since = [
        e for e in autopilot_events
        if float(e.get("ts", 0) or 0) >= drive_timestamp
    ]
    if not events_since:
        return ChatEvidence()

    now = time.time()
    last_event = events_since[-1]
    last_ts = float(last_event.get("ts", 0) or 0)

    return ChatEvidence(
        events_since_drive=len(events_since),
        has_message_sent=any(
            str(e.get("type", "")) == "message.sent" for e in events_since
        ),
        has_session_ended=any(
            str(e.get("type", "")) == "session.ended" for e in events_since
        ),
        last_event_type=str(last_event.get("type", "")),
        last_event_age_seconds=now - last_ts if last_ts > 0 else -1.0,
    )


def take_snapshot(project: Path, test_status: str = "unknown") -> Snapshot:
    """Capture current project state for later comparison."""
    git_head = _git_head(project)
    git_dirty = _git_dirty_count(project)
    return Snapshot(
        git_head=git_head,
        git_dirty_count=git_dirty,
        test_status=test_status,
        timestamp=time.time(),
    )


def collect_evidence(
    project: Path,
    *,
    before: Snapshot | None = None,
    wup_health: Any | None = None,
    autopilot_events: list[dict[str, Any]] | None = None,
    drive_timestamp: float = 0.0,
) -> Evidence:
    """Collect all available evidence after a drive."""
    if before and before.git_head:
        git = collect_git_diff_between(project, before.git_head)
    else:
        git = collect_git_evidence(project)

    tests = collect_test_evidence(wup_health)
    chat = collect_chat_evidence(autopilot_events or [], drive_timestamp)

    return Evidence(
        git=git,
        tests=tests,
        chat=chat,
        collected_at=time.time(),
    )


# ---------------------------------------------------------------------------
# Verdict logic (pure heuristics, no LLM)
# ---------------------------------------------------------------------------

def assess_verdict(
    evidence: Evidence,
    *,
    ticket_id: str = "",
    drive_count: int = 1,
) -> Verdict:
    """Produce a heuristic verdict from collected evidence.

    Scoring:
      - git changes present               → +0.4
      - tests passing                      → +0.3
      - chat activity (message.sent)       → +0.2
      - session ended (IDE done working)   → +0.1
    """
    score = 0.0
    reasons: list[str] = []

    # Git evidence
    if evidence.git.files_changed > 0:
        score += 0.4
        reasons.append(f"git: {evidence.git.files_changed} files changed")
    else:
        reasons.append("git: no changes")

    # Test evidence
    if evidence.tests.status == "ok":
        score += 0.3
        reasons.append("tests: passing")
    elif evidence.tests.status in {"changed", "unknown"}:
        score += 0.1
        reasons.append(f"tests: {evidence.tests.status}")
    elif evidence.tests.status in {"failing", "failed", "error", "down"}:
        score -= 0.2
        reasons.append(f"tests: {evidence.tests.status}")

    # Chat evidence
    if evidence.chat.has_message_sent:
        score += 0.2
        reasons.append("chat: message.sent detected")
    if evidence.chat.has_session_ended:
        score += 0.1
        reasons.append("chat: session.ended")

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    # Determine outcome
    if score >= 0.6:
        outcome: VerdictOutcome = "completed"
    elif score >= 0.3:
        outcome = "in_progress"
    elif evidence.git.files_changed == 0 and not evidence.chat.has_message_sent:
        outcome = "no_change"
    elif evidence.tests.status in {"failing", "failed", "error", "down"}:
        outcome = "degraded"
    else:
        outcome = "unknown"

    # Penalise repeated failures
    if drive_count > 2 and outcome == "no_change":
        reasons.append(f"stagnant after {drive_count} drives")

    return Verdict(
        outcome=outcome,
        confidence=round(score, 2),
        reason="; ".join(reasons),
        evidence=evidence,
        ticket_id=ticket_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return 0
        lines = [l for l in (result.stdout or "").strip().splitlines() if l.strip()]
        return len(lines)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return 0


__all__ = [
    "ChatEvidence",
    "Evidence",
    "FileEvidence",
    "GitEvidence",
    "Snapshot",
    "TestEvidence",
    "Verdict",
    "VerdictOutcome",
    "assess_verdict",
    "collect_chat_evidence",
    "collect_evidence",
    "collect_git_diff_between",
    "collect_git_evidence",
    "collect_test_evidence",
    "take_snapshot",
]
