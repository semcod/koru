from __future__ import annotations

from typing import Any
from unittest import mock

from koru.autonomous_plugin_runtime import (
    detect_stale_extension_host,
    live_plugin_version,
    plugin_reason_requires_reload,
    reload_retry_wait_seconds,
)


class StubClient:
    def __init__(self, status_payload: dict[str, Any] | None) -> None:
        self._payload = status_payload

    def status(self) -> dict[str, Any]:
        return self._payload or {}


def test_live_plugin_version_matches_ide_case_insensitively() -> None:
    client = StubClient(
        {
            "plugins": [
                {"ide": "cursor", "version": "0.1.70"},
                {"ide": "VSCodium", "version": "0.1.74"},
            ],
        },
    )

    assert live_plugin_version(client, "vscodium") == "0.1.74"


def test_plugin_reason_requires_reload_for_mismatch_protocol_and_empty_list() -> None:
    assert plugin_reason_requires_reload("connected autopilot plugin version mismatch")
    assert plugin_reason_requires_reload("connected autopilot plugin build mismatch")
    assert plugin_reason_requires_reload("plugin protocol incompatible")
    assert plugin_reason_requires_reload("daemon status plugin list is empty")
    assert not plugin_reason_requires_reload("daemon status unavailable")


def test_reload_retry_wait_seconds_clamps_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS", "100")
    assert reload_retry_wait_seconds(5.0) == 30.0

    monkeypatch.setenv("KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS", "1")
    assert reload_retry_wait_seconds(5.0) == 5.0

    monkeypatch.setenv("KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS", "bad")
    assert reload_retry_wait_seconds(0.0) == 12.0


def test_detect_stale_extension_host_accepts_live_version_hook() -> None:
    client = StubClient({"plugins": [{"ide": "vscodium", "version": "0.1.73"}]})

    with mock.patch(
        "koruide.plugin_installer.installed_extension_version_for_ide",
        return_value="0.1.74",
    ):
        stale, installed, live = detect_stale_extension_host(
            "vscodium",
            client,
            live_version=lambda *_args: "0.1.73",
        )

    assert stale is True
    assert installed == "0.1.74"
    assert live == "0.1.73"
