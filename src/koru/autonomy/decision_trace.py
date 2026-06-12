"""Structured ``observed → decided → action → evidence → next`` trace.

Every autonomous cycle produces ONE :class:`DecisionRecord` that captures
*why* Koru did or did not act. Records are persisted as a ring buffer in
``.planfile/.koru/autonomy-telemetry.json`` under the ``recent_decisions``
key and printed as a compact one-line summary in the operator log.

This is the structured complement to the ``autopilot=skipped(<code>)``
short-form previously appended to the cycle summary. Both share the same
``skip_code`` vocabulary so shell logs, telemetry JSON, and dashboard API
agree on what happened.

Skip codes (keep this list in sync with
``autonomous_cycle_orchestrator``, ``autonomous_cycle_skip_conditions``,
and ``autonomous_cycle_chat_activity``):

``plugin_not_connected``
    Autopilot needed a VSIX plugin session but the daemon has no live
    matching connection yet.

``plugin_version_mismatch``
    A plugin is present, but its version/protocol is incompatible with
    the daemon's strict policy.

``plugin_status_unavailable``
    Koru could not read plugin status from the daemon at all.

``plugin_missing``
    Generic fallback for plugin gate failures that do not fit a more
    specific class.

``ide_mismatch``
    The autopilot lane points at one IDE but the running IDE process
    belongs to a different family.

``idle_no_ticket``
    Queue is idle AND there is no open ticket in the planfile to drive.

``waiting_ticket_closed``
    Queue says ``waiting_input`` but the referenced ticket is already
    closed/done in the planfile, so stale redrive is suppressed.

``idle_only``
    ``--autopilot-on-idle-only`` is set and the queue is currently
    non-idle.

``idle_streak``
    Queue stayed idle for too many consecutive cycles; the loop is
    backing off to avoid spamming the IDE.

``diagnostics_fail``
    Pre-drive diagnostics reported a failure and
    ``--autopilot-skip-on-diagnostics-fail`` is enabled.

``chat_activity``
    A recent user message / drive ACK / session event blocks pasting to
    avoid clobbering the user's chat.

``topology``
    ``autopilot:drive`` is disabled in the topology configuration.

``action_off``
    ``--autopilot-action off`` (drive deliberately disabled).

``manual_focus``
    Drive ran but the plugin reports the chat surface needs manual focus
    (e.g. webview not foregrounded).

``manual_send_required``
    Text was pasted into the IDE chat, but submit verification failed.
    Koru must not blindly redrive because that can duplicate prompts.

``stuck_<queue_status>``
    Queue has been stuck on the same status (e.g. ``waiting_input``) for
    multiple cycles AND the waiting ticket is *not* marked ``llm-ready``
    — the loop refuses to spam the same chat prompt at a human ticket.

``ok``
    Drive completed and was verified.

``failed``
    Drive ran but the plugin reported a failure.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.autonomy.autopilot_status import parse_autopilot_status

DECISION_TRACE_RING_SIZE = 10
"""Number of recent decisions kept on disk and exposed by the API."""

# Map ``code → human description``. The ``because`` field on the record is
# allowed to override this with a more specific message (e.g. include the
# concrete ticket id, cooldown seconds, or plugin version mismatch text).
SKIP_CODE_DESCRIPTIONS: dict[str, str] = {
    "plugin_not_connected": (
        "Autopilot needs a connected VSIX plugin but no compatible live "
        "session is attached to the daemon yet. Reload the IDE window, then "
        "connect the IDE plugin."
    ),
    "plugin_version_mismatch": (
        "Autopilot found a plugin session, but its version/protocol does not "
        "match the daemon policy. Reload the IDE after installing the current VSIX."
    ),
    "plugin_status_unavailable": (
        "Autopilot could not read plugin status from the daemon. Check the "
        "daemon socket and run `koru autopilot status --explain`."
    ),
    "plugin_missing": (
        "Autopilot needs a connected VSIX plugin but the daemon has no "
        "compatible session for this IDE. Reload the IDE window and run "
        "`koru: Connect autopilot daemon`."
    ),
    "ide_mismatch": (
        "Autopilot lane targets a different IDE than the one currently "
        "running in the foreground."
    ),
    "idle_no_ticket": (
        "Queue is idle AND no open ticket exists in the planfile. Drive "
        "is suppressed so the user's chat input isn't clobbered with stale "
        "prompts."
    ),
    "waiting_ticket_closed": (
        "Queue points at a waiting ticket that is already closed in the "
        "planfile; stale redrive is suppressed."
    ),
    "idle_only": (
        "``--autopilot-on-idle-only`` is on and the queue is not idle."
    ),
    "idle_streak": (
        "Queue stayed idle for too many consecutive cycles; the loop is "
        "backing off."
    ),
    "diagnostics_fail": (
        "Pre-drive diagnostics reported a failure and skip-on-fail is on."
    ),
    "chat_activity": (
        "Recent chat activity (drive ack / user message) is still inside "
        "the cooldown window; pasting now would clobber the user."
    ),
    "topology": "``autopilot:drive`` is disabled in topology.",
    "action_off": "``--autopilot-action off``.",
    "manual_focus": (
        "Plugin ran the submit step but reports the chat surface needs "
        "manual focus (webview not foregrounded)."
    ),
    "manual_send_required": (
        "Plugin pasted text into chat but submit was not verified; manual "
        "send or a submit-strategy fix is required before another drive."
    ),
    "stuck_waiting_input": (
        "Queue has been stuck on ``waiting_input`` for several cycles and "
        "the waiting ticket is not marked ``llm-ready``; autopilot refuses "
        "to clobber the human operator's chat."
    ),
    "stuck_status": (
        "Queue has been stuck on the same non-idle status for several "
        "cycles; autopilot is escalating instead of redriving."
    ),
    "ok": "Drive completed and was verified.",
    "failed": "Drive ran but the plugin reported a failure.",
    "unknown": "No structured reason recorded for this cycle.",
}


@dataclass(frozen=True)
class DecisionRecord:
    """One structured ``observed → decided → action → evidence → next`` line.

    Designed to be small, JSON-serialisable, and stable across releases —
    the dashboard and CLI both render the same fields.

    Fields:
        at:
            ISO-8601 UTC timestamp of when the cycle ended.
        cycle:
            Cycle number (matches ``=== koru autonomous cycle #N ===``).
        observed:
            What the loop saw this cycle (queue status, waiting ticket,
            scan summary, recent chat activity).
        decided:
            The intent the loop chose (``drive_ticket_prompt``,
            ``skip``, ``intake_only``, ``redrive``…).
        action:
            What actually ran (``submit_attempted``, ``paste_only``,
            ``no_op``, ``scan_only``).
        evidence:
            Concrete signals supporting the decision (verification mode,
            backend used, bubble db match, sentinel probe result, ticket
            id).
    next_step:
            Short description of what the loop will try next.
        blocked_by:
            Machine-readable blocker for the cycle, when work is stalled by
            a specific gate such as ``plugin_missing`` or ``idle_no_ticket``.
        skip_code:
            Machine-readable reason from :data:`SKIP_CODE_DESCRIPTIONS`.
            ``ok`` when the cycle drove successfully; ``unknown`` if not
            classified.
        skip_because:
            Free-form human-readable supplement (e.g. concrete ticket id,
            cooldown remaining). Empty when the code already explains it.
    """

    at: str
    cycle: int
    observed: str
    decided: str
    action: str
    evidence: str
    next_step: str
    blocked_by: str = ""
    skip_code: str = "unknown"
    skip_because: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "at": self.at,
            "cycle": self.cycle,
            "observed": self.observed,
            "decided": self.decided,
            "action": self.action,
            "evidence": self.evidence,
            "next_step": self.next_step,
            "blocked_by": self.blocked_by,
            "skip_code": self.skip_code,
            "skip_because": self.skip_because,
        }
        if self.extra:
            out["extra"] = dict(self.extra)
        return out

    def compact_line(self) -> str:
        """One-line operator-friendly summary.

        Format: ``observed=… → decided=… → action=… → evidence=… → next=…``
        — five pieces separated by ``→`` so the eye can scan the same
        column across cycles. ``skip_code`` is folded into ``action``
        whenever the action was a skip, so the reader sees the code
        without having to widen the line.
        """
        return (
            f"observed={self.observed} → decided={self.decided}"
            f" → action={self.action} → evidence={self.evidence}"
            f" → next={self.next_step}"
        )


def now_utc_iso() -> str:
    """ISO-8601 UTC timestamp with second precision (no microseconds)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def decision_trace_path(project: Path) -> Path:
    """Same telemetry directory used by :mod:`telemetry_snapshot`.

    The trace lives alongside ``autonomy-telemetry.json`` so a single
    rsync of ``.planfile/.koru/`` ships both. We deliberately keep the
    snapshot in ``autonomy-telemetry.json`` and append the ring buffer to
    the same file under ``recent_decisions`` rather than creating a new
    file: the snapshot is already what operators copy/paste when
    debugging and the dashboard already loads it.
    """
    return project.resolve() / ".planfile" / ".koru" / "autonomy-telemetry.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomic rename so partial writes never leave a torn JSON file.

    A crash during ``write_text`` could otherwise leave the telemetry
    file with truncated JSON and break every dashboard load until the
    next cycle. ``tempfile`` + ``os.replace`` keeps the existing file
    intact until the new one is fully on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".autonomy-telemetry.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def append_decision_record(
    project: Path,
    record: DecisionRecord,
    *,
    ring_size: int = DECISION_TRACE_RING_SIZE,
) -> None:
    """Append ``record`` to the on-disk ring buffer (best-effort).

    Failures are swallowed: telemetry write must never crash the
    autonomous loop. The ring buffer survives across runs because we
    read the previous file first and merge.
    """
    path = decision_trace_path(project)
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    history = existing.get("recent_decisions")
    if not isinstance(history, list):
        history = []
    history.append(record.to_dict())
    if ring_size > 0 and len(history) > ring_size:
        history = history[-ring_size:]
    existing["recent_decisions"] = history
    try:
        _atomic_write_json(path, existing)
    except OSError:
        pass


def load_recent_decisions(
    project: Path,
    *,
    limit: int = DECISION_TRACE_RING_SIZE,
) -> list[dict[str, Any]]:
    """Read the ring buffer. Used by the dashboard API + ``koru autopilot trace``."""
    path = decision_trace_path(project)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return []
    history = payload.get("recent_decisions") if isinstance(payload, dict) else None
    if not isinstance(history, list):
        return []
    items = [item for item in history if isinstance(item, dict)]
    if limit > 0:
        items = items[-limit:]
    return items


_TELEMETRY_SKIP_FLAGS: tuple[tuple[str, str], ...] = (
    ("autopilot_skipped_ide_mismatch", "ide_mismatch"),
    ("autopilot_skipped_chat_activity", "chat_activity"),
    ("autopilot_skipped_idle_no_ticket", "idle_no_ticket"),
    ("autopilot_skipped_waiting_ticket_closed", "waiting_ticket_closed"),
    ("autopilot_skipped_idle_streak", "idle_streak"),
    ("autopilot_skipped_manual_focus", "manual_focus"),
    ("autopilot_skipped_diagnostics_fail", "diagnostics_fail"),
)


def _plugin_missing_skip_code(cycle_telemetry: dict[str, Any]) -> str | None:
    if not cycle_telemetry.get("autopilot_skipped_plugin_missing"):
        return None
    blocker = str(cycle_telemetry.get("autopilot_skipped_plugin_blocker") or "").strip()
    return blocker if blocker in SKIP_CODE_DESCRIPTIONS else "plugin_missing"


def _stuck_status_skip_code(cycle_telemetry: dict[str, Any]) -> str | None:
    if not cycle_telemetry.get("autopilot_skipped_stuck_status"):
        return None
    queue = str(cycle_telemetry.get("autopilot_skipped_stuck_status_queue") or "")
    specific = f"stuck_{queue}" if queue else "stuck_status"
    return specific if specific in SKIP_CODE_DESCRIPTIONS else "stuck_status"


def _status_skip_code(autopilot_status: str) -> str | None:
    status = parse_autopilot_status(autopilot_status)
    if status.skipped:
        # ``skipped(idle_only)`` -> ``idle_only`` etc.
        inner = status.code
        if inner in SKIP_CODE_DESCRIPTIONS:
            return inner
        # ``skipped(stuck_waiting_input)`` even when no telemetry flag was set
        # by an upstream skip path (defensive: keeps the trace honest).
        if inner.startswith("stuck_"):
            return inner if inner in SKIP_CODE_DESCRIPTIONS else "stuck_status"
    if status.ok:
        return "ok"
    if status.failed:
        if status.submit_unverified:
            return "manual_send_required"
        return "failed"
    return None


def classify_skip_code(cycle_telemetry: dict[str, Any], autopilot_status: str) -> str:
    """Pick the canonical skip code from telemetry flags.

    Order matters: ``plugin_missing`` and ``ide_mismatch`` are upstream
    gates and must be reported before any downstream skip
    (``chat_activity``, ``idle_*``). ``ok`` and ``failed`` come from
    ``autopilot_status`` directly because the orchestrator only sets one
    of them on the happy path.
    """
    if plugin_code := _plugin_missing_skip_code(cycle_telemetry):
        return plugin_code
    if cycle_telemetry.get("autopilot_submit_unverified"):
        return "manual_send_required"
    for flag, code in _TELEMETRY_SKIP_FLAGS:
        if cycle_telemetry.get(flag):
            return code
    if stuck_code := _stuck_status_skip_code(cycle_telemetry):
        return stuck_code
    if status_code := _status_skip_code(autopilot_status):
        return status_code
    return "unknown"


def human_skip_reason(code: str, *, fallback: str = "") -> str:
    """Description from :data:`SKIP_CODE_DESCRIPTIONS` or ``fallback``."""
    return SKIP_CODE_DESCRIPTIONS.get(code, fallback or code)


def _format_queue_observation(
    queue_status: str,
    waiting_ticket: str,
    stagnation_streak: int,
) -> str:
    """``queue=idle waiting=- streak=3`` style block for ``observed=``."""
    parts = [f"queue={queue_status or 'unknown'}"]
    if waiting_ticket and waiting_ticket != "-":
        parts.append(f"ticket={waiting_ticket}")
    if stagnation_streak:
        parts.append(f"streak={stagnation_streak}")
    return " ".join(parts)


def _decide_label(
    autopilot_status: str,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
) -> str:
    """``decided=`` field. Maps to drive intent or the chosen skip path."""
    status = parse_autopilot_status(autopilot_status)
    if status.ok:
        return autopilot_drive_kind or "drive"
    if cycle_telemetry.get("autopilot_chat_intake_ticket"):
        return "intake_only"
    if cycle_telemetry.get("autopilot_llx_operator_ticket"):
        return "llx_reflection"
    if status.failed and (status.submit_unverified or cycle_telemetry.get("autopilot_submit_unverified")):
        return "manual_send_required"
    if status.skipped:
        return f"skip:{status.code}"
    if status.failed:
        return "drive_failed"
    return status.code or "no_action"


def _action_label(
    autopilot_status: str,
    autopilot_backend: str | None,
) -> str:
    """``action=`` field. ``submit_verified`` / ``submit_unverified`` / ``no_op``."""
    status = parse_autopilot_status(autopilot_status)
    if status.ok:
        backend = autopilot_backend or "unknown"
        return f"submit_verified(backend={backend})"
    if status.skipped:
        return "no_op"
    if status.failed:
        return "submit_unverified"
    return status.code or "no_op"


def _evidence_label(
    cycle_telemetry: dict[str, Any],
    autopilot_backend: str | None,
    diag_status: str,
    wup_status: str,
    blocked_by: str,
) -> str:
    """``evidence=`` field. Concrete signals supporting the decision."""
    parts: list[str] = []
    if blocked_by:
        parts.append(f"blocked_by={blocked_by}")
    if autopilot_backend:
        parts.append(f"backend={autopilot_backend}")
    if diag_status:
        parts.append(f"diagnostics={diag_status}")
    if wup_status:
        parts.append(f"wup={wup_status}")
    intake = cycle_telemetry.get("autopilot_chat_intake_ticket")
    if intake:
        parts.append(f"intake_ticket={intake}")
    chat_event = cycle_telemetry.get("autopilot_chat_activity_last_event")
    if chat_event:
        parts.append(f"chat_event={chat_event}")
    plugin_reason = cycle_telemetry.get("autopilot_skipped_plugin_missing_reason")
    if plugin_reason:
        parts.append(f"plugin_reason={plugin_reason}")
    scan_run = cycle_telemetry.get("scan_after_idle_run")
    scan_applied = cycle_telemetry.get("scan_after_idle_applied")
    if scan_run:
        parts.append(f"scan_idle_applied={scan_applied or 0}")
    return ", ".join(parts) if parts else "-"


_PLUGIN_SKIP_CODES = frozenset(
    {
        "plugin_missing",
        "plugin_not_connected",
        "plugin_version_mismatch",
        "plugin_status_unavailable",
    }
)


def _chat_activity_skip_because(cycle_telemetry: dict[str, Any]) -> str:
    because = str(cycle_telemetry.get("autopilot_skipped_chat_activity_because") or "")
    if because:
        return because
    chat_event = cycle_telemetry.get("autopilot_chat_activity_last_event")
    if chat_event:
        return f"last chat event: {chat_event}"
    return ""


def _idle_streak_skip_because(stagnation_streak: int) -> str:
    if stagnation_streak:
        return f"queue idle for {stagnation_streak} consecutive cycles"
    return ""


def _plugin_skip_because(
    skip_code: str,
    cycle_telemetry: dict[str, Any],
    autopilot_ide: str,
) -> str:
    plugin_reason = str(cycle_telemetry.get("autopilot_skipped_plugin_missing_reason") or "")
    plugin_reason = plugin_reason.strip()
    if plugin_reason:
        return plugin_reason
    if skip_code == "plugin_version_mismatch":
        return (
            f"connected plugin session for ide={autopilot_ide} failed strict "
            "version/protocol checks"
        )
    if skip_code == "plugin_status_unavailable":
        return f"daemon status unavailable while probing ide={autopilot_ide}"
    return f"daemon has no compatible plugin session for ide={autopilot_ide}"


def _waiting_ticket_closed_skip_because(cycle_telemetry: dict[str, Any]) -> str:
    ticket = str(cycle_telemetry.get("autopilot_skipped_waiting_ticket_closed_ticket") or "-")
    ticket = ticket.strip()
    if ticket and ticket != "-":
        return (
            f"queue references ticket={ticket} in waiting_input, but planfile "
            "marks it closed/done"
        )
    return "queue references a waiting_input ticket already marked closed/done"


def _stuck_skip_because(
    cycle_telemetry: dict[str, Any],
    queue_status: str,
    waiting_ticket: str,
) -> str:
    streak = cycle_telemetry.get("autopilot_skipped_stuck_status_streak")
    queue = cycle_telemetry.get("autopilot_skipped_stuck_status_queue") or queue_status
    ticket_hint = f" ticket={waiting_ticket}" if waiting_ticket and waiting_ticket != "-" else ""
    streak_hint = f" streak={streak}" if streak else ""
    return (
        f"queue stuck on {queue}{ticket_hint}{streak_hint}; "
        "waiting ticket is not llm-ready, autopilot will not redrive"
    )


def _diagnostics_fail_skip_because(cycle_telemetry: dict[str, Any]) -> str:
    services = cycle_telemetry.get("autopilot_skipped_diagnostics_failed_services")
    if isinstance(services, list) and services:
        joined = ", ".join(str(s) for s in services)
        return (
            f"failing diagnostic services: {joined}; "
            "fix the underlying check, mark the related diagnostic "
            "ticket done, or set --no-autopilot-skip-on-diagnostics-fail"
        )
    return (
        "pre-drive diagnostics returned failed status; "
        "fix the underlying check or rerun with "
        "--no-autopilot-skip-on-diagnostics-fail"
    )


def _skip_because_for_code(
    *,
    skip_code: str,
    cycle_telemetry: dict[str, Any],
    queue_status: str,
    waiting_ticket: str,
    stagnation_streak: int,
    autopilot_ide: str,
) -> str:
    if skip_code == "chat_activity":
        return _chat_activity_skip_because(cycle_telemetry)
    if skip_code == "idle_streak":
        return _idle_streak_skip_because(stagnation_streak)
    if skip_code in _PLUGIN_SKIP_CODES:
        return _plugin_skip_because(skip_code, cycle_telemetry, autopilot_ide)
    if skip_code == "ide_mismatch":
        return f"autopilot lane ide={autopilot_ide} mismatches the foreground IDE"
    if skip_code == "idle_no_ticket":
        return "queue idle AND zero open planfile tickets"
    if skip_code == "waiting_ticket_closed":
        return _waiting_ticket_closed_skip_because(cycle_telemetry)
    if skip_code.startswith("stuck_"):
        return _stuck_skip_because(cycle_telemetry, queue_status, waiting_ticket)
    if skip_code == "diagnostics_fail":
        return _diagnostics_fail_skip_because(cycle_telemetry)
    if skip_code == "manual_send_required":
        reason = str(cycle_telemetry.get("autopilot_submit_unverified_reason") or "").strip()
        if reason:
            return reason
        return "chat text was pasted, but submit verification failed; do not redrive blindly"
    return ""


def build_decision_record(
    *,
    cycle: int,
    queue_status: str,
    waiting_ticket: str,
    stagnation_streak: int,
    autopilot_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    diag_status: str,
    wup_status: str,
    cycle_telemetry: dict[str, Any],
    next_step: str,
) -> DecisionRecord:
    """Build a :class:`DecisionRecord` from the data the orchestrator already has.

    The cycle orchestrator already collects everything we need (queue
    result, autopilot status, diagnostic + WUP results, the
    ``cycle_telemetry`` dict with skip flags). This function maps that to
    the structured trace without forcing the orchestrator to know about
    the trace internals.
    """
    skip_code = classify_skip_code(cycle_telemetry, autopilot_status)
    blocked_by = "" if skip_code in {"ok", "unknown"} else skip_code
    skip_because = _skip_because_for_code(
        skip_code=skip_code,
        cycle_telemetry=cycle_telemetry,
        queue_status=queue_status,
        waiting_ticket=waiting_ticket,
        stagnation_streak=stagnation_streak,
        autopilot_ide=autopilot_ide,
    )
    return DecisionRecord(
        at=now_utc_iso(),
        cycle=cycle,
        observed=_format_queue_observation(
            queue_status, waiting_ticket, stagnation_streak
        ),
        decided=_decide_label(autopilot_status, autopilot_drive_kind, cycle_telemetry),
        action=_action_label(autopilot_status, autopilot_backend),
        evidence=_evidence_label(
            cycle_telemetry, autopilot_backend, diag_status, wup_status, blocked_by
        ),
        next_step=next_step,
        blocked_by=blocked_by,
        skip_code=skip_code,
        skip_because=skip_because,
    )


__all__ = [
    "DECISION_TRACE_RING_SIZE",
    "DecisionRecord",
    "SKIP_CODE_DESCRIPTIONS",
    "append_decision_record",
    "build_decision_record",
    "classify_skip_code",
    "decision_trace_path",
    "human_skip_reason",
    "load_recent_decisions",
    "now_utc_iso",
]
