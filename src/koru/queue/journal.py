"""Append-only journal of a patch run: what was decided, what was mutated.

``.koru/runs/<run_id>/events.jsonl`` — one JSON object per line, sequence
numbers strictly monotonic, appended before *and* after every mutation. The
pairing is the point: an intent event (``staging``, ``applying``,
``promoting``) with no completion event after it means a crash interrupted a
mutation, while a completion event means the mutation finished even if the
process died before reporting. Recovery reads the journal and knows which of
the two worlds it woke up in — re-deciding is always safe, re-mutating never is.

The journal is observability plus recovery, not authority: the manifest says
what a run *may* do, evidence says what it *claims* to have done, the journal
says what it *was doing* at every step.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from koru.queue.manifest import manifest_run_directory

# Decision events — replaying them is free.
PHASE_RESOLVED = "resolved"  # plan built: gate, mode, targets known
PHASE_FROZEN = "frozen"  # manifest pinned and persisted
PHASE_REFUSED = "refused"  # a screen or gate said no; workspace untouched

# Mutation events, in intent/completion pairs — the crash-recovery backbone.
PHASE_STAGING = "staging"  # about to apply+verify in a worktree (branch ref may be created)
PHASE_STAGED = "staged"  # worktree proved the patch; any branch ref exists
PHASE_STAGING_UNAVAILABLE = "staging_unavailable"  # no worktree could be created
PHASE_APPLYING = "applying"  # about to write the workspace itself
PHASE_APPLIED = "applied"  # workspace written
PHASE_VERIFIED = "verified"  # gate ran green in the workspace
PHASE_ROLLED_BACK = "rolled_back"  # workspace write undone after a red gate
PHASE_PROMOTING = "promoting"  # about to commit
PHASE_PROMOTED = "promoted"  # commit exists

# Terminal events.
PHASE_COMPLETED = "completed"


class RunJournal:
    """The events.jsonl of one run, safe to reopen after a crash.

    Sequence numbers continue across instances: opening scans what survived and
    resumes after the last valid entry. A file whose final line was cut short by
    a dying process is healed by starting the next entry on a fresh line — the
    torn line stays in the file as bytes but never as an event.
    """

    def __init__(self, project: Path, run_id: str) -> None:
        self._path = manifest_run_directory(project, run_id) / "events.jsonl"
        self._run_id = run_id
        events = read_events(project, run_id)
        self._seq = events[-1]["seq"] if events else 0

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        phase: str,
        *,
        manifest_hash: str | None = None,
        data: dict | None = None,
    ) -> dict:
        """Durably record one event; returns it with its sequence number.

        One ``write`` of one line in append mode, flushed and fsynced: a crash
        leaves at most a torn final line, never an interleaved or missing one.
        """
        self._seq += 1
        event = {
            "seq": self._seq,
            "run_id": self._run_id,
            "phase": phase,
            "manifest_hash": manifest_hash,
            "at": datetime.now(UTC).isoformat(),
            "data": data or {},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as handle:
            if self._needs_newline(handle):
                handle.write("\n")
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def _needs_newline(self, handle) -> bool:
        """Whether the file ends mid-line — the signature of a torn write."""
        if handle.tell() == 0:
            return False
        with self._path.open("rb") as raw:
            raw.seek(-1, os.SEEK_END)
            return raw.read(1) != b"\n"


def read_events(project: Path, run_id: str) -> list[dict]:
    """Every trustworthy event, in order.

    Parsing stops at the first malformed line or broken sequence number:
    everything after a tear cannot be ordered relative to what was lost, and
    recovery acting on unordered events could re-run a mutation. Losing the
    tail is safe — the tail describes work that will be re-examined anyway.
    """
    path = manifest_run_directory(project, run_id) / "events.jsonl"
    if not path.is_file():
        return []
    events: list[dict] = []
    expected_seq = 1
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            break
        if not isinstance(event, dict) or event.get("seq") != expected_seq:
            break
        events.append(event)
        expected_seq += 1
    return events


def last_phase(events: list[dict]) -> str | None:
    return events[-1]["phase"] if events else None


def interrupted_mutation(events: list[dict]) -> str | None:
    """The mutation a crash cut short, or ``None`` when the journal is clean.

    An intent phase is "open" until its completion (or a refusal/rollback)
    follows. Only the *latest* intent matters: earlier pairs are closed by
    construction, or parsing would have stopped.
    """
    completions = {
        PHASE_STAGING: {PHASE_STAGED, PHASE_STAGING_UNAVAILABLE, PHASE_REFUSED},
        PHASE_APPLYING: {PHASE_APPLIED, PHASE_REFUSED},
        PHASE_PROMOTING: {PHASE_PROMOTED, PHASE_REFUSED, PHASE_ROLLED_BACK},
    }
    open_intent: str | None = None
    for event in events:
        phase = event.get("phase")
        if phase in completions:
            open_intent = phase
        elif open_intent and phase in completions[open_intent]:
            open_intent = None
    return open_intent
