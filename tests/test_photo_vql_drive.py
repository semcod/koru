from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from koru.integrations import vdisplay_client as vc


_VALID_JB_CHAT_TARGET = {
    "click_center": {"x": 1985, "y": 1049},
    "id": "window_0-input-46",
    "label": "Ask",
    "bounds": {"w": 280, "h": 32},
    "source": "test.vql.json",
    "selection_method": "jetbrains_corner_heuristic",
}


@pytest.fixture(autouse=True)
def _clear_autonomy_session_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "KORU_AUTONOMY_SESSION_DIR",
        "VDISPLAY_SESSION_DIR",
        "KORU_VDISPLAY_VQL_PATH",
        "KORU_VDISPLAY_PHOTO_PATH",
        "VDISPLAY_SESSION",
        "VDISPLAY_SESSION_ID",
        "KORU_VDISPLAY_CAPTURE_MATCHES_IDE",
        "KORU_VDISPLAY_SOURCE",
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH",
        "KORU_VDISPLAY_ALLOW_IDE_MISMATCH",
        "KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION",
        "KORU_VDISPLAY_PREFER_PHOTO_VQL",
        "KORU_VDISPLAY_LLM_VISION_DECISION",
        "KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT",
        "KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KORU_VDISPLAY_VERIFY_AFTER_PASTE", "0")


_CONFIRMED_OBSERVE_META = {
    "ui_elements": [{"id": "w0", "role": "window", "label": "proj - PyCharm"}],
    "capture_validation": {"capture_confirmed": True, "expected_ide": "jetbrains"},
}


def _patch_confirmed_observe_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: dict(_CONFIRMED_OBSERVE_META))


def test_validate_chat_coords_warns_on_editor_like_position() -> None:
    target = {"source": "test.vql.json", "id": "input-1", "note": "test"}
    warnings = vc._validate_chat_coords_for_ide(x=1666, y=799, ide="jetbrains", target=target)
    assert any("below_850" in w for w in warnings)
    warnings_left = vc._validate_chat_coords_for_ide(x=500, y=1049, ide="jetbrains", target=target)
    assert any("below_1100" in w for w in warnings_left)


def test_build_vql_command_plan_includes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vc,
        "_global_coords_from_vql_local",
        lambda **kwargs: (1588, 2771, {"capture_meta_rotation": "left"}),
    )
    target = {
        "id": "window_0-input-46",
        "role": "input",
        "click_center": {"x": 1985, "y": 1049},
        "source": ".vdisplay/session/observe/capture.png.vql.json",
        "note": "JetBrains chat corner heuristic",
        "vql_candidates": [{"click_center": {"x": 1985, "y": 1049}}],
    }
    plan = vc._build_vql_command_plan(
        target=target,
        x=1985,
        y=1049,
        source="DP-2",
        ide="jetbrains",
        prompt="hello autonomy",
        stage="test",
        capture_provenance={"capture_confirmed": True, "png_path": "observe/capture.png"},
    )
    assert plan["inference_ok"] is True
    assert plan["final_global"] == {"x": 1588, "y": 2771}
    assert len(plan["commands"]) >= 4
    assert plan["commands"][1]["verb"] == "POINTER_MOVE"


def test_photo_vql_sidecar_needs_refresh_when_missing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_VQL_REFRESH", "auto")
    assert vc.photo_vql_sidecar_needs_refresh(source="DP-1", ide="cursor") is True


def test_photo_vql_sidecar_skip_when_layers_present(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_VQL_REFRESH", "auto")
    png = tmp_path / "koru-cont-dp1.png"
    vql = tmp_path / "koru-cont-dp1.png.vql.json"
    png.write_bytes(b"png")
    vql.write_text(
        json.dumps(
            {
                "metadata": {
                    "render_intent": {
                        "layers": [
                            {
                                "id": "window_0",
                                "kind": "window",
                                "bbox": {"x": 0, "y": 0, "w": 100, "h": 50},
                                "click_center": {"x": 50, "y": 25},
                            }
                        ],
                        "ui_elements": [
                            {
                                "id": "window_0",
                                "role": "window",
                                "bounds": {"x": 0, "y": 0, "w": 100, "h": 50},
                                "click_center": {"x": 50, "y": 25},
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert vc.photo_vql_sidecar_needs_refresh(source="DP-1", ide="cursor") is False


def test_vdisplay_source_for_ide_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    assert vc._vdisplay_source_for_ide("cursor") == "DP-1"
    assert vc._vdisplay_source_for_ide("jetbrains") == "DP-1"


def test_photo_vql_ide_window_warning_detects_cursor_on_jetbrains_drive() -> None:
    meta = {
        "ui_elements": [
            {
                "id": "window_0",
                "role": "window",
                "label": "test_project_config.py - ts - Cursor",
                "bounds": {"x": 0, "y": 0, "w": 2048, "h": 1280},
                "click_center": {"x": 1024, "y": 640},
            }
        ]
    }
    warn = vc._photo_vql_ide_window_warning(ide="jetbrains", meta=meta)
    assert warn is not None
    assert "Cursor" in warn["window_titles"][0]
    assert "pycharm" in warn["expected_tokens"]


def test_photo_vql_ide_window_warning_accepts_pycharm_title() -> None:
    meta = {
        "layers": [
            {
                "id": "window_0",
                "kind": "window",
                "text": "koru – main.py – PyCharm",
                "bbox": {"x": 0, "y": 0, "w": 2048, "h": 1280},
                "click_center": {"x": 1024, "y": 640},
            }
        ]
    }
    assert vc._photo_vql_ide_window_warning(ide="jetbrains", meta=meta) is None


def test_photo_vql_ide_window_warning_rejects_cursor_despite_pycharm_breadcrumb() -> None:
    """Breadcrumb ``PyCharm/JB`` inside Cursor must not satisfy jetbrains match."""
    meta = {
        "layers": [
            {
                "id": "window_0",
                "kind": "window",
                "text": "test_project_config.py - ts - Cursor",
                "bbox": {"x": 0, "y": 0, "w": 2048, "h": 1280},
            },
            {
                "id": "input-1",
                "role": "input",
                "label": "PyCharm/JB",
                "click_center": {"x": 1666, "y": 799},
            },
        ]
    }
    warn = vc._photo_vql_ide_window_warning(ide="jetbrains", meta=meta)
    assert warn is not None
    assert "Cursor" in warn["window_titles"][0]


def test_photo_vql_ide_window_warning_uses_embedded_capture_validation() -> None:
    meta = {
        "capture_validation": {
            "expected_ide": "jetbrains",
            "capture_confirmed": False,
            "ide_window_warning": {
                "ide": "jetbrains",
                "window_titles": ["automation-gap-analysis - ts - Cursor"],
                "message": "embedded",
            },
        }
    }
    warn = vc._photo_vql_ide_window_warning(ide="jetbrains", meta=meta)
    assert warn is not None
    assert warn["message"] == "embedded"


def test_vql_sidecar_stale_from_embedded_capture_validation(tmp_path) -> None:
    vql = tmp_path / "capture.png.vql.json"
    png = tmp_path / "capture.png"
    png.write_bytes(b"png")
    vql.write_text(
        json.dumps(
            {
                "metadata": {
                    "capture_validation": {
                        "expected_ide": "jetbrains",
                        "capture_confirmed": False,
                        "reasons": ["ide_window_mismatch"],
                    },
                    "render_intent": {"layers": [{"kind": "window", "text": "Cursor"}]},
                }
            }
        ),
        encoding="utf-8",
    )
    from koru.integrations import autonomy_session as sess

    stale, info = sess.vql_sidecar_is_stale(vql, png, layer_count=1)
    assert stale is True
    assert "capture_validation_failed" in info["reasons"]


def test_photo_vql_sidecar_stale_when_older_than_max_age(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_VDISPLAY_VQL_MAX_AGE_S", "60")
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_VQL_REFRESH", "auto")
    png = tmp_path / "koru-cont-dp1.png"
    vql = tmp_path / "koru-cont-dp1.png.vql.json"
    png.write_bytes(b"png")
    vql.write_text(
        json.dumps(
            {
                "metadata": {
                    "render_intent": {
                        "layers": [{"id": "w", "kind": "window", "click_center": {"x": 1, "y": 2}}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    old = time.time() - 120
    os.utime(png, (old, old))
    os.utime(vql, (old, old))
    assert vc.photo_vql_sidecar_needs_refresh(source="DP-1", ide="cursor") is True


def test_begin_autonomy_session_creates_date_scoped_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    session = vc.begin_autonomy_session(ide="jetbrains", source="DP-2")
    assert session.is_dir()
    assert session.parent.name  # YYYY-MM-DD
    assert (session / "observe").is_dir()
    assert (session / "decide").is_dir()
    assert (session / "act").is_dir()
    assert (session / "session.json").is_file()
    png, vql = session / "observe" / "capture.png", session / "observe" / "capture.png.vql.json"
    assert os.environ["KORU_VDISPLAY_PHOTO_PATH"] == str(png)
    assert os.environ["KORU_VDISPLAY_VQL_PATH"] == str(vql)


def test_load_vql_metadata_skips_stale_global_sidecar(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    monkeypatch.setenv("KORU_VDISPLAY_VQL_MAX_AGE_S", "30")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vdisplay").mkdir()
    png = tmp_path / ".vdisplay" / "koru-cont-dp1.png"
    vql = tmp_path / ".vdisplay" / "koru-cont-dp1.png.vql.json"
    png.write_bytes(b"x")
    vql.write_text(json.dumps({"elements": [{"id": "e1", "bbox": [0, 0, 10, 10]}]}), encoding="utf-8")
    old = time.time() - 999
    os.utime(png, (old, old))
    os.utime(vql, (old, old))
    meta = vc.load_vql_metadata()
    assert meta.get("error") == "no fresh vql found"
    assert meta.get("stale_skipped")


def test_resolve_photo_png_path_from_vql_sidecar(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))
    png = tmp_path / "koru-cont-dp2.png"
    vql = tmp_path / "koru-cont-dp2.png.vql.json"
    png.write_bytes(b"png")
    vql.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("KORU_VDISPLAY_VQL_PATH", str(vql))
    assert vc._resolve_photo_png_path_from_vql() == str(png)


def test_ensure_vdisplay_ide_control_clicks_map_interior(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.setattr(vc, "_resolve_ide_prompt_map", lambda app_id: "/maps/pycharm-chat.json")
    monkeypatch.setattr(vc, "_map_interior_targets_for_ide", lambda app_id, map_path: ("ai-chat-input",))
    monkeypatch.setattr(vc, "_map_raise_targets_for_ide", lambda app_id, map_path: ("prompt",))
    monkeypatch.setattr(
        "koru.integrations.photo_vql_monitor.map_capture_monitor_mismatch",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(vc, "_control_focus", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(vc, "_dismiss_gnome_overview", lambda **kwargs: {"ok": True, "skipped": True})
    monkeypatch.setattr(
        vc,
        "_control_click",
        lambda **kwargs: {"ok": True, "local_x": 1900, "local_y": 1629, "map_target": kwargs.get("map_target")},
    )
    monkeypatch.setattr("vdisplay.control.timing.control_focus_type_seconds", lambda: 0)

    out = vc.ensure_vdisplay_ide_control(ide="jetbrains", source="DP-2")
    assert out["ok"] is True
    assert out.get("interior_focused") is True


def test_prefer_photo_vql_auto_enables_when_capture_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
    monkeypatch.setenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "1")
    assert vc._prefer_photo_vql_chat(ide="jetbrains") is True
    assert vc._prefer_ide_prompt_over_photo_vql(ide="jetbrains") is False


def test_prefer_photo_vql_auto_falls_back_to_map_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_PREFER_PHOTO_VQL", "auto")
    monkeypatch.delenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", raising=False)
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "wrong window"},
    )
    assert vc._prefer_photo_vql_chat(ide="jetbrains") is False
    assert vc._prefer_ide_prompt_over_photo_vql(ide="jetbrains") is True


def test_ensure_vdisplay_ide_control_dry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_DRY_RUN", "1")
    out = vc.ensure_vdisplay_ide_control(ide="jetbrains", source="DP-2")
    assert out["ok"] is True
    assert out.get("dry_run") is True


def test_perform_photo_vql_llm_coords_before_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    _patch_confirmed_observe_meta(monkeypatch)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: dict(_VALID_JB_CHAT_TARGET),
    )
    monkeypatch.setattr(
        vc,
        "_resolve_photo_vql_llm_coords",
        lambda **kwargs: (order.append("llm") or (1985, 1049, {"click_center": {"x": 1985, "y": 1049}, "confidence": 0.9})),
    )
    monkeypatch.setattr(
        vc,
        "move_mouse_to_vql_target_and_focus_keyboard",
        lambda target, **kwargs: order.append(f"focus:{target['click_center']['x']}") or {"ok": True},
    )
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda value, x, y, **kwargs: order.append(f"type:{x},{y}") or {"ok": True, "method": "paste"},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)

    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    assert out["ok"] is True
    assert out["llm_used"] is True
    assert order[0] == "llm"
    assert order[1] == "focus:1985"
    assert order[2] == "type:1985,1049"


def test_perform_photo_vql_map_fallback_when_type_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_confirmed_observe_meta(monkeypatch)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: dict(_VALID_JB_CHAT_TARGET),
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **kwargs: (1985, 1049, None))
    monkeypatch.setattr(vc, "move_mouse_to_vql_target_and_focus_keyboard", lambda *a, **k: {"ok": False})
    monkeypatch.setattr(vc, "_type_text_at_vql_coords", lambda *a, **k: {"ok": False, "error": "click failed"})
    monkeypatch.setattr(
        vc,
        "_photo_vql_map_paste_fallback",
        lambda prompt, **kwargs: {"ok": True, "method": "map-click-paste", "value": prompt},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    # Note: this test does not exercise LLM (no VISION_DECISION), it tests map paste fallback when focus+type fail

    out = vc.perform_photo_vql_focus_and_edit("fallback text", ide="jetbrains", source="DP-2")
    assert out["ok"] is True
    assert out["edit"].get("photo_vql_map_fallback") is True
    assert out["edit"]["method"] == "map-click-paste"


def test_jetbrains_chat_corner_prefers_bottom_right_input() -> None:
    layers = [
        {
            "id": "window_0-input-33",
            "role": "input",
            "label": "PyCharm/JB",
            "click_center": {"x": 1666, "y": 799},
            "bounds": {"x": 1617, "y": 789, "w": 98, "h": 21},
        },
        {
            "id": "window_0-input-46",
            "role": "input",
            "label": "Ask",
            "click_center": {"x": 1985, "y": 1049},
            "bounds": {"x": 1949, "y": 1041, "w": 280, "h": 32},
        },
    ]
    target = vc._jetbrains_chat_corner_target_from_layers(layers, source="test.vql.json")
    assert target is not None
    assert target["click_center"] == {"x": 1985, "y": 1049}


def test_jetbrains_chat_corner_rejects_small_background() -> None:
    layers = [
        {
            "id": "window_0-input-46",
            "role": "input",
            "label": "background",
            "click_center": {"x": 1653, "y": 1104},
            "bounds": {"x": 1608, "y": 1096, "w": 90, "h": 17},
        },
    ]
    assert vc._jetbrains_chat_corner_target_from_layers(layers, source="test.vql.json") is None


def test_validate_vql_chat_target_rejects_background_small() -> None:
    target = {
        "id": "window_0-input-46",
        "role": "input",
        "label": "background",
        "click_center": {"x": 1653, "y": 1104},
        "bounds": {"w": 90, "h": 17},
        "source": "observe/capture.png.vql.json",
    }
    val = vc.validate_vql_chat_target(target, ide="jetbrains")
    assert val["vql_element_size_ok"] is False
    assert "vql_element_too_small" in val["validation_errors"][0]
    assert val["ok"] is False


def test_validate_vql_chat_target_mismatch() -> None:
    target = {
        "id": "window_0-input-46",
        "role": "input",
        "label": "Ask",
        "click_center": {"x": 1985, "y": 1049},
        "bounds": {"w": 280, "h": 32},
        "source": "observe/capture.png.vql.json",
        "selection_method": "jetbrains_corner_heuristic",
    }
    meta = {
        "ui_elements": [
            {"id": "w0", "role": "window", "label": "project - Cursor"},
        ]
    }
    mismatch = {"message": "wrong IDE", "window_titles": ["project - Cursor"]}
    val = vc.validate_vql_chat_target(
        target, ide="jetbrains", meta=meta, capture_mismatch=mismatch
    )
    assert val["app_match"] is False
    assert val["capture_title"] == "project - Cursor"
    assert "vql_invalid_for_chat_capture_mismatch" in val["validation_errors"]
    assert val["ok"] is False


def test_get_vql_chat_map_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    layers = [
        {
            "id": "window_0-input-46",
            "role": "input",
            "label": "background",
            "click_center": {"x": 1653, "y": 1104},
            "bounds": {"w": 90, "h": 17},
        },
    ]
    monkeypatch.setattr(vc, "_photo_vql_elements", lambda: (layers, "observe/capture.png.vql.json"))
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "Cursor capture", "window_titles": ["x - Cursor"]},
    )
    monkeypatch.setattr(
        vc,
        "_map_chat_target_capture_local",
        lambda **kwargs: {
            "click_center": {"x": 1900, "y": 1629},
            "id": "map:ai-chat-input",
            "role": "input",
            "source": "/maps/pycharm-chat.json",
        },
    )
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {"ui_elements": []})
    target = vc.get_vql_chat_target_from_photo(ide="jetbrains")
    assert target["selection_method"] == "map_calibrated_on_mismatch"
    assert target["vql_validation"]["used_map_because_mismatch_or_bad_element"] is True


def test_capture_provenance_uses_embedded_validation() -> None:
    meta = {
        "ui_elements": [{"id": "w0", "role": "window", "label": "proj - PyCharm"}],
        "capture_validation": {"capture_confirmed": False, "expected_ide": "jetbrains"},
    }
    prov = vc._capture_provenance(ide="jetbrains", meta=meta)
    assert prov["capture_confirmed"] is False
    assert prov["capture_title"] == "proj - PyCharm"


def test_capture_validation_false_without_titles_triggers_warning() -> None:
    meta = {
        "capture_validation": {
            "capture_confirmed": False,
            "expected_ide": "jetbrains",
            "reasons": ["empty_vql_layers", "missing_window_layer"],
            "window_titles": [],
        }
    }
    warn = vc._photo_vql_ide_window_warning(ide="jetbrains", meta=meta)
    assert warn is not None
    assert warn.get("capture_validation_failed") is True
    assert "empty_vql_layers" in str(warn.get("reasons"))


def test_build_vql_command_plan_uses_observe_provenance_not_map() -> None:
    target = {
        "id": "map:ai-chat-input",
        "click_center": {"x": 1900, "y": 1629},
        "source": "/maps/pycharm-chat.json",
    }
    observe_prov = {
        "capture_confirmed": False,
        "png_path": "/session/observe/capture.png",
        "vql_path": "/session/observe/capture.png.vql.json",
    }
    plan = vc._build_vql_command_plan(
        target=target,
        x=1900,
        y=1629,
        source="DP-1",
        ide="jetbrains",
        prompt="hello",
        capture_provenance=observe_prov,
    )
    assert plan["capture_confirmed"] is False
    assert plan["inference_ok"] is False
    assert plan["capture_provenance"]["vql_path"] == "/session/observe/capture.png.vql.json"


def test_perform_photo_vql_verify_failure_blocks_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_VERIFY_AFTER_PASTE", "1")
    monkeypatch.setattr(
        vc,
        "load_vql_metadata",
        lambda *a, **k: {
            "ui_elements": [{"id": "w0", "role": "window", "label": "proj - PyCharm"}],
            "capture_validation": {"capture_confirmed": True, "expected_ide": "jetbrains"},
        },
    )
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: dict(_VALID_JB_CHAT_TARGET),
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **kwargs: (1985, 1049, None))
    monkeypatch.setattr(vc, "move_mouse_to_vql_target_and_focus_keyboard", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda value, **kwargs: {"ok": True, "method": "ydotool-paste", "value": value},
    )
    monkeypatch.setattr(
        vc,
        "verify_chat_text_visible",
        lambda *a, **k: {"ok": False, "verified": False, "mode": "ocr_contains", "error": "text not found"},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)

    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    assert out["edit"]["ok"] is True
    assert out["verified"] is False
    assert out["ok"] is False


def test_normalize_drive_result_blocks_false_ok_when_edit_ok_but_unverified() -> None:
    photo = {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "edit": {"ok": True, "method": "ydotool-paste"},
        "verified": False,
        "verification": {"verified": False},
        "capture_confirmed": True,
        "vql_command_plan": {"inference_ok": True},
    }
    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)
    assert out["ok"] is False
    assert out["verified"] is False


def test_normalize_drive_result_blocks_false_ok_on_inference_fail() -> None:
    photo = {
        "ok": False,
        "backend": "vdisplay+photo-vql",
        "edit": {"ok": True, "method": "ydotool-paste"},
        "capture_confirmed": False,
        "capture_provenance": {"capture_confirmed": False},
        "vql_command_plan": {"inference_ok": False, "warnings": ["capture_ide_mismatch"]},
    }
    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)
    assert out["ok"] is False
    assert out["capture_confirmed"] is False


def test_prepare_syncs_ide_control_capture_confirmed_from_observe(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    capture_png = Path("/tmp/capture.png")
    monkeypatch.setattr(vc, "_resolve_vdisplay_source_for_ide", lambda ide, **k: ("DP-1", {"ok": True, "resolved_source": "DP-1"}))
    monkeypatch.setattr(vc, "_vdisplay_source_for_ide", lambda ide: "DP-1")
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: True)
    monkeypatch.setattr(
        vc,
        "ensure_vdisplay_ide_control",
        lambda **k: {"map_path": "/maps/pycharm-chat.json", "map_actuation_ok": True, "interior_focused": True},
    )
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: False)
    monkeypatch.setattr(vc, "_resolve_photo_png_path", lambda src: capture_png)
    monkeypatch.setattr(
        vc,
        "load_vql_metadata",
        lambda *a, **k: {
            "ui_elements": [{"id": "w0", "role": "window", "label": "proj - PyCharm"}],
            "capture_validation": {
                "capture_confirmed": False,
                "expected_ide": "jetbrains",
                "reasons": ["empty_vql_layers"],
            },
        },
    )

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")

    assert out["capture_confirmed"] is False
    assert out["capture_ready"] is False
    assert out["ok"] is False
    assert out.get("error")
    assert out["ide_control"]["capture_confirmed"] is False
    assert out["ide_control"]["confirmation_bias_risk"]


def test_prepare_does_not_surface_confirm_when_vql_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vc,
        "_resolve_vdisplay_source_for_ide",
        lambda ide, **k: (
            "HDMI-1",
            {
                "ok": True,
                "ide_surface_best": {
                    "display_name": "PyCharm",
                    "monitor_name": "HDMI-1",
                    "stack": "jetbrains_xwayland",
                    "pid": 123,
                },
            },
        ),
    )
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: False)
    monkeypatch.setattr(vc, "_resolve_ide_prompt_map", lambda app_id: None)
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: True)
    capture_error = (
        "vdisplay host capture failed; screencast capture needs python3-dbus: "
        "No module named 'dbus'; portal screenshot denied (Screen Recording permission missing)"
    )
    monkeypatch.setattr(
        vc,
        "refresh_photo_vql_sidecar",
        lambda **k: {
            "ok": False,
            "source": "HDMI-1",
            "png": "/tmp/capture.png",
            "returncode": 1,
            "error": capture_error,
            "hint": vc._vdisplay_capture_failure_hint(capture_error),
        },
    )
    monkeypatch.setenv("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "1")

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")

    assert out["ok"] is False
    assert out["capture_confirmed"] is False
    assert out["capture_ready"] is False
    assert "vdisplay host capture failed" in out["error"]
    assert "dbus" in out["hint"].lower()
    assert "Screen Recording" in out["hint"]
    assert out.get("capture_confirmation_source") != "ide_surface_best"


def test_photo_vql_chat_input_candidates_penalizes_terminal_background() -> None:
    layers = [
        {
            "role": "input",
            "label": "background",
            "click_center": {"x": 1653, "y": 1104},
            "bounds": {"w": 90, "h": 17},
        },
        {
            "role": "input",
            "label": "Ask",
            "click_center": {"x": 1985, "y": 1049},
            "bounds": {"w": 280, "h": 32},
        },
    ]
    cands = vc._photo_vql_chat_input_candidates(layers, limit=2, ide="jetbrains")
    assert cands[0]["label"] == "ask"
    assert cands[1]["label"] == "background"


def test_windsurf_chat_input_candidates_prefer_top_composer() -> None:
    from koru.integrations.photo_vql_target import vscode_family_chat_target_from_layers

    layers = [
        {
            "kind": "input",
            "text": "",
            "click_center": {"x": 1200, "y": 51},
            "bbox": {"w": 420, "h": 36},
        },
        {
            "kind": "input",
            "text": "Windsurf (Pre-Release)",
            "click_center": {"x": 900, "y": 1240},
            "bbox": {"w": 180, "h": 24},
        },
        {
            "kind": "input",
            "text": "tom@nvidia:~/github/semcod/koru$",
            "click_center": {"x": 700, "y": 1177},
            "bbox": {"w": 500, "h": 28},
        },
    ]
    target = vscode_family_chat_target_from_layers(layers, ide="windsurf", source="test.vql.json")
    assert target is not None
    assert target["click_center"]["y"] == 51


def test_enrich_capture_meta_uses_map_region_when_sidecar_origin_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "pycharm-chat.json"
    map_path.write_text(
        json.dumps(
            {
                "capture_meta": {
                    "source": "DP-2",
                    "region": {"x": 0, "y": 1932, "width": 2048, "height": 1280},
                    "rotation": "left",
                    "screencast_stream": True,
                    "width": 2048,
                    "height": 1280,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vc, "_resolve_ide_prompt_map", lambda _app_id: str(map_path))
    meta = {"source": "DP-2", "width": 2048, "height": 1280, "region": {"x": 0, "y": 0, "width": 2048, "height": 1280}}
    enriched = vc._enrich_capture_meta_for_pointer(meta, "DP-2")
    region = enriched.get("region") or {}
    assert int(region.get("y") or 0) >= 1900 or enriched.get("rotation") == "left"


def test_perform_photo_vql_submit_after_paste(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_confirmed_observe_meta(monkeypatch)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: dict(_VALID_JB_CHAT_TARGET),
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **kwargs: (1985, 1049, None))
    monkeypatch.setattr(vc, "move_mouse_to_vql_target_and_focus_keyboard", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda value, **kwargs: {"ok": True, "method": "ydotool-paste", "value": value},
    )
    monkeypatch.setattr(
        vc,
        "_photo_vql_submit_chat",
        lambda **kwargs: {"ok": True, "method": "ydotool-key", "submit_key": "ctrl+Return"},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)

    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2", submit=True)
    assert out["ok"] is True
    assert out["submitted"] is True
    assert out["submit"]["method"] == "ydotool-key"


def test_build_vql_command_plan_flags_capture_mismatch() -> None:
    target = {
        "id": "window_0-input-54",
        "click_center": {"x": 1653, "y": 1104},
        "source": "capture.png.vql.json",
    }
    plan = vc._build_vql_command_plan(
        target=target,
        x=1653,
        y=1104,
        source="DP-2",
        ide="jetbrains",
        prompt="test",
        llm_decision={"confidence": 0.9},
        capture_mismatch={"message": "Cursor foreground"},
    )
    assert plan["inference_ok"] is False
    assert plan["capture_confirmed"] is False
    assert "capture_ide_mismatch" in plan["warnings"]
    assert "llm_refined_on_unconfirmed_ide_capture" in plan["warnings"]


def test_perform_photo_vql_blocks_jetbrains_chat_on_capture_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda **k: {"message": "capture shows Cursor", "window_titles": ["Cursor"]},
    )
    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    assert out["ok"] is False
    assert "Cursor" in str(out.get("error", ""))
    assert out.get("ide_window_warning")


def test_perform_photo_vql_blocks_invalid_chat_target_before_actuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_confirmed_observe_meta(monkeypatch)
    calls = {"focus": 0, "type": 0}
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **k: {
            "id": "photo-chat-editor-center",
            "click_center": {"x": 1024, "y": 640},
            "selection_method": "imgl_resolve_chat_target",
            "vql_validation": {
                "ok": False,
                "coord_warnings": [
                    "target_not_from_live_vql_layers_using_fallback_center",
                    "chat_local_y=640_below_850_likely_editor_not_bottom_right_composer",
                ],
                "validation_errors": [],
            },
        },
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **k: (1024, 640, None))
    monkeypatch.setattr(
        vc,
        "move_mouse_to_vql_target_and_focus_keyboard",
        lambda *a, **k: calls.__setitem__("focus", calls["focus"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda *a, **k: calls.__setitem__("type", calls["type"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)

    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    assert out["ok"] is False
    assert "photo-VQL chat target not verified" in out["error"]
    assert calls == {"focus": 0, "type": 0}


def test_perform_photo_vql_blocks_suspicious_surface_target_before_actuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_confirmed_observe_meta(monkeypatch)
    calls = {"focus": 0, "type": 0}
    monkeypatch.setenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "1")
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR", "1")
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **k: {
            "id": "surface:jetbrains-chat",
            "role": "input",
            "click_center": {"x": 1880, "y": 691},
            "selection_method": "jetbrains_surface_bounds",
            "vql_validation": {
                "ok": False,
                "vql_valid": True,
                "app_match": True,
                "coord_warnings": [
                    "chat_local_y=691_below_850_likely_editor_not_bottom_right_composer"
                ],
                "validation_errors": [],
                "surface_bounds_trusted": True,
            },
        },
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **k: (1880, 691, None))
    monkeypatch.setattr(
        vc,
        "move_mouse_to_vql_target_and_focus_keyboard",
        lambda *a, **k: calls.__setitem__("focus", calls["focus"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda *a, **k: calls.__setitem__("type", calls["type"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)

    out = vc.perform_photo_vql_focus_and_edit("probe test", ide="jetbrains", source="HDMI-1", submit=True)
    assert out["ok"] is False
    assert "photo-VQL chat target not verified" in out["error"]
    assert "chat_local_y=691" in str(out.get("vql_command_plan", {}).get("warnings"))
    assert calls == {"focus": 0, "type": 0}


def test_type_text_at_vql_coords_blocks_suspicious_chat_coords_before_click(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"click": 0}
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "vdisplay_available", lambda: True)
    monkeypatch.setattr(
        vc,
        "_ydotool_click_capture_local",
        lambda **k: calls.__setitem__("click", calls["click"] + 1) or {"ok": True},
    )

    out = vc._type_text_at_vql_coords(
        "probe test",
        x=1880,
        y=691,
        source="HDMI-1",
        ide="jetbrains",
        force_point_click=True,
        vql_target={
            "id": "surface:jetbrains-chat",
            "selection_method": "jetbrains_surface_bounds",
            "click_center": {"x": 1880, "y": 691},
            "vql_validation": {
                "ok": False,
                "coord_warnings": [
                    "chat_local_y=691_below_850_likely_editor_not_bottom_right_composer"
                ],
                "validation_errors": [],
            },
        },
    )

    assert out["ok"] is False
    assert "refusing to type at suspicious VQL chat coords" in out["error"]
    assert "chat_local_y=691" in str(out.get("warnings"))
    assert calls == {"click": 0}


def test_resolve_auto_picks_dp_when_default_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    monkeypatch.setitem(vc._IDE_DEFAULT_SOURCE, "jetbrains", "DP-2")
    probe = {
        "ok": True,
        "monitor_names": ["DP-1", "HDMI-1"],
        "monitors": [
            {"name": "DP-1", "primary": False},
            {"name": "HDMI-1", "primary": True},
        ],
    }
    src, resolved = vc._resolve_vdisplay_source_for_ide("jetbrains", probe=probe)
    assert src == "DP-1"
    assert resolved.get("source_auto_resolved") is True
    assert resolved.get("source_was") == "DP-2"
    assert resolved.get("ok") is True


def test_resolve_explicit_missing_monitor_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_SOURCE", "DP-2")
    probe = {
        "ok": True,
        "monitor_names": ["DP-1", "HDMI-1"],
        "monitors": [{"name": "DP-1"}, {"name": "HDMI-1", "primary": True}],
    }
    src, resolved = vc._resolve_vdisplay_source_for_ide("jetbrains", probe=probe)
    assert src == "DP-2"
    assert resolved.get("ok") is False
    assert "DP-2" in str(resolved.get("error"))


def test_resolve_prefers_ide_surface_monitor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    probe = {
        "ok": True,
        "monitor_names": ["DP-1", "HDMI-1"],
        "monitors": [
            {"name": "DP-1", "primary": False},
            {"name": "HDMI-1", "primary": True},
        ],
        "ide_surface_best": {
            "display_name": "PyCharm",
            "ide_hint": "jetbrains",
            "monitor_name": "HDMI-1",
            "stack": "jetbrains_xwayland",
        },
    }
    src, resolved = vc._resolve_vdisplay_source_for_ide("jetbrains", probe=probe)
    assert src == "HDMI-1"
    assert resolved.get("source_from_ide_surface") == "HDMI-1"
    assert resolved.get("ok") is True


def test_map_capture_monitor_mismatch(tmp_path: Path) -> None:
    from koru.integrations.photo_vql_monitor import map_capture_monitor_mismatch

    map_path = tmp_path / "pycharm-chat.json"
    map_path.write_text(
        json.dumps({"capture_meta": {"source": "DP-2", "rotation": "left"}, "elements": {}}),
        encoding="utf-8",
    )
    assert map_capture_monitor_mismatch(str(map_path), source="HDMI-1") == {
        "map_path": str(map_path),
        "map_source": "DP-2",
        "capture_source": "HDMI-1",
        "map_rotation": "left",
        "message": (
            f"GUI map {str(map_path)!r} is calibrated for monitor 'DP-2' (rotation='left'), "
            "but capture source is 'HDMI-1'. "
            "Recalibrate the map or set KORU_VDISPLAY_SOURCE='DP-2'."
        ),
    }
    assert map_capture_monitor_mismatch(str(map_path), source="DP-2") is None


def test_format_wayland_vdisplay_operator_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    from koru.integrations.photo_vql_monitor import format_wayland_vdisplay_operator_hint

    monkeypatch.setattr(
        "koru.integrations.vdisplay_client._desktop_probe",
        lambda **kwargs: {
            "ide_surface_best": {"monitor_name": "HDMI-1", "display_name": "PyCharm"},
        },
    )
    hint = format_wayland_vdisplay_operator_hint(ide="jetbrains")
    assert "HDMI-1" in hint
    assert "vdisplay-agent serve" in hint
    assert "screencast start --force" in hint
    assert "screencast probe --via-agent" in hint
    assert "prepare-vdisplay" in hint


def test_desktop_probe_missing_source_errors() -> None:
    probe = vc._desktop_probe(ide="jetbrains", source="DP-2")
    if probe.get("monitor_names") and "DP-2" not in probe["monitor_names"]:
        assert probe.get("ok") is False
        assert "DP-2" in str(probe.get("error"))


def test_prepare_aborts_when_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "1")
    monkeypatch.setattr(
        vc,
        "_resolve_vdisplay_source_for_ide",
        lambda ide, **k: (
            "DP-2",
            {"ok": False, "error": "no connected monitor", "monitor_names": ["DP-1"]},
        ),
    )
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    persisted: list[tuple[str, str]] = []

    def _persist(session_dir, phase, name, payload):
        persisted.append((phase, name))

    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", _persist)
    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")
    assert out["ok"] is False
    assert "desktop_probe" in out
    assert ("decide", "desktop_probe") in persisted


def test_find_latest_koru_session_uses_mtime_not_artifacts(tmp_path: Path) -> None:
    from koru.integrations import autonomy_session as sess

    day = tmp_path / "2026-06-12"
    day.mkdir()
    older = day / "09-00-00__koru-jetbrains"
    newer = day / "09-05-00__koru-jetbrains"
    older.mkdir()
    newer.mkdir()
    (older / "act").mkdir()
    (older / "act" / "drive_result.json").write_text("{}", encoding="utf-8")
    import os
    import time

    os.utime(newer, (time.time(), time.time() + 10))
    latest = sess.find_latest_koru_session(ide="jetbrains", root=tmp_path)
    assert latest == newer


def test_competing_ide_label_from_warning() -> None:
    warn = {
        "window_titles": ["automation-gap - Cursor"],
        "competing_detected": ["cursor", "vscode"],
    }
    assert vc._competing_ide_label_from_warning(warn) == "Cursor"


def test_prepare_aborts_after_single_attempt_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    calls = {"ide_control": 0, "refresh": 0}

    def _ide_control(**k):
        calls["ide_control"] += 1
        return {"map_path": "/maps/pycharm-chat.json", "map_actuation_ok": True}

    def _refresh(**k):
        calls["refresh"] += 1
        return {
            "ok": True,
            "source": "DP-2",
            "png": "/tmp/capture.png",
            "vql": "/tmp/capture.png.vql.json",
            "ide_window_warning": {
                "message": "wrong IDE",
                "window_titles": ["proj - Cursor"],
                "competing_detected": ["cursor"],
            },
        }

    monkeypatch.setattr(vc, "_resolve_vdisplay_source_for_ide", lambda ide, **k: ("DP-2", {"ok": True}))
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: True)
    monkeypatch.setattr(vc, "ensure_vdisplay_ide_control", _ide_control)
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: True)
    monkeypatch.setattr(vc, "refresh_photo_vql_sidecar", _refresh)
    monkeypatch.setenv("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "3")
    monkeypatch.setenv("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0")
    monkeypatch.setattr(vc, "_raise_alt_tab_enabled", lambda **k: False)

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")

    assert out["ok"] is False
    assert out["ide_control_attempts"] == 1
    assert calls["ide_control"] == 1
    assert calls["refresh"] == 1
    assert out.get("competing_ide") == "Cursor"


def test_perform_blocked_on_mismatch_without_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda **k: {"message": "cursor foreground", "window_titles": ["x - Cursor"]},
    )
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", raising=False)

    res = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    assert res["ok"] is False
    assert res.get("ide_window_warning")


def test_perform_map_path_allowed_with_explicit_ide_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_confirmed_observe_meta(monkeypatch)
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda **k: {"message": "cursor foreground"},
    )
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **k: {
            "id": "map:prompt",
            "click_center": {"x": 1900, "y": 1629},
            "selection_method": "map_calibrated_on_mismatch",
            "vql_validation": {"ok": True, "app_match": True},
        },
    )
    monkeypatch.setattr(vc, "_resolve_photo_vql_llm_coords", lambda **k: (1900, 1629, None))
    monkeypatch.setattr(vc, "_resolve_photo_png_path_from_vql", lambda **k: "/tmp/capture.png")
    monkeypatch.setattr(vc, "_observe_vql_sidecar_path", lambda **k: "/tmp/capture.png.vql.json")
    monkeypatch.setattr(vc, "move_mouse_to_vql_target_and_focus_keyboard", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(vc, "_type_text_at_vql_coords", lambda *a, **k: {"ok": True, "method": "paste"})
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", "1")

    res = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-2")
    plan = res.get("vql_command_plan") or {}
    assert plan.get("selection_method") == "map_calibrated_on_mismatch"
    assert plan.get("inference_ok") is True
    assert res.get("ok") is True


def test_raise_alt_tab_default_on_for_jetbrains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_RAISE_ALT_TAB", raising=False)
    assert vc._raise_alt_tab_enabled(ide="jetbrains") is True
    assert vc._raise_alt_tab_enabled(ide="cursor") is False


def test_prepare_map_fallback_requires_allow_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    capture_png = Path("/tmp/capture.png")
    monkeypatch.setattr(vc, "_resolve_vdisplay_source_for_ide", lambda ide, **k: ("DP-2", {"ok": True}))
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: True)
    monkeypatch.setattr(
        vc,
        "ensure_vdisplay_ide_control",
        lambda **k: {"map_path": "/maps/pycharm-chat.json", "map_actuation_ok": True},
    )
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: False)
    monkeypatch.setattr(vc, "_resolve_photo_png_path", lambda src: capture_png)
    monkeypatch.setattr(
        vc,
        "load_vql_metadata",
        lambda *a, **k: {
            "ui_elements": [{"id": "w0", "role": "window", "label": "proj - Cursor"}],
            "capture_validation": {"capture_confirmed": False, "expected_ide": "jetbrains"},
        },
    )
    monkeypatch.setattr(vc, "_raise_alt_tab_enabled", lambda **k: False)
    monkeypatch.delenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", raising=False)

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")
    assert out["ok"] is False
    assert out.get("map_only_fallback") is not True
    assert out["capture_confirmed"] is False


def test_prepare_focus_recovery_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    def _recovery(**k):
        return {
            "ok": True,
            "source": "DP-2",
            "png": "/tmp/capture.png",
            "vql": "/tmp/capture.png.vql.json",
            "capture_confirmed": True,
            "focus_recovery": {"ok": True, "recovered_on_attempt": 1, "attempts": [{"attempt": 1, "ok": True}]},
        }

    monkeypatch.setattr(vc, "_resolve_vdisplay_source_for_ide", lambda ide, **k: ("DP-2", {"ok": True}))
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: True)
    monkeypatch.setattr(vc, "ensure_vdisplay_ide_control", lambda **k: {"map_actuation_ok": True})
    monkeypatch.setattr(
        vc,
        "refresh_photo_vql_sidecar",
        lambda **k: {
            "ok": True,
            "source": "DP-2",
            "png": "/tmp/capture.png",
            "vql": "/tmp/capture.png.vql.json",
            "ide_window_warning": {"message": "wrong IDE", "window_titles": ["x - Cursor"]},
        },
    )
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: True)
    monkeypatch.setattr(vc, "_raise_alt_tab_enabled", lambda **k: True)
    monkeypatch.setattr(vc, "_attempt_focus_recovery_capture", _recovery)
    monkeypatch.setenv("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0")
    monkeypatch.setenv("KORU_VDISPLAY_IDE_CONTROL_RETRIES", "3")

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")

    assert out.get("focus_recovery", {}).get("ok") is True
    assert out["ok"] is True
    assert out["capture_ready"] is True


def test_prepare_force_refresh_after_ide_control(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"refresh": 0}

    def _refresh(**k):
        calls["refresh"] += 1
        return {
            "ok": True,
            "source": "DP-2",
            "png": "/tmp/capture.png",
            "vql": "/tmp/capture.png.vql.json",
            "capture_confirmed": True,
        }

    monkeypatch.setattr(vc, "_resolve_vdisplay_source_for_ide", lambda ide, **k: ("DP-2", {"ok": True}))
    monkeypatch.setattr(
        vc._autonomy_session,
        "begin_autonomy_session",
        lambda **k: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_auto_ide_control_enabled", lambda: True)
    monkeypatch.setattr(
        vc,
        "ensure_vdisplay_ide_control",
        lambda **k: {"map_actuation_ok": True, "interior_focused": True},
    )
    monkeypatch.setattr(vc, "photo_vql_sidecar_needs_refresh", lambda **k: False)
    monkeypatch.setattr(vc, "refresh_photo_vql_sidecar", _refresh)
    monkeypatch.setattr(vc, "_photo_vql_ide_window_warning", lambda **k: None)
    monkeypatch.setenv("KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S", "0")

    out = vc.prepare_photo_vql_for_drive(ide="jetbrains")

    assert calls["refresh"] == 1
    assert out["ok"] is True


def test_real_imgl_src_prefers_semco_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMGL_SRC", str(Path.home() / "github/semcod/imgl"))
    src = vc._real_imgl_src()
    assert src is not None
    assert (Path(src) / "imgl" / "pipeline.py").is_file()


def test_ensure_real_imgl_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    imgl_root = vc._real_imgl_src()
    if imgl_root is None:
        pytest.skip("semcod imgl not on disk")
    koru_stub = str(Path(vc.__file__).resolve().parents[2] / "imgl")
    sys.path.insert(0, koru_stub)
    vc._ensure_real_imgl_on_path()

    assert sys.path[0] == imgl_root
    assert koru_stub not in sys.path[:2]


def test_import_imgl_targets_clears_cached_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    imgl_root = vc._real_imgl_src()
    if imgl_root is None:
        pytest.skip("semcod imgl not on disk")
    koru_stub = Path(vc.__file__).resolve().parents[2] / "imgl"
    stub = types.ModuleType("imgl")
    stub.__file__ = str(koru_stub / "__init__.py")
    stub.__path__ = [str(koru_stub)]
    monkeypatch.setitem(sys.modules, "imgl", stub)
    monkeypatch.delitem(sys.modules, "imgl.targets", raising=False)

    resolve_chat_target = vc._import_imgl_targets("resolve_chat_target")

    assert callable(resolve_chat_target)
    import imgl

    assert str(Path(imgl.__file__).resolve()).startswith(str(Path(imgl_root).resolve()))


def test_vdisplay_subprocess_env_puts_imgl_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMGL_SRC", str(Path.home() / "github/semcod/imgl"))
    env = vc._vdisplay_subprocess_env(ide="jetbrains")
    first = (env.get("PYTHONPATH") or "").split(":")[0]
    assert "imgl" in first
    assert env.get("VDISPLAY_CAPTURE_VALIDATE_IDE") == "jetbrains"


def test_send_chat_persists_drive_result(monkeypatch: pytest.MonkeyPatch) -> None:
    persisted: list[tuple] = []

    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda **k: None)
    monkeypatch.setattr(vc, "_prefer_photo_vql_chat", lambda **k: True)
    monkeypatch.setattr(
        vc,
        "perform_photo_vql_focus_and_edit",
        lambda *a, **k: {"ok": True, "edit": {"ok": True, "method": "test"}, "coords": {"x": 1, "y": 2}},
    )
    monkeypatch.setattr(
        vc._autonomy_session,
        "active_session_dir",
        lambda: type("S", (), {"__str__": lambda self: "/tmp/session"})(),
    )
    monkeypatch.setattr(
        vc._autonomy_session,
        "persist_autonomy_phase",
        lambda session, phase, name, payload: persisted.append((phase, name, payload.get("ok"))),
    )

    out = vc.send_chat("hello", ide="jetbrains", submit=False, dry_run=False)

    assert out["ok"] is True
    assert ("act", "drive_result", True) in persisted
