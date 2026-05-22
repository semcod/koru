"""Regression: ``setup_autopilot_plugin`` must surface a clear remedy when the
selected IDE lane has no installable plugin.

The user-facing scenario: running ``koru auto`` in a shell where
``KORU_AUTOPILOT_INSTANCE=jetbrains`` is set (e.g. left over from a previous
session). The autonomous loop picks the JetBrains lane, the plugin installer
reports ``unsupported``, and the loop silently falls back to the keyboard /
OS-injector path — which is unreliable on Wayland. The previous log only said
``autopilot plugin unsupported for ide=jetbrains; using keyboard/OS-injector
path`` without telling the user how to fix it.

This test pins the new, actionable warning that explicitly names the env var
and the supported lanes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from koru.autonomous_operator import setup_autopilot_plugin


@dataclass
class _Args:
    enable_autopilot: bool = True
    autopilot_plugin_wait_seconds: float = 0.0
    emit_events: str = "human"


def _stub_plugin_install_result_unsupported() -> Any:
    @dataclass
    class _Result:
        status: str = "unsupported"
        ide: str = "jetbrains"

    return _Result()


def test_unsupported_ide_emits_env_remedy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "jetbrains")
    captured: list[str] = []

    def stdio_info(msg: str, *, fmt: str) -> None:
        captured.append(msg)

    setup_autopilot_plugin(
        _Args(),
        autopilot_ide="jetbrains",
        socket_path=Path("/tmp/koru-test.sock"),
        client=None,
        install_plugin_for_ide=lambda *, ide, socket_path: _stub_plugin_install_result_unsupported(),
        format_plugin_install_result=lambda r: f"plugin install: {r.status}",
        allow_keyboard_fallback=lambda: True,
        wait_for_plugin=lambda *_a, **_k: False,
        stdio_info=stdio_info,
    )

    joined = "\n".join(captured)
    assert "autopilot plugin unsupported for ide=jetbrains" in joined
    assert "KORU_AUTOPILOT_INSTANCE=jetbrains" in joined
    assert "unset KORU_AUTOPILOT_INSTANCE" in joined
    assert "cursor" in joined and "vscode" in joined and "windsurf" in joined


def test_unsupported_ide_without_env_does_not_print_env_remedy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    captured: list[str] = []

    def stdio_info(msg: str, *, fmt: str) -> None:
        captured.append(msg)

    setup_autopilot_plugin(
        _Args(),
        autopilot_ide="jetbrains",
        socket_path=Path("/tmp/koru-test.sock"),
        client=None,
        install_plugin_for_ide=lambda *, ide, socket_path: _stub_plugin_install_result_unsupported(),
        format_plugin_install_result=lambda r: f"plugin install: {r.status}",
        allow_keyboard_fallback=lambda: True,
        wait_for_plugin=lambda *_a, **_k: False,
        stdio_info=stdio_info,
    )

    joined = "\n".join(captured)
    assert "autopilot plugin unsupported for ide=jetbrains" in joined
    assert "KORU_AUTOPILOT_INSTANCE=jetbrains" not in joined
