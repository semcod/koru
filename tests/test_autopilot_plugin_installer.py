"""Tests for autopilot IDE plugin installation helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from koru.autopilot import plugin_installer


def test_resolve_target_ide_prefers_autopilot_env(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    monkeypatch.setattr(plugin_installer, "detect_focused_ide_id", lambda: "cursor")

    assert plugin_installer.resolve_target_ide("auto") == "windsurf"


def test_resolve_target_ide_uses_running_supported_ide(monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(plugin_installer, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        plugin_installer,
        "detect_running_ides",
        lambda: [SimpleNamespace(id="cursor")],
    )

    assert plugin_installer.resolve_target_ide("auto") == "cursor"


def test_install_plugin_dry_run_builds_editor_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")

    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda: vsix)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_runner(cmd, **_kwargs):
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError("dry-run should not install")

    result = plugin_installer.install_plugin_for_ide(
        ide="cursor",
        dry_run=True,
        runner=fake_runner,
    )

    assert result.status == "dry_run"
    assert result.command == ["/usr/bin/cursor", "--install-extension", str(vsix)]


def test_install_plugin_skips_when_extension_already_installed(monkeypatch) -> None:
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_runner(cmd, **_kwargs):
        assert cmd[1] == "--list-extensions"
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=plugin_installer.EXTENSION_ID + "\n",
            stderr="",
        )

    result = plugin_installer.install_plugin_for_ide(
        ide="windsurf",
        runner=fake_runner,
    )

    assert result.status == "already_installed"
