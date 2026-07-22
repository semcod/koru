"""Finding an IDE's chat input on screen: scoring VQL layers per IDE family.

Moved here from ``koru/src/koru/integrations/photo_vql_target.py`` on
2026-07-22. The heuristics below are knowledge about *IDEs* — where JetBrains
puts its composer, how a VS Code-family top chat differs from a status bar,
what a plausible input box looks like — which is koruide's domain, not
vdisplay's. The boundary proposal filed this file under "vdisplay owns screen
truth"; measuring it showed 31 of 34 functions never touch a screen fact at
all, only IDE layout.

What did not come along: recognising the *host's own* terminal output in a
capture. koru's token lists for that (``KORU_``, ``DRY_RUN``, Polish operator
prompts) describe koru, not any IDE, so they stay in koru and arrive through
:func:`set_label_noise_tokens` — the same injection idiom
``koruide.__init__`` already uses for its activity sink. With no tokens
registered the penalties are simply zero, which keeps this module usable
standalone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Host-declared noise vocabularies; empty until a host registers its own.
_LABEL_NOISE_TOKENS: tuple[str, ...] = ()
_SHELL_POLLUTION_TOKENS: tuple[str, ...] = ()


def set_label_noise_tokens(
    *,
    label_noise: tuple[str, ...] = (),
    shell_pollution: tuple[str, ...] = (),
) -> None:
    """Declare which labels betray the host's own terminal rather than an IDE.

    A capture often includes the terminal that drives the automation, so its
    own output can score as a chat input. Only the host knows what its output
    looks like, hence the injection.
    """
    global _LABEL_NOISE_TOKENS, _SHELL_POLLUTION_TOKENS
    _LABEL_NOISE_TOKENS = tuple(label_noise)
    _SHELL_POLLUTION_TOKENS = tuple(shell_pollution)


def label_noise_tokens() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the registered (label_noise, shell_pollution) vocabularies."""
    return _LABEL_NOISE_TOKENS, _SHELL_POLLUTION_TOKENS

VSCODE_FAMILY_TOP_CHAT_IDES = frozenset(
    {"cursor", "windsurf", "vscode", "vscodium", "antigravity", "code", "devin", "devin-desktop"}
)
VSCODE_CHAT_TEXT_HINTS = (
    "ask anything",
    "ctrl+shift",
    "type a message",
    "ask a question",
    "message",
    "composer",
    "chat",
)
VSCODE_STATUS_BAR_HINTS = (
    "windsurf",
    "pre-release",
    "python 3",
    " spaces",
    "koru)",
)
VDISPLAY_OVERLAY_STRONG_TOKENS = (
    "choose monitor",
    "screen recording settings",
    "vdisplay share manager",
)
VDISPLAY_OVERLAY_TOKENS = (
    "vdisplay share",
    "vdisplay screen",
    "screen recording",
    "choose monitor",
    "share manager",
)


@dataclass(frozen=True)
class _InputMetrics:
    cx: int
    cy: int
    label: str
    bw: int
    bh: int
    area: int


def _layer_role(layer: dict[str, Any]) -> str:
    return str(layer.get("role") or layer.get("kind") or "").lower()


def _layer_label(layer: dict[str, Any]) -> str:
    return str(layer.get("label") or layer.get("text") or "").lower()


def _layer_bounds(layer: dict[str, Any]) -> dict[str, Any]:
    bounds = layer.get("bounds") or layer.get("bbox") or {}
    return bounds if isinstance(bounds, dict) else {}


def _layer_click_center(layer: dict[str, Any]) -> dict[str, int] | None:
    cc = layer.get("click_center") or layer.get("center")
    if not isinstance(cc, dict) or "x" not in cc or "y" not in cc:
        return None
    return {"x": int(cc.get("x") or 0), "y": int(cc.get("y") or 0)}


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def _input_metrics(layer: dict[str, Any]) -> _InputMetrics | None:
    if _layer_role(layer) != "input":
        return None
    click_center = _layer_click_center(layer)
    if click_center is None:
        return None
    bounds = _layer_bounds(layer)
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    area = bw * bh if bw > 0 and bh > 0 else 0
    return _InputMetrics(
        cx=click_center["x"],
        cy=click_center["y"],
        label=_layer_label(layer),
        bw=bw,
        bh=bh,
        area=area,
    )


def _has_any(text: str, tokens: tuple[str, ...] | list[str]) -> bool:
    return any(token.lower() in text for token in tokens)


def _terminal_or_shell_noise(label: str) -> bool:
    return _has_any(label, _LABEL_NOISE_TOKENS) or _has_any(label, _SHELL_POLLUTION_TOKENS)


def vql_layers_show_vdisplay_overlay(layers: list[dict[str, Any]]) -> bool:
    """True when the screenshot includes the vdisplay Electron share manager UI."""
    hits = 0
    for layer in layers:
        label = _layer_label(layer)
        if _has_any(label, VDISPLAY_OVERLAY_STRONG_TOKENS):
            return True
        if _has_any(label, VDISPLAY_OVERLAY_TOKENS):
            hits += 1
    return hits >= 2


def score_photo_vql_chat_input(layer: dict[str, Any], *, ide: str = "auto") -> float | None:
    metrics = _input_metrics(layer)
    if metrics is None:
        return None
    if _canonical_ide(ide) in VSCODE_FAMILY_TOP_CHAT_IDES:
        return _score_vscode_metrics(metrics)
    return _score_jetbrains_metrics(metrics)


def _score_jetbrains_metrics(metrics: _InputMetrics) -> float:
    score = _jetbrains_position_score(metrics)
    score += _jetbrains_size_score(metrics)
    score += _label_noise_penalty(metrics.label)
    return score


def _jetbrains_position_score(metrics: _InputMetrics) -> float:
    score = float(metrics.cy)
    score += 400.0 if metrics.cx > 1400 else 0.0
    score += 200.0 if metrics.cx > 1100 else 0.0
    if metrics.cx < 900:
        score -= 1500.0
    return score - 800.0 if metrics.cy < 700 else score


def _jetbrains_size_score(metrics: _InputMetrics) -> float:
    if metrics.area <= 0:
        return 0.0
    score = 0.0
    if metrics.bw >= 250 and metrics.bh >= 28:
        score += 500.0
    elif metrics.bw >= 200 and metrics.bh >= 25:
        score += 300.0
    elif metrics.bw < 180 or metrics.bh < 22:
        score -= 900.0
    elif metrics.bw < 200 or metrics.bh < 25:
        score -= 500.0
    if metrics.label in {"background", ""} and (metrics.bw < 200 or metrics.bh < 25):
        score -= 900.0
    return score


def _label_noise_penalty(label: str) -> float:
    penalty = 0.0
    if _has_any(label, _LABEL_NOISE_TOKENS):
        penalty -= 1200.0
    if _has_any(label, _SHELL_POLLUTION_TOKENS):
        penalty -= 1500.0
    return penalty


def _score_vscode_top_chat_input(
    *,
    cx: int,
    cy: int,
    label: str,
    bw: int,
    bh: int,
    area: int,
) -> float:
    """Windsurf/Cursor chat composer is at the top ('Ask anything…'), not bottom-right."""
    return _score_vscode_metrics(_InputMetrics(cx=cx, cy=cy, label=label, bw=bw, bh=bh, area=area))


def _score_vscode_metrics(metrics: _InputMetrics) -> float:
    score = 1200.0 - float(metrics.cy)
    score += _vscode_label_score(metrics.label)
    score += _vscode_position_score(metrics.cy)
    score += _vscode_size_score(metrics)
    score += _label_noise_penalty(metrics.label)
    return score


def _vscode_label_score(label: str) -> float:
    score = 0.0
    if _has_any(label, VSCODE_CHAT_TEXT_HINTS):
        score += 2500.0
    if re.search(r"\bask\b", label):
        score += 800.0
    if _has_any(label, VSCODE_STATUS_BAR_HINTS):
        score -= 4000.0
    if "tom@" in label or "github/" in label or "venv" in label:
        score -= 3500.0
    return score


def _vscode_position_score(cy: int) -> float:
    if cy >= 900:
        return -4500.0
    if cy >= 700:
        return -1500.0
    if cy <= 220:
        return 600.0
    if cy <= 350:
        return 250.0
    return 0.0


def _vscode_size_score(metrics: _InputMetrics) -> float:
    score = 0.0
    if metrics.label in {"", "background"} and metrics.cy >= 700:
        score -= 2000.0
    if metrics.area > 0:
        if metrics.bw >= 180 and metrics.bh >= 20:
            score += 400.0
        elif metrics.bw < 80 or metrics.bh < 16:
            score -= 400.0
    return score


def photo_vql_chat_input_candidates(
    layers: list[dict[str, Any]],
    *,
    limit: int = 8,
    ide: str = "auto",
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for layer in layers:
        score = score_photo_vql_chat_input(layer, ide=ide)
        if score is None:
            continue
        ranked.append((score, _chat_candidate_from_layer(layer)))
    ranked.sort(key=lambda item: -item[0])
    return [item[1] for item in ranked[:limit]]


def _chat_candidate_from_layer(layer: dict[str, Any]) -> dict[str, Any]:
    click_center = _layer_click_center(layer) or {"x": 0, "y": 0}
    return {
        "id": layer.get("id"),
        "role": _layer_role(layer),
        "label": _layer_label(layer)[:80],
        "click_center": {"x": click_center["x"], "y": click_center["y"]},
        "bounds": _layer_bounds(layer),
    }


def vscode_family_top_chat_rejected(candidate: dict[str, Any]) -> bool:
    click_center = candidate.get("click_center") or {}
    cy = int(click_center.get("y") or 0)
    label = str(candidate.get("label") or "").lower()
    if cy >= 900:
        return True
    if cy >= 650 and _has_any(label, VSCODE_STATUS_BAR_HINTS):
        return True
    if "tom@" in label or "github/" in label:
        return True
    return False


def vscode_family_chat_target_from_layers(
    layers: list[dict[str, Any]],
    *,
    ide: str = "auto",
    source: str | None = None,
) -> dict[str, Any] | None:
    """Prefer top chat/composer inputs for VS Code-family IDEs (Windsurf, Cursor, …)."""
    candidates = photo_vql_chat_input_candidates(layers, limit=3, ide=ide)
    if not candidates:
        return None
    best = candidates[0]
    if vscode_family_top_chat_rejected(best):
        return None
    return _target_from_candidate(
        best,
        note=f"VS Code-family top chat heuristic ({source})",
        source=source,
    )


def jetbrains_corner_rejected(corner: dict[str, Any]) -> bool:
    click_center = corner.get("click_center") or {}
    bounds = _target_bounds(corner)
    label = str(corner.get("label") or "").lower()
    cx = int(click_center.get("x") or 0)
    return (
        cx < 900
        or int(click_center.get("y") or 0) < 850
        or _target_bounds_too_small(bounds)
        or label == "background"
        or _terminal_or_shell_noise(label)
    )


def _target_bounds(target: dict[str, Any]) -> dict[str, int]:
    raw = target.get("bounds") or {}
    if not isinstance(raw, dict):
        return {"w": 0, "h": 0}
    return {
        "w": int(raw.get("w") or raw.get("width") or 0),
        "h": int(raw.get("h") or raw.get("height") or 0),
    }


def _target_bounds_too_small(bounds: dict[str, int]) -> bool:
    bw = bounds.get("w", 0)
    bh = bounds.get("h", 0)
    return bw > 0 and bh > 0 and (bw < 200 or bh < 25)


def jetbrains_chat_corner_target_from_layers(
    layers: list[dict[str, Any]],
    *,
    source: str | None = None,
) -> dict[str, Any] | None:
    """Prefer bottom-right composer inputs for JetBrains AI chat on rotated DP-2."""
    candidates = photo_vql_chat_input_candidates(layers, limit=1)
    if not candidates:
        return None
    best = candidates[0]
    if jetbrains_corner_rejected(best):
        return None
    return _target_from_candidate(
        best,
        note=f"JetBrains chat corner heuristic (bottom-right input; {source})",
        source=source,
    )


def _surface_window_rect(surface: dict[str, Any], source: str) -> tuple[int, int, int, int] | None:
    """Validated window rect from a correlated IDE surface (None when unusable)."""
    monitor_name = str(surface.get("monitor_name") or "").strip()
    if monitor_name and monitor_name != source:
        return None
    name = str(surface.get("display_name") or "").lower()
    if "toolbox" in name:
        return None
    bounds = surface.get("bounds")
    if not isinstance(bounds, dict):
        return None
    x = int(bounds.get("x") or 0)
    y = int(bounds.get("y") or 0)
    w = int(bounds.get("width") or 0)
    h = int(bounds.get("height") or 0)
    if w < 240 or h < 320:
        return None
    return x, y, w, h


def _composer_capture_point(
    *,
    win_x: int,
    win_y: int,
    win_w: int,
    win_h: int,
    gx: int,
    gy: int,
    coordinate_map: Any,
) -> tuple[int, int, tuple[int, int, int, int] | None] | None:
    local_rect = coordinate_map.global_rect_to_local(
        (win_x, win_y, win_w, win_h),
        min_width=120,
        min_height=160,
    )
    if local_rect is None:
        local = coordinate_map.global_to_local(gx, gy)
        if local is None:
            return None
        lx_i, ly_i = local
    else:
        tlx, tly, rect_w, rect_h = local_rect
        lx_i = tlx + int(rect_w * 0.82)
        ly_i = tly + rect_h - max(32, int(rect_h * 0.05))
    return lx_i, ly_i, local_rect


def _surface_target_payload(
    *,
    surface: dict[str, Any],
    source: str,
    lx_i: int,
    ly_i: int,
    gx: int,
    gy: int,
    local_rect: tuple[int, int, int, int] | None,
) -> dict[str, Any]:
    monitor_name = str(surface.get("monitor_name") or "").strip()
    out: dict[str, Any] = {
        "click_center": {"x": lx_i, "y": ly_i},
        "id": "surface:jetbrains-chat",
        "role": "input",
        "note": (
            f"JetBrains chat from IDE surface bounds "
            f"({surface.get('display_name') or 'PyCharm'} on {monitor_name or source})"
        ),
        "source": f"surface:{surface.get('pid') or 'jetbrains'}",
        "map_global": {"x": gx, "y": gy},
    }
    if local_rect is not None:
        tlx, tly, rect_w, rect_h = local_rect
        out["surface_window_capture_local"] = {
            "x": tlx,
            "y": tly,
            "w": rect_w,
            "h": rect_h,
        }
    return out


def jetbrains_chat_target_from_surface(
    surface: dict[str, Any],
    *,
    capture_meta: dict[str, Any],
    source: str,
) -> dict[str, Any] | None:
    """Estimate JetBrains AI chat composer from correlated IDE surface bounds (Wayland/native)."""
    if not isinstance(surface, dict):
        return None
    rect = _surface_window_rect(surface, source)
    if rect is None:
        return None
    x, y, w, h = rect

    try:
        from vdisplay.capture import compile_capture_coordinate_map

        coordinate_map = compile_capture_coordinate_map(
            capture_meta,
            source=source,
            default_size=(2048, 1280),
        )
    except Exception:
        return None
    clamped = coordinate_map.clamp_global_rect(
        (x, y, w, h),
        min_width=240,
        min_height=320,
    )
    if clamped is None:
        return None
    win_x, win_y, win_w, win_h = clamped

    # AI assistant panel sits on the right; composer is near the bottom of the IDE frame.
    gx = win_x + win_w - max(48, int(win_w * 0.10))
    gy = win_y + win_h - max(40, int(win_h * 0.05))
    point = _composer_capture_point(
        win_x=win_x,
        win_y=win_y,
        win_w=win_w,
        win_h=win_h,
        gx=gx,
        gy=gy,
        coordinate_map=coordinate_map,
    )
    if point is None:
        return None
    lx_i, ly_i, local_rect = point

    png_w = coordinate_map.capture_width
    png_h = coordinate_map.capture_height
    if lx_i < 0 or ly_i < 0 or lx_i >= png_w or ly_i >= png_h:
        return None
    return _surface_target_payload(
        surface=surface,
        source=source,
        lx_i=lx_i,
        ly_i=ly_i,
        gx=gx,
        gy=gy,
        local_rect=local_rect,
    )


def _target_from_candidate(
    candidate: dict[str, Any],
    *,
    note: str,
    source: str | None,
) -> dict[str, Any]:
    return {
        "click_center": candidate.get("click_center") or {},
        "id": candidate.get("id"),
        "role": candidate.get("role") or "input",
        "bounds": candidate.get("bounds"),
        "label": candidate.get("label"),
        "note": note,
        "source": source,
    }


__all__ = [
    "VSCODE_FAMILY_TOP_CHAT_IDES",
    "jetbrains_chat_corner_target_from_layers",
    "jetbrains_chat_target_from_surface",
    "jetbrains_corner_rejected",
    "photo_vql_chat_input_candidates",
    "score_photo_vql_chat_input",
    "set_label_noise_tokens",
    "label_noise_tokens",
    "vql_layers_show_vdisplay_overlay",
    "vscode_family_chat_target_from_layers",
    "vscode_family_top_chat_rejected",
]
