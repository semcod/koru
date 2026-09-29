"""Evidence collectors (git, tests, chat) for post-drive verification."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from koru.autonomy.verification_engine.git_utils import (
    _extract_leading_int,
    _git_dirty_paths,
    _git_head,
    _workspace_delta,
    _workspace_fingerprints,
)
from koru.autonomy.verification_engine.models import (
    ChatEvidence,
    Evidence,
    GitEvidence,
    Snapshot,
    TestEvidence,
)


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
        return GitEvidence(observed=False)

    if result.returncode != 0:
        return GitEvidence(observed=False)

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
        return GitEvidence(observed=False)

    if result.returncode != 0:
        return GitEvidence(observed=False)

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

    events_since = [e for e in autopilot_events if float(e.get("ts", 0) or 0) >= drive_timestamp]
    if not events_since:
        return ChatEvidence()

    now = time.time()
    last_event = events_since[-1]
    last_ts = float(last_event.get("ts", 0) or 0)

    return ChatEvidence(
        events_since_drive=len(events_since),
        has_message_sent=any(str(e.get("type", "")) == "message.sent" for e in events_since),
        has_session_ended=any(str(e.get("type", "")) == "session.ended" for e in events_since),
        last_event_type=str(last_event.get("type", "")),
        last_event_age_seconds=now - last_ts if last_ts > 0 else -1.0,
    )


def take_snapshot(project: Path, test_status: str = "unknown") -> Snapshot:
    """Capture current project state for later comparison."""
    git_head = _git_head(project)
    dirty_paths = _git_dirty_paths(project)
    return Snapshot(
        git_head=git_head,
        git_dirty_count=len(dirty_paths),
        test_status=test_status,
        timestamp=time.time(),
        git_dirty_paths=dirty_paths,
        workspace_fingerprints=_workspace_fingerprints(project),
    )


def absorbed_foreign_paths(project: Path, before: Snapshot | None) -> list[str]:
    """Pre-drive dirty paths that ended up inside the drive's commits.

    Compares the commit range ``before.git_head..HEAD`` against the paths that
    were already dirty/untracked before the drive. A non-empty result means an
    agent commit swept up the operator's work in progress (the
    ``git commit -a "refactoring"`` failure mode).
    """
    if before is None or not before.git_head or not before.git_dirty_paths:
        return []
    head = _git_head(project)
    if not head or head == before.git_head:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{before.git_head}..{head}"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    committed = {line.strip() for line in (result.stdout or "").splitlines() if line.strip()}
    return sorted(committed & set(before.git_dirty_paths))


def collect_evidence(
    project: Path,
    *,
    before: Snapshot | None = None,
    wup_health: Any | None = None,
    autopilot_events: list[dict[str, Any]] | None = None,
    drive_timestamp: float = 0.0,
) -> Evidence:
    """Collect all available evidence after a drive."""
    if before and before.workspace_fingerprints is not None:
        git = _workspace_delta(project, before)
    else:
        # Without a baseline, a per-drive delta is unknown (not zero).
        git = GitEvidence(observed=False, diff_stat="pre-drive workspace baseline unavailable")

    tests = collect_test_evidence(wup_health)
    chat = collect_chat_evidence(autopilot_events or [], drive_timestamp)

    return Evidence(
        git=git,
        tests=tests,
        chat=chat,
        collected_at=time.time(),
    )
