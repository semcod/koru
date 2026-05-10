"""Best-effort management event emission for koru tools."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any


def emit_management_event(
    *,
    tool: str,
    action: str,
    status: str = "info",
    message: str = "",
    queue: str | None = None,
    level: str = "info",
    details: dict[str, Any] | None = None,
    source: str = "koru",
    events_url: str | None = None,
) -> bool:
    """Emit a management event to planfile if KORU_EVENTS_URL is configured."""
    url = events_url or os.getenv("KORU_EVENTS_URL")
    if not url:
        base_url = os.getenv("KORU_PLANFILE_API_URL")
        if base_url:
            url = f"{base_url.rstrip('/')}/events/ingest"
    if not url:
        return False

    payload = {
        "source": source,
        "tool": tool,
        "action": action,
        "status": status,
        "message": message,
        "queue": queue or "default",
        "level": level,
        "details": details or {},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2.0):
            return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--status", default="info")
    parser.add_argument("--message", default="")
    parser.add_argument("--queue", default="default")
    parser.add_argument("--level", default="info")
    parser.add_argument("--source", default="koru")
    parser.add_argument("--details-json", default="{}")
    args = parser.parse_args()

    try:
        details = json.loads(args.details_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --details-json: {exc}") from exc
    if not isinstance(details, dict):
        raise SystemExit("--details-json must decode to an object")

    ok = emit_management_event(
        source=args.source,
        tool=args.tool,
        action=args.action,
        status=args.status,
        message=args.message,
        queue=args.queue,
        level=args.level,
        details=details,
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
