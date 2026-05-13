"""Versioned NDJSON records for koru orchestration (autonomous loop, …)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any, TextIO

KORU_STDIO_EVENT_SCHEMA_VERSION = "1.0"


def iso_ts() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_stdio_event(
    stream: TextIO,
    *,
    event_type: str,
    correlation_id: str,
    payload: dict[str, Any],
    command: str | None = None,
    schema_version: str = KORU_STDIO_EVENT_SCHEMA_VERSION,
) -> None:
    row: dict[str, Any] = {
        "type": event_type,
        "schema_version": schema_version,
        "ts": iso_ts(),
        "correlation_id": correlation_id,
        "payload": payload,
    }
    if command is not None:
        row["command"] = command
    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    stream.flush()


def default_stdio_format_from_env() -> str:
    raw = (os.environ.get("KORU_STDIO_FORMAT") or "human").strip().lower()
    return raw if raw in {"human", "jsonl"} else "human"


__all__ = [
    "KORU_STDIO_EVENT_SCHEMA_VERSION",
    "default_stdio_format_from_env",
    "iso_ts",
    "write_stdio_event",
]
