"""Tests for desktop notifications."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from koru.notifications.desktop import notify_desktop


def test_notify_desktop_disabled_when_env_off() -> None:
    with patch.dict("os.environ", {"KORU_DESKTOP_NOTIFY": "0"}, clear=False):
        assert notify_desktop(title="t", body="b") is False


def test_notify_desktop_reports_command_success() -> None:
    completed = subprocess.CompletedProcess(["notify-send"], returncode=0)
    with (
        patch.dict("os.environ", {"KORU_DESKTOP_NOTIFY": "1"}, clear=False),
        patch("koru.notifications.desktop.shutil.which", return_value="/usr/bin/notify-send"),
        patch("koru.notifications.desktop.subprocess.run", return_value=completed) as run,
    ):
        assert notify_desktop(title="Koru", body="ticket-027") is True

    assert run.call_args.args[0][-2:] == ["Koru", "ticket-027"]


def test_notify_desktop_reports_command_failure() -> None:
    completed = subprocess.CompletedProcess(["notify-send"], returncode=1)
    with (
        patch.dict("os.environ", {"KORU_DESKTOP_NOTIFY": "1"}, clear=False),
        patch("koru.notifications.desktop.shutil.which", return_value="/usr/bin/notify-send"),
        patch("koru.notifications.desktop.subprocess.run", return_value=completed),
    ):
        assert notify_desktop(title="Koru", body="ticket-027") is False
