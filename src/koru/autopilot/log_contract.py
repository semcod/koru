"""Shared logging contract helpers for ``koru autopilot`` commands."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from typing import Any


def _resolve_log_format(args: Any) -> str:
    raw = str(getattr(args, "log_format", "") or "").strip().lower()
    if raw in {"human", "jsonl"}:
        return raw
    env_raw = (os.environ.get("KORU_STDIO_FORMAT") or "").strip().lower()
    if env_raw in {"human", "jsonl"}:
        return env_raw
    return "human"


def emit_log(
    args: Any,
    *,
    component: str,
    level: str,
    action: str,
    result: str,
    rc: int | None = None,
    corr: str = "koru-autopilot",
    **extra: Any,
) -> None:
    """Emit standardized jsonl logs when ``--log-format jsonl`` is enabled."""
    if _resolve_log_format(args) != "jsonl":
        return
    row: dict[str, Any] = {
        "ts": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "corr": corr,
        "component": component,
        "level": level,
        "action": action,
        "result": result,
    }
    if rc is not None:
        row["rc"] = int(rc)
    row.update({k: v for k, v in extra.items() if v is not None})
    sys.stderr.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stderr.flush()


__all__ = ["emit_log"]
