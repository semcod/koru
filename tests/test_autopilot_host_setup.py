"""Tests for ``koru autopilot setup-host`` host dependency reporting."""

from __future__ import annotations

import json
import shutil
import subprocess
from unittest import mock

import pytest

from koru.autopilot.host_setup import build_setup_host_report, run_host_setup


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
        "koru.autopilot.host_setup.build_setup_host_report", next_report,
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
