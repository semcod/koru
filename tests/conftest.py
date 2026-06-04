"""Global pytest fixtures and hooks."""

from __future__ import annotations

import os

from koruide.config import clear_config_cache


def pytest_runtest_teardown(item, nextitem):
    """Defensive cleanup after every test to prevent cross-test leaks."""
    for key in (
        "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD",
        "KORU_AUTOPILOT_NEW_WINDOW_RELOAD",
        "KORU_AUTO_SKIP_WIZARD",
        "KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS",
    ):
        os.environ.pop(key, None)
    clear_config_cache()
