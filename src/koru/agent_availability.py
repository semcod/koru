"""Durable operational availability for IDE and shell agents.

Installation detection answers whether an agent *can* be used.  This module
tracks whether it *should* be used now, for example after an account quota is
exhausted.  The registry is machine-global because provider/account limits are
not project state.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import time
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REGISTRY_VERSION = 1
_DEFAULT_RATE_LIMIT_RETRY_SECONDS = 15 * 60

_HARD_LIMIT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:usage|monthly|daily|weekly|credit|token)\s+(?:quota|limit)\s+"
        r"(?:has\s+been\s+|is\s+)?(?:reached|exceeded|exhausted)\b",
        r"\b(?:quota|credits?)\s+(?:has\s+been\s+|have\s+been\s+|is\s+|are\s+)?"
        r"(?:reached|exceeded|exhausted|depleted)\b",
        r"\b(?:no|not enough|insufficient)\s+(?:credits?|quota)\b",
        r"\b(?:you(?:'ve| have)?\s+)?hit\s+(?:your\s+|the\s+)?(?:usage\s+)?limit\b",
        r"\b(?:you\s+)?(?:have\s+)?(?:reached|exceeded|exhausted)\s+"
        r"(?:your\s+|the\s+)?(?:usage\s+|credit\s+|token\s+)?(?:limit|quota|credits?)\b",
        r"\b(?:0|zero)\s+(?:weighted\s+)?(?:tokens?|credits?)\s+(?:left|remaining)\b",
        r"\b(?:limit|quota)\s+(?:zosta[łl]a?\s+)?wyczerpan(?:y|a|e)\b",
        r"\bbrak\s+(?:dost[eę]pnych\s+)?(?:kredyt[oó]w|limitu)\b",
    )
)
_RATE_LIMIT_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brate[ -]?limit(?:ed|ing)?\b",
        r"\btoo many requests\b",
        r"(?:^|\D)429(?:\D|$)",
    )
)


def normalize_agent_id(raw: str) -> str:
    """Return a stable registry key for a user- or runtime-provided agent id."""
    normalized = raw.strip().lower().replace(" ", "-")
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in normalized).strip("-")


def availability_registry_path() -> Path:
    explicit = os.environ.get("KORU_AGENT_AVAILABILITY_FILE", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    root = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return root / "koru" / "agent-availability.json"


@dataclass(frozen=True)
class AgentAvailability:
    agent_id: str
    status: str = "unknown"
    reason: str = ""
    source: str = ""
    observed_at: float = 0.0
    retry_after: float | None = None

    @property
    def blocked(self) -> bool:
        return self.status == "unavailable"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AvailabilitySignal:
    reason: str
    retry_after_seconds: float | None = None


def _env_ids(name: str) -> set[str]:
    return {
        normalized
        for raw in os.environ.get(name, "").split(",")
        if (normalized := normalize_agent_id(raw))
    }


def _read_registry() -> dict[str, dict[str, Any]]:
    path = availability_registry_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("agents"), dict):
        return {}
    return {
        str(key): value
        for key, value in payload["agents"].items()
        if isinstance(value, dict)
    }


def _write_registry(agents: Mapping[str, Mapping[str, Any]]) -> None:
    path = availability_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    payload = {"version": _REGISTRY_VERSION, "agents": dict(sorted(agents.items()))}
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


@contextmanager
def _registry_write_lock() -> Iterator[None]:
    """Serialize updates from concurrent autonomous lanes on the same machine."""
    path = availability_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        lock_path.chmod(0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def get_agent_availability(agent_id: str, *, now: float | None = None) -> AgentAvailability:
    """Return effective availability, including environment overrides and expiry."""
    normalized = normalize_agent_id(agent_id)
    if not normalized:
        return AgentAvailability(agent_id="", reason="empty_agent_id")
    if normalized in _env_ids("KORU_AGENT_AVAILABLE"):
        return AgentAvailability(
            agent_id=normalized,
            status="available",
            reason="environment override",
            source="env:KORU_AGENT_AVAILABLE",
        )
    if normalized in _env_ids("KORU_AGENT_UNAVAILABLE"):
        return AgentAvailability(
            agent_id=normalized,
            status="unavailable",
            reason="environment override",
            source="env:KORU_AGENT_UNAVAILABLE",
        )

    raw = _read_registry().get(normalized)
    if raw is None:
        return AgentAvailability(agent_id=normalized)
    try:
        availability = AgentAvailability(
            agent_id=normalized,
            status=str(raw.get("status") or "unknown"),
            reason=str(raw.get("reason") or ""),
            source=str(raw.get("source") or "registry"),
            observed_at=float(raw.get("observed_at") or 0.0),
            retry_after=(
                float(raw["retry_after"])
                if raw.get("retry_after") is not None
                else None
            ),
        )
    except (TypeError, ValueError):
        return AgentAvailability(agent_id=normalized, reason="invalid_registry_entry")
    current = time.time() if now is None else now
    if availability.blocked and availability.retry_after is not None:
        if availability.retry_after <= current:
            return AgentAvailability(
                agent_id=normalized,
                reason="temporary block expired",
                source=availability.source,
                observed_at=availability.observed_at,
            )
    return availability


def set_agent_availability(
    agent_id: str,
    *,
    status: str,
    reason: str,
    source: str,
    retry_after: float | None = None,
    now: float | None = None,
) -> AgentAvailability:
    normalized = normalize_agent_id(agent_id)
    if not normalized:
        raise ValueError("agent id must not be empty")
    if status not in {"available", "unavailable", "unknown"}:
        raise ValueError(f"unsupported availability status: {status}")
    availability = AgentAvailability(
        agent_id=normalized,
        status=status,
        reason=reason.strip(),
        source=source.strip() or "manual",
        observed_at=time.time() if now is None else now,
        retry_after=retry_after,
    )
    with _registry_write_lock():
        agents = _read_registry()
        agents[normalized] = availability.to_dict()
        _write_registry(agents)
    return availability


def block_agent(
    agent_id: str,
    *,
    reason: str,
    source: str = "manual",
    retry_after_seconds: float | None = None,
    now: float | None = None,
) -> AgentAvailability:
    observed_at = time.time() if now is None else now
    retry_after = (
        observed_at + max(0.0, retry_after_seconds)
        if retry_after_seconds is not None
        else None
    )
    return set_agent_availability(
        agent_id,
        status="unavailable",
        reason=reason,
        source=source,
        retry_after=retry_after,
        now=observed_at,
    )


def clear_agent_block(agent_id: str, *, source: str = "manual") -> AgentAvailability:
    return set_agent_availability(
        agent_id,
        status="available",
        reason="availability restored",
        source=source,
    )


def classify_unavailability(text: str) -> AvailabilitySignal | None:
    """Recognize only high-confidence quota/rate-limit failures."""
    compact = " ".join(text.split())
    if not compact:
        return None
    if any(pattern.search(compact) for pattern in _HARD_LIMIT_PATTERNS):
        return AvailabilitySignal(reason="usage_limit_exhausted")
    if any(pattern.search(compact) for pattern in _RATE_LIMIT_PATTERNS):
        try:
            retry_seconds = float(
                os.environ.get(
                    "KORU_AGENT_RATE_LIMIT_RETRY_SECONDS",
                    str(_DEFAULT_RATE_LIMIT_RETRY_SECONDS),
                )
            )
        except ValueError:
            retry_seconds = float(_DEFAULT_RATE_LIMIT_RETRY_SECONDS)
        return AvailabilitySignal(
            reason="rate_limit",
            retry_after_seconds=max(0.0, retry_seconds),
        )
    return None


def _event_text(event: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "text",
        "message",
        "error",
        "reason",
        "detail",
        "summary",
        "stderr",
        "output",
    ):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    data = event.get("data")
    if isinstance(data, Mapping):
        nested = _event_text(data)
        if nested:
            parts.append(nested)
    return "\n".join(parts)


def learn_unavailability_from_events(
    agent_id: str,
    events: Iterable[Mapping[str, Any]],
) -> AgentAvailability | None:
    """Persist a limit response emitted by the selected agent, if unambiguous."""
    for event in events:
        if str(event.get("type") or "") != "message.received":
            continue
        signal = classify_unavailability(_event_text(event))
        if signal is not None:
            return block_agent(
                agent_id,
                reason=signal.reason,
                source="autopilot:message.received",
                retry_after_seconds=signal.retry_after_seconds,
            )
    return None


def learn_unavailability_from_reply(
    agent_id: str,
    reply: Mapping[str, Any],
) -> AgentAvailability | None:
    """Persist a limit reported directly in a failed drive response."""
    signal = classify_unavailability(_event_text(reply))
    if signal is None:
        return None
    return block_agent(
        agent_id,
        reason=signal.reason,
        source="autopilot:drive_failure",
        retry_after_seconds=signal.retry_after_seconds,
    )
