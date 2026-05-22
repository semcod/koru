"""koru gate — formalize advisory waivers and gate authorizations.

The c2004 session surfaced a recurring pattern: an agent runs a
*subset* of the CI gate (e.g. `task quality:regix:local` + targeted
pytest) and the human operator says "trust the advisory, proceed."
Until now this decision was recorded ad-hoc inside `outputs.notes`
strings, with no consistent shape and no easy way to query later
("which tickets were advisory-waived this sprint?").

`koru gate authorize` writes a *structured* note tagged
``KORU-GATE-AUTH`` so downstream tooling (audit reports, run-log
dashboards, sprint retrospectives) can parse the trail. The structure
is intentionally a single line of JSON inside the note string so it
works with both the existing `outputs.notes: list[str]` schema and
human-friendly `planfile ticket show` rendering.

Schema
------
::

    {
      "kind": "gate_authorization",
      "mode": "advisory" | "auto" | "mandatory_human",
      "skipped": ["task test", "task quality:gate"],
      "reason": "agent ran targeted subset; full CI deferred",
      "authorized_by": "tom",
      "authorized_at": "2026-05-11T11:24:18Z",
      "ticket": "PLF-070"
    }

PLF-koru improvement #1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GATE_AUTH_TAG = "KORU-GATE-AUTH"
"""Single-token marker that prefixes every gate-authorization note."""

VALID_MODES = ("advisory", "auto", "mandatory_human")


@dataclass(frozen=True)
class GateAuthorization:
    """Parsed gate-authorization record extracted from a ticket note."""

    mode: str
    skipped: tuple[str, ...]
    reason: str
    authorized_by: str
    authorized_at: str
    ticket: str

    def to_note(self) -> str:
        """Render the authorization as a single tagged note string."""
        payload = {
            "kind": "gate_authorization",
            "mode": self.mode,
            "skipped": list(self.skipped),
            "reason": self.reason,
            "authorized_by": self.authorized_by,
            "authorized_at": self.authorized_at,
            "ticket": self.ticket,
        }
        return f"{GATE_AUTH_TAG} {json.dumps(payload, sort_keys=True)}"


def parse_authorizations(notes: Sequence[str]) -> list[GateAuthorization]:
    """Extract all gate authorizations recorded on a ticket.

    Returns them in insertion order so callers can pick the most
    recent one with ``parse_authorizations(notes)[-1]``.
    """
    out: list[GateAuthorization] = []
    for note in notes or ():
        if not isinstance(note, str):
            continue
        if not note.startswith(f"{GATE_AUTH_TAG} "):
            continue
        try:
            payload = json.loads(note[len(GATE_AUTH_TAG) + 1 :])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("kind") != "gate_authorization":
            continue
        mode = str(payload.get("mode", ""))
        if mode not in VALID_MODES:
            continue
        skipped = payload.get("skipped") or []
        if not isinstance(skipped, list):
            continue
        out.append(
            GateAuthorization(
                mode=mode,
                skipped=tuple(str(s) for s in skipped),
                reason=str(payload.get("reason", "")),
                authorized_by=str(payload.get("authorized_by", "")),
                authorized_at=str(payload.get("authorized_at", "")),
                ticket=str(payload.get("ticket", "")),
            ),
        )
    return out


def _resolve_actor(explicit: str | None) -> str:
    """Pick a human-readable identifier for the authorizing user."""
    if explicit:
        return explicit
    # USER env var is set on every POSIX login shell; LOGNAME is the
    # POSIX fallback; agent identifier from KORU_AGENT covers cases
    # where the actor is the agent itself (rare but legal).
    for key in ("KORU_AGENT", "USER", "LOGNAME"):
        value = os.environ.get(key)
        if value:
            return value
    return "unknown"


def _planfile_base() -> list[str]:
    """Resolve the planfile CLI invocation prefix.

    Mirrors :func:`koru.planfile_queue._planfile_command` so behaviour
    stays consistent between queue execution and the gate subcommand.
    """
    configured = os.environ.get("KORU_PLANFILE_CMD")
    if configured:
        import shlex

        return shlex.split(configured)
    try:
        from importlib.util import find_spec

        if find_spec("planfile") is not None:
            return [sys.executable, "-m", "planfile.cli"]
    except Exception:  # pragma: no cover
        pass
    return ["planfile"]


def authorize_gate(
    ticket_id: str,
    *,
    mode: str,
    skipped: Sequence[str],
    reason: str,
    project: Path,
    authorized_by: str | None = None,
    runner: Callable[..., Any] | None = None,
) -> GateAuthorization:
    """Record a gate authorization on ``ticket_id`` via planfile CLI.

    Raises ``ValueError`` if the mode is unknown so the caller surfaces
    a clear error to the operator instead of silently storing junk.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"unknown gate mode {mode!r}; expected one of {VALID_MODES}")
    if not reason.strip():
        raise ValueError("--reason is required so future readers know why")

    authorization = GateAuthorization(
        mode=mode,
        skipped=tuple(s for s in skipped if s.strip()),
        reason=reason.strip(),
        authorized_by=_resolve_actor(authorized_by),
        authorized_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ticket=ticket_id,
    )

    command = [
        *_planfile_base(),
        "ticket",
        "update",
        ticket_id,
        "--note",
        authorization.to_note(),
    ]
    run = runner or subprocess.run
    result = run(command, cwd=str(project), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"planfile ticket update failed (exit {result.returncode}): "
            f"{(result.stderr or result.stdout or '').strip()}",
        )
    return authorization


__all__ = [
    "GATE_AUTH_TAG",
    "VALID_MODES",
    "GateAuthorization",
    "authorize_gate",
    "parse_authorizations",
]
