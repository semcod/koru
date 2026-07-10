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
    # configure_loop_state() writes these straight into os.environ when it
    # routes --ide auto to a shell client; without cleanup they leak the
    # selected client into every later test in the same worker.
    "KORU_TILLM_CLIENT",
    "KORU_TILLM_MODEL",
    "KORU_TILLM_EXECUTE_PROFILE",
    "KORU_AUTOPILOT_SOCKET",
)


@pytest.fixture(autouse=True)
def _no_real_shell_clients(monkeypatch: pytest.MonkeyPatch):
    """Keep unit tests from executing a real vendor CLI (claude-code, aider, …).

    On a developer host with tillm + a shell client installed, ``--ide auto``
    autodetection would otherwise drive the real CLI headlessly — slow
    (minutes per call), nondeterministic, and billed. Tests that exercise
    autodetection itself opt back in with ``monkeypatch.delenv``.
    """
    monkeypatch.setenv("KORU_AUTO_SHELL_CLIENT", "0")


@pytest.fixture(autouse=True)
def _isolated_global_killswitch(monkeypatch: pytest.MonkeyPatch, tmp_path_factory):
    """Never let the developer's real `koru off` state leak into tests.

    ``is_globally_disabled()`` reads ``~/.config/koru/killswitch``; on a host
    where the operator disabled koru, half the suite would otherwise see the
    kill-switch and fail. Tests that exercise the switch set
    ``KORU_GLOBAL_CONTROL_DIR`` themselves (see test_global_control.py).
    """
    ctl_dir = tmp_path_factory.mktemp("koru-global-ctl")
    monkeypatch.setenv("KORU_GLOBAL_CONTROL_DIR", str(ctl_dir))
    monkeypatch.delenv("KORU_GLOBAL_DISABLE", raising=False)


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


@pytest.fixture(autouse=True)
def _no_real_planfile_ticket_probes(monkeypatch: pytest.MonkeyPatch):
    """Keep the ghost-ticket guard from probing real planfile in unit tests.

    Fixture ticket ids (PLF-001, T-1, …) do not exist in any real planfile;
    on hosts with a planfile binary on PATH the guard would (correctly) drop
    them and change prompt behaviour depending on the machine. Tests that
    exercise the guard itself re-patch `_waiting_ticket_is_missing`.
    """
    try:
        import koru.autonomy.cycle.cycle_drive_retry as _drv
    except ImportError:  # pre-migration layout
        import koru.autonomous_cycle_drive_retry as _drv

    monkeypatch.setattr(_drv, "_waiting_ticket_is_missing", lambda _p, _t: False)
