from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from koru.autonomous_cycle_drive_retry import _invoke_client_autopilot_drive
from koru.integrations import vdisplay_client


def test_vdisplay_fallback_enabled_auto_on_wayland_without_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_VDISPLAY_CONTROL_FALLBACK", "auto")
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    assert vdisplay_client.vdisplay_fallback_enabled(ide="windsurf", plugin_connected=False) is True
    assert vdisplay_client.vdisplay_fallback_enabled(ide="windsurf", plugin_connected=True) is False


def test_vdisplay_fallback_disabled_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_CONTROL_FALLBACK", "0")
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    assert vdisplay_client.vdisplay_fallback_enabled(ide="windsurf", plugin_connected=False) is False


def test_send_chat_dry_run() -> None:
    reply = vdisplay_client.send_chat("hello", ide="windsurf", submit=True, dry_run=True)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay"
    assert reply["dry_run"] is True
    assert reply["app"] == "Windsurf"


def test_send_chat_prefers_ide_prompt_for_jetbrains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    monkeypatch.setattr(
        "gillm.injection.os_injector.try_drive_with_profile",
        lambda **kwargs: {
            "ok": True,
            "backend": "os_injector",
            "chat_x": 2323,
            "chat_y": 2409,
            "submitted": kwargs["submit"],
        },
    )
    monkeypatch.setattr(vdisplay_client, "_resolve_ide_prompt_map", lambda app_id: "/maps/pycharm-chat.json")
    ide_prompt = MagicMock(
        return_value={
            "ok": True,
            "backend": "vdisplay+ide-prompt",
            "message": "typed via vdisplay ide prompt",
            "map_path": "/maps/pycharm-chat.json",
        }
    )
    monkeypatch.setattr(vdisplay_client, "send_chat_via_ide_prompt", ide_prompt)

    reply = vdisplay_client.send_chat("hello jetbrains", ide="jetbrains", submit=False, dry_run=False)
    assert reply["ok"] is True
    assert reply["backend"] == "os_injector"
    ide_prompt.assert_not_called()


def test_send_chat_uses_semantic_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    monkeypatch.setattr(vdisplay_client, "_VDISPLAY_DIRECT", True)

    def _find_first(*, ide, selectors):
        if selectors is vdisplay_client._CHAT_INPUT_SELECTORS:
            return ({"role": "input", "name_contains": "Chat"}, {"ok": True, "count": 1, "selected": {"id": "atspi:chat-input"}})
        return (None, {"ok": False, "count": 0})

    monkeypatch.setattr(vdisplay_client, "_find_first_selector", _find_first)
    monkeypatch.setattr(vdisplay_client, "_control_focus", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(vdisplay_client, "_control_set_value", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(vdisplay_client, "_submit_via_keyboard", lambda **kwargs: {"ok": True, "backend": "vdisplay+keyboard"})

    reply = vdisplay_client.send_chat("fix tests", ide="windsurf", submit=True, dry_run=False)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay"
    assert reply["selector"]["name_contains"] == "Chat"
    assert reply["submitted"] is True


def test_invoke_drive_uses_vdisplay_after_plugin_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.drive = MagicMock(return_value={"ok": False, "backend": "plugin", "message": "not connected"})

    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_ide_control",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_imgl_gui_fallback",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_gillm_gui_fallback",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_nlp2uri_focus_fallback",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_os_injector_fallback",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_drive_retry._try_vdisplay_control_fallback",
        lambda *a, **k: {"ok": True, "backend": "vdisplay", "type": "drive"},
    )

    reply, ok = _invoke_client_autopilot_drive(
        client,
        prompt="hello",
        submit=True,
        autopilot_ide="windsurf",
        require_plugin=False,
    )
    assert ok is True
    assert reply["backend"] == "vdisplay"
