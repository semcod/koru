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
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KORU_VDISPLAY_VERIFY_AFTER_PASTE", "0")


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
    assert vc._vdisplay_source_for_ide("jetbrains") == "DP-2"


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
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {"layers": [{"id": "w"}], "ui_elements": [{"id": "w"}]})
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
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {"layers": [{"id": "w"}], "ui_elements": [{"id": "w"}]})
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
    cands = vc._photo_vql_chat_input_candidates(layers, limit=2)
    assert cands[0]["label"] == "ask"
    assert cands[1]["label"] == "background"


def test_enrich_capture_meta_uses_map_region_when_sidecar_origin_zero() -> None:
    meta = {"source": "DP-2", "width": 2048, "height": 1280, "region": {"x": 0, "y": 0, "width": 2048, "height": 1280}}
    enriched = vc._enrich_capture_meta_for_pointer(meta, "DP-2")
    region = enriched.get("region") or {}
    assert int(region.get("y") or 0) >= 1900 or enriched.get("rotation") == "left"


def test_perform_photo_vql_submit_after_paste(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {"layers": [{"id": "w"}], "ui_elements": [{"id": "w"}]})
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

