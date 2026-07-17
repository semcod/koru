"""Photo-VQL capture metadata / window-title validation helpers.

Extracted from ``vdisplay_client`` so observe/drive gates share one source of
truth for IDE-window and system-overlay warnings without loading the full
control plane.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

IDE_WINDOW_TITLE_TOKENS: dict[str, tuple[str, ...]] = {
    "cursor": ("cursor",),
    "windsurf": ("windsurf",),
    "vscode": ("visual studio code", "vscode"),
    "vscodium": ("vscodium",),
    "antigravity": ("antigravity",),
    "qoder": ("qoder",),
    "zed": ("zed",),
    "jetbrains": (
        "jetbrains",
        "pycharm",
        "intellij",
        "idea",
        "webstorm",
        "goland",
        "clion",
        "rider",
    ),
    "pycharm": ("pycharm", "jetbrains"),
    "idea": ("intellij", "idea", "jetbrains"),
}

# Tokens that invalidate a capture for the requested IDE (avoid breadcrumb FPs).
COMPETING_IDE_WINDOW_TOKENS: dict[str, tuple[str, ...]] = {
    "jetbrains": (
        "cursor",
        "visual studio code",
        "vscode",
        "windsurf",
        "vscodium",
        "antigravity",
        "zed",
        "qoder",
    ),
    "pycharm": ("cursor", "visual studio code", "vscode", "windsurf", "qoder"),
    "idea": ("cursor", "visual studio code", "vscode", "windsurf", "qoder"),
    "cursor": ("pycharm", "intellij", "jetbrains", "webstorm"),
    "windsurf": ("pycharm", "intellij", "jetbrains"),
    "vscode": ("pycharm", "intellij", "jetbrains", "cursor"),
    "qoder": ("pycharm", "intellij", "jetbrains", "cursor", "windsurf"),
}


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def capture_validation_from_meta(meta: dict | None) -> dict[str, Any] | None:
    if not meta:
        return None
    cv = meta.get("capture_validation")
    if isinstance(cv, dict):
        return cv
    nested = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    cv = nested.get("capture_validation") if isinstance(nested, dict) else None
    return cv if isinstance(cv, dict) else None


def photo_vql_overlay_labels(meta: dict) -> list[str]:
    """Collect layer label/text/id strings for overlay detection."""
    labels: list[str] = []
    for layer in meta.get("ui_elements") or meta.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        for key in ("label", "text", "id"):
            value = str(layer.get(key) or "").strip()
            if value:
                labels.append(value)
    return labels


def photo_vql_share_prompt_detected(joined: str) -> bool:
    return (
        "share screen" in joined
        or "share your screen" in joined
        or ("wants" in joined and "share" in joined and "screen" in joined)
    )


def photo_vql_portal_actor_detected(joined: str) -> bool:
    return (
        "org.chromium.chromium" in joined
        or ("gnome" in joined and "share" in joined)
        or ("choose what" in joined and "share" in joined)
    )


def photo_vql_system_overlay_warning(*, meta: dict) -> dict[str, Any] | None:
    """Detect modal OS/browser share prompts that obscure the automation target."""
    labels = photo_vql_overlay_labels(meta)
    joined = " ".join(labels).lower()
    if not joined:
        return None
    if not (
        photo_vql_share_prompt_detected(joined) and photo_vql_portal_actor_detected(joined)
    ):
        return None
    return {
        "ide": "system-overlay",
        "system_overlay": True,
        "reason": "screen_share_overlay",
        "window_titles": [],
        "message": (
            "Screen Share permission dialog is visible in the capture; "
            "approve or dismiss it before drive so clicks do not target the modal."
        ),
        "matched_text": joined[:500],
    }


def photo_vql_capture_validation_failed_warning(
    cv: dict[str, Any],
    *,
    ide: str,
    meta: dict,
    window_titles: Callable[[dict], list[str]],
) -> dict[str, Any]:
    """Warning dict for an embedded capture_validation that reported failure."""
    reasons = list(cv.get("reasons") or [])
    structure = cv.get("structure") if isinstance(cv.get("structure"), dict) else {}
    for item in structure.get("reasons") or []:
        if item not in reasons:
            reasons.append(item)
    canon = _canonical_ide(ide)
    return {
        "ide": canon,
        "expected_tokens": list(IDE_WINDOW_TITLE_TOKENS.get(canon, ())),
        "window_titles": list(cv.get("window_titles") or window_titles(meta)),
        "capture_validation_failed": True,
        "reasons": reasons,
        "message": (
            f"Photo VQL capture not confirmed for {canon}: "
            f"validation reasons={reasons!r}. Focus the target IDE and refresh observe."
        ),
    }


def photo_vql_expected_title_tokens(
    canon: str,
    *,
    ide_hints: Callable[[str], dict[str, str]] | None = None,
) -> tuple[str, ...]:
    tokens = IDE_WINDOW_TITLE_TOKENS.get(canon)
    if not tokens and ide_hints is not None:
        hints = ide_hints(canon)
        needle = str(hints.get("window_title_contains") or "").strip().lower()
        tokens = (needle,) if needle else ()
    return tokens or ()


def photo_vql_title_mismatch_warning(
    canon: str, tokens: tuple[str, ...], titles: list[str]
) -> dict[str, Any] | None:
    """Compare capture window titles against expected/competing IDE tokens."""
    joined_titles = " | ".join(titles).lower()
    competing = COMPETING_IDE_WINDOW_TOKENS.get(canon, ())
    if any(comp in joined_titles for comp in competing):
        return {
            "ide": canon,
            "expected_tokens": list(tokens),
            "window_titles": titles,
            "competing_detected": list(competing),
            "message": (
                f"Photo VQL capture foreground window looks like a different IDE than {canon}: "
                f"title(s)={titles!r}. Re-focus {canon} on the capture monitor and refresh observe."
            ),
        }
    if any(token in joined_titles for token in tokens):
        return None
    return {
        "ide": canon,
        "expected_tokens": list(tokens),
        "window_titles": titles,
        "message": (
            f"Photo VQL capture does not look like {canon}: "
            f"window title(s)={titles!r}. Focus the correct IDE on the target monitor before real drive."
        ),
    }


def photo_vql_ide_window_warning(
    *,
    ide: str,
    meta: dict,
    window_titles: Callable[[dict], list[str]],
    ide_hints: Callable[[str], dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    """Warn when captured foreground window title does not match requested IDE."""
    overlay = photo_vql_system_overlay_warning(meta=meta)
    if overlay:
        return overlay

    cv = capture_validation_from_meta(meta)
    if isinstance(cv, dict):
        if cv.get("capture_confirmed") is True:
            return None
        embedded = cv.get("ide_window_warning")
        if isinstance(embedded, dict):
            return embedded
        if cv.get("capture_confirmed") is False:
            return photo_vql_capture_validation_failed_warning(
                cv, ide=ide, meta=meta, window_titles=window_titles
            )

    canon = _canonical_ide(ide)
    if canon in {"", "auto"}:
        return None
    tokens = photo_vql_expected_title_tokens(canon, ide_hints=ide_hints)
    if not tokens:
        return None
    titles = window_titles(meta)
    if not titles:
        return None
    return photo_vql_title_mismatch_warning(canon, tokens, titles)


def type_text_plan_validation_warnings(
    *,
    target_for_log: dict[str, Any],
    command_plan: dict[str, Any] | None,
) -> list[str]:
    """Warnings coming from the command plan + VQL validation payloads."""
    warnings: list[str] = []
    plan_warnings = (command_plan or {}).get("warnings") if isinstance(command_plan, dict) else None
    if isinstance(plan_warnings, list):
        warnings.extend(str(item) for item in plan_warnings)
    validation = None
    if isinstance(command_plan, dict):
        validation = command_plan.get("vql_validation")
    if not isinstance(validation, dict) and isinstance(target_for_log, dict):
        validation = target_for_log.get("vql_validation")
    if isinstance(validation, dict):
        warnings.extend(str(item) for item in validation.get("coord_warnings") or [])
        warnings.extend(str(item) for item in validation.get("validation_errors") or [])
    return warnings


# Historical private aliases.
_IDE_WINDOW_TITLE_TOKENS = IDE_WINDOW_TITLE_TOKENS
_COMPETING_IDE_WINDOW_TOKENS = COMPETING_IDE_WINDOW_TOKENS
_capture_validation_from_meta = capture_validation_from_meta
_photo_vql_overlay_labels = photo_vql_overlay_labels
_photo_vql_share_prompt_detected = photo_vql_share_prompt_detected
_photo_vql_portal_actor_detected = photo_vql_portal_actor_detected
_photo_vql_system_overlay_warning = photo_vql_system_overlay_warning
_type_text_plan_validation_warnings = type_text_plan_validation_warnings

__all__ = [
    "COMPETING_IDE_WINDOW_TOKENS",
    "IDE_WINDOW_TITLE_TOKENS",
    "capture_validation_from_meta",
    "photo_vql_capture_validation_failed_warning",
    "photo_vql_expected_title_tokens",
    "photo_vql_ide_window_warning",
    "photo_vql_overlay_labels",
    "photo_vql_portal_actor_detected",
    "photo_vql_share_prompt_detected",
    "photo_vql_system_overlay_warning",
    "photo_vql_title_mismatch_warning",
    "type_text_plan_validation_warnings",
]
