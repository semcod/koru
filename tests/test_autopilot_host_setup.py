"""Tests for ``koru autopilot setup-host`` host dependency reporting."""

from __future__ import annotations

import json
import shutil
import subprocess
from unittest import mock

import pytest

from koru.autopilot.host_setup import (
    build_setup_host_report,
    install_ydotoold_user_service,
    run_host_setup,
)


def test_build_setup_host_report_has_expected_keys() -> None:
    report = build_setup_host_report()
    assert "session" in report
    assert "backends" in report and isinstance(report["backends"], list)
    assert "human_actions_required" in report
    assert "deb_packages_missing" in report
    assert "automated_apt_suggestion" in report


def test_build_setup_host_report_json_roundtrip() -> None:
    report = build_setup_host_report()
    text = json.dumps(report, default=str)
    assert json.loads(text)["session"] == report["session"]


def test_run_host_setup_install_dry_run_no_sudo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autopilot.host_setup.build_setup_host_report",
        lambda: {
            "session": "wayland",
            "selected_backend": "wtype",
            "backends": [],
            "ides": [],
            "focused_ide": None,
            "package_manager": "apt",
            "deb_packages_missing": ["wtype"],
            "human_actions_required": [],
            "automated_apt_suggestion": "sudo apt-get install -y wtype",
        },
    )
    real_which = shutil.which

    def which(name: str) -> str | None:
        if name == "apt-get":
            return "/usr/bin/apt-get"
        return real_which(name)

    monkeypatch.setattr("koru.autopilot.host_setup.shutil.which", which)
    code = run_host_setup(output_format="json", install=True, install_dry_run=True)
    assert code == 0


def test_run_host_setup_install_calls_apt_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = [
        {
            "session": "wayland",
            "selected_backend": None,
            "backends": [],
            "ides": [],
            "focused_ide": None,
            "package_manager": "apt",
            "deb_packages_missing": ["xdotool"],
            "human_actions_required": [],
            "automated_apt_suggestion": "sudo apt-get install -y xdotool",
        },
        {
            "session": "wayland",
            "selected_backend": "xdotool",
            "backends": [],
            "ides": [],
            "focused_ide": None,
            "package_manager": "apt",
            "deb_packages_missing": [],
            "human_actions_required": [],
            "automated_apt_suggestion": None,
        },
    ]
    idx = {"i": 0}

    def next_report() -> dict:
        i = min(idx["i"], len(reports) - 1)
        idx["i"] += 1
        return reports[i]

    monkeypatch.setattr(
        "koru.autopilot.host_setup.build_setup_host_report",
        next_report,
    )

    real_which = shutil.which

    def which(name: str) -> str | None:
        if name == "apt-get":
            return "/usr/bin/apt-get"
        return real_which(name)

    monkeypatch.setattr("koru.autopilot.host_setup.shutil.which", which)

    def fake_run(cmd, **kwargs):
        assert cmd[:3] == ["sudo", "apt-get", "install"]
        assert "xdotool" in cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("koru.autopilot.host_setup.subprocess.run", fake_run)
    code = run_host_setup(output_format="json", install=True, install_dry_run=False)
    assert code == 0


def test_autopilot_cli_setup_host_invokes_runner() -> None:
    from koru.autopilot import cli_command as cc

    with mock.patch("koru.autopilot.host_setup.run_host_setup", return_value=0) as m:
        rc = cc.autopilot_main(["setup-host", "--format", "json"])
    assert rc == 0
    m.assert_called_once()
    kwargs = m.call_args.kwargs
    assert kwargs["output_format"] == "json"
    assert kwargs["install"] is False


def test_install_ydotoold_user_service_skips_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("koru.autopilot.host_setup.shutil.which", lambda name: None)
    result = install_ydotoold_user_service(dry_run=True)
    assert result["ok"] is False
    assert result["skipped"] is True
    assert "ydotoold binary not on PATH" in result["reason"]


def test_install_ydotoold_user_service_dry_run_writes_no_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # Regression for plugin/koru autopilot bootstrap: on Wayland-native
    # compositors that lack `virtual-keyboard-v1` (e.g. GNOME), `ydotool` is the
    # only injector that actually reaches the focused window. Running it as a
    # systemd --user service avoids the "ydotoold backend unavailable" notice
    # plus the daemonless-mode latency. The installer must be a single
    # idempotent call wired into `koru autopilot setup-host`.
    fake_path = {"ydotoold": "/usr/bin/ydotoold", "systemctl": "/usr/bin/systemctl"}
    monkeypatch.setattr("koru.autopilot.host_setup.shutil.which", fake_path.get)
    monkeypatch.setenv("HOME", str(tmp_path))
    result = install_ydotoold_user_service(dry_run=True)
    assert result["ok"] is True
    assert result.get("dry_run") is True
    assert any("daemon-reload" in step for step in result["log"])
    # Dry-run must not actually touch the user systemd dir.
    assert not (tmp_path / ".config/systemd/user/ydotoold.service").exists()


def test_install_ydotoold_user_service_writes_unit_and_runs_systemctl(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake_path = {"ydotoold": "/usr/bin/ydotoold", "systemctl": "/usr/bin/systemctl"}
    monkeypatch.setattr("koru.autopilot.host_setup.shutil.which", fake_path.get)
    monkeypatch.setenv("HOME", str(tmp_path))
    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=False, text=False, timeout=None):  # noqa: ARG001
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("koru.autopilot.host_setup.subprocess.run", fake_run)
    result = install_ydotoold_user_service(dry_run=False)
    assert result["ok"] is True
    unit_path = tmp_path / ".config/systemd/user/ydotoold.service"
    assert unit_path.exists()
    contents = unit_path.read_text()
    assert "/usr/bin/ydotoold" in contents
    assert "/tmp/.ydotool_socket" in contents
    assert ["systemctl", "--user", "daemon-reload"] in calls
    assert ["systemctl", "--user", "enable", "--now", "ydotoold.service"] in calls
