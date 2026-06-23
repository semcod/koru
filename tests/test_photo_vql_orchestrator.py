from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru.integrations import photo_vql_guard as guard
from koru.integrations import photo_vql_drive as drive_mod
from koru.integrations import vdisplay_client as vc


@pytest.fixture(autouse=True)
def _clear_guard_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH",
        "KORU_VDISPLAY_ALLOW_IDE_MISMATCH",
    ):
        monkeypatch.delenv(key, raising=False)


def test_capture_guard_blocks_mismatch_by_default() -> None:
    mismatch = {"message": "capture shows Cursor", "window_titles": ["Cursor"]}
    g = guard.CaptureGuard.from_observe(
        ide="jetbrains",
        confirmed=False,
        ide_window_warning=mismatch,
    )
    out = g.apply_to_prepare_out({"elements": 31}, ide_control={})
    assert out["ok"] is False
    assert out["capture_confirmed"] is False
    assert out["competing_ide"] == "Cursor"
    assert "error" in out


def test_capture_guard_allows_map_only_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "1")
    mismatch = {"message": "capture shows Cursor", "window_titles": ["Cursor"]}
    ide_control = {"map_actuation_ok": True, "interior_focused": True}
    g = guard.CaptureGuard.from_observe(
        ide="jetbrains",
        confirmed=False,
        ide_window_warning=mismatch,
        ide_control=ide_control,
    )
    out = g.apply_to_prepare_out({"elements": 31}, ide_control=ide_control)
    assert out["ok"] is True
    assert out["map_only_fallback"] is True
    assert ide_control["visual_guard_failed"] is True


def test_session_prepare_is_fresh_reads_recent_prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session = tmp_path / "2026-06-09__koru-jetbrains"
    observe = session / "observe"
    observe.mkdir(parents=True)
    prepare = observe / "prepare.json"
    prepare.write_text(
        json.dumps({"ok": True, "capture_confirmed": True, "elements": 42}),
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTONOMY_SESSION_DIR", str(session))

    reused = drive_mod.session_prepare_is_fresh(max_age_s=120.0)
    assert reused is not None
    assert reused["prepare_reused"] is True
    assert reused["elements"] == 42


def test_session_prepare_is_fresh_rejects_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session = tmp_path / "2026-06-09__koru-jetbrains"
    observe = session / "observe"
    observe.mkdir(parents=True)
    prepare = observe / "prepare.json"
    prepare.write_text(json.dumps({"ok": True}), encoding="utf-8")
    old = time.time() - 300
    import os

    os.utime(prepare, (old, old))
    monkeypatch.setenv("KORU_AUTONOMY_SESSION_DIR", str(session))

    assert drive_mod.session_prepare_is_fresh(max_age_s=120.0) is None


def test_session_prepare_is_fresh_rejects_unconfirmed_map_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "2026-06-09__koru-jetbrains"
    observe = session / "observe"
    observe.mkdir(parents=True)
    prepare = observe / "prepare.json"
    prepare.write_text(
        json.dumps({"ok": False, "map_only_fallback": True, "capture_confirmed": False}),
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTONOMY_SESSION_DIR", str(session))

    assert drive_mod.session_prepare_is_fresh(max_age_s=120.0) is None


def test_session_prepare_is_fresh_finds_latest_session_without_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = tmp_path / "2026-06-12"
    older = day / "2026-06-12T10-00-00Z__koru-jetbrains" / "observe"
    newer = day / "2026-06-12T11-00-00Z__koru-jetbrains" / "observe"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "prepare.json").write_text(
        json.dumps({"ok": True, "source": "DP-1", "capture_confirmed": True}),
        encoding="utf-8",
    )
    (newer / "prepare.json").write_text(
        json.dumps(
            {
                "ok": True,
                "source": "HDMI-1",
                "capture_confirmed": True,
                "surface_only_fallback": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("KORU_AUTONOMY_SESSION_DIR", raising=False)
    monkeypatch.setenv("VDISPLAY_METADATA_DIR", str(tmp_path))

    reused = drive_mod.session_prepare_is_fresh(ide="jetbrains", max_age_s=120.0)
    assert reused is None


def test_photo_vql_drive_act_surface_only_blocks_send_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    observe = {
        "ok": True,
        "surface_only_fallback": True,
        "capture_confirmed": True,
        "source": "HDMI-1",
    }
    surface_act = MagicMock(return_value={"ok": True, "backend": "vdisplay+photo-vql"})
    send_chat = MagicMock()
    monkeypatch.setattr(drive_mod.PhotoVqlDrive, "_act_surface_only", surface_act)
    monkeypatch.setattr(drive_mod.PhotoVqlDrive, "_send_chat", send_chat)

    drive = drive_mod.PhotoVqlDrive(ide="jetbrains")
    reply = drive.act("probe test", submit=True, observe=observe)
    assert reply["ok"] is False
    assert reply["backend"] == "semantic_required"
    assert reply["surface_only_fallback"] is True
    surface_act.assert_not_called()
    send_chat.assert_not_called()


def test_photo_vql_drive_reuses_fresh_prepare(monkeypatch: pytest.MonkeyPatch) -> None:
    prepare_fn = MagicMock(return_value={"ok": True, "capture_confirmed": True})
    monkeypatch.setattr(vc, "prepare_photo_vql_for_drive", prepare_fn)
    monkeypatch.setattr(
        drive_mod,
        "session_prepare_is_fresh",
        lambda **kwargs: {"ok": True, "capture_confirmed": True, "prepare_reused": True},
    )

    drive = drive_mod.PhotoVqlDrive(ide="jetbrains")
    out = drive.prepare(reuse_fresh=True)
    assert out["prepare_reused"] is True
    prepare_fn.assert_not_called()


def test_run_photo_vql_drive_aborts_on_prepare_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        drive_mod.PhotoVqlDrive,
        "prepare",
        lambda self, **kwargs: {"ok": False, "error": "monitor not found"},
    )
    act = MagicMock()
    monkeypatch.setattr(drive_mod.PhotoVqlDrive, "act", act)

    reply = drive_mod.run_photo_vql_drive("hello", ide="jetbrains")
    assert reply["ok"] is False
    assert reply["phase"] == "prepare"
    act.assert_not_called()


def test_run_photo_vql_drive_blocks_surface_only_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    observe = {
        "ok": True,
        "surface_only_fallback": True,
        "capture_confirmed": True,
    }
    monkeypatch.setattr(
        drive_mod.PhotoVqlDrive,
        "prepare",
        lambda self, **kwargs: observe,
    )

    reply = drive_mod.run_photo_vql_drive("probe test", ide="jetbrains")
    assert reply["ok"] is False
    assert reply["backend"] == "semantic_required"


def test_build_user_guidance_monitor_not_connected() -> None:
    from koru.integrations.photo_vql_user_guidance import build_user_guidance

    steps = build_user_guidance(
        ide="jetbrains",
        observe={
            "error": "requested monitor 'DP-2' not connected (available: ['DP-1', 'HDMI-1'])",
            "source": "DP-2",
            "desktop_probe": {"monitor_names": ["HDMI-1", "DP-1"], "resolved_source": "DP-2"},
        },
        reply={"ok": False},
        vdisplay_root="/home/tom/github/wronai/vdisplay",
    )
    joined = " ".join(steps)
    assert "DP-2" in joined and "nie jest podpięty" in joined
    assert "--source DP-1" in joined
    assert "--source DP-2" not in joined.split("Sprawdź")[-1]  # retry uses DP-1

    from koru.integrations.photo_vql_user_guidance import build_user_guidance

    steps = build_user_guidance(
        ide="jetbrains",
        observe={
            "error": "capture does not match requested IDE",
            "competing_ide": "Cursor",
            "source": "DP-2",
            "desktop_probe": {"monitor_names": ["DP-1", "DP-2"], "resolved_source": "DP-2"},
        },
        reply={"ok": False},
        vdisplay_root="/tmp/vdisplay",
    )
    joined = " ".join(steps).lower()
    assert "pycharm" in joined
    assert "cursor" in joined
    assert "wronai/vdisplay" not in joined  # path in retry via cd


def test_preflight_repo_paths_detects_missing_koru(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from koru.integrations.photo_vql_user_guidance import preflight_repo_paths

    monkeypatch.setenv("KORU_SRC", str(tmp_path / "missing"))
    monkeypatch.setenv("IMGL_SRC", str(Path(vc._real_imgl_src() or tmp_path)))
    issues = preflight_repo_paths()
    assert any("koru" in i.lower() for i in issues)


def test_emit_user_guidance_includes_success_audit(tmp_path: Path) -> None:
    from koru.integrations.photo_vql_user_guidance import format_user_guidance, build_user_guidance

    steps = build_user_guidance(
        ide="jetbrains",
        reply={"ok": True},
        vdisplay_root=tmp_path,
    )
    text = format_user_guidance(steps)
    assert "CO TERAZ ZROBIĆ" in text
    assert "audit" in text.lower()


def test_import_imgl_targets_with_koru_stub_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    koru_root = Path(vc.__file__).resolve().parents[2]
    stub = str(koru_root / "imgl")
    real = vc._real_imgl_src()
    if not real:
        pytest.skip("semcod imgl not available")
    monkeypatch.setenv("IMGL_SRC", real)
    if stub not in sys.path:
        sys.path.insert(0, stub)
    for name in list(sys.modules):
        if name == "imgl" or name.startswith("imgl."):
            sys.modules.pop(name, None)

    fn = vc._import_imgl_targets("resolve_chat_target")
    assert fn is not None
    assert fn.__name__ == "resolve_chat_target"


def test_copy_observe_artifacts_pins_session_paths(tmp_path: Path) -> None:
    from koru.integrations.autonomy_session import copy_observe_artifacts_to_session

    session = tmp_path / "2026-06-09__koru-jetbrains"
    (session / "observe").mkdir(parents=True)
    png = tmp_path / "fresh.png"
    vql = tmp_path / "fresh.png.vql.json"
    png.write_bytes(b"png")
    vql.write_text("{}", encoding="utf-8")

    copied = copy_observe_artifacts_to_session(session, png=png, vql=vql)
    assert (session / "observe" / "capture.png").read_bytes() == b"png"
    assert copied["png"] == str((session / "observe" / "capture.png").resolve())


def test_photo_vql_drive_act_uses_llm_photo_vql_before_map_on_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    perform = MagicMock(
        return_value={
            "ok": True,
            "backend": "vdisplay+photo-vql",
            "edit": {"ok": True},
            "vql_target": {"id": "llm:chat-input"},
            "llm_used": True,
        }
    )
    normalize = MagicMock(
        return_value={"ok": True, "backend": "vdisplay+photo-vql", "message": "llm paste"}
    )
    ide_prompt = MagicMock(return_value={"ok": True, "backend": "vdisplay+ide-prompt"})
    monkeypatch.setattr("koru.integrations.photo_vql_config.llm_vision_enabled", lambda: True)
    monkeypatch.setattr(vc, "perform_photo_vql_focus_and_edit", perform)
    monkeypatch.setattr(vc, "_normalize_photo_vql_drive_result", normalize)
    monkeypatch.setattr(vc, "send_chat_via_ide_prompt", ide_prompt)
    monkeypatch.setattr(vc, "_vdisplay_source", lambda: "DP-1")

    drive = drive_mod.PhotoVqlDrive(ide="jetbrains")
    out = drive.act(
        "probe test",
        submit=True,
        observe={"map_only_fallback": True, "ok": True, "png": "/tmp/capture.png"},
    )
    assert out["ok"] is True
    perform.assert_called_once()
    ide_prompt.assert_not_called()


def test_photo_vql_drive_act_uses_ide_prompt_when_llm_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_prompt = MagicMock(return_value={"ok": True, "backend": "vdisplay+ide-prompt", "message": "map paste"})
    perform = MagicMock()
    monkeypatch.setattr("koru.integrations.photo_vql_config.llm_vision_enabled", lambda: False)
    monkeypatch.setattr(vc, "perform_photo_vql_focus_and_edit", perform)
    monkeypatch.setattr(vc, "send_chat_via_ide_prompt", ide_prompt)

    drive = drive_mod.PhotoVqlDrive(ide="jetbrains")
    out = drive.act(
        "probe test",
        submit=True,
        observe={"map_only_fallback": True, "ok": True, "ide_control": {"map_actuation_ok": True}},
    )
    assert out["ok"] is True
    assert out["backend"] == "vdisplay+ide-prompt"
    perform.assert_not_called()
    ide_prompt.assert_called_once()


def test_get_vql_chat_target_uses_jetbrains_surface_bounds_on_hdmi1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_elements", lambda: ([], None))
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(vc, "_vql_candidates_polluted", lambda c: False)
    monkeypatch.setattr(vc, "llm_vision_enabled", lambda: False)
    monkeypatch.setattr(
        vc,
        "_resolve_vdisplay_source_for_ide",
        lambda ide, probe=None: (
            "HDMI-1",
            {
                "ide_surface_best": {
                    "display_name": "PyCharm",
                    "pid": 35616,
                    "monitor_name": "HDMI-1",
                    "bounds": {"x": 3216, "y": 2550, "width": 880, "height": 1548},
                }
            },
        ),
    )
    monkeypatch.setattr(
        vc,
        "_live_surface_capture_meta",
        lambda source: {
            "source": source,
            "monitor_name": source,
            "width": 2048,
            "height": 1280,
            "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
        },
    )
    monkeypatch.setattr(vc, "_enrich_capture_meta_for_pointer", lambda meta, source: meta)
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_log_vql_cursor_positioning_at_command", lambda *a, **k: None)
    monkeypatch.setattr(vc, "validate_vql_chat_target", lambda *a, **k: {"ok": True})

    out = vc.get_vql_chat_target_from_photo(ide="jetbrains")
    assert out.get("selection_method") == "jetbrains_surface_bounds"
    assert out["id"] == "surface:jetbrains-chat"
    assert out["click_center"]["y"] >= 600


def test_get_vql_chat_target_rejects_suspicious_jetbrains_surface_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_elements", lambda: ([], None))
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(vc, "_vql_candidates_polluted", lambda c: False)
    monkeypatch.setattr(vc, "llm_vision_enabled", lambda: False)
    monkeypatch.setattr(
        vc,
        "_resolve_vdisplay_source_for_ide",
        lambda ide, probe=None: (
            "HDMI-1",
            {
                "ide_surface_best": {
                    "display_name": "PyCharm",
                    "pid": 35616,
                    "monitor_name": "HDMI-1",
                    "bounds": {"x": 3216, "y": 2550, "width": 880, "height": 1548},
                }
            },
        ),
    )
    monkeypatch.setattr(
        vc,
        "_live_surface_capture_meta",
        lambda source: {
            "source": source,
            "monitor_name": source,
            "width": 2048,
            "height": 1280,
            "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
        },
    )
    monkeypatch.setattr(
        vc,
        "_map_chat_target_capture_local",
        lambda **k: {"click_center": {"x": 1900, "y": 1160}, "id": "map:chat", "role": "input"},
    )
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {})
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_log_vql_cursor_positioning_at_command", lambda *a, **k: None)

    def fake_validate(target, *, selection_method=None, **kwargs):
        if selection_method == "jetbrains_surface_bounds":
            return {
                "ok": False,
                "coord_warnings": ["chat_local_y=691_below_850_likely_editor_not_bottom_right_composer"],
                "validation_errors": [],
            }
        return {"ok": True, "coord_warnings": [], "validation_errors": []}

    monkeypatch.setattr(vc, "validate_vql_chat_target", fake_validate)

    out = vc.get_vql_chat_target_from_photo(ide="jetbrains")
    assert out.get("selection_method") == "map_calibrated_on_empty_vql"
    assert out["id"] == "map:chat"


def test_get_vql_chat_target_accepts_jetbrains_surface_when_surface_fallback_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "1")
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION", "1")
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    monkeypatch.setattr(vc, "_photo_vql_elements", lambda: ([], None))
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "capture does not match requested IDE"},
    )
    monkeypatch.setattr(vc, "_vql_candidates_polluted", lambda c: False)
    monkeypatch.setattr(vc, "llm_vision_enabled", lambda: False)
    monkeypatch.setattr(
        vc,
        "_resolve_vdisplay_source_for_ide",
        lambda ide, probe=None: (
            "HDMI-1",
            {
                "ide_surface_best": {
                    "display_name": "PyCharm",
                    "pid": 35616,
                    "monitor_name": "HDMI-1",
                    "stack": "jetbrains_xwayland",
                    "bounds": {"x": 3216, "y": 3100, "width": 880, "height": 1548},
                }
            },
        ),
    )
    monkeypatch.setattr(
        vc,
        "_live_surface_capture_meta",
        lambda source: {
            "source": source,
            "monitor_name": source,
            "width": 2048,
            "height": 1280,
            "region": {"x": 0, "y": 2560, "width": 4096, "height": 2560},
        },
    )
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {})
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_log_vql_cursor_positioning_at_command", lambda *a, **k: None)

    out = vc.get_vql_chat_target_from_photo(ide="jetbrains")
    assert out.get("selection_method") == "jetbrains_surface_bounds"
    assert out["vql_validation"]["surface_bounds_trusted"] is True
    assert out["vql_validation"]["ok"] is True


def test_get_vql_chat_target_prefers_llm_detect_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_LLM_VISION_DECISION", "1")
    monkeypatch.setattr(vc, "_photo_vql_elements", lambda: ([], None))
    monkeypatch.setattr(
        vc,
        "_photo_vql_ide_capture_mismatch",
        lambda ide: {"message": "wrong window"},
    )
    monkeypatch.setattr(vc, "_vql_candidates_polluted", lambda c: False)
    monkeypatch.setattr(
        vc,
        "_map_chat_target_capture_local",
        lambda **k: {"click_center": {"x": 100, "y": 200}, "id": "map:prompt"},
    )
    monkeypatch.setattr(vc, "_resolve_photo_png_path_from_vql", lambda source: "/tmp/capture.png")
    monkeypatch.setattr(vc, "load_vql_metadata", lambda *a, **k: {"ui_elements": [], "capture_validation": {"capture_confirmed": False}})
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)
    monkeypatch.setattr(vc, "_log_vql_cursor_positioning_at_command", lambda *a, **k: None)
    monkeypatch.setattr(
        "vdisplay.integrations.chat_target.resolve_chat_target_from_screenshot",
        lambda *a, **k: {
            "click_center": {"x": 1800, "y": 1200},
            "id": "llm:chat-input",
            "role": "input",
            "llm_used": True,
        },
    )
    monkeypatch.setattr(vc, "validate_vql_chat_target", lambda *a, **k: {"ok": True})

    out = vc.get_vql_chat_target_from_photo(ide="jetbrains")
    assert out["id"] == "llm:chat-input"
    assert out.get("selection_method") == "llm_vision_detect"


def test_photo_vql_drive_act_uses_ide_prompt_on_map_only_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_prompt = MagicMock(return_value={"ok": True, "backend": "vdisplay+ide-prompt", "message": "map paste"})
    send_chat = MagicMock(return_value={"ok": True, "backend": "vdisplay+photo-vql"})
    monkeypatch.setattr("koru.integrations.photo_vql_config.llm_vision_enabled", lambda: False)
    monkeypatch.setattr(vc, "send_chat_via_ide_prompt", ide_prompt)
    monkeypatch.setattr(vc, "send_chat", send_chat)

    drive = drive_mod.PhotoVqlDrive(ide="jetbrains")
    out = drive.act(
        "probe test",
        submit=True,
        observe={"map_only_fallback": True, "ok": True, "ide_control": {"map_actuation_ok": True}},
    )
    assert out["ok"] is True
    assert out["backend"] == "vdisplay+ide-prompt"
    assert out.get("map_only_fallback") is True
    ide_prompt.assert_called_once()
    send_chat.assert_not_called()


def test_normalize_drive_result_blocks_map_edit_when_capture_unconfirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "1")
    photo = {
        "ok": True,
        "backend": "vdisplay+photo-vql",
        "edit": {"ok": True, "method": "ydotool-paste"},
        "verified": False,
        "capture_confirmed": False,
        "vql_target": {"id": "map:ai-chat-input"},
        "vql_command_plan": {"inference_ok": False, "warnings": ["capture_ide_mismatch"]},
    }
    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)
    assert out["ok"] is False
    assert out["capture_confirmed"] is False


def test_normalize_drive_result_allows_map_edit_when_ide_mismatch_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_IDE_MISMATCH", "1")
    photo = {
        "ok": True,
        "backend": "vdisplay+photo-vql",
        "edit": {"ok": True, "method": "ydotool-paste"},
        "verified": False,
        "capture_confirmed": False,
        "vql_target": {"id": "map:ai-chat-input"},
        "vql_command_plan": {"inference_ok": False, "warnings": ["capture_ide_mismatch"]},
    }
    out = vc._normalize_photo_vql_drive_result(photo, ide="jetbrains", submit=False)
    assert out["ok"] is True
    assert out["capture_confirmed"] is False


def test_perform_photo_vql_skips_stale_abort_when_map_mismatch_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH", "1")
    monkeypatch.setattr(
        vc,
        "load_vql_metadata",
        lambda *a, **k: {"error": "no fresh vql found", "stale_skipped": True},
    )
    monkeypatch.setattr(vc, "_photo_vql_ide_capture_mismatch", lambda ide: None)
    monkeypatch.setattr(vc, "_map_capture_mismatch_for_ide", lambda **k: None)
    monkeypatch.setattr(vc, "_map_capture_mismatch_for_target", lambda **k: None)
    monkeypatch.setattr(
        vc,
        "get_vql_chat_target_from_photo",
        lambda **kwargs: {"id": "map:ai-chat-input", "click_center": {"x": 100, "y": 200}},
    )
    monkeypatch.setattr(
        vc,
        "move_mouse_to_vql_target_and_focus_keyboard",
        lambda target, **kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        vc,
        "_type_text_at_vql_coords",
        lambda value, x, y, **kwargs: {"ok": True, "method": "paste"},
    )
    monkeypatch.setattr(vc, "_dry_run", lambda: False)
    monkeypatch.setattr(vc._autonomy_session, "active_session_dir", lambda: None)
    monkeypatch.setattr(vc._autonomy_session, "persist_autonomy_phase", lambda *a, **k: None)

    out = vc.perform_photo_vql_focus_and_edit("hello", ide="jetbrains", source="DP-1")
    assert out.get("error") != "no fresh vql found"
    assert (out.get("edit") or {}).get("ok") is True
    assert out.get("vql_command_plan", {}).get("inference_ok") is False


def test_refresh_photo_vql_sidecar_copies_observe_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.integrations import autonomy_session as sess

    session = tmp_path / "2026-06-09__koru-jetbrains"
    (session / "observe").mkdir(parents=True)
    png = tmp_path / "DP-1.png"
    vql = tmp_path / "DP-1.png.vql.json"
    png.write_bytes(b"png")
    vql.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("KORU_AUTONOMY_SESSION_DIR", str(session))
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    monkeypatch.setattr(vc, "_resolve_photo_png_path", lambda src: png)
    monkeypatch.setattr(vc, "_vdisplay_source_for_ide", lambda ide: "DP-1")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: MagicMock(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        vc,
        "load_vql_metadata",
        lambda *a, **k: {"ui_elements": [{"id": "window_0"}]},
    )
    monkeypatch.setattr(vc, "_main_vql_layer_count", lambda path: 1)
    monkeypatch.setattr(vc, "_photo_vql_ide_window_warning", lambda **kwargs: None)
    monkeypatch.setattr(
        vc,
        "_capture_provenance",
        lambda **kwargs: {"capture_confirmed": True},
    )
    monkeypatch.setattr(sess, "vql_sidecar_is_stale", lambda *a, **k: (False, {}))

    out = vc.refresh_photo_vql_sidecar(ide="jetbrains")
    assert out.get("observe_session_paths")
    assert (session / "observe" / "capture.png").is_file()
    assert out["png"] == str((session / "observe" / "capture.png").resolve())
