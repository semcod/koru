"""Dashboard helpers for the mesh observation grid.

Exposes three HTTP endpoints (rendered by ``serve_mesh_http``):

- ``GET /grid`` — single-page HTML loaded from ``grid_template.html``
  via ``@lru_cache``.
- ``GET /api/mesh/frames`` — JSON list of recently observed
  ``vision/frame`` envelopes (decoded thumbnails + monitor metadata).
- ``GET /api/mesh/diagnostics`` — JSON describing why ``/grid`` is empty
  when capture is blocked (e.g. Wayland security policy): detected
  monitors plus the last capture error from the agent log.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from korumesh.dashboard_parse import envelope_to_frame_entry
from korumesh.store import list_vision_frames

_TEMPLATE_NAME = "grid_template.html"


@lru_cache(maxsize=1)
def grid_html() -> str:
    """Return the cached observation grid HTML template."""
    return (files(__package__) / _TEMPLATE_NAME).read_text(encoding="utf-8")


def _diagnostics_payload(project: Path) -> dict[str, Any]:
    """Return capture diagnostics, gracefully degrading when koruobserve is absent."""
    try:
        from koruobserve.diagnostics import capture_diagnostics
    except Exception:
        return {"session_type": "unknown", "monitors": [], "status": "unavailable"}
    try:
        return capture_diagnostics(project)
    except Exception as exc:  # noqa: BLE001 — diagnostics must never break /grid
        return {
            "session_type": "unknown",
            "monitors": [],
            "status": "error",
            "last_error": str(exc),
        }


def mesh_frames_payload() -> dict[str, object]:
    """Return ``/api/mesh/frames`` JSON with parsed monitor metadata per frame."""
    frames = [envelope_to_frame_entry(envelope) for envelope in list_vision_frames()]
    return {"ok": True, "frames": frames}


def mesh_diagnostics_payload(project: Path | None = None) -> dict[str, object]:
    """Return ``/api/mesh/diagnostics`` JSON (monitors + last capture error)."""
    return _diagnostics_payload(project or Path.cwd())


def _serve_grid(handler: object, _project: Path | None) -> None:
    getattr(handler, "_send")(200, grid_html().encode("utf-8"), "text/html; charset=utf-8")


def _serve_frames(handler: object, _project: Path | None) -> None:
    getattr(handler, "_send_json")(mesh_frames_payload())


def _serve_diagnostics(handler: object, project: Path | None) -> None:
    getattr(handler, "_send_json")(mesh_diagnostics_payload(project))


_MESH_ROUTES = {
    "/grid": _serve_grid,
    "/api/mesh/frames": _serve_frames,
    "/api/mesh/diagnostics": _serve_diagnostics,
}


def serve_mesh_http(handler: object, path: str, *, project: Path | None = None) -> bool:
    """Serve any of the ``_MESH_ROUTES`` paths; return ``False`` otherwise."""
    route = _MESH_ROUTES.get(path)
    if route is None:
        return False
    route(handler, project)
    return True
