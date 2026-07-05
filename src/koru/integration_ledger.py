"""Append-only integration action ledger and compact DSL lines."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from koru.activity_log import activity

DSL_VERSION = "koru.integration.v1"


def integration_ledger_path(project: Path | None = None) -> Path:
    raw = os.environ.get("KORU_INTEGRATION_LEDGER_PATH", "").strip()
    if raw:
        return Path(raw).expanduser()
    root = project or Path.cwd()
    return root / ".planfile" / ".koru" / "integration-actions.jsonl"


def _json_default(value: Any) -> str:
    """Degrade non-JSON values instead of raising.

    Drive replies can carry raw ``bytes`` (vendor CLI stdout) and arbitrary
    assessment objects; a telemetry ledger must never crash the autonomous
    loop over an unserializable payload.
    """
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return repr(value)


def _quote(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if any(ch.isspace() or ch in '"=;' for ch in text):
        return json.dumps(text, ensure_ascii=False)
    return text


def integration_dsl(
    *,
    action: str,
    intent: str,
    target: str,
    outcome: str,
    actor: str = "koru",
    transport: str = "",
    phase: str = "",
    attempt: int | None = None,
    evidence: str = "",
    reason: str = "",
    next_step: str = "",
) -> str:
    """Return one compact DSL line for a human/operator timeline."""
    parts = [
        DSL_VERSION,
        f"action={_quote(action)}",
        f"intent={_quote(intent)}",
        f"actor={_quote(actor)}",
        f"target={_quote(target)}",
        f"outcome={_quote(outcome)}",
    ]
    optional: dict[str, Any] = {
        "transport": transport,
        "phase": phase,
        "attempt": attempt,
        "reason": reason,
        "evidence": evidence,
        "next": next_step,
    }
    for key, value in optional.items():
        if value not in (None, ""):
            parts.append(f"{key}={_quote(value)}")
    return " ".join(parts)


def record_integration_action(
    *,
    project: Path | None = None,
    action: str,
    intent: str,
    target: str,
    outcome: str,
    actor: str = "koru",
    transport: str = "",
    phase: str = "",
    attempt: int | None = None,
    evidence: str = "",
    reason: str = "",
    next_step: str = "",
    data: dict[str, Any] | None = None,
    emit_activity: bool = True,
) -> str:
    """Append a JSONL record and optionally emit its DSL line to activity log."""
    line = integration_dsl(
        action=action,
        intent=intent,
        actor=actor,
        target=target,
        transport=transport,
        phase=phase,
        attempt=attempt,
        outcome=outcome,
        reason=reason,
        evidence=evidence,
        next_step=next_step,
    )
    payload = {
        "ts": time.time(),
        "dsl": line,
        "action": action,
        "intent": intent,
        "actor": actor,
        "target": target,
        "transport": transport,
        "phase": phase,
        "attempt": attempt,
        "outcome": outcome,
        "reason": reason,
        "evidence": evidence,
        "next": next_step,
        "data": data or {},
    }
    path = integration_ledger_path(project)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_default)
                + "\n"
            )
    except (OSError, TypeError, ValueError):
        # Best-effort ledger: a circular/unserializable payload must not
        # take the autonomous loop down (2026-07-05: bytes in a drive reply
        # killed `koru autonomous up` mid-cycle).
        pass
    if emit_activity:
        activity("INTEGRATION", line, data=payload)
    return line


__all__ = [
    "DSL_VERSION",
    "integration_dsl",
    "integration_ledger_path",
    "record_integration_action",
]
