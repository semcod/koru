"""User-tunable autopilot config — re-exported from :mod:`gillm.config`.

Canonical implementation lives in gillm (shared by injector, koruide daemon,
and koru CLI). This module preserves legacy ``koruide.config`` import paths.
"""

from __future__ import annotations

from gillm.config import (
    AutopilotConfig,
    cached_config,
    clear_config_cache,
    default_config_path,
    load_config,
)

__all__ = [
    "AutopilotConfig",
    "cached_config",
    "clear_config_cache",
    "default_config_path",
    "load_config",
]
