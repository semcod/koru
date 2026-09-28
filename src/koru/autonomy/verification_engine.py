"""Post-drive verification engine for autonomous cycles.

Collects evidence from multiple sources (git, tests, chat history, file
modifications) and produces a structured ``Verdict`` that the decision
arbiter can act on.  Phase 1 of ADR AUTO-002: zero LLM cost, pure
heuristics.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
import subprocess
import time
from contextlib import closing
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


def _git_bytes(project: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=project, capture_output=True, timeout=10, check=True,
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
    changed = {
        name.split(":", 1)[1] for name in prior.keys() | after.keys()
        if prior.get(name) != after.get(name)
    }
    return GitEvidence(files_changed=len(changed), diff_stat=f"{len(changed)} workspace paths changed")


def _drive_budget_db(project: Path) -> sqlite3.Connection:
    path = project / ".planfile" / ".koru" / "drive-budget.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS failures (ticket TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS attempts (ticket TEXT PRIMARY KEY, count INTEGER NOT NULL)")
        return db
    except sqlite3.Error:
        db.close()
        raise


def record_unsuccessful_drive(project: Path, ticket: str) -> None:
    """Persist failure count independently of waiting streak and loop restarts."""
    if not ticket:
        return
    with closing(_drive_budget_db(project)) as db, db:
        db.execute(
            "INSERT INTO failures VALUES (?, 1) ON CONFLICT(ticket) DO UPDATE SET count=count+1", (ticket,),
        )



def drive_budget_exhausted(project: Path, ticket: str, limit: int = 3) -> bool:
    """Storage errors close admission; failures need an explicit ticket repair."""
    if not ticket:
        return False
    try:
        with closing(_drive_budget_db(project)) as db, db:
            counts = _drive_budget_counts(db, ticket)
        return max(counts) >= limit
    except (OSError, sqlite3.Error):
        return True


def _drive_budget_counts(db: sqlite3.Connection, ticket: str) -> tuple[int, int]:
    counts = []
    for table in ("failures", "attempts"):
        row = db.execute(f"SELECT count FROM {table} WHERE ticket=?", (ticket,)).fetchone()
        counts.append(int(row[0]) if row else 0)
    return counts[0], counts[1]


def reserve_drive_attempt(project: Path, ticket: str, limit: int = 3) -> bool:
    """Reserve before a paid shell call, atomically; crashes cannot erase attempts.

    The protected finalizer owns completion. Unverified shell calls share the
    admission budget with failed GUI drives; separate counts avoid double debit.
    """
    if not ticket:
        return True
    try:
        with closing(_drive_budget_db(project)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if max(_drive_budget_counts(db, ticket)) >= limit:
                return False
            db.execute(
                "INSERT INTO attempts VALUES (?, 1) ON CONFLICT(ticket) DO UPDATE SET count=count+1",
                (ticket,),
            )
        return True
    except (OSError, sqlite3.Error):
        return False


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
    if evidence.tests.status in {"failing", "failed", "error", "down"}:
        outcome: VerdictOutcome = "degraded"
    elif not evidence.git.observed:
        outcome = "unknown"
        reasons.append("git: observation unavailable")
    elif evidence.verification_passed:
        outcome = "completed"
        score = 1.0
        reasons.append("verification: matching drive passed")
    elif score >= 0.3:
        outcome = "in_progress"
    elif evidence.git.files_changed == 0 and not evidence.chat.has_message_sent:
        outcome = "no_change"
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


__all__ = [
    "ChatEvidence",
    "Evidence",
    "FileEvidence",
    "GitEvidence",
    "Snapshot",
    "TestEvidence",
    "Verdict",
    "VerdictOutcome",
    "absorbed_foreign_paths",
    "assess_verdict",
    "collect_chat_evidence",
    "collect_evidence",
    "collect_git_diff_between",
    "collect_git_evidence",
    "collect_test_evidence",
    "take_snapshot",
]
