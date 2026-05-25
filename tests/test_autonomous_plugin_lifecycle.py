from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.autonomous_plugin_lifecycle import (
    PluginLifecycleHooks,
    setup_autopilot_plugin_lifecycle,
)


def _hooks(calls: list[str], status: str = "already_installed") -> PluginLifecycleHooks:
    return PluginLifecycleHooks(
        install_plugin_for_ide=lambda **_kwargs: calls.append("install") or SimpleNamespace(status=status),
        format_plugin_install_result=lambda result: f"status={result.status}",
        allow_keyboard_fallback=lambda: False,
        report_unsupported=lambda *_args, **_kwargs: calls.append("unsupported") or False,
        prepare_plugin_wait=lambda *_args, **_kwargs: calls.append("prepare") or (False, None),
        wait_for_plugin_connection=lambda *_args, **_kwargs: calls.append("wait") or True,
        stdio_info=lambda *_args, **_kwargs: calls.append("log"),
    )


def test_lifecycle_waits_after_installed_plugin() -> None:
    calls: list[str] = []
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")

    result = setup_autopilot_plugin_lifecycle(
        args,
        "vscodium",
        Path("/tmp/koru.sock"),
        client=object(),
        wait_for_plugin=lambda *_args, **_kwargs: True,
        hooks=_hooks(calls),
    )

    assert result is True
    assert calls == ["install", "log", "prepare", "wait"]


def test_lifecycle_skipped_install_does_not_wait() -> None:
    calls: list[str] = []
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")

    result = setup_autopilot_plugin_lifecycle(
        args,
        "auto",
        Path("/tmp/koru.sock"),
        client=object(),
        wait_for_plugin=lambda *_args, **_kwargs: True,
        hooks=_hooks(calls, status="skipped"),
    )

    assert result is None
    assert calls == ["install", "log"]
