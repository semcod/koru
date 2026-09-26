"""Unit tests for koru.integrations.vdisplay_readiness."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from koru.integrations import vdisplay_readiness as vr


def test_canonical_ide() -> None:
    assert vr._canonical_ide("Cursor") == "cursor"
    assert vr._canonical_ide("Windsurf") == "windsurf"
    assert vr._canonical_ide("custom-ide") == "custom-ide"


def test_real_vdisplay_src(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake_src = tmp_path / "vdisplay_root"
    ide_prompt = fake_src / "vdisplay" / "ide_prompt.py"
    ide_prompt.parent.mkdir(parents=True)
    ide_prompt.write_text("# fake ide_prompt")

    monkeypatch.setenv("VDISPLAY_SRC", str(fake_src))
    assert vr._real_vdisplay_src() == str(fake_src)

    monkeypatch.delenv("VDISPLAY_SRC", raising=False)
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert vr._real_vdisplay_src() is None


def test_abort_on_desktop_probe_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "1")
    assert vr._abort_on_desktop_probe_fail() is True

    monkeypatch.setenv("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "0")
    assert vr._abort_on_desktop_probe_fail() is False

    monkeypatch.setenv("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "false")
    assert vr._abort_on_desktop_probe_fail() is False


def test_vdisplay_source_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_VDISPLAY_SOURCE", raising=False)
    assert vr._vdisplay_source_for_ide("cursor") == "DP-1"
    assert vr._vdisplay_source_for_ide("vscode") == "DP-1"

    monkeypatch.setenv("KORU_VDISPLAY_SOURCE", "HDMI-1")
    assert vr._vdisplay_source_for_ide("cursor") == "HDMI-1"
    assert vr._vdisplay_source() == "HDMI-1"


def test_probe_agent() -> None:
    with patch("urllib.request.urlopen") as mock_open:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true, "data": {"service": "vdisplay-agent"}}'
        mock_resp.__enter__.return_value = mock_resp
        mock_open.return_value = mock_resp
        assert vr._probe_agent("http://127.0.0.1:8765") is True

    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        assert vr._probe_agent("http://127.0.0.1:8765") is False


def test_vdisplay_missing_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vr, "_agent_url", lambda: "http://127.0.0.1:8765")
    assert vr.vdisplay_missing_message() == ""

    monkeypatch.setattr(vr, "_agent_url", lambda: None)
    monkeypatch.setattr(vr, "_VDISPLAY_IMPORT_ERROR", None)
    msg = vr.vdisplay_missing_message()
    assert "Install vdisplay control plane" in msg

    monkeypatch.setattr(vr, "_VDISPLAY_IMPORT_ERROR", "ModuleNotFoundError: no module")
    msg_err = vr.vdisplay_missing_message()
    assert "ModuleNotFoundError" in msg_err


def test_annotate_prepare_drive_readiness() -> None:
    # All good
    out: dict[str, object] = {
        "ok": True,
        "capture_confirmed": True,
        "elements": 5,
    }
    vr._annotate_prepare_drive_readiness(out)
    assert out["drive_ready"] is True
    assert "drive_blocked_reasons" not in out

    # Prepare not ok
    out_fail: dict[str, object] = {
        "ok": False,
        "capture_confirmed": True,
        "elements": 5,
    }
    vr._annotate_prepare_drive_readiness(out_fail)
    assert out_fail["drive_ready"] is False
    assert "prepare_not_ok" in out_fail["drive_blocked_reasons"]

    # Capture not confirmed
    out_unconfirmed: dict[str, object] = {
        "ok": True,
        "capture_confirmed": False,
        "elements": 5,
    }
    vr._annotate_prepare_drive_readiness(out_unconfirmed)
    assert out_unconfirmed["drive_ready"] is False
    assert "capture_not_confirmed" in out_unconfirmed["drive_blocked_reasons"]

    # Empty VQL layers without surface fallback
    out_empty: dict[str, object] = {
        "ok": True,
        "capture_confirmed": True,
        "elements": 0,
        "main_vql_layers": 0,
    }
    vr._annotate_prepare_drive_readiness(out_empty)
    assert out_empty["drive_ready"] is False
    assert "empty_vql_layers" in out_empty["drive_blocked_reasons"]


def test_vdisplay_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vr, "_VDISPLAY_DIRECT", True)
    assert vr.vdisplay_available() is True

    monkeypatch.setattr(vr, "_VDISPLAY_DIRECT", False)
    monkeypatch.setattr(vr, "_load_vdisplay_control", lambda: False)
    monkeypatch.setattr(vr, "_ensure_vdisplay_runtime", lambda: False)
    monkeypatch.setattr(vr, "_agent_url", lambda: None)
    assert vr.vdisplay_available() is False

    monkeypatch.setattr(vr, "_agent_url", lambda: "http://127.0.0.1:8765")
    monkeypatch.setattr(vr, "_probe_agent", lambda url: True)
    assert vr.vdisplay_available() is True


def test_vdisplay_client_reexports() -> None:
    from koru.integrations import vdisplay_client as vc

    assert callable(vc.vdisplay_available)
    assert callable(vc.vdisplay_missing_message)
    assert callable(vc.simplified_control_likely_insufficient)
    assert callable(vc.vdisplay_fallback_enabled)
    assert callable(vc._annotate_prepare_drive_readiness)
    assert callable(vc._vdisplay_source_for_ide)
    assert callable(vc._vdisplay_source)
    assert isinstance(vc._IDE_DEFAULT_SOURCE, dict)
