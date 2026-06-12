"""Repair reaction policy for ``koru autopilot drive`` failures."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DriveRepairReaction:
    fallback_to_direct: bool
    reason: str
    action: str = "none"
    recent_direct_fallbacks: int = 0


_SEMANTIC_BLOCK_MARKERS = (
    "refusing blind keyboard",
    "vdisplay/imgl did not confirm",
)


def daemon_reply_blocks_direct_fallback(reply: dict[str, Any] | None) -> bool:
    """True when the daemon explicitly refused blind keyboard/OS-injector fallback."""
    if not reply:
        return False
    backend = str(reply.get("backend") or "").strip().lower()
    if backend == "semantic_required":
        return True
    message = str(reply.get("message") or "").lower()
    return any(marker in message for marker in _SEMANTIC_BLOCK_MARKERS)


def _primary_hypothesis_id(status: Any) -> str:
    hypotheses = getattr(status, "hypotheses", None)
    if not isinstance(hypotheses, list) or not hypotheses:
        return "ready" if bool(getattr(status, "ready", False)) else "bridge_not_ready"
    first = hypotheses[0]
    return str(getattr(first, "id", None) or "bridge_not_ready")


def _recent_direct_fallback_count(recent_events: Sequence[Any]) -> int:
    count = 0
    for event in recent_events:
        payload = getattr(event, "payload", {}) or {}
        actions = payload.get("actions") if isinstance(payload, dict) else None
        if (
            isinstance(actions, list)
            and "drive reaction: switch to local direct injection" in actions
        ):
            count += 1
    return count


def decide_drive_repair_reaction(
    status: Any,
    *,
    require_plugin: bool,
    recent_events: Sequence[Any] = (),
    drive_reply: dict[str, Any] | None = None,
) -> DriveRepairReaction:
    """Choose how a failed daemon drive should react to bridge diagnostics."""
    primary = _primary_hypothesis_id(status)
    recent_direct = _recent_direct_fallback_count(recent_events)
    if daemon_reply_blocks_direct_fallback(drive_reply):
        return DriveRepairReaction(
            fallback_to_direct=False,
            reason=(
                "daemon blocked blind keyboard fallback (semantic drive required); "
                f"bridge diagnostic: {primary}"
            ),
            action="semantic_required",
            recent_direct_fallbacks=recent_direct,
        )
    if bool(getattr(status, "ready", False)):
        return DriveRepairReaction(
            fallback_to_direct=False,
            reason=f"bridge diagnostic: {primary}",
            action="none",
            recent_direct_fallbacks=recent_direct,
        )
    if require_plugin:
        return DriveRepairReaction(
            fallback_to_direct=False,
            reason=f"bridge diagnostic: {primary}; require_plugin=true",
            action="manual_reconnect_required",
            recent_direct_fallbacks=recent_direct,
        )
    if not bool(getattr(status, "plugins_connected", False)):
        return DriveRepairReaction(
            fallback_to_direct=True,
            reason=f"bridge diagnostic: {primary}; recent_direct_fallbacks={recent_direct}",
            action="direct_fallback",
            recent_direct_fallbacks=recent_direct,
        )
    if not bool(getattr(status, "plugins_compatible", False)):
        return DriveRepairReaction(
            fallback_to_direct=True,
            reason=f"bridge diagnostic: {primary}; recent_direct_fallbacks={recent_direct}",
            action="direct_fallback",
            recent_direct_fallbacks=recent_direct,
        )
    return DriveRepairReaction(
        fallback_to_direct=False,
        reason=f"bridge diagnostic: {primary}",
        action="none",
        recent_direct_fallbacks=recent_direct,
    )


__all__ = [
    "DriveRepairReaction",
    "daemon_reply_blocks_direct_fallback",
    "decide_drive_repair_reaction",
]
