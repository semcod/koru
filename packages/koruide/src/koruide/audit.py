"""Persistent audit log for koru autopilot (P2.7).

Every injection request, plugin lifecycle event, and shutdown is
appended as a single NDJSON line under
``$XDG_STATE_HOME/koru/autopilot.log`` (fallback:
``~/.local/state/koru/autopilot.log``).

The log lets the user audit exactly what autopilot typed on their
behalf. The schema is intentionally tiny so the file can be tailed
with ``jq -c .`` or read by ``koru autopilot tail`` without parsing
heroics.

We use the stdlib :class:`logging.handlers.RotatingFileHandler` so the
file caps at ``10 MiB`` with up to 5 archived rotations — no extra
dependency, no log-shipping pipeline required.

Each line has the shape::

    {"ts": "2026-05-11T18:30:01.234Z",
     "event": "drive",
     "ide": "windsurf",
     "backend": "plugin",
     "chars": 5388,
     "submit": true,
     "ok": true,
     "extra": {...}}

Schema additions are append-only: ``koru autopilot tail`` skips
unknown keys gracefully.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_NAME = "koru.autopilot.audit"
MAX_BYTES = 10 * 1024 * 1024  # 10 MiB
BACKUP_COUNT = 5


def default_log_path() -> Path:
    """Return the canonical audit-log path under ``$XDG_STATE_HOME``."""
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return base / "koru" / "autopilot.log"


class _JSONFormatter(logging.Formatter):
    """Emit ``record.msg`` verbatim — we hand it in pre-serialised."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def _isoformat_utc(ts: float | None = None) -> str:
    t = ts if ts is not None else time.time()
    secs = int(t)
    millis = int((t - secs) * 1000)
    tm = time.gmtime(secs)
    return time.strftime("%Y-%m-%dT%H:%M:%S", tm) + f".{millis:03d}Z"


class AuditLog:
    """Append-only audit log for autopilot events.

    Construct once at daemon start; call :meth:`record` for each event.
    Safe to instantiate even when the log directory does not exist —
    the constructor creates it (``mode=0700``).
    """

    def __init__(
        self,
        *,
        path: Path | None = None,
        max_bytes: int = MAX_BYTES,
        backup_count: int = BACKUP_COUNT,
        enabled: bool = True,
    ) -> None:
        self.path = path or default_log_path()
        self.enabled = enabled
        self._logger = logging.getLogger(f"{LOG_NAME}.{id(self):x}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._handler: RotatingFileHandler | None = None
        if not enabled:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Best-effort permission lockdown on the directory.
            with contextlib.suppress(OSError):
                os.chmod(self.path.parent, 0o700)
        except OSError as exc:
            # Fail open: log to stderr once and disable, so a missing
            # XDG_STATE_HOME doesn't crash the daemon.
            print(
                f"koru autopilot audit: cannot create {self.path.parent}: {exc}",
                flush=True,
            )
            self.enabled = False
            return
        handler = RotatingFileHandler(
            self.path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(_JSONFormatter())
        self._logger.addHandler(handler)
        self._handler = handler
        # 0600 on the file itself (RotatingFileHandler creates it 0644 on
        # first write — patch it post-hoc on the next write below).
        self._needs_chmod = True

    def record(self, event: str, **fields: Any) -> None:
        """Append one NDJSON line. Silently no-ops when disabled."""
        if not self.enabled:
            return
        payload: dict[str, Any] = {"ts": _isoformat_utc(), "event": event}
        for k, v in fields.items():
            if v is None:
                continue
            payload[k] = v
        line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        self._logger.info(line)
        if self._needs_chmod and self.path.exists():
            with contextlib.suppress(OSError):
                os.chmod(self.path, 0o600)
            self._needs_chmod = False

    def close(self) -> None:
        if self._handler is not None:
            try:
                self._handler.flush()
                self._handler.close()
            except OSError:
                pass
            self._logger.removeHandler(self._handler)
            self._handler = None


__all__ = [
    "AuditLog",
    "default_log_path",
    "LOG_NAME",
    "MAX_BYTES",
    "BACKUP_COUNT",
]
