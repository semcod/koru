"""VQL candidate/metadata loading, freshness policy and the optional-extra
``vdisplay.vql`` shims extracted from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _vql_candidate_is_stale(cand: str, png_path: Path | None, stale_tried: list[dict[str, Any]]) -> bool:
    """Check sidecar staleness, recording skipped candidates into stale_tried."""
    stale, freshness = _vdc()._autonomy_session.vql_sidecar_is_stale(
        Path(cand),
        png_path,
        layer_count=_vdc()._main_vql_layer_count(cand),
    )
    if stale:
        stale_tried.append({"path": cand, **freshness})
    return stale


def _vql_imgl_fallback_layers(
    cand: str, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> tuple[list[dict], str]:
    """Fall back to imgl sidecar layers for cand; returns (layers, effective_cand)."""
    imgl_layers, imgl_source = _vdc()._layers_from_imgl_sidecar_file(cand)
    if imgl_layers:
        imgl_path = Path(imgl_source or cand)
        png_for_imgl = _vdc()._png_path_for_vql_sidecar(str(cand))
        if not allow_stale and png_for_imgl and imgl_path.is_file():
            imgl_stale, _ = _vdc()._autonomy_session.vql_sidecar_is_stale(
                imgl_path,
                png_for_imgl,
                layer_count=len(imgl_layers),
            )
            if imgl_stale:
                stale_tried.append({"path": str(imgl_path), "reasons": ["stale_imgl_fallback"]})
                imgl_layers = []
        if imgl_layers:
            return imgl_layers, (imgl_source or cand)
    return [], cand


def _parse_vql_candidate_data(
    data: dict, cand: str, png_path: Path | None, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> dict:
    """Normalize various VQL structures (analysis, fresh capture from screenshot, imgl, etc.)."""
    if "ui_elements" in data and data.get("ui_elements"):
        return _vdc()._vql_from_ui_elements(data, cand, png_path)
    if "elements" in data and isinstance(data.get("elements"), list) and data["elements"]:
        return _vdc()._vql_from_fresh_elements(data, cand, png_path)
    sidecar_layers = _vdc()._layers_from_vdisplay_sidecar(data)
    if not sidecar_layers:
        sidecar_layers, cand = _vdc()._vql_imgl_fallback_layers(cand, allow_stale=allow_stale, stale_tried=stale_tried)
    if sidecar_layers:
        return _vdc()._vql_from_sidecar_layers(data, cand, sidecar_layers, png_path)
    prog = _vdc()._vql_from_program_wrapper(data, cand)
    if prog is not None:
        return prog
    if "screen_context" in data or "metadata" in data:
        return _vdc()._vql_from_screen_context(data, cand)
    return _vdc()._vql_metadata_default(data, cand)


def _load_vql_candidate_metadata(
    cand: str, *, allow_stale: bool, stale_tried: list[dict[str, Any]]
) -> dict | None:
    """Resolve, freshness-check, load and normalize a single VQL candidate; None to skip."""
    resolved = _vdc()._resolve_vql_candidate(cand)
    if not resolved:
        return None
    cand = resolved
    if not os.path.exists(cand):
        return None
    png_path = _vdc()._png_path_for_vql_sidecar(cand)
    if not allow_stale and _vdc()._vql_candidate_is_stale(cand, png_path, stale_tried):
        return None
    with open(cand) as f:
        data = json.load(f)
    return _vdc()._parse_vql_candidate_data(data, cand, png_path, allow_stale=allow_stale, stale_tried=stale_tried)


def load_vql_metadata(path: str | None = None, *, allow_stale: bool = False) -> dict:
    """Load VQL metadata for decide/act. Skips stale sidecars unless ``allow_stale=True``.

    During an autonomy session only ``.vdisplay/YYYY-MM-DD/.../observe/capture.png.vql.json`` is used.
    """
    candidates = _vdc()._get_vql_candidates(path)
    stale_tried: list[dict[str, Any]] = []
    for cand in candidates:
        try:
            parsed = _vdc()._load_vql_candidate_metadata(cand, allow_stale=allow_stale, stale_tried=stale_tried)
        except Exception:
            continue
        if parsed is not None:
            return parsed
    return {
        "error": "no fresh vql found",
        "tried": candidates,
        "stale_skipped": stale_tried,
        "layers": [],
        "ui_elements": [],
    }


def _resolve_vql_candidate(cand: str) -> str | None:
    """Resolve a VQL path or glob to the newest existing file."""
    import glob

    if "*" not in cand:
        return cand if os.path.exists(cand) else None
    matches = [m for m in glob.glob(cand) if os.path.isfile(m)]
    if not matches:
        return None
    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return matches[0]


def _monitor_source_slugs(source: str) -> list[str]:
    raw = source.strip().lower().replace("/", "-")
    compact = raw.replace("-", "")
    return list(dict.fromkeys([s for s in (raw, compact) if s]))


def _get_vql_candidates(path: str | None) -> list:
    """VQL sidecar search order: explicit path → active session observe → fresh koru-cont-*."""
    if path:
        return [path]
    env_path = os.environ.get("KORU_VDISPLAY_VQL_PATH", "").strip()
    if env_path:
        return [env_path]
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _vdc()._autonomy_session.session_observe_paths(session)
        return [str(vql)]
    source = os.environ.get("KORU_VDISPLAY_SOURCE", "DP-1").strip() or "DP-1"
    candidates: list[str] = []
    for slug in _vdc()._monitor_source_slugs(source):
        candidates.extend([
            f".vdisplay/koru-cont-{slug}.png.vql.json",
            f".vdisplay/koru-cont-{slug}-*.png.vql.json",
            f"/tmp/koru-cont-{slug}.png.vql.json",
            f"/tmp/koru-cont-{slug}-*.png.vql.json",
        ])
    candidates.extend([
        ".vdisplay/koru-cont-dp1.png.vql.json",
        ".vdisplay/koru-cont-dp1-*.png.vql.json",
        ".vdisplay/koru-cont-dp2-*.png.vql.json",
        "/tmp/koru-cont-dp1.png.vql.json",
        "/tmp/koru-cont-dp1-*.png.vql.json",
    ])
    best = _vdc()._freshest_populated_vql_candidate()
    if best:
        if best in candidates:
            candidates.remove(best)
        candidates.insert(0, best)
    return candidates


def _freshest_populated_vql_candidate() -> str | None:
    """Newest non-stale koru-cont VQL sidecar with a meaningful element count."""
    import glob
    best = None
    best_mt = 0
    max_age = _vdc()._autonomy_session.vql_max_age_seconds()
    now = __import__("time").time()
    for p in glob.glob(".vdisplay/koru-cont-*.vql.json"):
        if not os.path.isfile(p):
            continue
        if max_age > 0 and (now - os.path.getmtime(p)) > max_age:
            continue
        try:
            with open(p) as fh:
                data = json.load(fh)
            ec = data.get("element_count") or len(data.get("elements", []) or data.get("ui_elements", []))
            if ec and ec > 20:
                mt = os.path.getmtime(p)
                if mt > best_mt:
                    best_mt = mt
                    best = p
        except Exception:
            pass
    return best


def get_vql_target(ide: str, *, role: str | None = None, name_contains: str | None = None, label: str | None = None) -> dict | None:  # noqa: E501
    """Select target from loaded VQL ui_elements/layers by role or name/label.
    Returns dict with click_center, bounds, id for use in act (mouse nav).
    Used to close observe -> decide -> act gap when vision stub or no map.
    """
    vql = _vdc().load_vql_metadata()
    targets = vql.get("ui_elements") or vql.get("layers") or []
    for t in targets:
        if role and t.get("role") != role:
            continue
        if name_contains and name_contains.lower() not in str(t.get("label", "")).lower() and name_contains.lower() not in str(t.get("id", "")).lower():  # noqa: E501
            continue
        if label and label.lower() not in str(t.get("label", "")).lower():
            continue
        cc = t.get("click_center") or {}
        if cc:
            return {
                "id": t.get("id"),
                "role": t.get("role"),
                "click_center": cc,
                "bounds": t.get("bounds"),
                "source": vql.get("_source"),
            }
    return None


def resolve_click_for_frame(source: str = "DP-1", vql_path: str | None = None, vision_fallback: bool = True) -> dict:
    """Helper: return best click coords for a monitor/frame.
    Prefers explicit from load_vql_metadata (fresh capture or analysis).
    Can be used when vision find returns no match (e.g. "planfile" anchor) as general editor/center action.
    """
    m = _vdc().load_vql_metadata(vql_path)
    if m.get("ui_elements"):
        # Prefer first (usually the main capture frame for --source)
        for el in m.get("ui_elements", []):
            if source.lower() in str(el.get("source", "")).lower() or "dp-1" in str(el).lower() or not el.get("source"):
                if cc := el.get("click_center"):
                    return {"x": cc.get("x"), "y": cc.get("y"), "source": m.get("_source"), "note": el.get("note", "from VQL")}  # noqa: E501
        # fallback any
        el = m["ui_elements"][0]
        if cc := el.get("click_center") or el.get("center"):
            return {"x": cc.get("x") if isinstance(cc, dict) else cc[0], "y": cc.get("y") if isinstance(cc, dict) else cc[1], "source": m.get("_source")}  # noqa: E501
    # last resort frame center for 2048x1280 DP-1 crop
    return {"x": 1024, "y": 640, "source": "hardcoded-fallback", "note": "DP-1 capture frame center"}


# ---------------------------------------------------------------------------
# VQL sidecar reading lives in vdisplay (boundary proposal §1, 2026-07-22).
#
# The sidecar format is vdisplay's own contract, and vdisplay already owned
# half of the parsing through `normalize_vql_ui_elements` / `build_imgl_layers`,
# so the reader moved to `vdisplay.vql`. What stayed in koru is the freshness
# *policy*: `load_vql_metadata`, `_vql_candidate_is_stale` and
# `_vql_imgl_fallback_layers` decide whether a sidecar may be acted on, using
# autonomy-session directories and age thresholds. That is a statement about a
# run, not about a screen.
#
# These are real functions, not aliases and not a module-level `__getattr__`:
#
#   * a module-level `from vdisplay import vql` breaks `import koru` outright
#     wherever vdisplay is absent — it is an optional extra, which is why every
#     other vdisplay import in this file also sits inside a function body;
#   * PEP 562 `__getattr__` looks like it solves that, but it is only consulted
#     for `module.attr` access. Callers *inside* this module read these names as
#     globals, and LOAD_GLOBAL never consults it — the resulting NameError was
#     swallowed by the broad `except Exception` in `load_vql_metadata`, which
#     then quietly returned zero ui_elements.
#
# Defining them keeps `monkeypatch.setattr(vc, "…")` working, which the existing
# tests rely on, and the proposal asks for koru-side shims for one release cycle.
def _vdisplay_vql():
    """Import `vdisplay.vql` on demand; vdisplay is an optional extra."""
    from vdisplay import vql

    return vql


def _png_path_for_vql_sidecar(*args, **kwargs):
    return _vdc()._vdisplay_vql().png_path_for_vql_sidecar(*args, **kwargs)


def _main_vql_layer_count(*args, **kwargs):
    return _vdc()._vdisplay_vql().main_vql_layer_count(*args, **kwargs)


def _imgl_sidecar_path_for_vql(*args, **kwargs):
    return _vdc()._vdisplay_vql().imgl_sidecar_path_for_vql(*args, **kwargs)


def _layers_from_imgl_sidecar_file(*args, **kwargs):
    return _vdc()._vdisplay_vql().layers_from_imgl_sidecar_file(*args, **kwargs)


def _layers_from_vdisplay_sidecar(*args, **kwargs):
    return _vdc()._vdisplay_vql().layers_from_vdisplay_sidecar(*args, **kwargs)


def _with_embedded_capture_validation(*args, **kwargs):
    return _vdc()._vdisplay_vql().with_embedded_capture_validation(*args, **kwargs)


def _vql_from_ui_elements(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_from_ui_elements(*args, **kwargs)


def _vql_from_fresh_elements(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_from_fresh_elements(*args, **kwargs)


def _vql_from_sidecar_layers(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_from_sidecar_layers(*args, **kwargs)


def _vql_from_program_wrapper(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_from_program_wrapper(*args, **kwargs)


def _vql_from_screen_context(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_from_screen_context(*args, **kwargs)


def _vql_metadata_default(*args, **kwargs):
    return _vdc()._vdisplay_vql().vql_metadata_default(*args, **kwargs)


def _parse_fresh_vql_elements(*args, **kwargs):
    return _vdc()._vdisplay_vql().parse_fresh_vql_elements(*args, **kwargs)
