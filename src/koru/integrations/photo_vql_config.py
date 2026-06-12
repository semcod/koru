"""Central env parsing for koru photo-VQL / vdisplay drive."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_truthy(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class PhotoVqlConfig:
    vql_max_age_s: float
    post_focus_capture_delay_s: float
    focus_recovery_attempts: int
    ide_control_retries: int
    allow_map_on_mismatch: bool
    allow_ide_mismatch: bool
    llm_vision_decision: bool
    verify_after_paste: bool
    auto_ide_control: bool
    dry_run: bool

    @classmethod
    def from_env(cls) -> PhotoVqlConfig:
        return cls(
            vql_max_age_s=_env_float("KORU_VDISPLAY_VQL_MAX_AGE_S", 300.0),
            post_focus_capture_delay_s=_env_float("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", 0.8),
            focus_recovery_attempts=max(1, _env_int("KORU_VDISPLAY_FOCUS_RECOVERY_ATTEMPTS", 3)),
            ide_control_retries=max(1, _env_int("KORU_VDISPLAY_IDE_CONTROL_RETRIES", 3)),
            allow_map_on_mismatch=_env_truthy("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH"),
            allow_ide_mismatch=_env_truthy("KORU_VDISPLAY_ALLOW_IDE_MISMATCH"),
            llm_vision_decision=_env_truthy("KORU_VDISPLAY_LLM_VISION_DECISION", default=True),
            verify_after_paste=_env_truthy("KORU_VDISPLAY_VERIFY_AFTER_PASTE", default=True),
            auto_ide_control=_env_truthy("KORU_VDISPLAY_AUTO_IDE_CONTROL", default=True),
            dry_run=_env_truthy("KORU_VDISPLAY_DRY_RUN"),
        )


def llm_vision_enabled() -> bool:
    """Whether OpenRouter vision may detect/refine photo-VQL click targets."""
    return PhotoVqlConfig.from_env().llm_vision_decision


__all__ = ["PhotoVqlConfig", "llm_vision_enabled"]
