"""Secret-free routing receipts and read-only projections of observed models."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.task_model_policy import safe_identifier

_ROUTING_FIELDS = {"request_id", "ticket", "client", "requested_model", "reason", "status"}


def routing_path(project: Path) -> Path:
    return project / ".planfile" / ".koru" / "model-routing.jsonl"


def append_routing_event(project: Path, event: dict[str, Any]) -> bool:
    row: dict[str, Any] = {key: safe_identifier(event.get(key)) for key in _ROUTING_FIELDS}
    row["timestamp"] = datetime.now(UTC).isoformat(timespec="milliseconds")
    if type(event.get("duration_ms")) is int:
        row["duration_ms"] = max(0, event["duration_ms"])
    try:
        path = routing_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.write(fd, (json.dumps(row) + "\n").encode())
        finally:
            os.close(fd)
        return True
    except OSError:
        return False  # Observability never retries a paid call or changes its outcome.


def _routing_history(project: Path, limit: int) -> list[dict[str, Any]]:
    try:
        with routing_path(project).open("rb") as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 262144))
            lines = stream.read().splitlines()
        rows = []
        for line in lines:
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    continue
                row = {key: safe_identifier(event.get(key)) for key in _ROUTING_FIELDS}
                row["timestamp"] = _timestamp(event.get("timestamp"))
                row["duration_ms"] = _count(event.get("duration_ms"))
                rows.append(row)
            except (ValueError, TypeError):
                continue
        return rows[-limit:][::-1]
    except OSError:
        return []


def _timestamp(value: Any) -> str:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.astimezone(UTC).isoformat() if stamp.tzinfo else ""
    except (TypeError, ValueError, AttributeError):
        return ""


def _count(value: Any) -> int | None:
    return value if type(value) is int and 0 <= value <= 10**12 else None


def _opencode_history(project: Path, limit: int, db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "missing", "calls": []}
    if not db_path.is_file():
        return result
    try:
        with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.5)) as db:
            db.execute("PRAGMA query_only=ON")
            # Bound database work as well as returned rows on large shared histories.
            deadline = time.monotonic() + 2
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
            project_path = str(project.resolve())
            prefix = project_path + "/.worktrees/"
            rows = db.execute(
                """
                SELECT m.id, m.session_id, m.time_created,
                  json_extract(m.data,'$.providerID'), json_extract(m.data,'$.modelID'),
                  json_extract(m.data,'$.tokens.input'), json_extract(m.data,'$.tokens.output'),
                  json_extract(m.data,'$.tokens.cache.read'), json_extract(m.data,'$.finish'),
                  json_type(m.data,'$.error')
                FROM message m JOIN session s ON s.id=m.session_id
                WHERE (s.directory=? OR substr(s.directory,1,?)=?)
                  AND json_extract(m.data,'$.role')='assistant'
                ORDER BY m.time_created DESC, m.id DESC LIMIT ?
            """,
                (project_path, len(prefix), prefix, limit),
            ).fetchall()
        calls = []
        for mid, sid, stamp, provider, model, tin, tout, cache, finish, error in rows:
            calls.append(
                {
                    "message_id": safe_identifier(mid),
                    "session_id": safe_identifier(sid),
                    "timestamp": datetime.fromtimestamp(stamp / 1000, UTC).isoformat(),
                    "provider": safe_identifier(provider),
                    "model": safe_identifier(model),
                    "input_tokens": _count(tin),
                    "output_tokens": _count(tout),
                    "cache_read_tokens": _count(cache),
                    "status": "error" if error not in (None, "null") else ("completed" if finish else "recorded"),
                    "source": "opencode-message",
                    "ticket": None,
                }
            )
        return {"status": "available", "calls": calls}
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError):
        return {"status": "unavailable", "calls": []}


def _subllm_history(limit: int) -> dict[str, Any]:
    """Use the installed producer API; do not copy its storage/schema/catalog."""
    try:
        from subllm.usage import query_usage
    except ImportError:
        return {"status": "not_installed", "calls": []}
    try:
        payload = query_usage({"application": "koru-agent", "limit": limit})
        calls = []
        for item in payload.get("attempts", []):
            row = {
                key: safe_identifier(item.get(key))
                for key in ("request_id", "application", "function", "provider", "model", "status")
            }
            row["timestamp"] = _timestamp(item.get("timestamp"))
            row.update({key: _count(item.get(key)) for key in ("input_tokens", "output_tokens", "duration_ms")})
            calls.append(row)
        return {"status": payload.get("storage", "available"), "scope": "koru-agent across projects", "calls": calls}
    except Exception:
        return {"status": "unavailable", "calls": []}


def model_history_payload(project: Path, *, limit: int = 100, db_path: Path | None = None) -> dict[str, Any]:
    limit = max(1, min(200, limit))
    if db_path is None:
        data_root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        db_path = data_root / "opencode" / "opencode.db"
    return {
        "project": str(project),
        "limit": limit,
        "opencode": _opencode_history(project, limit, db_path),
        "subllm": _subllm_history(limit),
        "decisions": _routing_history(project, limit),
        "coverage": (
            "OpenCode messages for this project and its .worktrees; installed SubLLM API for koru-agent "
            "across projects. Requested CLI models are not proof of execution; "
            "no inferred ticket/session joins or billing totals."
        ),
    }
