"""VQL chat-target validation helpers (extracted from vdisplay_client)."""

from __future__ import annotations

from typing import Any

VQL_TERMINAL_LABEL_NOISE = (
    ".py",
    ".ts",
    "session",
    "metadata",
    "vdisplay",
    "automation",
    "env",
    "KORU",
    "DRY_RUN",
    "PREFER",
    "LLM",
    " --source",
    "po clear",
    "recznie",
    "wpisz",
    "to do",
    "drive after",
    "Re-run",
    "audit",
    "cursor_positioning",
    "Explored",
    "passed",
    "Clear",
    "folder",
    "Gap Analysis",
    "Monitored",
    "screenshot",
    "act/",
    "ts - Cursor",
    "File Edit Selection",
    "Go Run Terminal",
    "Publish v",
    "247K",
    "Path(str(vql_path)",
    "imgl_path",
    "sidecar older than",
    "reasons.append",
    "You have folder",
    "faster responses",
)
VQL_CHAT_LABEL_HINTS = ("ask", "prompt", "message", "chat", "composer", "type")
VSCODE_FAMILY_TOP_CHAT_IDES = frozenset(
    {"cursor", "windsurf", "vscode", "vscodium", "antigravity", "code", "devin", "devin-desktop"}
)

SHELL_POLLUTION_TOKENS = (
    "KORU_",
    "DRY_RUN",
    "PREFER LLM",
    " --source",
    "po clear",
    "recznie",
    "wpisz",
    "to do",
    "drive after",
    "Re-run",
    "audit",
    "cursor_positioning",
    "Explored",
    "passed",
    "Clear",
    "Gap Analysis",
    "Monitored",
    "screenshot",
    "act/",
    "ts - Cursor",
    "File Edit",
    "Go Run Terminal",
    "Publish v",
    "247K",
    "automation-gap",
)


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def window_titles_from_vql_meta(meta: dict) -> list[str]:
    titles = _window_titles_from_layers(meta)
    if not titles:
        titles = _window_titles_from_capture_validation(meta)
    return _unique_titles(titles)


def _window_titles_from_layers(meta: dict) -> list[str]:
    titles: list[str] = []
    for layer in meta.get("ui_elements") or meta.get("layers") or []:
        title = _window_title_from_layer(layer)
        if title:
            titles.append(title)
    return titles


def _window_title_from_layer(layer: Any) -> str | None:
    if not isinstance(layer, dict):
        return None
    role = str(layer.get("role") or layer.get("kind") or "").lower()
    if role != "window":
        return None
    title = str(layer.get("label") or layer.get("text") or layer.get("title") or "").strip()
    return title or None


def _window_titles_from_capture_validation(meta: dict) -> list[str]:
    cv = meta.get("capture_validation") or {}
    if not isinstance(cv, dict):
        return []
    titles: list[str] = []
    for key in ("window_titles", "title", "capture_title"):
        titles.extend(_strings_from_capture_value(cv.get(key)))
    titles.extend(_strings_from_capture_value(cv.get("body_ide_mentions")))
    return titles


def _strings_from_capture_value(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _unique_titles(titles: list[str]) -> list[str]:
    seen: set[str] = set()
    uniq: list[str] = []
    for title in titles:
        low = title.lower()
        if low not in seen:
            seen.add(low)
            uniq.append(title)
    return uniq


def capture_title_from_meta(meta: dict | None) -> str | None:
    titles = window_titles_from_vql_meta(meta or {})
    return titles[0] if titles else None


def _coord_warnings_for_bounds(*, bw: int, bh: int) -> list[str]:
    if bw > 0 and bh > 0 and (bw < 150 or bh < 25):
        return [f"bounds_{bw}x{bh}_too_small_for_chat_composer"]
    return []


def _coord_warnings_for_label(*, label: str, y: int) -> list[str]:
    warnings: list[str] = []
    if label == "background":
        warnings.append("label_background_not_chat_composer")
    if _label_looks_like_code_file(label):
        warnings.append(f"label_{label}_looks_like_code_file_not_chat")
    if _label_looks_like_terminal_metadata(label):
        warnings.append(f"label_{label}_looks_like_terminal_not_chat")
    if _label_looks_like_vdisplay_env(label):
        warnings.append(f"label_{label}_looks_like_env_var_not_chat")
    if _has_any(label, SHELL_POLLUTION_TOKENS):
        warnings.append("label_looks_like_terminal_command_history_or_env_pollution")
    if "pycharm/jb" in label and y < 850:
        warnings.append("breadcrumb_pycharm_jb_label_but_y_too_high_for_chat_composer")
    return warnings


def _label_looks_like_code_file(label: str) -> bool:
    return any(term in label for term in {".py", ".ts"})


def _label_looks_like_terminal_metadata(label: str) -> bool:
    return label.startswith("session") or label.startswith("metadata")


def _label_looks_like_vdisplay_env(label: str) -> bool:
    normalized = label.replace("_", "").replace("=", "").replace(".", "")
    return "vdisplay_metadata_dir" in normalized


def _coord_warnings_for_jetbrains(*, x: int, y: int, canon: str, is_code_edit: bool) -> list[str]:
    if is_code_edit or canon not in {"jetbrains", "pycharm", "idea"}:
        return []
    warnings: list[str] = []
    if y < 850:
        warnings.append(f"chat_local_y={y}_below_850_likely_editor_not_bottom_right_composer")
    if x < 1100:
        warnings.append(f"chat_local_x={x}_below_1100_likely_left_panel_not_chat_corner")
    return warnings


def _coord_warnings_for_jetbrains_surface(
    *,
    x: int,
    y: int,
    target: dict[str, Any],
) -> list[str]:
    rect = target.get("surface_window_capture_local")
    if not isinstance(rect, dict):
        return []
    tlx = int(rect.get("x") or 0)
    tly = int(rect.get("y") or 0)
    ww = int(rect.get("w") or 0)
    hh = int(rect.get("h") or 0)
    if ww < 120 or hh < 160:
        return []
    warnings: list[str] = []
    rel_x = x - tlx
    rel_y = y - tly
    if rel_y < int(hh * 0.82):
        warnings.append(
            f"chat_local_y={y}_not_in_bottom_18pct_of_ide_surface_window"
        )
    if rel_x < int(ww * 0.55):
        warnings.append(
            f"chat_local_x={x}_not_in_right_45pct_of_ide_surface_window"
        )
    return warnings


def _coord_warnings_for_vscode_family(*, x: int, y: int, canon: str, is_code_edit: bool) -> list[str]:
    if is_code_edit or canon not in VSCODE_FAMILY_TOP_CHAT_IDES:
        return []
    warnings: list[str] = []
    if y >= 900:
        warnings.append(f"chat_local_y={y}_likely_status_bar_or_taskbar_not_top_composer")
    elif y >= 650:
        warnings.append(f"chat_local_y={y}_too_low_for_vscode_top_chat_composer")
    if x < 400:
        warnings.append(f"chat_local_x={x}_likely_left_sidebar_not_chat_input")
    return warnings


def validate_chat_coords_for_ide(
    *,
    x: int,
    y: int,
    ide: str,
    target: dict[str, Any],
    is_code_edit: bool = False,
) -> list[str]:
    """Heuristic warnings when VQL-derived chat coords look wrong for the IDE."""
    role = str(target.get("role") or "").lower()
    tid = str(target.get("id") or "").lower()
    if is_code_edit or role == "editor" or "editor" in tid:
        return []
    warnings: list[str] = []
    canon = _canonical_ide(ide)
    if _target_uses_fallback_center(target):
        warnings.append("target_not_from_live_vql_layers_using_fallback_center")
    bw, bh = _target_bounds_size(target)
    label = _target_label(target)
    warnings.extend(_coord_warnings_for_bounds(bw=bw, bh=bh))
    warnings.extend(_coord_warnings_for_label(label=label, y=y))
    if str(target.get("id") or "").startswith("surface:"):
        warnings.extend(_coord_warnings_for_jetbrains_surface(x=x, y=y, target=target))
    else:
        warnings.extend(_coord_warnings_for_jetbrains(x=x, y=y, canon=canon, is_code_edit=is_code_edit))
    warnings.extend(_coord_warnings_for_vscode_family(x=x, y=y, canon=canon, is_code_edit=is_code_edit))
    return warnings


def _target_uses_fallback_center(target: dict[str, Any]) -> bool:
    tid = str(target.get("id") or "")
    if tid.startswith("map:"):
        return False
    src = str(target.get("source") or "")
    note = str(target.get("note") or "").lower()
    return src in {"vql-analysis-fallback", ""} or "fallback" in note


def _target_bounds_size(target: dict[str, Any]) -> tuple[int, int]:
    bounds = target.get("bounds") or {}
    if not isinstance(bounds, dict):
        return 0, 0
    return (
        int(bounds.get("w") or bounds.get("width") or 0),
        int(bounds.get("h") or bounds.get("height") or 0),
    )


def _target_label(target: dict[str, Any]) -> str:
    return str(target.get("label") or target.get("note") or "").lower()


def _target_geometry(
    target: dict[str, Any],
    *,
    x: int | None,
    y: int | None,
) -> tuple[int, int, int, int, int, bool, str]:
    cc = target.get("click_center") or {}
    lx = int(x if x is not None else cc.get("x") or 0)
    ly = int(y if y is not None else cc.get("y") or 0)
    bw, bh = _target_bounds_size(target)
    has_bounds = bw > 0 and bh > 0
    return lx, ly, bw, bh, bw * bh if has_bounds else 0, has_bounds, _target_label(target)


def _label_ok_for_chat(*, label: str, has_bounds: bool, bw: int, bh: int) -> bool:
    if label == "background":
        return False
    if not label:
        return not has_bounds or (bw >= 200 and bh >= 25)
    return any(hint in label for hint in VQL_CHAT_LABEL_HINTS)


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)


def _collect_vql_validation_errors(
    *,
    is_code_edit: bool,
    is_map: bool,
    app_match: bool,
    capture_mismatch: dict[str, Any] | None,
    method: str,
    has_bounds: bool,
    vql_element_size_ok: bool,
    label: str,
    area: int,
    label_ok: bool,
    target: dict[str, Any],
    bw: int,
    bh: int,
) -> list[str]:
    if is_code_edit:
        return []
    errors = _capture_validation_errors(app_match=app_match)
    errors.extend(
        _map_validation_errors(
            is_map=is_map,
            capture_mismatch=capture_mismatch,
            method=method,
        )
    )
    if not is_map:
        errors.extend(
            _live_vql_validation_errors(
                has_bounds=has_bounds,
                vql_element_size_ok=vql_element_size_ok,
                label=label,
                area=area,
                label_ok=label_ok,
                target=target,
                bw=bw,
                bh=bh,
            )
        )
    return errors


def _capture_validation_errors(*, app_match: bool) -> list[str]:
    if not app_match:
        return ["vql_invalid_for_chat_capture_mismatch"]
    return []


def _map_validation_errors(
    *,
    is_map: bool,
    capture_mismatch: dict[str, Any] | None,
    method: str,
) -> list[str]:
    if is_map and capture_mismatch:
        return ["used_map_because_mismatch_or_bad_element"]
    if is_map and method == "map_fallback_after_bad_corner":
        return ["used_map_because_mismatch_or_bad_element"]
    return []


def _live_vql_validation_errors(
    *,
    has_bounds: bool,
    vql_element_size_ok: bool,
    label: str,
    area: int,
    label_ok: bool,
    target: dict[str, Any],
    bw: int,
    bh: int,
) -> list[str]:
    errors: list[str] = []
    if has_bounds and not vql_element_size_ok:
        errors.append(f"vql_element_too_small_for_chat_composer_{bw}x{bh}")
    if label == "background" or (label in {"", "background"} and has_bounds and area < 5000):
        errors.append("vql_label_background_not_composer")
    if _has_any(label, VQL_TERMINAL_LABEL_NOISE):
        errors.append(f"vql_label_terminal_noise:{label[:40]}")
    if _has_any(label, SHELL_POLLUTION_TOKENS):
        errors.append("vql_label_shell_pollution_from_terminal_text")
    if not label_ok and has_bounds:
        errors.append("vql_label_not_chat_composer")
    if _target_confidence_too_low(target):
        errors.append("vql_confidence_too_low")
    return errors


def _target_confidence_too_low(target: dict[str, Any]) -> bool:
    confidence = target.get("confidence")
    return isinstance(confidence, (int, float)) and float(confidence) < 0.25


def _vql_valid(*, is_code_edit: bool, is_map: bool, validation_errors: list[str]) -> bool:
    return not (not is_code_edit and not is_map and validation_errors)


def _used_map_because_mismatch_or_bad_element(
    *,
    is_map: bool,
    capture_mismatch: dict[str, Any] | None,
    method: str,
) -> bool:
    return is_map and (
        bool(capture_mismatch)
        or method in {"map_fallback_after_bad_corner", "map_calibrated_on_mismatch"}
    )


def validate_vql_chat_target(
    target: dict[str, Any],
    *,
    ide: str,
    meta: dict | None = None,
    capture_mismatch: dict[str, Any] | None = None,
    selection_method: str | None = None,
    is_code_edit: bool = False,
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    """Hard validation of a VQL/map chat target before actuation (audit + inference_ok)."""
    meta = meta or {}
    method = str(selection_method or target.get("selection_method") or "")
    is_map = method.startswith("map_") or str(target.get("id") or "").startswith("map:")
    lx, ly, bw, bh, area, has_bounds, label = _target_geometry(target, x=x, y=y)
    vql_element_size_ok = (not has_bounds) or (bw >= 200 and bh >= 25)
    label_ok = _label_ok_for_chat(label=label, has_bounds=has_bounds, bw=bw, bh=bh)
    app_match = capture_mismatch is None
    coord_warnings = validate_chat_coords_for_ide(
        x=lx,
        y=ly,
        ide=ide,
        target=target,
        is_code_edit=is_code_edit,
    )
    validation_errors = _collect_vql_validation_errors(
        is_code_edit=is_code_edit,
        is_map=is_map,
        app_match=app_match,
        capture_mismatch=capture_mismatch,
        method=method,
        has_bounds=has_bounds,
        vql_element_size_ok=vql_element_size_ok,
        label=label,
        area=area,
        label_ok=label_ok,
        target=target,
        bw=bw,
        bh=bh,
    )
    vql_valid = _vql_valid(
        is_code_edit=is_code_edit,
        is_map=is_map,
        validation_errors=validation_errors,
    )
    return {
        "ok": vql_valid and app_match and not coord_warnings,
        "vql_valid": vql_valid,
        "vql_element_size_ok": vql_element_size_ok,
        "app_match": app_match,
        "capture_title": capture_title_from_meta(meta),
        "selection_method": method or None,
        "is_map_target": is_map,
        "validation_errors": validation_errors,
        "coord_warnings": coord_warnings,
        "bounds": {"w": bw, "h": bh} if has_bounds else None,
        "label": label[:80] if label else None,
        "used_map_because_mismatch_or_bad_element": _used_map_because_mismatch_or_bad_element(
            is_map=is_map,
            capture_mismatch=capture_mismatch,
            method=method,
        ),
    }


__all__ = [
    "capture_title_from_meta",
    "validate_chat_coords_for_ide",
    "validate_vql_chat_target",
    "window_titles_from_vql_meta",
]
