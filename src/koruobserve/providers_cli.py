"""``koru observe providers`` — list, test, and reset capture backends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def screencast_session_path(project: Path) -> Path:
    from koruvision.providers.screencast_session import session_file_for_project

    return session_file_for_project(project)


def providers_list_payload(project: Path) -> dict[str, Any]:
    """JSON-friendly provider table (same shape as ``/api/mesh/diagnostics``)."""
    del project
    from koruvision.providers.detector import provider_diagnostics_rows

    ranked, rows = provider_diagnostics_rows()
    return {"ranked": ranked, "providers": rows}


def providers_list_text(payload: dict[str, Any]) -> str:
    ranked = payload.get("ranked") or []
    rows = payload.get("providers") or []
    lines = [
        "koru observe providers:",
        f"  auto-rank order: {', '.join(ranked) if ranked else '(none available)'}",
        "",
        f"{'name':<22} {'avail':<6} {'rank':<5} {'stream':<7} reason",
    ]
    for row in rows:
        name = str(row.get("name") or "")
        avail = "yes" if row.get("available") else "no"
        rank = str(row.get("rank") or "-")
        stream = "yes" if row.get("streams") else "no"
        reason = str(row.get("reason") or "")
        hint = str(row.get("install_hint") or "").strip()
        if hint:
            reason = f"{reason} ({hint})" if reason else hint
        lines.append(f"  {name:<20} {avail:<6} {rank:<5} {stream:<7} {reason[:72]}")
    return "\n".join(lines)


def providers_test_payload(name: str | None, *, scale: float = 0.2) -> dict[str, Any]:
    from koruvision.providers.detector import probe_capture_providers

    results = probe_capture_providers(name, scale=scale)
    return {
        "target": name or "all",
        "results": results,
        "ok_count": sum(1 for row in results if row.get("ok")),
        "fail_count": sum(1 for row in results if not row.get("ok")),
    }


def providers_test_text(payload: dict[str, Any]) -> str:
    target = payload.get("target") or "all"
    lines = [f"koru observe providers test ({target}):"]
    for row in payload.get("results") or []:
        name = str(row.get("name") or "?")
        if row.get("ok"):
            detail = (
                f"{row.get('frame_count', 1)} frame(s), "
                f"{row.get('bytes', 0)} bytes, "
                f"{row.get('width')}x{row.get('height')}"
            )
            if name == "portal_screencast" and int(row.get("frame_count") or 0) == 1:
                detail += (
                    " — for all monitors: koru observe providers reset, "
                    "then test again and select every display in the GNOME picker (Ctrl+click)"
                )
            lines.append(f"  {name}: ok ({detail})")
        else:
            err = str(row.get("error") or row.get("reason") or "failed")
            if name == "portal_screencast" and "Missing token" in err:
                err = (
                    f"{err[:80]} — run from a GNOME terminal (not SSH), accept the "
                    "'Share screen' dialog when it appears; use "
                    "'koru observe providers reset' then 'koru observe up'"
                )
            lines.append(f"  {name}: FAIL — {err[:200]}")
    lines.append(
        f"  summary: {payload.get('ok_count', 0)} ok, {payload.get('fail_count', 0)} failed"
    )
    return "\n".join(lines)


def providers_reset_consent(project: Path) -> dict[str, Any]:
    """Remove saved ScreenCast session token (forces portal dialog on next capture)."""
    from koruvision.providers.screencast_session import clear_session_file

    removed: list[str] = []
    session = screencast_session_path(project)
    if clear_session_file(session):
        removed.append(str(session))
    keys_dir = session.parent
    if keys_dir.is_dir() and not any(keys_dir.iterdir()):
        keys_dir.rmdir()
        removed.append(f"{keys_dir}/ (empty)")
    return {
        "ok": True,
        "removed": removed,
        "message": "screencast consent cache cleared" if removed else "no screencast session file",
    }


def providers_reset_text(payload: dict[str, Any]) -> str:
    removed = payload.get("removed") or []
    if not removed:
        return "koru observe providers reset: no screencast session file found"
    return "koru observe providers reset:\n  removed: " + "\n  removed: ".join(removed)


def cmd_providers_list(project: Path, *, json_out: bool) -> int:
    payload = providers_list_payload(project)
    if json_out:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(providers_list_text(payload))
    return 0


def cmd_providers_test(
    project: Path,
    name: str | None,
    *,
    json_out: bool,
    scale: float,
) -> int:
    del project
    payload = providers_test_payload(name, scale=scale)
    if json_out:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(providers_test_text(payload))
    return 0 if payload.get("ok_count") else 1


def cmd_providers_reset(project: Path, *, json_out: bool) -> int:
    payload = providers_reset_consent(project)
    if json_out:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(providers_reset_text(payload))
    return 0
