"""Tests for desktop notifications."""

from __future__ import annotations

from unittest.mock import patch

from koru.notifications.desktop import notify_desktop


def test_notify_desktop_disabled_when_env_off() -> None:
    with patch.dict("os.environ", {"KORU_DESKTOP_NOTIFY": "0"}, clear=False):
        assert notify_desktop(title="t", body="b") is False
