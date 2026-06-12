"""Auto-apply vdisplay drive defaults for keyboard-lane IDEs on Wayland."""

from __future__ import annotations

import os

_JETBRAINS_IDES = frozenset({"jetbrains", "pycharm", "idea"})
_VSCODE_FAMILY_IDES = frozenset({"cursor", "windsurf", "vscode", "vscodium", "antigravity"})
_VDISPLAY_DEFAULT_IDES = _JETBRAINS_IDES | _VSCODE_FAMILY_IDES


def _session_type() -> str:
    if (os.environ.get("WAYLAND_DISPLAY") or "").strip():
        return "wayland"
    if (os.environ.get("DISPLAY") or "").strip():
        return "x11"
    return "headless"


def apply_vdisplay_drive_defaults(*, ide: str) -> list[str]:
    """Set vdisplay env defaults for JetBrains-family lanes on Wayland (no-op if unset)."""
    canon = ide.strip().lower()
    if canon not in _VDISPLAY_DEFAULT_IDES:
        return []
    if _session_type() != "wayland":
        return []
    applied: list[str] = []
    defaults = {
        "KORU_VDISPLAY_CONTROL_FALLBACK": "1",
        "KORU_VDISPLAY_PREFER_PHOTO_VQL": "auto",
        "KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS": "1",
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH": "1",
        "KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR": "1",
        "KORU_VDISPLAY_LLM_VISION_DECISION": "1",
        "VDISPLAY_VISION_LLM_ENABLED": "1",
        "VDISPLAY_VISION_LLM_MODE": "both",
        "VDISPLAY_VISION_CHAT_DETECT": "1",
    }
    for key, value in defaults.items():
        if not os.environ.get(key, "").strip():
            os.environ[key] = value
            applied.append(f"{key}={value}")
    try:
        from koru.integrations.vdisplay_agent_bootstrap import apply_vdisplay_agent_env

        agent = apply_vdisplay_agent_env()
        applied.extend(str(item) for item in agent.get("applied") or [])
    except ImportError:
        pass
    return applied


__all__ = ["apply_vdisplay_drive_defaults"]
