"""Desktop / IDE surface preflight probe extracted from ``vdisplay_client``.

Lists monitors, correlated surfaces, and target IDE processes so drive/prepare
paths can refuse work when the requested monitor or IDE window is missing.
Re-exported from ``vdisplay_client`` for backward-compatible imports.
"""

from __future__ import annotations

from typing import Any


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


_IDE_PROCESS_PATTERNS: dict[str, tuple[str, ...]] = {
    "cursor": ("cursor",),
    "windsurf": ("windsurf",),
    "vscode": ("code", "vscode", "vscodium"),
    "antigravity": ("antigravity",),
    "qoder": ("qoder",),
    "jetbrains": ("pycharm", "idea", "webstorm", "goland", "clion", "rider", "jetbrains"),
    "pycharm": ("pycharm", "jetbrains"),
    "idea": ("idea", "intellij", "jetbrains"),
}


def probe_ide_processes(ide: str) -> list[dict[str, Any]]:
    """Best-effort process list for target IDE (includes native Wayland not in X11 window list)."""
    import subprocess

    patterns = _IDE_PROCESS_PATTERNS.get(_canonical_ide(ide), (_canonical_ide(ide),))
    found: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,comm,args"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in proc.stdout.splitlines()[1:]:
            low = line.lower()
            if not any(p in low for p in patterns):
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            found.append(
                {
                    "pid": pid,
                    "comm": parts[1],
                    "cmdline": parts[2] if len(parts) > 2 else "",
                }
            )
    except Exception as exc:
        return [{"error": str(exc)}]
    return found


def desktop_probe_ide_hints(ide: str) -> set[str]:
    """IDE hint tokens used to filter correlated surfaces in desktop_probe."""
    canon = _canonical_ide(ide)
    ide_hints = {canon}
    if canon in {"jetbrains", "pycharm", "idea"}:
        ide_hints.add("jetbrains")
    if canon in {"vscode", "vscodium"}:
        ide_hints.add("vscode")
    return ide_hints


def desktop_probe_ide_surface_rank(row: dict[str, Any]) -> float:
    """Rank a correlated IDE surface for desktop_probe best-surface selection."""
    score = float(row.get("confidence") or 0)
    name = str(row.get("display_name") or "").lower()
    if "toolbox" in name:
        score -= 0.45
    stack = str(row.get("stack") or "")
    if stack == "wayland_native":
        score += 0.25
    elif stack == "xwayland":
        score += 0.1
    proc = ((row.get("sources") or {}).get("process")) or {}
    comm = str(proc.get("comm") or "").lower()
    if comm in {"pycharm", "idea", "webstorm", "goland", "clion", "rider"}:
        score += 0.35
    elif comm == "java" and "pycharm" in str(proc.get("cmdline") or "").lower():
        score += 0.3
    return score


def _desktop_probe_windows(out: dict[str, Any], *, ide: str, list_windows_local: Any) -> None:
    """Populate window/surface correlation fields on the desktop_probe payload."""
    try:
        win_payload = list_windows_local(apps_only=True, correlate=True)
        out["windows"] = win_payload.get("windows") or []
        out["window_count"] = win_payload.get("window_count")
        out["window_hint"] = win_payload.get("hint")
        out["correlated"] = bool(win_payload.get("correlated"))
        out["surfaces"] = win_payload.get("surfaces") or []
        out["surface_count"] = win_payload.get("surface_count", 0)
        out["gnome_window_count"] = win_payload.get("gnome_window_count", 0)
        out["atspi_application_count"] = win_payload.get("atspi_application_count", 0)
        out["correlation_sources"] = win_payload.get("correlation_sources") or {}
        out["correlation_process_count"] = win_payload.get("correlation_process_count", 0)
        ide_hints = desktop_probe_ide_hints(ide)
        ide_surfaces = [
            row
            for row in out["surfaces"]
            if isinstance(row, dict) and row.get("ide_hint") in ide_hints
        ]
        out["ide_surfaces"] = ide_surfaces
        if ide_surfaces:
            best = max(ide_surfaces, key=desktop_probe_ide_surface_rank)
            out["ide_surface_best"] = {
                "display_name": best.get("display_name"),
                "pid": best.get("pid"),
                "stack": best.get("stack"),
                "monitor_name": best.get("monitor_name"),
                "bounds": best.get("bounds"),
                "confidence": best.get("confidence"),
                "match_reasons": best.get("match_reasons"),
            }
    except Exception as exc:
        out["windows_error"] = str(exc)


def desktop_probe(*, ide: str, source: str | None = None) -> dict[str, Any]:
    """Preflight: monitors, X11 windows, correlated surfaces, target IDE processes."""
    out: dict[str, Any] = {"ok": True, "ide": ide, "requested_source": source}
    try:
        from vdisplay.application.services.discovery import list_monitors_local, list_windows_local

        mon_payload = list_monitors_local()
        monitors = mon_payload.get("monitors") or []
        monitor_names = [str(m.get("name")) for m in monitors if m.get("name")]
        out["monitors"] = monitors
        out["monitor_names"] = monitor_names
        out["monitor_count"] = mon_payload.get("monitor_count")
        _desktop_probe_windows(out, ide=ide, list_windows_local=list_windows_local)
    except Exception as exc:
        out["ok"] = False
        out["discovery_error"] = str(exc)
        out["monitor_names"] = []

    out["ide_processes"] = probe_ide_processes(ide)
    names = set(out.get("monitor_names") or [])
    if source:
        out["source_available"] = source in names
        if source not in names and names:
            out["ok"] = False
            out["error"] = (
                f"requested monitor {source!r} not connected "
                f"(available: {sorted(names)})"
            )
    return out


# Private aliases matching historical vdisplay_client names.
_probe_ide_processes = probe_ide_processes
_desktop_probe_ide_hints = desktop_probe_ide_hints
_desktop_probe_ide_surface_rank = desktop_probe_ide_surface_rank
_desktop_probe = desktop_probe

__all__ = [
    "desktop_probe",
    "desktop_probe_ide_hints",
    "desktop_probe_ide_surface_rank",
    "probe_ide_processes",
    "_desktop_probe",
    "_desktop_probe_ide_hints",
    "_desktop_probe_ide_surface_rank",
    "_probe_ide_processes",
]
