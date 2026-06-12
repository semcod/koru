"""Monitor/source resolution for photo-VQL capture."""

from __future__ import annotations

import os
from typing import Any


_IDE_DEFAULT_SOURCE: dict[str, str] = {
    "cursor": "DP-1",
    "windsurf": "DP-1",
    "antigravity": "DP-1",
    "vscode": "DP-1",
    "jetbrains": "DP-1",
    "pycharm": "DP-1",
    "idea": "DP-1",
}


def _monitor_candidate_order(
    *,
    explicit: str,
    preferred: str,
    probe: dict[str, Any],
    names: set[str],
) -> list[str]:
    candidates: list[str] = []
    for value in (explicit, preferred):
        if value and value not in candidates:
            candidates.append(value)
    for monitor in probe.get("monitors") or []:
        name = str(monitor.get("name") or "")
        if name.startswith("DP-") and name not in candidates:
            candidates.append(name)
    for monitor in probe.get("monitors") or []:
        if monitor.get("primary") and monitor.get("name"):
            name = str(monitor["name"])
            if name not in candidates:
                candidates.append(name)
    for name in sorted(names):
        if name not in candidates:
            candidates.append(name)
    return candidates


def _finalize_resolved_probe(
    probe: dict[str, Any],
    *,
    preferred: str,
    chosen: str,
    names: set[str],
) -> dict[str, Any]:
    resolved_probe = {
        **probe,
        "requested_source": preferred,
        "resolved_source": chosen,
        "source_available": chosen in names if names else None,
    }
    if names and chosen not in names:
        resolved_probe["ok"] = False
        resolved_probe["error"] = (
            f"no connected monitor for {preferred!r} "
            f"(available: {sorted(names)})"
        )
    elif chosen != preferred:
        resolved_probe["source_auto_resolved"] = True
        resolved_probe["source_was"] = preferred
        resolved_probe["ok"] = True
        resolved_probe["source_available"] = True
        resolved_probe.pop("error", None)
    else:
        resolved_probe["ok"] = bool(resolved_probe.get("ok", True))
        resolved_probe["source_available"] = chosen in names if names else None
    return resolved_probe


def resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    canonical_ide: Any,
    desktop_probe: Any,
    probe: dict[str, Any] | None = None,
    ide_default_source: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Pick capture monitor: explicit env > IDE default > DP-* > primary > first connected."""
    defaults = ide_default_source or _IDE_DEFAULT_SOURCE
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    canon = canonical_ide(ide)
    preferred = explicit or defaults.get(canon, "DP-1")
    if probe is None:
        probe = desktop_probe(ide=ide, source=preferred)
    names = set(probe.get("monitor_names") or [])

    if explicit and explicit not in names and names:
        failed_probe = {
            **probe,
            "requested_source": explicit,
            "resolved_source": explicit,
            "source_available": False,
            "ok": False,
            "error": (
                f"requested monitor {explicit!r} not connected "
                f"(available: {sorted(names)})"
            ),
        }
        return explicit, failed_probe

    candidates = _monitor_candidate_order(
        explicit=explicit,
        preferred=preferred,
        probe=probe,
        names=names,
    )
    chosen = preferred
    for candidate in candidates:
        if candidate in names:
            chosen = candidate
            break
    return chosen, _finalize_resolved_probe(probe, preferred=preferred, chosen=chosen, names=names)


__all__ = ["resolve_vdisplay_source_for_ide"]
