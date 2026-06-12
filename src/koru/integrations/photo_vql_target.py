"""Photo-VQL chat target selection helpers (extracted from vdisplay_client)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from koru.integrations.photo_vql_validation import (
    SHELL_POLLUTION_TOKENS,
    VQL_TERMINAL_LABEL_NOISE,
)

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
    return _has_any(label, VQL_TERMINAL_LABEL_NOISE) or _has_any(label, SHELL_POLLUTION_TOKENS)


def vql_candidates_polluted(candidates: list[dict[str, Any]]) -> bool:
    polluted_count = 0
    for candidate in candidates:
        label = str(candidate.get("label") or "").lower()
        if _has_any(label, SHELL_POLLUTION_TOKENS):
            polluted_count += 1
    return len(candidates) > 0 and polluted_count >= max(1, len(candidates) // 2)


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
    if _has_any(label, VQL_TERMINAL_LABEL_NOISE):
        penalty -= 1200.0
    if _has_any(label, SHELL_POLLUTION_TOKENS):
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
        click_center = _layer_click_center(layer) or {"x": 0, "y": 0}
        cx = click_center["x"]
        cy = click_center["y"]
        label = _layer_label(layer)
        bounds = _layer_bounds(layer)
        ranked.append(
            (
                score,
                {
                    "id": layer.get("id"),
                    "role": _layer_role(layer),
                    "label": label[:80],
                    "click_center": {"x": cx, "y": cy},
                    "bounds": bounds,
                },
            )
        )
    ranked.sort(key=lambda item: -item[0])
    return [item[1] for item in ranked[:limit]]


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
    return {
        "click_center": best.get("click_center") or {},
        "id": best.get("id"),
        "role": best.get("role") or "input",
        "bounds": best.get("bounds"),
        "label": best.get("label"),
        "note": f"VS Code-family top chat heuristic ({source})",
        "source": source,
    }


def jetbrains_corner_rejected(corner: dict[str, Any]) -> bool:
    click_center = corner.get("click_center") or {}
    bounds = _target_bounds(corner)
    label = str(corner.get("label") or "").lower()
    return (
        int(click_center.get("y") or 0) < 850
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
    return {
        "click_center": best.get("click_center") or {},
        "id": best.get("id"),
        "role": best.get("role") or "input",
        "bounds": best.get("bounds"),
        "note": f"JetBrains chat corner heuristic (bottom-right input; {source})",
        "source": source,
    }


__all__ = [
    "VSCODE_FAMILY_TOP_CHAT_IDES",
    "jetbrains_chat_corner_target_from_layers",
    "jetbrains_corner_rejected",
    "photo_vql_chat_input_candidates",
    "score_photo_vql_chat_input",
    "vql_candidates_polluted",
    "vscode_family_chat_target_from_layers",
    "vscode_family_top_chat_rejected",
]
