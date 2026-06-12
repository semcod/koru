"""``koru autopilot prepare-vdisplay`` — run photo-VQL observe before drive."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def action_prepare_vdisplay(args: argparse.Namespace) -> int:
    ide = str(getattr(args, "ide", "auto") or "auto").strip().lower()
    from koru.autonomous_vdisplay_defaults import apply_vdisplay_drive_defaults

    applied = apply_vdisplay_drive_defaults(ide=ide)
    if applied:
        print(f"koru autopilot prepare-vdisplay: env defaults → {', '.join(applied)}", file=sys.stderr)
    from koru.integrations.vdisplay_client import prepare_photo_vql_for_drive

    result: dict[str, Any] = prepare_photo_vql_for_drive(ide=ide)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


__all__ = ["action_prepare_vdisplay"]
