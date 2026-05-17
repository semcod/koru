"""IDE discovery bridge for `koruide` extraction.

Current implementation re-exports legacy detection/runtime helpers from
`koru.autopilot.ide` while callers migrate to `koruide.*` imports.
"""

from __future__ import annotations

from koru.autopilot.ide import (
    RunningIDE,
    clear_detect_cache,
    detect_focused_ide_id,
    detect_running_ides,
    detect_running_ides_cached,
    focused_ide,
    is_linux,
    pick_target,
)

__all__ = [
    "RunningIDE",
    "detect_running_ides",
    "detect_running_ides_cached",
    "detect_focused_ide_id",
    "clear_detect_cache",
    "focused_ide",
    "pick_target",
    "is_linux",
]
