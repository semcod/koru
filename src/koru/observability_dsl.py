"""Koru observability event DSL v1.

The JSONL event store is the source of truth.  This module only renders and
parses a compact, human-readable view of the same event envelope.
"""

from __future__ import annotations

import json
import shlex
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from koru.cqrs.event_store import StoredEvent

DSL_VERSION = "koru.obs.v1"
OBSERVABILITY_CONTEXT = "observability"

_KIND_TO_KEYWORD = {
    "control.command": "command",
    "autopilot.intent": "intent",
    "autopilot.route.decision": "decision",
    "autopilot.drive.requested": "action",
    "autopilot.drive.phase": "phase",
    "autopilot.drive.verified": "verify",
    "autopilot.drive.failed": "failure",
    "autonomy.blocker": "blocker",
    "autonomy.next": "next",
    "autonomy.summary": "result",
}
_KEYWORD_TO_KIND = {value: key for key, value in _KIND_TO_KEYWORD.items()}


@dataclass(frozen=True)
class KoruObsEvent:
    """Structured observability event used by autopilot and autonomy traces."""

    corr: str
    component: str
    kind: str
    ts: str | None = None
    session: str | None = None
    cycle: int | None = None
    ticket: str | None = None
    actor: str | None = None
    severity: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def keyword(self) -> str:
        return kind_to_keyword(self.kind)

    def payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "corr": self.corr,
            "component": self.component,
            "kind": self.kind,
            "data": dict(self.data),
        }
        for key in ("ts", "session", "cycle", "ticket", "actor", "severity"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload

    def to_dsl(self) -> str:
        return render_observability_dsl(self)

    @classmethod
    def from_stored_event(cls, event: StoredEvent) -> KoruObsEvent:
        payload = dict(event.payload)
        return cls(
            ts=str(payload.get("ts") or event.occurred_at),
            corr=str(payload.get("corr") or event.aggregate_id or event.event_id),
            component=str(payload.get("component") or ""),
            kind=str(payload.get("kind") or event.event_type),
            session=_optional_str(payload.get("session")),
            cycle=_optional_int(payload.get("cycle")),
            ticket=_optional_str(payload.get("ticket")),
            actor=_optional_str(payload.get("actor")),
            severity=_optional_str(payload.get("severity")),
            data=dict(payload.get("data") or {}),
        )


def kind_to_keyword(kind: str) -> str:
    return _KIND_TO_KEYWORD.get(kind, kind.rsplit(".", 1)[-1].replace("-", "_"))


def keyword_to_kind(keyword: str) -> str:
    return _KEYWORD_TO_KIND.get(keyword, keyword)


def render_observability_dsl(event: KoruObsEvent) -> str:
    header = [f"@{event.ts}" if event.ts else "@-"]
    header.append(f"version={_quote(DSL_VERSION)}")
    header.append(f"corr={_quote(event.corr)}")
    if event.session:
        header.append(f"session={_quote(event.session)}")
    if event.cycle is not None:
        header.append(f"cycle={event.cycle}")
    if event.ticket:
        header.append(f"ticket={_quote(event.ticket)}")
    header.append(f"component={_quote(event.component)}")
    if event.actor:
        header.append(f"actor={_quote(event.actor)}")
    if event.severity:
        header.append(f"severity={_quote(event.severity)}")

    statement = [event.keyword]
    for key in sorted(event.data):
        value = event.data[key]
        if value is None:
            continue
        statement.append(f"{key}={_quote(value)}")
    return " ".join(header) + "\n" + " ".join(statement)


def parse_observability_dsl(text: str) -> KoruObsEvent:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("observability DSL record must contain a header and one statement")
    header_raw, statement_raw = lines
    if not header_raw.startswith("@"):
        raise ValueError("observability DSL header must start with '@'")

    header_parts = shlex.split(header_raw)
    ts = header_parts[0][1:]
    meta = _parse_pairs(header_parts[1:])
    statement_parts = shlex.split(statement_raw)
    if not statement_parts:
        raise ValueError("observability DSL statement is empty")
    keyword = statement_parts[0]
    data = _parse_pairs(statement_parts[1:])

    return KoruObsEvent(
        ts=None if ts == "-" else ts,
        corr=str(meta.get("corr") or ""),
        session=_optional_str(meta.get("session")),
        cycle=_optional_int(meta.get("cycle")),
        ticket=_optional_str(meta.get("ticket")),
        component=str(meta.get("component") or ""),
        actor=_optional_str(meta.get("actor")),
        severity=_optional_str(meta.get("severity")),
        kind=keyword_to_kind(keyword),
        data=data,
    )


def stored_event_to_dsl(event: StoredEvent) -> str:
    return KoruObsEvent.from_stored_event(event).to_dsl()


def render_compact_observability_line(event: KoruObsEvent) -> str:
    """Render one human-scannable terminal line for an observability event."""
    return f"[{_compact_time(event.ts)}] koru ▸ OBS: {render_compact_observability_message(event)}"


def render_compact_observability_message(event: KoruObsEvent) -> str:
    """Render the compact OBS payload without timestamp/log prefix."""
    meta: list[str] = []
    if event.session:
        meta.append(f"session={_quote(event.session)}")
    meta.append(f"corr={_quote(event.corr)}")
    if event.cycle is not None:
        meta.append(f"cycle={event.cycle}")
    if event.ticket:
        meta.append(f"ticket={_quote(event.ticket)}")
    meta.append(f"component={_quote(event.component)}")
    if event.severity:
        meta.append(f"severity={_quote(event.severity)}")
    statement = [event.keyword]
    for key, value in _compact_data(event).items():
        if value is not None:
            statement.append(f"{key}={_quote(value)}")
    return " ".join([*meta, *statement])


def stored_event_to_compact_line(event: StoredEvent) -> str:
    return render_compact_observability_line(KoruObsEvent.from_stored_event(event))


def render_observability_path(events: Iterable[KoruObsEvent | StoredEvent]) -> str:
    """Render a one-line semantic path for a trace."""
    steps = [_path_step(_as_obs_event(event)) for event in events]
    visible = [step for step in steps if step]
    if not visible:
        return "OBS"
    return "OBS " + " -> ".join(visible)


def _as_obs_event(event: KoruObsEvent | StoredEvent) -> KoruObsEvent:
    if isinstance(event, KoruObsEvent):
        return event
    return KoruObsEvent.from_stored_event(event)


def _path_step(event: KoruObsEvent) -> str:
    data = event.data
    if event.kind == "control.command":
        surface = str(data.get("surface") or "control")
        operation = str(data.get("operation") or "").strip()
        return f"command({surface} {operation})" if operation else f"command({surface})"
    if event.kind == "autopilot.intent":
        goal = str(data.get("goal") or "intent")
        return f"intent({goal})"
    if event.kind == "autopilot.route.decision":
        chosen = data.get("chosen") or data.get("route") or data.get("transport")
        return f"decision({chosen})" if chosen else "decision"
    if event.kind == "autopilot.drive.requested":
        name = str(data.get("name") or "drive")
        return f"action({name})"
    if event.kind == "autopilot.drive.phase":
        name = str(data.get("name") or "phase")
        status = str(data.get("status") or "").strip()
        return f"phase({name} {status})" if status else f"phase({name})"
    if event.kind == "autopilot.drive.verified":
        name = str(data.get("name") or "submit")
        status = str(data.get("status") or "ok")
        return f"verify({name} {status})"
    if event.kind == "autopilot.drive.failed":
        code = str(data.get("code") or "failed")
        return f"failure({code})"
    if event.kind == "autonomy.blocker":
        name = str(data.get("name") or "blocked")
        return f"blocker({name})"
    if event.kind == "autonomy.next":
        action = str(data.get("action") or "next")
        return f"next({action})"
    if event.kind == "autonomy.summary":
        status = str(data.get("status") or data.get("outcome") or "result")
        return f"result({status})"
    return ""


def _compact_data(event: KoruObsEvent) -> dict[str, Any]:
    data = dict(event.data)
    if event.kind == "autopilot.intent":
        return _pick(data, "goal", "target", "ide", "submit", "require_plugin", "chars")
    if event.kind == "autopilot.route.decision":
        return _pick(
            data,
            "name",
            "chosen",
            "because",
            "transport",
            "plugin_fd",
            "cli_fd",
            "protocol",
        )
    if event.kind == "autopilot.drive.requested":
        return _pick(data, "name", "transport", "ide", "submit", "chars")
    if event.kind == "autopilot.drive.phase":
        return _pick(data, "name", "status", "transport", "ide")
    if event.kind == "autopilot.drive.verified":
        return _pick(data, "name", "status", "ide", "delivered", "submitted", "backend")
    if event.kind == "autopilot.drive.failed":
        return _pick(data, "code", "message", "verification", "ide", "delivered", "submitted")
    if event.kind == "autonomy.blocker":
        return _pick(data, "name", "because", "ide", "status")
    if event.kind == "autonomy.next":
        return _pick(data, "action", "ide", "decision_kind")
    if event.kind == "control.command":
        return _pick(
            data,
            "surface",
            "interface_id",
            "transport",
            "operation",
            "target",
            "replayable",
        )
    return data


def _pick(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: data[key] for key in keys if key in data}


def _compact_time(value: str | None) -> str:
    if not value:
        return "--:--:--"
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(UTC).strftime("%H:%M:%S")
    except ValueError:
        if "T" in value:
            value = value.rsplit("T", 1)[-1]
        return value[:8] if value else "--:--:--"


def _parse_pairs(parts: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            raise ValueError(f"invalid DSL pair: {part!r}")
        key, raw = part.split("=", 1)
        parsed[key] = _parse_scalar(raw)
    return parsed


def _parse_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith(("{", "[")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _quote(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, (dict, list)):
        return shlex.quote(json.dumps(value, ensure_ascii=True, separators=(",", ":")))
    text = str(value)
    if not text:
        return '""'
    if any(ch.isspace() or ch in '"=;' for ch in text):
        return json.dumps(text, ensure_ascii=True)
    return text


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DSL_VERSION",
    "OBSERVABILITY_CONTEXT",
    "KoruObsEvent",
    "kind_to_keyword",
    "keyword_to_kind",
    "parse_observability_dsl",
    "render_compact_observability_line",
    "render_compact_observability_message",
    "render_observability_dsl",
    "render_observability_path",
    "stored_event_to_compact_line",
    "stored_event_to_dsl",
]
