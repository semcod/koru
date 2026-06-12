from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from koru.integrations import vdisplay_client


@pytest.fixture(autouse=True)
def _clear_vdisplay_drive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH",
        "KORU_VDISPLAY_ALLOW_IDE_MISMATCH",
        "KORU_VDISPLAY_CAPTURE_MATCHES_IDE",
        "KORU_VDISPLAY_PREFER_PHOTO_VQL",
        "KORU_VDISPLAY_LLM_VISION_DECISION",
        "KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT",
        "KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS",
        "KORU_VDISPLAY_DRY_RUN",
        "KORU_VDISPLAY_CONTROL_FALLBACK",
        "KORU_VDISPLAY_SOURCE",
        "KORU_VDISPLAY_VQL_PATH",
        "KORU_VDISPLAY_PHOTO_PATH",
        "KORU_VDISPLAY_ABORT_ON_PROBE_FAIL",
        "KORU_VDISPLAY_PHOTO_VQL_MAP_FALLBACK",
        "VDISPLAY_METADATA_DIR",
        "VDISPLAY_SESSION",
        "VDISPLAY_SESSION_ID",
    ):
        monkeypatch.delenv(key, raising=False)


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


def test_send_chat_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT", raising=False)
    reply = vdisplay_client.send_chat("hello", ide="windsurf", submit=True, dry_run=True)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay"
    assert reply["dry_run"] is True
    assert reply["app"] == "Windsurf"


def test_send_chat_prefers_ide_prompt_for_jetbrains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", raising=False)
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    monkeypatch.setattr(vdisplay_client, "_photo_vql_ide_capture_mismatch", lambda **kwargs: None)
    import types

    fake_oi = types.ModuleType("gillm.injection.os_injector")
    fake_oi.try_drive_with_profile = lambda **kwargs: {
        "ok": True,
        "backend": "os_injector",
        "chat_x": 2323,
        "chat_y": 2409,
        "submitted": kwargs["submit"],
    }
    gillm_injection = types.ModuleType("gillm.injection")
    gillm_injection.os_injector = fake_oi
    gillm = types.ModuleType("gillm")
    gillm.injection = gillm_injection
    monkeypatch.setitem(sys.modules, "gillm", gillm)
    monkeypatch.setitem(sys.modules, "gillm.injection", gillm_injection)
    monkeypatch.setitem(sys.modules, "gillm.injection.os_injector", fake_oi)
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


def test_send_chat_skips_os_injector_on_wayland(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "0")
    monkeypatch.setenv("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "0")
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    monkeypatch.setattr(vdisplay_client, "_photo_vql_ide_capture_mismatch", lambda **kwargs: {"message": "mismatch"})
    import types

    fake_oi = types.ModuleType("gillm.injection.os_injector")
    fake_oi.try_drive_with_profile = lambda **kwargs: {
        "ok": True,
        "backend": "os_injector",
        "chat_x": 2323,
        "chat_y": 2409,
    }
    gillm_injection = types.ModuleType("gillm.injection")
    gillm_injection.os_injector = fake_oi
    gillm = types.ModuleType("gillm")
    gillm.injection = gillm_injection
    monkeypatch.setitem(sys.modules, "gillm", gillm)
    monkeypatch.setitem(sys.modules, "gillm.injection", gillm_injection)
    monkeypatch.setitem(sys.modules, "gillm.injection.os_injector", fake_oi)
    monkeypatch.setattr(vdisplay_client, "send_chat_via_ide_prompt", lambda *a, **k: None)
    monkeypatch.setattr(vdisplay_client, "_find_first_selector", lambda **k: (None, {"ok": False}))
    monkeypatch.setattr(vdisplay_client, "get_vql_chat_target_from_photo", lambda **k: {})

    reply = vdisplay_client.send_chat("hello jetbrains", ide="jetbrains", submit=False, dry_run=False)
    assert reply.get("backend") != "os_injector"


def test_verify_chat_text_visible_resolves_ocr_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vdisplay_client, "_ensure_vdisplay_runtime", lambda: True)
    monkeypatch.setattr(
        "koru.deps_autorepair.ensure_vision_ocr",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        vdisplay_client,
        "_capture_for_verify",
        lambda *args, **kwargs: (None, None, None),
    )

    out = vdisplay_client.verify_chat_text_visible("probe test", ide="jetbrains")
    assert out.get("error") == "screenshot capture failed"


def test_send_chat_uses_semantic_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "0")
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT", "0")
    monkeypatch.setenv("KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS", "0")
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
    monkeypatch.setattr(vdisplay_client, "_photo_vql_ide_capture_mismatch", lambda **kwargs: None)
    monkeypatch.setattr(vdisplay_client, "_VDISPLAY_DIRECT", True)

    def _find_first(*, ide, selectors):
        if selectors is vdisplay_client._CHAT_INPUT_SELECTORS:
            return ({"role": "input", "name_contains": "Chat"}, {"ok": True, "count": 1, "selected": {"id": "atspi:chat-input"}})
        return (None, {"ok": False, "count": 0})

    monkeypatch.setattr(vdisplay_client, "_find_first_selector", _find_first)
    monkeypatch.setattr(vdisplay_client, "_control_focus", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(vdisplay_client, "_control_set_value", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(vdisplay_client, "_submit_via_keyboard", lambda **kwargs: {"ok": True, "backend": "vdisplay+keyboard"})
    monkeypatch.setattr(vdisplay_client, "send_chat_via_ide_prompt", lambda *a, **k: None)
    monkeypatch.setattr(vdisplay_client, "get_vql_chat_target_from_photo", lambda **k: {})

    reply = vdisplay_client.send_chat("fix tests", ide="windsurf", submit=True, dry_run=False)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay"
    assert reply["selector"]["name_contains"] == "Chat"
    assert reply["submitted"] is True


def test_invoke_drive_uses_vdisplay_after_plugin_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from koru.autonomous_cycle_drive_retry import _invoke_client_autopilot_drive

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


def test_vdisplay_control_fallback_blocks_when_capture_preflight_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autonomous_cycle_gate import try_vdisplay_control_fallback

    send = MagicMock(return_value={"ok": True, "backend": "vdisplay"})
    monkeypatch.setattr(vdisplay_client, "vdisplay_fallback_enabled", lambda **kwargs: True)
    monkeypatch.setattr(
        vdisplay_client,
        "prepare_photo_vql_for_drive",
        lambda **kwargs: {
            "ok": False,
            "capture_confirmed": False,
            "message": "monitor not found: DP-2",
        },
    )
    monkeypatch.setattr(vdisplay_client, "load_vql_metadata", lambda: {"ui_elements": []})
    monkeypatch.setattr(vdisplay_client, "send_chat", send)

    reply = try_vdisplay_control_fallback(
        "hello",
        submit=True,
        ide="jetbrains",
        plugin_connected=False,
    )

    assert reply is not None
    assert reply["ok"] is False
    assert reply["backend"] == "vdisplay"
    assert reply["reason"] == "capture_prepare_failed"
    assert reply["capture_confirmed"] is False
    assert reply["desktop_preflight"]["vql_elements"] == 0
    send.assert_not_called()


def test_vdisplay_control_fallback_attaches_successful_desktop_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autonomous_cycle_gate import try_vdisplay_control_fallback

    send = MagicMock(return_value={"ok": True, "backend": "vdisplay"})
    monkeypatch.setattr(vdisplay_client, "vdisplay_fallback_enabled", lambda **kwargs: True)
    monkeypatch.setattr(
        vdisplay_client,
        "prepare_photo_vql_for_drive",
        lambda **kwargs: {"ok": True, "capture_confirmed": True},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "load_vql_metadata",
        lambda: {
            "_source": "test-sidecar",
            "ui_elements": [
                {"id": "window_0", "role": "window", "click_center": {"x": 10, "y": 20}}
            ],
        },
    )
    monkeypatch.setattr(vdisplay_client, "send_chat", send)
    monkeypatch.setattr(vdisplay_client, "record_koru_drive_step", lambda *args, **kwargs: None)

    reply = try_vdisplay_control_fallback(
        "hello",
        submit=True,
        ide="jetbrains",
        plugin_connected=False,
    )

    assert reply is not None
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay"
    assert reply["desktop_preflight"]["ok"] is True
    assert reply["desktop_preflight"]["capture_confirmed"] is True
    assert reply["desktop_preflight"]["vql_elements"] == 1
    assert reply["vql_context"] == "test-sidecar"
    send.assert_called_once()


def test_send_chat_prefers_photo_vql_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "1")
    monkeypatch.setattr(vdisplay_client, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(
        vdisplay_client,
        "perform_photo_vql_focus_and_edit",
        lambda prompt, **kwargs: {
            "ok": True,
            "backend": "vdisplay+photo-vql",
            "target": "chat",
            "coords": {"x": 854, "y": 440},
            "focus": {"ok": True, "message": "photo vql chat focus"},
            "edit": {"ok": True, "method": "ydotool-paste", "value": prompt},
            "is_code_edit": False,
        },
    )

    reply = vdisplay_client.send_chat("hello jetbrains", ide="jetbrains", submit=False, dry_run=False)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay+photo-vql"
    assert reply["coords"] == {"x": 854, "y": 440}


def test_send_chat_skips_photo_vql_for_jetbrains_on_capture_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "1")
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "1")
    photo = MagicMock()
    monkeypatch.setattr(vdisplay_client, "perform_photo_vql_focus_and_edit", photo)
    monkeypatch.setattr(
        vdisplay_client,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "capture shows Cursor, expected PyCharm", "window_titles": ["Cursor"]},
    )
    monkeypatch.setattr(vdisplay_client, "vdisplay_available", lambda: True)
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
    assert reply["backend"] == "vdisplay+ide-prompt"
    assert reply.get("photo_vql_skipped") is True
    photo.assert_not_called()
    ide_prompt.assert_called_once()


def test_send_chat_blocks_jetbrains_on_capture_mismatch_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", raising=False)
    photo = MagicMock()
    monkeypatch.setattr(vdisplay_client, "perform_photo_vql_focus_and_edit", photo)
    monkeypatch.setattr(
        vdisplay_client,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "capture shows Cursor", "window_titles": ["Cursor"]},
    )
    ide_prompt = MagicMock()
    monkeypatch.setattr(vdisplay_client, "send_chat_via_ide_prompt", ide_prompt)

    reply = vdisplay_client.send_chat("hello jetbrains", ide="jetbrains", submit=False, dry_run=False)
    assert reply["ok"] is False
    assert reply.get("backend") == "vdisplay+capture-blocked"
    assert reply.get("capture_confirmed") is False
    photo.assert_not_called()
    ide_prompt.assert_not_called()


def test_jetbrains_ide_hints_use_pycharm_not_toolbox() -> None:
    hints = vdisplay_client._ide_hints("jetbrains")
    assert hints["app"] == "pycharm"
    assert hints["window_title_contains"] == "PyCharm"


def test_send_chat_routes_code_edit_to_photo_vql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT", "1")
    monkeypatch.setattr(
        vdisplay_client,
        "perform_photo_vql_focus_and_edit",
        lambda prompt, **kwargs: {
            "ok": True,
            "backend": "vdisplay+photo-vql",
            "target": "editor/open-file",
            "coords": {"x": 1024, "y": 493},
            "focus": {"ok": True, "message": "focused editor"},
            "edit": {"ok": True, "dry_run": True, "value": prompt},
            "is_code_edit": kwargs.get("is_code_edit", True),
        },
    )

    reply = vdisplay_client.send_chat("# edit line", ide="cursor", submit=False, dry_run=False)
    assert reply["ok"] is True
    assert reply["backend"] == "vdisplay+photo-vql"
    assert reply["is_code_edit"] is True
    assert reply["coords"] == {"x": 1024, "y": 493}


def test_perform_photo_vql_focus_and_edit_dry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_DRY_RUN", "1")
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "0")
    monkeypatch.setattr(vdisplay_client, "_photo_vql_ide_capture_mismatch", lambda **kwargs: None)
    monkeypatch.setattr(
        vdisplay_client,
        "move_mouse_to_vql_target_and_focus_keyboard",
        lambda *args, **kwargs: {"ok": True, "dry_run": True},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "click_editor_via_photo_vql",
        lambda **kwargs: {"ok": True, "dry_run": True},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "get_vql_editor_target_from_photo",
        lambda: {"click_center": {"x": 1024, "y": 493}, "id": "window_0", "role": "window"},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: {"click_center": {"x": 854, "y": 440}, "id": "panel_3", "role": "panel"},
    )

    editor = vdisplay_client.perform_photo_vql_focus_and_edit("code", is_code_edit=True, ide="cursor")
    chat = vdisplay_client.perform_photo_vql_focus_and_edit("hello", is_code_edit=False, ide="cursor")
    assert editor["ok"] is True
    assert editor["coords"] == {"x": 1024, "y": 493}
    assert chat["ok"] is True
    assert chat["coords"] == {"x": 854, "y": 440}


def test_load_vql_metadata_sidecar_layers(tmp_path) -> None:
    sidecar = tmp_path / "capture.png.vql.json"
    sidecar.write_text(
        """{
          "metadata": {
            "render_intent": {
              "layers": [
                {"id": "window_0", "kind": "window", "bbox": {"x": 0, "y": 0, "w": 2040, "h": 1272}, "click_center": {"x": 1020, "y": 636}},
                {"id": "panel_3", "kind": "panel", "bbox": {"x": 700, "y": 300, "w": 300, "h": 280}, "click_center": {"x": 854, "y": 440}, "location": "center"}
              ]
            }
          }
        }""",
        encoding="utf-8",
    )
    meta = vdisplay_client.load_vql_metadata(str(sidecar))
    assert len(meta.get("ui_elements") or []) == 2
    assert meta["ui_elements"][0]["role"] == "window"
    assert meta["ui_elements"][0]["click_center"] == {"x": 1020, "y": 636}


def test_get_vql_editor_target_uses_window_bbox_w_h(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / "capture.png.vql.json"
    sidecar.write_text(
        """{
          "metadata": {
            "render_intent": {
              "layers": [
                {"id": "window_0", "kind": "window", "bbox": {"x": 0, "y": 0, "w": 2040, "h": 1272}, "click_center": {"x": 1020, "y": 636}},
                {"id": "panel_3", "kind": "panel", "bbox": {"x": 700, "y": 300, "w": 300, "h": 280}, "click_center": {"x": 854, "y": 440}, "location": "center"}
              ]
            }
          }
        }""",
        encoding="utf-8",
    )
    monkeypatch.delenv("KORU_VDISPLAY_VQL_PATH", raising=False)
    meta = vdisplay_client.load_vql_metadata(str(sidecar))
    try:
        from imgl.targets import resolve_editor_target

        target = resolve_editor_target(meta.get("ui_elements") or [], source=str(sidecar))
    except ImportError:
        pytest.skip("imgl not installed")
    assert target["id"] == "window_0"
    assert target["click_center"] == {"x": 1020, "y": 636}


def test_get_vql_chat_target_prefers_panel_over_send_chat_ocr(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / "capture.png.vql.json"
    sidecar.write_text(
        """{
          "metadata": {
            "render_intent": {
              "layers": [
                {"id": "window_0-input-50", "kind": "input", "label": "send_chat", "bbox": {"x": 964, "y": 507, "w": 77, "h": 17}, "click_center": {"x": 1002, "y": 515}},
                {"id": "panel_3", "kind": "panel", "bbox": {"x": 700, "y": 300, "w": 320, "h": 280}, "click_center": {"x": 854, "y": 440}, "location": "center"}
              ]
            }
          }
        }""",
        encoding="utf-8",
    )
    monkeypatch.delenv("KORU_VDISPLAY_VQL_PATH", raising=False)
    target = vdisplay_client.get_vql_chat_target_from_photo()
    # Uses default candidate path unless sidecar is pinned — load explicit path for test
    meta = vdisplay_client.load_vql_metadata(str(sidecar))
    try:
        from imgl.targets import resolve_chat_target

        target = resolve_chat_target(meta.get("ui_elements") or [], source=str(sidecar))
    except ImportError:
        pytest.skip("imgl not installed")
    assert target["id"] == "panel_3"
    assert target["click_center"] == {"x": 854, "y": 440}


def test_send_chat_via_ide_prompt_map_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vdisplay_client,
        "_resolve_ide_prompt_map",
        lambda app_id: "/maps/pycharm-chat.json",
    )
    monkeypatch.setattr(
        "vdisplay.ide_prompt.send_ide_prompt",
        lambda **kwargs: {"ok": False, "message": "set_value failed"},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "_control_click",
        lambda **kwargs: {"ok": True, "local_x": 1900, "local_y": 1629, "method": "ydotool"},
    )
    monkeypatch.setattr(
        vdisplay_client,
        "_type_text_at_vql_coords",
        lambda value, **kwargs: {"ok": True, "method": "ydotool-paste", "value": value},
    )

    reply = vdisplay_client.send_chat_via_ide_prompt(
        "hello fallback",
        ide="jetbrains",
        submit=False,
        dry_run=False,
    )
    assert reply is not None
    assert reply["ok"] is True
    assert reply.get("ide_prompt_fallback") is True
    assert reply["typed"]["method"] == "ydotool-paste"
