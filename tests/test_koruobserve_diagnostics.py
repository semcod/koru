"""Tests for :mod:`koruobserve.diagnostics` capture-blocked surface."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from koruobserve.diagnostics import (
    _last_failure_line,
    _monitors_from_xrandr,
    capture_diagnostics,
    detect_monitors,
)

_XRANDR_OUT = """\
Monitors: 3
 0: +*DP-3 2160/700x3840/390+2560+0  DP-3
 1: +DP-2 2560/610x1600/350+0+562  DP-2
 2: +HDMI-1 2560/300x1600/260+0+2162  HDMI-1
"""


def _proc(stdout: str, code: int = 0):
    import subprocess

    return subprocess.CompletedProcess(args=["xrandr"], returncode=code, stdout=stdout, stderr="")


def test_xrandr_parses_three_monitors() -> None:
    with mock.patch("subprocess.run", return_value=_proc(_XRANDR_OUT)):
        monitors = _monitors_from_xrandr()
    assert monitors is not None
    assert len(monitors) == 3
    assert monitors[0]["output"] == "DP-3"
    assert (monitors[0]["width"], monitors[0]["height"]) == (2160, 3840)
    assert {m["output"] for m in monitors} == {"DP-3", "DP-2", "HDMI-1"}
    assert all(m["source"] == "xrandr" for m in monitors)


def test_last_failure_line_picks_most_recent() -> None:
    text = (
        "koru vision agent: capture failed: backend portal denied\n"
        "koru vision: noise\n"
        "koru vision agent: capture failed: all monitors black\n"
    )
    assert _last_failure_line(text) == "all monitors black"


def test_capture_diagnostics_blocked_on_wayland(tmp_path: Path) -> None:
    log_dir = tmp_path / ".koru" / "run"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "vision.log"
    log_path.write_text(
        "koru vision agent: capture failed: no screenshot backend succeeded; ...\n",
        encoding="utf-8",
    )
    env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
    xrandr_monitors = [
        {"id": 0, "output": "DP-3", "width": 3840, "height": 2160, "source": "xrandr"},
        {"id": 1, "output": "DP-2", "width": 2560, "height": 1600, "source": "xrandr"},
    ]
    with (
        mock.patch.dict("os.environ", env, clear=False),
        mock.patch("koruobserve.diagnostics._monitors_from_mss", return_value=None),
        mock.patch("koruobserve.diagnostics._monitors_from_xrandr", return_value=xrandr_monitors),
    ):
        diag = capture_diagnostics(tmp_path)
    assert diag["session_type"] == "wayland"
    assert diag["status"] == "blocked"
    assert "no screenshot backend" in (diag["last_error"] or "")
    assert "wayland" in diag["hint"].lower()
    assert len(diag["monitors"]) == 2
    assert diag["monitors"][0]["output"] == "DP-3"
    assert "providers" in diag
    assert isinstance(diag.get("ranked_providers"), list)


def test_capture_diagnostics_no_log(tmp_path: Path) -> None:
    with mock.patch("koruobserve.diagnostics._monitors_from_mss", return_value=None), \
         mock.patch("koruobserve.diagnostics._monitors_from_xrandr", return_value=None):
        diag = capture_diagnostics(tmp_path)
    assert diag["status"] == "no-log"
    assert diag["last_error"] is None
    assert diag["monitors"] == []


def test_detect_monitors_prefers_mss_over_xrandr() -> None:
    mss_rows = [{"id": 0, "output": "via-mss", "width": 100, "height": 100, "source": "mss"}]
    with mock.patch("koruobserve.diagnostics._monitors_from_mss", return_value=mss_rows), \
         mock.patch("koruobserve.diagnostics._monitors_from_xrandr") as xrandr:
        assert detect_monitors() == mss_rows
        xrandr.assert_not_called()


def test_mesh_diagnostics_endpoint_payload(tmp_path: Path) -> None:
    """``/api/mesh/diagnostics`` JSON is well-formed and project-scoped."""
    from korumesh.dashboard import mesh_diagnostics_payload

    log_dir = tmp_path / ".koru" / "run"
    log_dir.mkdir(parents=True)
    (log_dir / "vision.log").write_text(
        "koru vision agent: capture failed: portal denied\n",
        encoding="utf-8",
    )
    with mock.patch("koruobserve.diagnostics._monitors_from_mss", return_value=None), \
         mock.patch("koruobserve.diagnostics._monitors_from_xrandr", return_value=[]):
        payload = mesh_diagnostics_payload(tmp_path)
    assert payload["status"] == "blocked"
    assert payload["last_error"] == "portal denied"
    json.dumps(payload)  # must be JSON-serialisable
