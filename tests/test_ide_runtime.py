"""Tests for :mod:`koru.ide_runtime`."""

from __future__ import annotations

from koru import ide_runtime
from koru.autopilot import host_setup as host_setup_mod
from koruide import ide as koruide_ide_mod


def test_build_host_setup_report_delegates_to_legacy_backend(monkeypatch) -> None:
    expected = {"session": "x11", "selected_backend": "xdotool"}
    monkeypatch.setattr(host_setup_mod, "build_setup_host_report", lambda: dict(expected))

    out = ide_runtime.build_host_setup_report()

    assert out == expected


def test_detect_running_ides_normalizes_rows(monkeypatch) -> None:
    class FakeRunningIDE:
        def to_dict(self):
            return {"id": "windsurf", "label": "Windsurf", "pid": 123, "exe": "/opt/windsurf"}

    monkeypatch.setattr(
        koruide_ide_mod,
        "detect_running_ides",
        lambda: [
            FakeRunningIDE(),
            {"id": "cursor", "label": "Cursor"},
            "vscode",
        ],
    )

    rows = ide_runtime.detect_running_ides()

    assert rows[0]["id"] == "windsurf"
    assert rows[1]["id"] == "cursor"
    assert rows[2] == {"id": "vscode"}
