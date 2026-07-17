"""Drive/control policy flags extracted from ``vdisplay_client``.

Pure-ish env + IDE heuristics used by send_chat / fallback routing.
``vdisplay_available`` is injected at call time to avoid circular imports.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def session_type() -> str:
    from koru.integrations.vdisplay.env_session import session_type as _session_type

    return _session_type()


def send_chat_os_injector_enabled(*, ide: str) -> bool:
    """Blind OS-injector clicks are unreliable on Wayland (focus stays in the terminal)."""
    if session_type() == "wayland":
        return False
    return _canonical_ide(ide) in {
        "jetbrains",
        "pycharm",
        "idea",
        "cursor",
        "windsurf",
        "vscode",
        "vscodium",
        "antigravity",
    }


def simplified_control_likely_insufficient(*, ide: str, plugin_connected: bool = False) -> bool:
    """Heuristic: simplified keyboard/plugin paths are unlikely to work."""
    if plugin_connected:
        return False
    if session_type() == "wayland":
        return True
    canon = _canonical_ide(ide)
    if canon in {"cursor", "windsurf", "antigravity"} and not plugin_connected:
        return True
    if not os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip():
        return True
    return False


def vdisplay_fallback_enabled(
    *,
    ide: str | None = None,
    plugin_connected: bool = False,
    available: Callable[[], bool] | None = None,
) -> bool:
    """Whether drive may use vdisplay semantic control as fallback."""
    raw = os.environ.get("KORU_VDISPLAY_CONTROL_FALLBACK", "auto").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    is_available = available if available is not None else (lambda: True)
    if not is_available():
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    if plugin_connected:
        return False
    if ide and simplified_control_likely_insufficient(ide=ide, plugin_connected=plugin_connected):
        return True
    return False


def trusted_visual_target_id(target_id: str) -> bool:
    tid = str(target_id or "")
    return tid.startswith("map:") or tid.startswith("llm:")


def photo_vql_code_edit_enabled() -> bool:
    return os.environ.get("KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def prefer_photo_vql_chat(
    *,
    ide: str = "auto",
    capture_matches: Callable[[str], bool] | None = None,
) -> bool:
    """When set, send_chat uses photo VQL mouse+focus path before os_injector/ide_prompt."""
    raw = os.environ.get("KORU_VDISPLAY_PREFER_PHOTO_VQL", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw == "auto":
        canon = _canonical_ide(ide)
        if canon in {"jetbrains", "pycharm", "idea"}:
            if capture_matches is None:
                return True
            return capture_matches(ide)
        return True
    return False


# Historical private names.
_send_chat_os_injector_enabled = send_chat_os_injector_enabled
_photo_vql_code_edit_enabled = photo_vql_code_edit_enabled
_prefer_photo_vql_chat = prefer_photo_vql_chat
_trusted_visual_target_id = trusted_visual_target_id

__all__ = [
    "photo_vql_code_edit_enabled",
    "prefer_photo_vql_chat",
    "send_chat_os_injector_enabled",
    "simplified_control_likely_insufficient",
    "trusted_visual_target_id",
    "vdisplay_fallback_enabled",
    "_photo_vql_code_edit_enabled",
    "_prefer_photo_vql_chat",
    "_send_chat_os_injector_enabled",
    "_trusted_visual_target_id",
]
