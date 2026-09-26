"""Photo-VQL chat target resolution extracted from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import functools
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("koru.integrations.vdisplay_client")


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _resolve_vql_chat_target(ide: str, hints: dict) -> dict | None:
    """Resolve chat target using VQL metadata for precise mouse nav on second monitor (DP-1).
    Used in autonomous PyCharm/JetBrains control via vdisplay + VQL centers (e.g. 1024,640).
    """
    vql_target = _vdc()._find_vql_chat_target(ide)
    if not vql_target and ide in ("pycharm", "jetbrains"):
        vql_target = {"click_center": {"x": 1024, "y": 640, "note": "PyCharm/JetBrains editor area on DP-1 second monitor from VQL"}}  # noqa: E501
    if vql_target:
        return _vdc()._extract_vql_click_from_target(vql_target)
    return None


def _find_vql_chat_target(ide: str) -> dict | None:
    """Helper extracted to reduce CC."""
    return _vdc().get_vql_target(ide, role="input", name_contains="chat") or _vdc().get_vql_target(ide, role="input") or _vdc().get_vql_target(ide, label="chat")  # noqa: E501


def _extract_vql_click_from_target(vql_target: dict) -> dict:
    """Helper extracted to reduce CC in _resolve_vql_chat_target (autonomous refactor)."""
    return {
        "id": vql_target.get("id", "vql-chat"),
        "backend": "vql",
        "role": vql_target.get("role"),
        "click_point": vql_target.get("click_center"),
        "note": f"VQL target from {vql_target.get('source', 'VQL analysis for second monitor')}"
    }


def _get_pycharm_vql_editor_center():
    """PyCharm specific VQL target for editor on second monitor (DP-1), using VQL click 1024,640 as if clicked in PyCharm on DP-1."""  # noqa: E501
    return {"click_center": {"x": 1024, "y": 640, "note": "PyCharm editor area on DP-1 second monitor from VQL (autonomous click at 1024,640)"}}  # noqa: E501


def _get_jetbrains_pycharm_chat_center():
    """Shim: prefer photo VQL based locate for chat window + mouse + kb focus (see get_vql_chat_target_from_photo)."""
    # From current foto screen VQL (31 elems), main editor/chat area on DP-1
    return {"x": 1024, "y": 640, "note": "Chat window area from screen photo VQL (use move_mouse_to_vql_target_and_focus_keyboard for real mouse+focus)"}  # noqa: E501


def _photo_vql_elements() -> tuple[list[dict], str | None]:
    vql = _vdc().load_vql_metadata()
    els = vql.get("ui_elements") or vql.get("layers") or []
    return els, vql.get("_source")


def _live_surface_capture_meta(source: str) -> dict[str, Any]:
    """Fresh VDisplay-owned snapshot for surface-based pointer math."""
    from vdisplay.capture import resolve_live_capture_meta

    return resolve_live_capture_meta(source, default_size=(2048, 1280))


def _jetbrains_surface_chat_target(*, ide: str, source: str | None = None) -> dict[str, Any] | None:
    """Chat composer from PyCharm surface bounds when map/VQL are unreliable."""
    try:
        resolved_source, probe = _vdc()._resolve_vdisplay_source_for_ide(ide)
    except Exception:
        return None
    effective_source = (source or resolved_source or _vdc()._vdisplay_source_for_ide(ide)).strip()
    if not probe.get("ide_surface_best"):
        try:
            probe = _vdc()._desktop_probe(ide=ide, source=effective_source)
        except Exception:
            return None
    best = probe.get("ide_surface_best")
    if not isinstance(best, dict):
        return None
    if isinstance(best.get("bounds"), dict):
        surface = best
    else:
        pid = best.get("pid")
        surface = next(
            (
                row
                for row in probe.get("ide_surfaces") or []
                if isinstance(row, dict) and row.get("pid") == pid
            ),
            best,
        )
    capture_meta = _vdc()._live_surface_capture_meta(effective_source)
    return _vdc()._jetbrains_chat_target_from_surface(
        surface,
        capture_meta=capture_meta,
        source=effective_source,
    )


def _chat_target_validation_accepts(target: dict[str, Any]) -> bool:
    validation = target.get("vql_validation")
    if not isinstance(validation, dict):
        return True
    if validation.get("validation_errors"):
        return False
    if validation.get("coord_warnings"):
        return False
    if validation.get("ok") is False:
        return False
    return True


def _vql_file_for_positioning(src: Any) -> str | None:
    """VQL sidecar path for cursor-positioning logs (None for non-sidecar sources)."""
    return src if isinstance(src, str) and str(src).endswith(".vql.json") else None


def _photo_vql_jetbrains_chat_flow(
    *,
    canon: str,
    src_name: str,
    src: Any,
    els: list,
    empty_layers: bool,
    mismatch: dict[str, Any] | None,
    is_polluted: bool,
    finalize: Any,
    try_llm: Any,
) -> dict[str, Any] | None:
    """JetBrains chat-target selection cascade (LLM vision, surface bounds, map, corner)."""
    if _vdc()._photo_vql_needs_vision_or_map(
        mismatch=mismatch,
        empty_layers=empty_layers,
        polluted=is_polluted,
    ):
        map_hint = _vdc()._map_chat_target_capture_local(ide=canon, source=src_name)
        llm_target = try_llm(map_hint=map_hint)
        if llm_target:
            llm_target = finalize(llm_target, method="llm_vision_detect")
            _vdc()._log_vql_cursor_positioning_at_command(
                llm_target,
                stage="vql_target_selection_llm_vision",
                ide=canon,
                source=src_name,
                final_local=llm_target.get("click_center", {}),
                vql_file=_vdc()._vql_file_for_positioning(src),
            )
            return llm_target
        surface_target = _vdc()._jetbrains_surface_chat_target(ide=canon, source=src_name)
        if surface_target:
            surface_target = finalize(surface_target, method="jetbrains_surface_bounds")
            if _vdc()._chat_target_validation_accepts(surface_target):
                _vdc()._log_vql_cursor_positioning_at_command(
                    surface_target,
                    stage="vql_target_selection_jetbrains_surface",
                    ide=canon,
                    source=src_name,
                    final_local=surface_target.get("click_center", {}),
                    final_global=surface_target.get("map_global"),
                    vql_file=_vdc()._vql_file_for_positioning(src),
                )
                return surface_target
            logger.warning(
                "VQL_CHAT_TARGET_REJECTED ide=%s method=jetbrains_surface_bounds validation=%s",
                canon,
                surface_target.get("vql_validation"),
            )
        # Distrust VQL layers; prefer calibrated map when LLM unavailable.
        map_target = map_hint
        if map_target:
            method = _vdc()._jetbrains_map_selection_method(empty_layers=empty_layers)
            stage = _vdc()._jetbrains_map_selection_stage(empty_layers=empty_layers)
            map_target = finalize(map_target, method=method)
            _vdc()._log_vql_cursor_positioning_at_command(
                map_target,
                stage=stage,
                ide=canon,
                source=src_name,
                final_local=map_target.get("click_center", {}),
                final_global=map_target.get("map_global"),
                vql_file=_vdc()._vql_file_for_positioning(src),
            )
            return map_target
    corner = _vdc()._jetbrains_chat_corner_target_from_layers(els, source=src)
    if corner:
        corner = finalize(corner, method="jetbrains_corner_heuristic")
        _vdc()._log_vql_cursor_positioning_at_command(
            corner,
            stage="vql_target_selection_jetbrains_corner",
            ide=canon,
            source=src_name,
            final_local=corner.get("click_center", {}),
            vql_file=_vdc()._vql_file_for_positioning(src),
        )
        return corner
    map_target = _vdc()._map_chat_target_capture_local(ide=canon, source=src_name)
    if map_target:
        map_target = finalize(map_target, method="map_calibrated")
        _vdc()._log_vql_cursor_positioning_at_command(
            map_target,
            stage="vql_target_selection_jetbrains_map",
            ide=canon,
            source=src_name,
            final_local=map_target.get("click_center", {}),
            final_global=map_target.get("map_global"),
            vql_file=_vdc()._vql_file_for_positioning(src),
        )
        return map_target
    return None


def _photo_vql_vscode_chat_flow(
    *,
    canon: str,
    src_name: str,
    src: Any,
    els: list,
    empty_layers: bool,
    mismatch: dict[str, Any] | None,
    is_polluted: bool,
    finalize: Any,
    try_llm: Any,
) -> dict[str, Any] | None:
    """VSCode-family chat-target selection (LLM vision on mismatch, then top-chat heuristic)."""
    if _vdc()._photo_vql_needs_vision_or_map(
        mismatch=mismatch,
        empty_layers=empty_layers,
        polluted=is_polluted,
    ):
        llm_target = try_llm()
        if llm_target:
            llm_target = finalize(llm_target, method="llm_vision_detect")
            return llm_target
    top_chat = _vdc()._vscode_family_chat_target_from_layers(els, ide=canon, source=src)
    if top_chat:
        top_chat = finalize(top_chat, method="vscode_top_chat_heuristic")
        _vdc()._log_vql_cursor_positioning_at_command(
            top_chat,
            stage="vql_target_selection_vscode_top_chat",
            ide=canon,
            source=src_name,
            final_local=top_chat.get("click_center", {}),
            vql_file=_vdc()._vql_file_for_positioning(src),
        )
        return top_chat
    return None


def _try_ocr_anchor_chat_target(*, ide: str, source: str) -> dict[str, Any] | None:
    """Deterministic chat-input target from the OCR placeholder bbox, or None."""
    try:
        from vdisplay.control.vision_chat_detect import ocr_anchor_chat_target
    except ImportError:
        return None
    png = _vdc()._resolve_photo_png_path_from_vql(source=source)
    if not png:
        return None
    try:
        data = Path(png).read_bytes()
    except OSError:
        return None
    try:
        return ocr_anchor_chat_target(data, ide=ide)
    except Exception:
        return None


def _vql_chat_canonical_ide(*, ide: str) -> str:
    """Canonical IDE name with the KORU_DRIVE_IDE environment fallback."""
    canon = _vdc()._canonical_ide(ide)
    if canon in {"", "auto"}:
        canon = _vdc()._canonical_ide(os.environ.get("KORU_DRIVE_IDE", "auto"))
    return canon


def _vql_chat_source_name(*, canon: str) -> str:
    """Explicit KORU_VDISPLAY_SOURCE override or the IDE-resolved vdisplay source."""
    explicit_source = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit_source:
        return explicit_source
    name, _ = _vdc()._resolve_vdisplay_source_for_ide(canon)
    return name


def _vql_chat_selection_context(*, ide: str) -> dict[str, Any]:
    """Collect VQL layers, canonical IDE, candidates, source and pollution context."""
    els, src = _vdc()._photo_vql_elements()
    canon = _vdc()._vql_chat_canonical_ide(ide=ide)
    candidates = _vdc()._photo_vql_chat_input_candidates(els, limit=8, ide=canon)

    # Detect terminal pollution in VQL (common on DP-2 when control terminal text is visible in screenshot).
    # If many candidates look like shell/env/command history (from the log's fake "PREFER LLM", "KORU_*", "po clear" etc.),  # noqa: E501
    # treat as polluted and force map for jetbrains (VQL is unreliable).
    return {
        "ide": canon,
        "source": _vdc()._vql_chat_source_name(canon=canon),
        "vql_file": src,
        "elements": els,
        "candidates": candidates,
        "polluted": _vdc()._vql_candidates_polluted(candidates) or _vdc()._vql_layers_show_vdisplay_overlay(els),
        "mismatch": _vdc()._photo_vql_ide_capture_mismatch(ide=canon) if canon not in {"", "auto"} else None,
        "empty_layers": not els,
        "session": _vdc()._autonomy_session.active_session_dir(),
    }


def _log_vql_chat_candidates(context: dict[str, Any]) -> None:
    """Log the VQL chat-target candidates and persist the decide-phase snapshot."""
    logger.info(
        "VQL_CHAT_TARGET_CANDIDATES ide=%s source=%s vql_file=%s layer_count=%d candidates=%s polluted=%s",
        context["ide"],
        context["source"],
        context["vql_file"],
        len(context["elements"]),
        json.dumps(context["candidates"], default=str)[:1200],
        context["polluted"],
    )
    session = context.get("session")
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(
            session,
            "decide",
            "vql_chat_candidates",
            {
                "vql_source": context["vql_file"],
                "layer_count": len(context["elements"]),
                "candidates": context["candidates"],
                "ide": context["ide"],
            },
        )


def _surface_trusted_validation_patch(validation: dict[str, Any]) -> dict[str, Any]:
    """Patch validation for trusted surface-bounds targets: ok stays true unless hard errors exist."""
    patched = dict(validation)
    patched["surface_bounds_trusted"] = True
    if not validation.get("validation_errors") and not validation.get("coord_warnings"):
        patched["ok"] = bool(validation.get("vql_valid", True)) and bool(validation.get("app_match", True))
    return patched


def _finalize_vql_chat_target(
    target: dict[str, Any],
    *,
    method: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Attach VQL candidates/validation metadata and persist the selected chat target."""
    out = {
        **target,
        "vql_candidates": context["candidates"],
        "vql_layers_count": len(context["elements"]),
        "selection_method": method,
    }
    eff_mismatch = (
        None if method == "jetbrains_surface_bounds" and _vdc()._surface_only_fallback_active() else context["mismatch"]
    )
    validation = _vdc().validate_vql_chat_target(
        out,
        ide=context["ide"],
        meta=_vdc().load_vql_metadata(allow_stale=True),
        capture_mismatch=eff_mismatch,
        selection_method=method,
    )
    if _vdc()._surface_bounds_target_trusted(target=out, method=method):
        validation = _vdc()._surface_trusted_validation_patch(validation)
    out["vql_validation"] = validation
    session = context.get("session")
    if session is not None:
        _vdc()._autonomy_session.persist_autonomy_phase(
            session,
            "decide",
            "vql_chat_target_selected",
            {
                "selection_method": method,
                "target": out,
                "warnings": validation.get("coord_warnings") or [],
                "vql_validation": validation,
            },
        )
        _vdc()._autonomy_session.persist_autonomy_phase(session, "decide", "vql_validation", validation)
    return out


def _try_llm_vision_chat_detect(
    *,
    map_hint: dict[str, Any] | None = None,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """LLM-vision chat-target detection over the current photo screenshot."""
    if not _vdc().llm_vision_enabled():
        return None
    png = _vdc()._resolve_photo_png_path_from_vql(source=context["source"])
    if not png:
        return None
    try:
        from vdisplay.integrations.chat_target import resolve_chat_target_from_screenshot
    except ImportError:
        from koru.integrations.photo_vql_llm_detect import detect_chat_target_from_llm_vision

        meta_for_title = _vdc().load_vql_metadata(allow_stale=True)
        capture_title = _vdc()._capture_title_from_meta(meta_for_title)
        return detect_chat_target_from_llm_vision(
            ide=context["ide"],
            source=context["source"],
            image_path=png,
            candidates=context["candidates"],
            map_hint=map_hint,
            capture_title=capture_title,
        )

    meta_for_title = _vdc().load_vql_metadata(allow_stale=True)
    capture_validation = (meta_for_title.get("capture_validation") or {}) if isinstance(meta_for_title, dict) else {}  # noqa: E501
    return resolve_chat_target_from_screenshot(
        png,
        ide=context["ide"],
        source=context["source"],
        layers=context["elements"],
        capture_validation=capture_validation,
        map_hint=map_hint,
        polluted=context["polluted"],
    )


def _vql_chat_target_hardened_fallback() -> dict[str, Any]:
    """imgl-absent fallback: DP-1 main editor/chat area center."""
    return {
        "click_center": {"x": 1024, "y": 640, "note": "DP-1 main editor/chat area center (imgl not installed)"},
        "id": "dp1-chat-editor-center",
        "role": "editor-chat-area",
        "note": "hardened fallback — pip install imgl",
        "source": "vql-analysis-fallback",
    }


def _vql_chat_target_generic_flow(
    *,
    finalize: Any,
    try_llm: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    """IDE-agnostic tail: imgl resolve, then LLM vision, then hardened fallback."""
    resolve_chat_target = _vdc()._import_imgl_targets("resolve_chat_target")
    if resolve_chat_target is not None:
        resolved = resolve_chat_target(context["elements"], source=context["vql_file"])
        return finalize(resolved, method="imgl_resolve_chat_target")
    llm_target = try_llm()
    if llm_target:
        return finalize(llm_target, method="llm_vision_detect")
    logger.warning(
        "VQL_CHAT_TARGET_FALLBACK ide=%s using hardcoded center (1024,640) — no live VQL match",
        context["ide"],
    )
    return finalize(_vdc()._vql_chat_target_hardened_fallback(), method="hardened_fallback")


def get_vql_chat_target_from_photo(*, prefer_role: str | None = "panel", ide: str = "auto") -> dict:
    """Na podstawie foto screen VQL zlokalizuj okno/panel chat (deleguje do imgl.targets)."""
    context = _vdc()._vql_chat_selection_context(ide=ide)
    _vdc()._log_vql_chat_candidates(context)

    # Deterministic OCR placeholder anchor first: the input's placeholder text
    # ("Plan and build autonomously", "Ask anything", …) has an exact tesseract
    # bbox, so its center is a precise click point with no LLM pixel-precision
    # risk. Only when the placeholder is absent/unreadable do we fall to the
    # per-IDE heuristics + vision below.
    anchor = _vdc()._try_ocr_anchor_chat_target(ide=context["ide"], source=context["source"])
    if anchor is not None:
        return _vdc()._finalize_vql_chat_target(anchor, method="ocr_anchor_chat_placeholder", context=context)

    finalize = functools.partial(_vdc()._finalize_vql_chat_target, context=context)
    try_llm = functools.partial(_vdc()._try_llm_vision_chat_detect, context=context)
    if context["ide"] in {"jetbrains", "pycharm", "idea"}:
        jb_target = _vdc()._photo_vql_jetbrains_chat_flow(
            canon=context["ide"],
            src_name=context["source"],
            src=context["vql_file"],
            els=context["elements"],
            empty_layers=context["empty_layers"],
            mismatch=context["mismatch"],
            is_polluted=context["polluted"],
            finalize=finalize,
            try_llm=try_llm,
        )
        if jb_target is not None:
            return jb_target
    if context["ide"] in _vdc().VSCODE_FAMILY_TOP_CHAT_IDES:
        vscode_target = _vdc()._photo_vql_vscode_chat_flow(
            canon=context["ide"],
            src_name=context["source"],
            src=context["vql_file"],
            els=context["elements"],
            empty_layers=context["empty_layers"],
            mismatch=context["mismatch"],
            is_polluted=context["polluted"],
            finalize=finalize,
            try_llm=try_llm,
        )
        if vscode_target is not None:
            return vscode_target
    return _vdc()._vql_chat_target_generic_flow(finalize=finalize, try_llm=try_llm, context=context)
