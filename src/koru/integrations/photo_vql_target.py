"""Photo-VQL chat target selection helpers (extracted from vdisplay_client)."""

from __future__ import annotations

from typing import Any

from koru.integrations.photo_vql_validation import (
    SHELL_POLLUTION_TOKENS,
    VQL_TERMINAL_LABEL_NOISE,
)


def vql_candidates_polluted(candidates: list[dict[str, Any]]) -> bool:
    polluted_count = 0
    for candidate in candidates:
        label = str(candidate.get("label") or "").lower()
        if any(tok.lower() in label for tok in SHELL_POLLUTION_TOKENS):
            polluted_count += 1
    return len(candidates) > 0 and polluted_count >= max(1, len(candidates) // 2)


def score_photo_vql_chat_input(layer: dict[str, Any]) -> float | None:
    if str(layer.get("role") or "").lower() != "input":
        return None
    click_center = layer.get("click_center") or {}
    if not isinstance(click_center, dict) or "x" not in click_center or "y" not in click_center:
        return None
    cx = int(click_center.get("x") or 0)
    cy = int(click_center.get("y") or 0)
    label = str(layer.get("label") or layer.get("text") or "").lower()
    bounds = layer.get("bounds") or layer.get("bbox") or {}
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    area = bw * bh if bw > 0 and bh > 0 else 0
    score = float(cy) + (400.0 if cx > 1400 else 0.0) + (200.0 if cx > 1100 else 0.0)
    if cy < 700:
        score -= 800.0
    if area > 0:
        if bw >= 250 and bh >= 28:
            score += 500.0
        elif bw >= 200 and bh >= 25:
            score += 300.0
        elif bw < 180 or bh < 22:
            score -= 900.0
        elif bw < 200 or bh < 25:
            score -= 500.0
    if label in {"background", ""} and area > 0 and (bw < 200 or bh < 25):
        score -= 900.0
    if any(term in label for term in VQL_TERMINAL_LABEL_NOISE):
        score -= 1200.0
    if any(tok.lower() in label for tok in SHELL_POLLUTION_TOKENS):
        score -= 1500.0
    return score


def photo_vql_chat_input_candidates(
    layers: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for layer in layers:
        score = score_photo_vql_chat_input(layer)
        if score is None:
            continue
        click_center = layer.get("click_center") or {}
        cx = int(click_center.get("x") or 0)
        cy = int(click_center.get("y") or 0)
        label = str(layer.get("label") or layer.get("text") or "").lower()
        bounds = layer.get("bounds") or layer.get("bbox") or {}
        ranked.append(
            (
                score,
                {
                    "id": layer.get("id"),
                    "role": layer.get("role"),
                    "label": label[:80],
                    "click_center": {"x": cx, "y": cy},
                    "bounds": bounds,
                },
            )
        )
    ranked.sort(key=lambda item: -item[0])
    return [item[1] for item in ranked[:limit]]


def jetbrains_corner_rejected(corner: dict[str, Any]) -> bool:
    click_center = corner.get("click_center") or {}
    if int(click_center.get("y") or 0) < 850:
        return True
    bounds = corner.get("bounds") or {}
    bw = int(bounds.get("w") or bounds.get("width") or 0)
    bh = int(bounds.get("h") or bounds.get("height") or 0)
    if bw > 0 and bh > 0 and (bw < 200 or bh < 25):
        return True
    label = str(corner.get("label") or "").lower()
    if label == "background":
        return True
    if any(term in label for term in VQL_TERMINAL_LABEL_NOISE):
        return True
    return any(tok.lower() in label for tok in SHELL_POLLUTION_TOKENS)


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
    return {
        "click_center": best.get("click_center") or {},
        "id": best.get("id"),
        "role": best.get("role") or "input",
        "bounds": best.get("bounds"),
        "note": f"JetBrains chat corner heuristic (bottom-right input; {source})",
        "source": source,
    }


__all__ = [
    "jetbrains_chat_corner_target_from_layers",
    "jetbrains_corner_rejected",
    "photo_vql_chat_input_candidates",
    "score_photo_vql_chat_input",
    "vql_candidates_polluted",
]
