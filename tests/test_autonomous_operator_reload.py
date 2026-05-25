"""Stale extension-host detection for the autonomous operator.

After ``koru auto`` reasserts a fresh VSIX, the IDE extension host may
still be running the previous build until the user manually triggers
``Developer: Reload Window``. The detector compares the installed
extension version (read from the IDE's ``--list-extensions``) against
what the daemon's plugin status reports — divergence implies the
running extension is stale and we should reload automatically.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from koru.autonomous_operator import (
    _detect_stale_extension_host,
    _force_reload_if_extension_host_stale,
    _live_plugin_version,
    _retry_plugin_wait_after_reload,
)


class StubClient:
    def __init__(self, status_payload: dict[str, Any] | None) -> None:
        self._payload = status_payload

    def status(self) -> dict[str, Any]:
        return self._payload or {}


class LivePluginVersionTests(unittest.TestCase):
    def test_returns_version_when_match_ide(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.70"}]},
        )
        self.assertEqual(_live_plugin_version(client, "cursor"), "0.1.70")

    def test_returns_none_when_status_unavailable(self) -> None:
        class Boom:
            def status(self) -> dict[str, Any]:
                raise OSError("daemon down")

        self.assertIsNone(_live_plugin_version(Boom(), "cursor"))

    def test_returns_none_when_no_plugins(self) -> None:
        client = StubClient({})
        self.assertIsNone(_live_plugin_version(client, "cursor"))


class DetectStaleExtensionHostTests(unittest.TestCase):
    def test_stale_when_installed_differs_from_live(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.70"}]},
        )
        with mock.patch(
            "koruide.plugin_installer.installed_extension_version_for_ide",
            return_value="0.1.71",
        ):
            stale, installed, live = _detect_stale_extension_host("cursor", client)
        self.assertTrue(stale)
        self.assertEqual(installed, "0.1.71")
        self.assertEqual(live, "0.1.70")

    def test_not_stale_when_versions_match(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.71"}]},
        )
        with mock.patch(
            "koruide.plugin_installer.installed_extension_version_for_ide",
            return_value="0.1.71",
        ):
            stale, _, _ = _detect_stale_extension_host("cursor", client)
        self.assertFalse(stale)

    def test_not_stale_for_non_vscode_family(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "claude-code", "version": "0.0.1"}]},
        )
        stale, installed, live = _detect_stale_extension_host("claude-code", client)
        self.assertFalse(stale)
        self.assertIsNone(installed)
        self.assertIsNone(live)


class ForceReloadIfStaleTests(unittest.TestCase):
    def _args(self) -> mock.Mock:
        return mock.Mock(emit_events="text")

    def test_reload_triggered_when_stale(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.70"}]},
        )
        logs: list[str] = []
        wait_calls: list[float] = []

        def stdio_info(msg: str, *, fmt: str) -> None:
            logs.append(msg)

        def wait_for_plugin(*_a: Any, timeout_seconds: float, **_kw: Any) -> bool:
            wait_calls.append(timeout_seconds)
            return True

        reload_result = mock.Mock(attempted=True, ok=True, method="command", detail="ok")
        with (
            mock.patch(
                "koruide.plugin_installer.installed_extension_version_for_ide",
                return_value="0.1.71",
            ),
            mock.patch(
                "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
                return_value=reload_result,
            ),
        ):
            _force_reload_if_extension_host_stale(
                self._args(),
                "cursor",
                wait_seconds=10.0,
                client=client,
                project=None,
                wait_for_plugin=wait_for_plugin,
                stdio_info=stdio_info,
            )
        self.assertTrue(
            any("stale extension host detected" in m for m in logs),
            f"expected detection log; got {logs}",
        )
        self.assertTrue(any("reload after VSIX install" in m for m in logs))
        self.assertEqual(wait_calls, [12.0])

    def test_no_reload_when_versions_match(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.71"}]},
        )
        logs: list[str] = []
        with mock.patch(
            "koruide.plugin_installer.installed_extension_version_for_ide",
            return_value="0.1.71",
        ):
            _force_reload_if_extension_host_stale(
                self._args(),
                "cursor",
                wait_seconds=10.0,
                client=client,
                project=None,
                wait_for_plugin=lambda *_a, **_kw: True,
                stdio_info=lambda msg, **_kw: logs.append(msg),
            )
        self.assertEqual(logs, [])

    def test_logs_when_reload_unavailable(self) -> None:
        client = StubClient(
            {"plugins": [{"ide": "cursor", "version": "0.1.70"}]},
        )
        logs: list[str] = []
        reload_result = mock.Mock(attempted=False, ok=False, method=None, detail=None)
        with (
            mock.patch(
                "koruide.plugin_installer.installed_extension_version_for_ide",
                return_value="0.1.71",
            ),
            mock.patch(
                "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
                return_value=reload_result,
            ),
        ):
            _force_reload_if_extension_host_stale(
                self._args(),
                "cursor",
                wait_seconds=10.0,
                client=client,
                project=None,
                wait_for_plugin=lambda *_a, **_kw: True,
                stdio_info=lambda msg, **_kw: logs.append(msg),
            )
        self.assertTrue(
            any("Reload Window unavailable" in m for m in logs),
            f"expected manual-reload hint; got {logs}",
        )


class RetryPluginWaitAfterReloadTests(unittest.TestCase):
    def test_logs_integrated_terminal_reload_refusal_without_waiting(self) -> None:
        logs: list[str] = []
        wait_called = False
        reload_result = mock.Mock(
            attempted=True,
            ok=False,
            method="command_palette",
            detail=(
                "refusing command-palette reload from integrated terminal focus; "
                "typing `Developer: Reload Window` here would write into the shell"
            ),
        )

        def wait_for_plugin(*_a: Any, **_kw: Any) -> bool:
            nonlocal wait_called
            wait_called = True
            return True

        with mock.patch(
            "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
            return_value=reload_result,
        ):
            result = _retry_plugin_wait_after_reload(
                mock.Mock(emit_events="text"),
                "vscodium",
                5.0,
                client=StubClient({"plugins": []}),
                project=None,
                wait_for_plugin=wait_for_plugin,
                stdio_info=lambda msg, **_kw: logs.append(msg),
            )

        self.assertIsNone(result)
        self.assertFalse(wait_called)
        joined = "\n".join(logs)
        self.assertIn("automatyczny Reload Window po mismatch nie powiódł się", joined)
        self.assertIn("would write into the shell", joined)

    def test_reuse_window_falls_back_to_fresh_window_when_plugin_still_missing(self) -> None:
        logs: list[str] = []
        wait_results = iter([False, True])
        wait_calls: list[float] = []
        reload_result = mock.Mock(
            attempted=True,
            ok=True,
            method="reuse_window",
            detail="opened",
        )
        fresh_window = mock.Mock(
            attempted=True,
            ok=True,
            method="new_window",
            detail="opened",
        )

        def wait_for_plugin(*_a: Any, timeout_seconds: float, **_kw: Any) -> bool:
            wait_calls.append(timeout_seconds)
            return next(wait_results)

        with (
            mock.patch(
                "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
                return_value=reload_result,
            ),
            mock.patch(
                "koru.ide_adapters.ide_reload.try_open_vscode_family_ide_new_window",
                return_value=fresh_window,
            ) as open_new,
        ):
            result = _retry_plugin_wait_after_reload(
                mock.Mock(emit_events="text"),
                "vscodium",
                5.0,
                client=StubClient({"plugins": []}),
                project=mock.Mock(),
                wait_for_plugin=wait_for_plugin,
                stdio_info=lambda msg, **_kw: logs.append(msg),
            )

        self.assertTrue(result)
        self.assertEqual(wait_calls, [12.0, 12.0])
        open_new.assert_called_once()
        joined = "\n".join(logs)
        self.assertIn("reuse-window workspace reopen", joined)
        self.assertIn("otwieram świeże okno IDE", joined)


if __name__ == "__main__":
    unittest.main()
