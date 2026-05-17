"""OS-coordinate injector bridge for `koruide` extraction.

Current implementation re-exports legacy os-injector helpers from
`koru.autopilot.os_injector`.
"""

from __future__ import annotations

from koru.autopilot.os_injector import (
    OsInjectorError,
    OsInjectorProfile,
    capture_from_xdotool,
    capture_mouse_xy,
    default_config_path,
    dry_run_from_env,
    focus_mode_from_env,
    inject_with_profile,
    input_mode_from_env,
    iter_config_paths,
    load_profile,
    os_injector_env_disabled,
    os_injector_env_forced,
    profile_from_mouse,
    save_profile,
    try_drive_with_profile,
    try_load_profile,
)

__all__ = [
    "OsInjectorError",
    "OsInjectorProfile",
    "default_config_path",
    "iter_config_paths",
    "os_injector_env_disabled",
    "os_injector_env_forced",
    "dry_run_from_env",
    "focus_mode_from_env",
    "input_mode_from_env",
    "try_load_profile",
    "load_profile",
    "save_profile",
    "profile_from_mouse",
    "capture_mouse_xy",
    "capture_from_xdotool",
    "inject_with_profile",
    "try_drive_with_profile",
]
