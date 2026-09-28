"""Hermetic tests for vdisplay prepare/session env helpers."""

from __future__ import annotations

from pathlib import Path

from koru.integrations.vdisplay import env_session as es
from koru.integrations.vdisplay_client import (
    clear_stale_observe_session_env,
    sync_prepare_capture_flags_to_env,
)


def test_clear_stale_observe_session_env(monkeypatch):
    monkeypatch.setenv("KORU_AUTONOMY_SESSION_DIR", "/tmp/x")
    monkeypatch.setenv("KORU_VDISPLAY_PHOTO_PATH", "/tmp/y.png")
    monkeypatch.setenv("KORU_VDISPLAY_VQL_PATH", "/tmp/y.png.vql.json")
    monkeypatch.setenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "1")
    clear_stale_observe_session_env()
    assert "KORU_AUTONOMY_SESSION_DIR" not in __import__("os").environ
    assert "KORU_VDISPLAY_PHOTO_PATH" not in __import__("os").environ
    assert "KORU_VDISPLAY_CAPTURE_MATCHES_IDE" not in __import__("os").environ


def test_sync_prepare_capture_flags_to_env(tmp_path, monkeypatch):
    png = tmp_path / "cap.png"
    png.write_bytes(b"png")
    vql = Path(str(png) + ".vql.json")
    vql.write_text("{}")
    session = tmp_path / "session"
    session.mkdir()
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    monkeypatch.delenv("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", raising=False)
    sync_prepare_capture_flags_to_env(
        {
            "source": "DP-2",
            "session_dir": str(session),
            "png": str(png),
            "capture_confirmed": True,
            "ok": True,
        }
    )
    import os

    assert os.environ["KORU_VDISPLAY_SOURCE"] == "DP-2"
    assert os.environ["KORU_AUTONOMY_SESSION_DIR"] == str(session)
    assert os.environ["KORU_VDISPLAY_PHOTO_PATH"] == str(png.resolve())
    assert os.environ["KORU_VDISPLAY_VQL_PATH"] == str(vql.resolve())
    assert os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] == "1"


def test_session_type_and_dry_run(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert es.session_type() == "wayland"
    monkeypatch.delenv("KORU_VDISPLAY_DRY_RUN", raising=False)
    assert es.dry_run_enabled() is False
    monkeypatch.setenv("KORU_VDISPLAY_DRY_RUN", "1")
    assert es.dry_run_enabled() is True


def test_vdisplay_client_reexports_env_helpers():
    from koru.integrations import vdisplay_client as vc

    assert vc.clear_stale_observe_session_env is es.clear_stale_observe_session_env
    assert vc.sync_prepare_capture_flags_to_env is es.sync_prepare_capture_flags_to_env
    assert vc._session_type is es.session_type
    assert vc._dry_run is es.dry_run_enabled


def test_vdisplay_subprocess_env_pythonpath_does_not_shadow_queue(monkeypatch):
    import subprocess
    import sys

    from koru.integrations.vdisplay.imgl_loader import _vdisplay_subprocess_env

    monkeypatch.delenv("KORU_SRC", raising=False)
    env = _vdisplay_subprocess_env()
    pythonpath = env.get("PYTHONPATH", "")
    parts = pythonpath.split(":")
    for part in parts:
        assert not part.endswith("/src/koru"), f"Poisoned PYTHONPATH part: {part}"
        assert not part.endswith("\\src\\koru"), f"Poisoned PYTHONPATH part: {part}"

    proc = subprocess.run(
        [sys.executable, "-c", "import concurrent.futures.thread; import queue; assert hasattr(queue, 'Queue')"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Failed importing stdlib queue: {proc.stderr}"

