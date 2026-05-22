"""Tests for ScreenCast session cache (.koru/keys/screencast.session)."""

from __future__ import annotations

import json
from pathlib import Path

from koruvision.providers.screencast_session import (
    clear_session_file,
    load_session_path,
    resolve_screencast_session_file,
    save_session_path,
    session_file_for_project,
)


def test_save_and_load_session_path(tmp_path: Path) -> None:
    path = session_file_for_project(tmp_path)
    save_session_path("/org/freedesktop/portal/desktop/session/abc", path)
    assert load_session_path(path) == "/org/freedesktop/portal/desktop/session/abc"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["session_path"].startswith("/org/freedesktop/portal/")


def test_resolve_from_mesh_frame_store(monkeypatch, tmp_path: Path) -> None:
    store = tmp_path / ".koru" / "run" / "mesh-frames.jsonl"
    store.parent.mkdir(parents=True)
    store.touch()
    monkeypatch.setenv("KORU_MESH_FRAME_STORE", str(store))
    resolved = resolve_screencast_session_file()
    assert resolved == tmp_path / ".koru" / "keys" / "screencast.session"


def test_clear_session_file(tmp_path: Path) -> None:
    path = session_file_for_project(tmp_path)
    save_session_path("/org/freedesktop/portal/desktop/session/x", path)
    assert clear_session_file(path) is True
    assert not path.is_file()
    assert clear_session_file(path) is False
