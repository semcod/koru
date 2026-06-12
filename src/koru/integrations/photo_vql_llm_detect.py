"""LLM vision detection for photo-VQL chat targets.

The preferred implementation lives in ``vdisplay.integrations.chat_target``.
This module remains as a Koru-owned fallback so OpenRouter vision is still
usable when the local vdisplay checkout/package does not expose that helper.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from koru.integrations.photo_vql_config import llm_vision_enabled


def detect_chat_target_from_llm_vision(
    *,
    ide: str,
    source: str,
    image_path: str | None = None,
    candidates: list[dict[str, Any]] | None = None,
    map_hint: dict[str, Any] | None = None,
    capture_title: str | None = None,
) -> dict[str, Any] | None:
    """Detect an IDE chat target from screenshot pixels with validated LLM output."""
    if not llm_vision_enabled() or not image_path:
        return None
    try:
        from vdisplay.integrations.chat_target import resolve_chat_target_from_screenshot
    except ImportError:
        resolved = None
    else:
        try:
            resolved = resolve_chat_target_from_screenshot(
                image_path,
                ide=ide,
                source=source,
                layers=_candidates_to_layers(candidates),
                map_hint=map_hint,
                polluted=bool(candidates and _looks_polluted(candidates)),
            )
        except Exception:
            resolved = None
    if resolved:
        return _normalize_llm_target(resolved, image_path=image_path, source=source)
    return _detect_chat_target_with_openrouter(
        ide=ide,
        source=source,
        image_path=image_path,
        candidates=candidates,
        map_hint=map_hint,
        capture_title=capture_title,
    )


def _detect_chat_target_with_openrouter(
    *,
    ide: str,
    source: str,
    image_path: str,
    candidates: list[dict[str, Any]] | None,
    map_hint: dict[str, Any] | None,
    capture_title: str | None,
) -> dict[str, Any] | None:
    try:
        from koru.autonomy_strategy.openrouter import call_openrouter_vision
    except ImportError:
        return None

    image_data_url = _image_data_url(image_path)
    if image_data_url is None:
        return None

    response = call_openrouter_vision(
        _build_detection_prompt(
            ide=ide,
            source=source,
            candidates=candidates,
            map_hint=map_hint,
            capture_title=capture_title,
        ),
        image_data_url,
        system_prompt=(
            "You are a cautious desktop automation vision agent. "
            "Return only valid minified JSON. Never choose a terminal, shell, "
            "browser, editor text area, or wrong IDE window as a chat input. "
            "If the screenshot does not clearly show the requested IDE chat input "
            "or chat panel, return should_act=false."
        ),
        timeout_seconds=_float(
            os.environ.get("KORU_VDISPLAY_LLM_CHAT_DETECT_TIMEOUT_S"),
            default=45.0,
        ),
    )
    if not response.ok:
        return None
    decision = _parse_json_object(response.content)
    if not decision:
        return None
    return _target_from_decision(
        decision,
        image_path=image_path,
        source=source,
        map_hint=map_hint,
    )


def _build_detection_prompt(
    *,
    ide: str,
    source: str,
    candidates: list[dict[str, Any]] | None,
    map_hint: dict[str, Any] | None,
    capture_title: str | None,
) -> str:
    payload = {
        "task": "Locate the chat input or chat panel for Koru to type into.",
        "expected_ide": ide,
        "capture_source": source,
        "capture_title": capture_title or "",
        "vql_candidates": _candidate_excerpt(candidates),
        "calibrated_map_hint": _map_hint_excerpt(map_hint),
        "rules": _detection_rules(),
        "schema": _detection_schema(),
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _detection_rules() -> list[str]:
    return [
        "Return should_act=false if the requested IDE is not the foreground window.",
        "Return should_act=false if the best target is a terminal or shell.",
        "Prefer the visible chat text box. If only the chat panel is visible, choose a safe point inside the chat input area.",
        "Use screenshot-local coordinates, not global monitor coordinates.",
        "Use the calibrated_map_hint only as a hint, never as proof that the chat is visible.",
    ]


def _detection_schema() -> dict[str, Any]:
    return {
        "should_act": "boolean",
        "target_type": "chat_input|chat_panel|wrong_window|unknown",
        "click_center": {"x": "integer", "y": "integer"},
        "bounds": {"x": "integer", "y": "integer", "w": "integer", "h": "integer"},
        "confidence": "number 0..1",
        "window_title_seen": "string",
        "reason": "short string",
    }


def _image_data_url(image_path: str) -> str | None:
    path = Path(image_path)
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data:
        return None
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _parse_json_object(content: str) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _target_from_decision(
    decision: dict[str, Any],
    *,
    image_path: str,
    source: str,
    map_hint: dict[str, Any] | None,
) -> dict[str, Any] | None:
    target_type = _decision_target_type(decision)
    if target_type is None:
        return None
    confidence = _decision_confidence(decision)
    if confidence < _min_detection_confidence():
        return None
    click_center = _decision_click_center(decision)
    if click_center is None:
        return None
    bounds = decision.get("bounds") if isinstance(decision.get("bounds"), dict) else None
    out: dict[str, Any] = {
        "id": "llm:chat-target",
        "role": "input" if target_type == "chat_input" else "panel",
        "label": "LLM detected IDE chat target",
        "click_center": {
            "x": click_center["x"],
            "y": click_center["y"],
            "note": str(decision.get("reason") or "OpenRouter vision chat detection")[:160],
        },
        "source": image_path,
        "selection_method": "llm_vision_detect",
        "llm_used": True,
        "llm_decision": decision,
        "confidence": confidence,
        "target_type": target_type,
        "note": "OpenRouter vision detected chat target from screenshot",
    }
    if bounds:
        out["bounds"] = _clean_bounds(bounds)
    if map_hint:
        out["map_hint"] = map_hint
    out["vql_source"] = source
    return out


def _decision_target_type(decision: dict[str, Any]) -> str | None:
    if decision.get("should_act") is not True:
        return None
    target_type = str(decision.get("target_type") or "").strip().lower()
    return target_type if target_type in {"chat_input", "chat_panel"} else None


def _decision_confidence(decision: dict[str, Any]) -> float:
    return _float(decision.get("confidence"), default=0.0)


def _min_detection_confidence() -> float:
    return _float(os.environ.get("KORU_VDISPLAY_LLM_CHAT_DETECT_MIN_CONFIDENCE"), default=0.70)


def _decision_click_center(decision: dict[str, Any]) -> dict[str, int] | None:
    cc = decision.get("click_center") if isinstance(decision.get("click_center"), dict) else {}
    x = _int(cc.get("x"))
    y = _int(cc.get("y"))
    if x is None or y is None or x < 0 or y < 0:
        return None
    return {"x": x, "y": y}


def _normalize_llm_target(
    target: dict[str, Any],
    *,
    image_path: str,
    source: str,
) -> dict[str, Any] | None:
    if not isinstance(target, dict):
        return None
    cc = target.get("click_center")
    if not isinstance(cc, dict):
        return None
    x = _int(cc.get("x"))
    y = _int(cc.get("y"))
    if x is None or y is None or x < 0 or y < 0:
        return None
    return {
        **target,
        "id": target.get("id") or "llm:chat-target",
        "click_center": {**cc, "x": x, "y": y},
        "source": target.get("source") or image_path,
        "vql_source": target.get("vql_source") or source,
        "selection_method": target.get("selection_method") or "llm_vision_detect",
        "llm_used": True,
    }


def _candidates_to_layers(candidates: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for item in candidates or []:
        if not isinstance(item, dict):
            continue
        layers.append(
            {
                "id": item.get("id"),
                "role": item.get("role") or "input",
                "label": item.get("label"),
                "click_center": item.get("click_center"),
            }
        )
    return layers


def _candidate_excerpt(candidates: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    excerpt: list[dict[str, Any]] = []
    for item in candidates or []:
        if not isinstance(item, dict):
            continue
        excerpt.append(
            {
                "id": item.get("id"),
                "role": item.get("role"),
                "label": str(item.get("label") or item.get("text") or "")[:120],
                "click_center": item.get("click_center"),
                "bounds": item.get("bounds") or item.get("bbox"),
            }
        )
        if len(excerpt) >= 8:
            break
    return excerpt


def _map_hint_excerpt(map_hint: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(map_hint, dict):
        return None
    return {
        "id": map_hint.get("id"),
        "click_center": map_hint.get("click_center"),
        "bounds": map_hint.get("bounds") or map_hint.get("bbox"),
        "selection_method": map_hint.get("selection_method"),
        "note": str(map_hint.get("note") or "")[:120],
    }


def _clean_bounds(bounds: dict[str, Any]) -> dict[str, int]:
    cleaned: dict[str, int] = {}
    for key in ("x", "y", "w", "h"):
        val = _int(bounds.get(key))
        if val is not None:
            cleaned[key] = val
    return cleaned


def _int(value: Any) -> int | None:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _looks_polluted(candidates: list[dict[str, Any]]) -> bool:
    polluted = 0
    for c in candidates:
        label = str(c.get("label") or "").lower()
        if any(tok in label for tok in ("export ", "koru ", "autopilot", "perform_photo")):
            polluted += 1
    return len(candidates) > 0 and polluted >= max(1, len(candidates) // 2)


__all__ = ["detect_chat_target_from_llm_vision", "llm_vision_enabled"]
