"""IDE-map capture/pointer target math extracted from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _photo_vql_needs_vision_or_map(
    *,
    mismatch: dict[str, Any] | None,
    empty_layers: bool,
    polluted: bool,
) -> bool:
    return bool(mismatch) or empty_layers or polluted


def _jetbrains_map_selection_method(*, empty_layers: bool) -> str:
    return "map_calibrated_on_empty_vql" if empty_layers else "map_calibrated_on_mismatch"


def _jetbrains_map_selection_stage(*, empty_layers: bool) -> str:
    if empty_layers:
        return "vql_target_selection_jetbrains_map_on_empty_vql"
    return "vql_target_selection_jetbrains_map_on_mismatch"


def get_vql_editor_target_from_photo() -> dict:
    """Na podstawie foto screen VQL zlokalizuj główny obszar edytora (deleguje do imgl.targets)."""
    els, src = _vdc()._photo_vql_elements()
    resolve_editor_target = _vdc()._import_imgl_targets("resolve_editor_target")
    if resolve_editor_target is not None:
        return resolve_editor_target(els, source=src)
    return {
        "click_center": {"x": 1024, "y": 640, "note": "DP-1 main editor area center (imgl not installed)"},
        "id": "dp1-editor-center",
        "role": "editor",
        "note": "hardened fallback — pip install imgl",
        "source": "vql-analysis-fallback",
    }


def click_editor_via_photo_vql(ide: str = "auto", source: str = "DP-1") -> dict:
    """Użyj VQL z foto do zlokalizowania edytora (otwarty plik), kliknij center dla focus,
    przygotuj do precyzyjnego edit via coords.

    Parallel to chat focus. Zwraca wynik z click_center z foto VQL.
    Autonomia może potem użyć coords do edit (set_value, keyboard, lub control na tym punkcie).
    """
    t = _vdc().get_vql_editor_target_from_photo()
    # Reuse the move logic (it does mouse to center + window focus for kb)
    res = _vdc().move_mouse_to_vql_target_and_focus_keyboard(t, ide=ide, source=source)
    res["target_kind"] = "editor"
    res["for"] = "see open file + precise edit via VQL photo coords"
    return res


def _photo_capture_meta_for_source(source: str) -> dict[str, Any]:
    """Best-effort capture metadata for translating local VQL coords to global pointer space."""
    meta: dict[str, Any] = {}
    png = _vdc()._resolve_photo_png_path(source)
    ctx_path = png.with_suffix(png.suffix + ".context.json")
    if ctx_path.is_file():
        try:
            with open(ctx_path) as f:
                ctx = json.load(f)
            cap = ctx.get("capture") if isinstance(ctx, dict) else None
            if isinstance(cap, dict):
                meta = dict(cap)
        except Exception:
            pass
    if not meta:
        sidecar = _vdc().load_vql_metadata(str(png.with_suffix(png.suffix + ".vql.json")))
        cap = (sidecar.get("metadata") or {}).get("capture") if isinstance(sidecar.get("metadata"), dict) else None
        if isinstance(cap, dict):
            meta = dict(cap)
    meta.setdefault("source", source)
    meta.setdefault("monitor_name", source)
    return _vdc()._enrich_capture_meta_for_pointer(meta, source)


def _matching_ide_map_capture_meta(source: str) -> dict[str, Any]:
    """Load caller-approved calibrated metadata; VDisplay owns its normalization."""
    app_id = _vdc()._ide_prompt_app_id(source if source in {"pycharm", "jetbrains", "idea"} else "pycharm")
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    if map_path and os.path.isfile(map_path):
        try:
            with open(map_path) as f:
                map_data = json.load(f)
            mcap = map_data.get("capture_meta") if isinstance(map_data.get("capture_meta"), dict) else {}
            if str(mcap.get("source") or mcap.get("monitor_name") or "") in {source, ""}:
                return dict(mcap)
        except Exception:
            pass
    return {}


def _enrich_capture_meta_for_pointer(meta: dict[str, Any], source: str) -> dict[str, Any]:
    """Bind Koru's calibrated snapshot to VDisplay's canonical metadata model."""
    try:
        from vdisplay.capture import canonicalize_capture_meta
        from vdisplay.capture.screencast_stream_meta import enrich_screencast_stream_meta
        from vdisplay.input import monitor_by_name

        enriched = enrich_screencast_stream_meta(dict(meta or {}))
        try:
            monitor = monitor_by_name(enriched.get("display"), source)
        except Exception:
            # Headless runners have no discoverable host display. Canonical
            # capture metadata and a calibrated fallback do not require one.
            monitor = None
        return canonicalize_capture_meta(
            enriched,
            source=source,
            fallback_meta=_vdc()._matching_ide_map_capture_meta(source),
            monitor=monitor,
            replace_zero_origin=True,
        )
    except Exception:
        return dict(meta or {})


def _map_chat_input_candidate_keys(app_id: str) -> list[str]:
    """Ordered map element keys to try for the chat composer click point."""
    # Preferred order: prompt (known good in ide_control for DP-2), then chat specific, then fallbacks.
    candidates: list[str] = []
    try:
        from vdisplay.desktop_apps import map_input_target_candidates
        cands = map_input_target_candidates(app_id) or []
        for c in cands:
            if c not in candidates:
                candidates.append(c)
    except Exception:
        pass
    for fb in ("prompt", "ai-chat-input", "chat-input", "message", "input"):
        if fb not in candidates:
            candidates.append(fb)
    return candidates


def _map_chat_pointer_meta(source: str) -> dict[str, Any]:
    """Enriched capture meta used to map global map points to capture-local coords."""
    meta = _vdc()._enrich_capture_meta_for_pointer(_vdc()._photo_capture_meta_for_source(source), source)
    region = (meta or {}).get("region") or {}
    cap_w = int(region.get("width") or 2048)  # noqa: F841
    cap_h = int(region.get("height") or 1280)  # noqa: F841
    return meta


def _map_chat_element_local_point(
    element: dict[str, Any], meta: dict[str, Any]
) -> tuple[int, int, int, int] | None:
    """Map an element's global click_point to capture-local ints; None if unusable."""
    from vdisplay.input.coords import global_point_to_capture_local
    click = element.get("click_point") or {}
    gx = int(click.get("x") or 0)
    gy = int(click.get("y") or 0)
    if gx <= 0 or gy <= 0:
        return None
    lx, ly = global_point_to_capture_local(gx, gy, meta)
    return gx, gy, int(lx), int(ly)


def _map_chat_target_entry(
    key: str,
    element: dict[str, Any],
    lx_i: int,
    ly_i: int,
    gx: int,
    gy: int,
    map_path: str,
) -> dict[str, Any]:
    """Map-calibrated chat target dict for a resolved element/coords pair."""
    return {
        "click_center": {"x": lx_i, "y": ly_i},
        "id": f"map:{key}",
        "role": "input",
        "bounds": element.get("action_bounds") or element.get("raw_bounds"),
        "note": f"map-calibrated JetBrains chat input ({key} from {map_path})",
        "source": map_path,
        "map_global": {"x": gx, "y": gy},
        "map_element_key": key,
    }


def _map_chat_bottom_right_target(
    candidates: list[str],
    elems: Any,
    meta: dict[str, Any],
    map_path: str,
) -> dict[str, Any] | None:
    """First candidate whose local point lands in the bottom-right composer area."""
    for key in candidates:
        element = elems.get(key) if isinstance(elems, dict) else None
        if not isinstance(element, dict):
            continue
        point = _vdc()._map_chat_element_local_point(element, meta)
        if point is None:
            continue
        gx, gy, lx_i, ly_i = point
        # Accept bottom-right composer area; skip top-of-screen/editor coords from stale maps.
        if ly_i >= 700 and lx_i >= 900:
            return _vdc()._map_chat_target_entry(key, element, lx_i, ly_i, gx, gy, map_path)
    return None


def _map_chat_nonnegative_target(
    candidates: list[str],
    elems: Any,
    meta: dict[str, Any],
    map_path: str,
) -> dict[str, Any] | None:
    """Last resort: first candidate with a non-negative local point."""
    # Last resort: take the first valid element even if y low (will get coord warning later)
    # But still refuse to return a negative local y (safer than feeding garbage coords to ydotool plan).
    for key in candidates:
        element = elems.get(key) if isinstance(elems, dict) else None
        if not isinstance(element, dict):
            continue
        point = _vdc()._map_chat_element_local_point(element, meta)
        if point is None:
            continue
        gx, gy, lx_i, ly_i = point
        if ly_i < 0 or lx_i < 0:
            continue
        return _vdc()._map_chat_target_entry(key, element, lx_i, ly_i, gx, gy, map_path)
    return None


def _map_chat_target_capture_local(*, ide: str, source: str) -> dict[str, Any] | None:
    """Convert calibrated map chat input global point into capture-local coords.
    Tries several element keys (prompt first for JetBrains on DP-2, then ai-chat-input etc)
    and returns the first that yields a sane positive local y (bottom composer area).
    This avoids negative y or editor coords from stale/wrong-calibrated map entries
    under rotated screencast capture_meta (e.g. origin_y=1932, scale 0.8).
    """
    app_id = _vdc()._ide_prompt_app_id(ide)
    map_path = _vdc()._resolve_ide_prompt_map(app_id)
    if not map_path or not os.path.isfile(map_path):
        return None
    try:
        with open(map_path) as f:
            map_data = json.load(f)
        map_meta = map_data.get("capture_meta") if isinstance(map_data.get("capture_meta"), dict) else {}
        map_source = str(map_meta.get("source") or map_meta.get("monitor_name") or "").strip()
        if map_source and map_source != source:
            return None
        elems = (map_data.get("elements") or {})
        candidates = _vdc()._map_chat_input_candidate_keys(app_id)
        meta = _vdc()._map_chat_pointer_meta(source)
        target = _vdc()._map_chat_bottom_right_target(candidates, elems, meta, map_path)
        if target is not None:
            return target
        return _vdc()._map_chat_nonnegative_target(candidates, elems, meta, map_path)
    except Exception:
        return None


def _global_coords_from_vql_local(*, x: int, y: int, source: str) -> tuple[int | None, int | None, dict[str, Any]]:
    """Map capture-local VQL coords to global pointer space (for command generation audit)."""
    try:
        from vdisplay.capture import compile_capture_coordinate_map, global_pointer_coords

        capture_meta = _vdc()._enrich_capture_meta_for_pointer(_vdc()._photo_capture_meta_for_source(source), source)
        coordinate_map = compile_capture_coordinate_map(capture_meta, source=source)
        pointer_meta = dict(capture_meta)
        # The compiled contract resolves an absent rotation to ``normal``.
        # Pass that fact on so coordinate mapping remains pure and does not
        # fall back to optional live-monitor discovery in headless runtimes.
        pointer_meta.setdefault("rotation", coordinate_map.rotation)
        gx, gy, details = global_pointer_coords(int(x), int(y), pointer_meta)
        return int(gx), int(gy), {
            "capture_meta_region": capture_meta.get("region"),
            "capture_meta_rotation": pointer_meta.get("rotation"),
            "coordinate_map": coordinate_map.to_dict(),
            "mapping_details": details,
        }
    except Exception as exc:
        return None, None, {"mapping_error": str(exc)}
