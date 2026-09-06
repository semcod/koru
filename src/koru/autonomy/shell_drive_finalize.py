"""Auto-finalize planfile tickets after a successful shell-client drive.

IDE-chat lanes submit asynchronously; shell clients return synchronously.
Transport success alone does not establish task completion. Preserve execution
output and refuse automatic closure when it explicitly reports unsuccessful work.

Policy via ``KORU_SHELL_DRIVE_AUTODONE``:

- ``verified`` (default): append the agent reply as a ticket note,
  run ``queue.post_run_verify`` commands (``koru.yaml``), then mark the
  ticket done only after successful verification. A red verify uses the existing
  policy. When no verify commands are configured the ticket is left open (note only) — an
  agent's exit code alone is not proof of done.
- ``always``: note + done without verification (trust the agent).
- ``off``: note only.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

_NOTE_TAG = "[KORU-SHELL-DRIVE]"
_MAX_NOTE_CHARS = 1500
_FINALIZE_KINDS = frozenset({"ticket_prompt", "escalation_prompt", "idle_ticket_prompt"})


def _autodone_policy() -> str:
    raw = (os.environ.get("KORU_SHELL_DRIVE_AUTODONE") or "").strip().lower()
    return raw if raw in {"verified", "always", "off"} else "verified"


_RESOLVED_STATUSES = frozenset({"done", "canceled"})


def _ticket_already_resolved(
    project: Path,
    ticket_id: str,
    *,
    runner: Callable[..., Any],
) -> bool:
    """True if some other actor already closed this ticket.

    The shell-drive lane spawns a real vendor CLI (``claude -p ...``) that
    can take minutes; by the time it returns, the same ticket may have
    already been resolved through a different path (a human, or another
    concurrent koru/agent session working the same planfile queue). Blindly
    running ``ticket done`` + verify in that case risks *reopening* work
    that was already correctly finished, just because this stale drive
    attempt's own verify run hit an unrelated failure (2026-07-05: a
    concurrent session closed a ticket while this lane's own post_run_verify
    was mid-flight and got killed, and the finalize path reopened it anyway).
    Best-effort: any lookup failure is treated as "not resolved" so the
    existing done+verify path still runs.
    """
    from koru.queue.ticket import planfile_command

    result = planfile_command(
        project,
        ["ticket", "show", ticket_id, "--format", "json"],
        runner=runner,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        import json

        data = json.loads(result.stdout)
    except (ValueError, TypeError):
        return False
    status = str(data.get("status") or "").strip().lower()
    return status in _RESOLVED_STATUSES


def provider_switch_note(reply: dict[str, Any]) -> str | None:
    """Ticket-visible record of an autonomous LLM-provider fallback.

    The tillm drive payload carries ``provider`` (the one that actually
    served the drive) and ``provider_attempts`` (the configured queue). When
    the winner is not the queue's first choice, the earlier providers were
    unavailable — typically an exhausted limit (429/402) — and koru switched
    autonomously. The operator only sees the loop's stdout if they are
    watching, so the ticket itself must say what happened and how to change
    the queue.
    """
    used = str(reply.get("provider") or "").strip()
    attempts = [
        str(item).strip()
        for item in (reply.get("provider_attempts") or ())
        if str(item).strip()
    ]
    if not used or len(attempts) < 2 or attempts[0] == used:
        return None
    skipped = attempts[: attempts.index(used)] if used in attempts else attempts[:1]
    return (
        f"{_NOTE_TAG} provider-switch: {' → '.join([*skipped, used])} — "
        f"{', '.join(repr(p) for p in skipped)} unavailable/exhausted (limit?), "
        f"koru autonomously drove this ticket with {used!r}. "
        "Re-prioritize with `tillm provider order …` or TILLM_PROVIDER_ORDER."
    )


# (project, ticket_id, attempts-signature) tuples already noted by this loop
# process — a failed drive is retried every cycle and must not spam the ticket.
_EXHAUSTION_NOTED: set[tuple[str, str, str]] = set()


def note_provider_exhaustion(
    *,
    project: Path,
    ticket_id: str,
    reply: dict[str, Any],
    _hp: Callable[..., Any],
) -> str:
    """Record on the ticket that the whole provider queue was exhausted.

    ``provider_switch_note`` covers the *successful* fallback; this covers the
    drive that failed after every attempt (429/402/credits on each provider).
    The loop keeps retrying, so the note is written once per loop process per
    attempts-signature. Returns the action taken for telemetry.
    """
    if not ticket_id or ticket_id == "-":
        return "skipped"
    attempts = [
        str(item).strip()
        for item in (reply.get("provider_attempts") or ())
        if str(item).strip()
    ]
    if not attempts:
        return "skipped"
    try:
        from koru.tillm_bridge import ensure_local_tillm_path

        ensure_local_tillm_path()
        from tillm.providers import is_provider_exhaustion
    except ImportError:
        return "skipped"
    if not is_provider_exhaustion(
        stdout=str(reply.get("stdout") or ""),
        stderr=str(reply.get("stderr") or ""),
        message=str(reply.get("message") or ""),
    ):
        return "skipped"
    key = (str(project.resolve()), ticket_id, ",".join(attempts))
    if key in _EXHAUSTION_NOTED:
        return "already_noted"
    note = (
        f"{_NOTE_TAG} provider-exhausted: tried {' → '.join(attempts)} — every "
        "provider in the queue was unavailable/exhausted (limits/credits); the "
        "drive failed and this ticket stays open. Add a provider token "
        "(`tillm provider set …`) or re-prioritize (`tillm provider order …`)."
    )
    _hp(f"  shell-drive: {note}")
    from koru.queue.runners import run_process
    from koru.queue.ticket import planfile_command

    result = planfile_command(
        project,
        ["ticket", "update", ticket_id, "--note", note],
        runner=run_process,
    )
    if result.returncode != 0:
        return "note_failed"
    _EXHAUSTION_NOTED.add(key)
    return "noted_exhaustion"


def _reply_note(reply: dict[str, Any]) -> str:
    message = reply.get("stdout") or reply.get("output") or reply.get("message") or ""
    if isinstance(message, bytes):
        message = message.decode("utf-8", errors="replace")
    text = str(message).strip()
    if len(text) > _MAX_NOTE_CHARS:
        text = text[:_MAX_NOTE_CHARS] + " …[truncated]"
    client = str(reply.get("client_id") or reply.get("backend") or "shell")
    provider = str(reply.get("provider") or "").strip()
    provider_part = f" provider={provider}" if provider else ""
    header = f"{_NOTE_TAG} client={client}{provider_part} ok=true"
    body = text if text else "(no output captured)"
    note = f"{header}\n{body}" if text else f"{header} {body}"
    switch = provider_switch_note(reply)
    return f"{note}\n{switch}" if switch else note



def _reports_unsuccessful_work(reply: dict[str, Any]) -> bool:
    """Negative execution evidence vetoes auto-done; prose never proves success."""
    text = "\n".join(
        value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
        for key in ("stdout", "output", "message", "stderr")
        if (value := reply.get(key))
    )
    return bool(re.search(
        r"\b(?:no files (?:were )?modified|no changes (?:were )?made|"
        r"(?:edit|write) permission denied|permission denied (?:for|to) (?:edit|write))\b",
        text, flags=re.IGNORECASE,
    ))

def _eligible_for_finalize(
    *,
    ok: bool,
    ticket_id: str,
    decision_kind: str | None,
    autopilot_ide: str,
) -> bool:
    if not ok or not ticket_id:
        return False
    if (decision_kind or "") not in _FINALIZE_KINDS:
        return False
    try:
        from koru.tillm_bridge import shell_drive_client_id

        return bool(shell_drive_client_id(autopilot_ide))
    except Exception:
        return False


def _load_verify_config_or_skip(
    project: Path,
    ticket_id: str,
    *,
    _hp: Callable[..., Any],
) -> tuple[Any | None, str | None]:
    """Return ``(config, early_action)``. Early action is set when finalize should stop."""
    try:
        from koru.autonomy.post_run_verify import load_post_run_verify_config

        verify_config = load_post_run_verify_config(project)
    except Exception:
        verify_config = None
    if verify_config is None or not verify_config.enabled or not verify_config.commands:
        _hp(
            f"  shell-drive finalize: {ticket_id} left open — no queue.post_run_verify "
            "commands in koru.yaml (set KORU_SHELL_DRIVE_AUTODONE=always to trust the agent)",
        )
        return None, "noted"
    return verify_config, None


def _mark_done(
    project: Path,
    ticket_id: str,
    *,
    runner: Callable[..., Any],
    planfile_command: Callable[..., Any],
    _hp: Callable[..., Any],
) -> bool:
    done = planfile_command(project, ["ticket", "done", ticket_id], runner=runner)
    if done.returncode != 0:
        _hp(f"  shell-drive finalize: ticket done failed for {ticket_id} (rc={done.returncode})")
        return False
    return True


def _run_pre_done_verify(
    project: Path,
    ticket_id: str,
    *,
    verify_config: Any,
    runner: Callable[..., Any],
    _hp: Callable[..., Any],
) -> str:
    from koru.autonomy.post_run_verify import verify_completed_tickets

    # shell_runner deliberately omitted: the default sanitized runner strips
    # the loop's KORU_*/TILLM_*/VDISPLAY_* env, which otherwise flips
    # env-sensitive test branches and bounces finished tickets.
    outcomes = verify_completed_tickets(
        project,
        [ticket_id],
        config=verify_config,
        planfile_runner=runner,
    )
    if len(outcomes) != 1 or outcomes[0].get("ticket_id") != ticket_id:
        _hp(f"  shell-drive finalize: {ticket_id} verification receipt missing or mismatched")
        return "verify_failed:missing_receipt"
    failed = [o for o in outcomes if not o.get("ok")]
    if failed:
        action = str(failed[0].get("action") or "reopened")
        _hp(
            f"  shell-drive finalize: {ticket_id} verify FAILED → {action} "
            "(agent work did not pass post_run_verify)",
        )
        return f"verify_failed:{action}"
    return "verified"


def finalize_shell_drive_ticket(
    *,
    project: Path,
    autopilot_ide: str,
    ticket_id: str,
    reply: dict[str, Any],
    ok: bool,
    decision_kind: str | None,
    _hp: Callable[..., Any],
) -> str:
    """Best-effort ticket finalization; returns the action taken for telemetry."""
    if not _eligible_for_finalize(
        ok=ok,
        ticket_id=ticket_id,
        decision_kind=decision_kind,
        autopilot_ide=autopilot_ide,
    ):
        return "skipped"

    policy = _autodone_policy()
    from koru.queue.runners import run_process
    from koru.queue.ticket import planfile_command

    if _ticket_already_resolved(project, ticket_id, runner=run_process):
        _hp(
            f"  shell-drive finalize: {ticket_id} already resolved (done/canceled) by "
            "another actor — skipping done+verify to avoid reopening finished work",
        )
        return "already_resolved"

    if switch := provider_switch_note(reply):
        _hp(f"  shell-drive: {switch}")
    planfile_command(
        project,
        ["ticket", "update", ticket_id, "--note", _reply_note(reply)],
        runner=run_process,
    )
    if policy == "off":
        _hp(f"  shell-drive finalize: note appended to {ticket_id} (autodone=off)")
        return "noted"

    if _reports_unsuccessful_work(reply):
        _hp(f"  shell-drive finalize: {ticket_id} left open — execution reports unsuccessful work")
        return "noted_unsuccessful"

    if policy == "verified":
        verify_config, early = _load_verify_config_or_skip(project, ticket_id, _hp=_hp)
        if early is not None:
            return early
        verification = _run_pre_done_verify(
            project, ticket_id, verify_config=verify_config, runner=run_process, _hp=_hp,
        )
        if verification != "verified":
            return verification

    if not _mark_done(
        project,
        ticket_id,
        runner=run_process,
        planfile_command=planfile_command,
        _hp=_hp,
    ):
        return "done_failed"

    if policy == "always":
        _hp(f"  shell-drive finalize: {ticket_id} marked done (autodone=always)")
        return "done"

    _hp(f"  shell-drive finalize: {ticket_id} done + verified green")
    return "done_verified"



__all__ = [
    "finalize_shell_drive_ticket",
    "note_provider_exhaustion",
    "provider_switch_note",
]
