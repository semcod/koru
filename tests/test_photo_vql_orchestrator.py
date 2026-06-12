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
