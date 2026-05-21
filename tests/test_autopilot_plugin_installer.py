"""Tests for autopilot IDE plugin installation helpers."""

from __future__ import annotations

import os
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
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("VSCODE_NLS_CONFIG", raising=False)
    monkeypatch.delenv("VSCODE_IPC_HOOK", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.setattr(plugin_installer, "detect_terminal_host_ide_id", lambda **_k: None)
    monkeypatch.setattr(plugin_installer, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        plugin_installer,
        "detect_running_ides",
        lambda: [SimpleNamespace(id="cursor")],
    )

    assert plugin_installer.resolve_target_ide("auto") == "cursor"


def test_resolve_target_ide_uses_integrated_terminal_hint(monkeypatch) -> None:
    for key in ("TERM_PROGRAM_VERSION", "WINDSURF_CASCADE_TERMINAL", "GIO_LAUNCHED_DESKTOP_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "cursor")
    monkeypatch.setattr(plugin_installer, "detect_focused_ide_id", lambda: "windsurf")

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


def test_resolve_extension_vsix_finds_repo_plugin_package(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "koru"
    plugin_dir = root / "plugins" / "koru-autopilot-vscode"
    plugin_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    old = plugin_dir / "koru-autopilot-0.1.1.vsix"
    new = plugin_dir / "koru-autopilot-0.1.2.vsix"
    old.write_text("old", encoding="utf-8")
    new.write_text("new", encoding="utf-8")
    os.utime(old, (1, 1))
    os.utime(new, (2, 2))
    monkeypatch.setattr(plugin_installer, "_repo_root", lambda: root)
    monkeypatch.chdir(tmp_path)

    assert plugin_installer.resolve_extension_vsix() == new.resolve()


def test_install_plugin_configures_socket_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")
    socket_path = tmp_path / "koru-autopilot-windsurf.sock"
    config_home = tmp_path / "config"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda: vsix)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_runner(cmd, **_kwargs):
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=plugin_installer.EXTENSION_ID, stderr=""
            )
        if cmd[1] == "--install-extension" and cmd[2] == str(vsix) and cmd[3] == "--force":
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="windsurf",
        socket_path=socket_path,
        runner=fake_runner,
    )

    settings_path = config_home / "Windsurf" / "User" / "settings.json"
    assert result.status == "already_installed"
    assert result.settings_path == str(settings_path)
    assert result.socket_path == str(socket_path)
    assert f'"{plugin_installer.SOCKET_SETTING_KEY}": "{socket_path}"' in settings_path.read_text(
        encoding="utf-8",
    )
    assert "reassert rc=0" in result.message
    assert result.command == ["/usr/bin/windsurf", "--install-extension", str(vsix), "--force"]


def test_install_plugin_targets_vscodium_from_integrated_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.8.vsix"
    vsix.write_text("fake", encoding="utf-8")
    socket_path = tmp_path / "koru-autopilot-vscode.sock"
    config_home = tmp_path / "config"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/snap/codium/current/resources/app")
    monkeypatch.setattr(plugin_installer, "detect_running_ides", lambda: [])
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda: vsix)
    monkeypatch.setattr(
        plugin_installer.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"code", "codium"} else None,
    )

    def fake_runner(cmd, **_kwargs):
        assert cmd[0] == "/usr/bin/codium"
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=plugin_installer.EXTENSION_ID, stderr=""
            )
        if cmd[1] == "--install-extension":
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="vscode",
        socket_path=socket_path,
        runner=fake_runner,
    )

    settings_path = config_home / "VSCodium" / "User" / "settings.json"
    assert result.status == "already_installed"
    assert result.settings_path == str(settings_path)
    assert f'"{plugin_installer.SOCKET_SETTING_KEY}": "{socket_path}"' in settings_path.read_text(
        encoding="utf-8",
    )


def test_install_plugin_prefers_running_vscode_over_stale_codium_terminal_hint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.8.vsix"
    vsix.write_text("fake", encoding="utf-8")
    socket_path = tmp_path / "koru-autopilot-vscode.sock"
    config_home = tmp_path / "config"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/snap/codium/current/resources/app")
    monkeypatch.setattr(
        plugin_installer,
        "detect_running_ides",
        lambda: [SimpleNamespace(id="vscode", exe="/snap/code/240/usr/share/code/code")],
    )
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda: vsix)
    monkeypatch.setattr(
        plugin_installer.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"code", "codium"} else None,
    )

    def fake_runner(cmd, **_kwargs):
        assert cmd[0] == "/usr/bin/code"
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=plugin_installer.EXTENSION_ID, stderr=""
            )
        if cmd[1] == "--install-extension":
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="vscode",
        socket_path=socket_path,
        runner=fake_runner,
    )

    settings_path = config_home / "Code" / "User" / "settings.json"
    assert result.status == "already_installed"
    assert result.settings_path == str(settings_path)


def test_install_plugin_skips_when_extension_already_installed(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REASSERT_INSTALL", "0")
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


def test_installed_extension_version_for_ide_reads_editor_cli(monkeypatch) -> None:
    monkeypatch.setattr(plugin_installer, "_vscode_flavor", lambda: None)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_runner(cmd, **_kwargs):
        assert cmd == ["/usr/bin/code", "--list-extensions", "--show-versions"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="other.extension@1.2.3\nsemcod.koru-autopilot-vscode@0.1.13\n",
            stderr="",
        )

    version = plugin_installer.installed_extension_version_for_ide(
        ide="vscode",
        runner=fake_runner,
    )

    assert version == "0.1.13"
