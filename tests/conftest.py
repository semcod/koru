"""Global pytest fixtures and hooks."""

from __future__ import annotations

import os

import pytest

from koruide import command_picker
from koruide.config import clear_config_cache

# Environment variables that influence command-picker / LLM behaviour and must
# never leak between tests. A value set (or inherited, e.g. a real
# ``OPENROUTER_API_KEY`` sourced from a developer ``.env``) by one test would
# otherwise change the behaviour of unrelated tests running later in the same
# (xdist) worker.
_VOLATILE_ENV_KEYS = (
    "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD",
    "KORU_AUTOPILOT_NEW_WINDOW_RELOAD",
    "KORU_AUTO_SKIP_WIZARD",
    "KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS",
    "KORU_LLM_PICKER",
    "KORU_COMMAND_CATALOG",
    "KORU_COMMAND_PICKER",
    "KORU_VSCODIUM_COMMAND_ORDER_FOCUS_OPEN",
    "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _isolate_command_picker_state():
    """Snapshot & restore the command-picker module's shared mutable state.

    ``command_picker._LLM_CACHE`` is a module-level dict that persists for the
    lifetime of the (worker) process. Without resetting it, a test that
    populates the cache (e.g. one that mocks a successful OpenRouter response)
    leaks that ordering into any later test that queries the same
    ``ide|version|capability`` key, producing order-dependent failures that
    only surface under xdist's load scheduling.

    ``OPENROUTER_API_KEY`` is removed so the heuristic-fallback path is taken
    deterministically: tests that exercise the LLM path explicitly monkeypatch
    ``call_openrouter_json`` and set ``KORU_LLM_PICKER`` themselves, so they are
    unaffected, while accidental real network calls are prevented.
    """
    command_picker._LLM_CACHE.clear()
    os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        yield
    finally:
        command_picker._LLM_CACHE.clear()


def pytest_runtest_teardown(item, nextitem):
    """Defensive cleanup after every test to prevent cross-test leaks."""
    for key in _VOLATILE_ENV_KEYS:
        os.environ.pop(key, None)
    command_picker._LLM_CACHE.clear()
    clear_config_cache()
