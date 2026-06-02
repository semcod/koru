"""Tests for autopilot IDE plugin installation helpers."""

from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.autopilot import plugin_installer


def _cp(
    cmd: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


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
    for key in (
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
        "CHROME_DESKTOP",
    ):
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

    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: vsix)
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


def test_resolve_extension_vsix_prefers_package_version(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "koru"
    plugin_dir = root / "plugins" / "koru-autopilot-vscode"
    plugin_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (plugin_dir / "package.json").write_text('{"version":"0.1.15"}', encoding="utf-8")
    stale = plugin_dir / "koru-autopilot-0.1.14.vsix"
    current = plugin_dir / "koru-autopilot-0.1.15.vsix"
    stale.write_text("stale", encoding="utf-8")
    current.write_text("current", encoding="utf-8")
    os.utime(stale, (20, 20))
    os.utime(current, (10, 10))
    monkeypatch.setattr(plugin_installer, "_repo_root", lambda: root)
    monkeypatch.chdir(tmp_path)

    assert plugin_installer.resolve_extension_vsix() == current.resolve()


def test_install_plugin_configures_socket_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")
    socket_path = tmp_path / "koru-autopilot-windsurf.sock"
    config_home = tmp_path / "config"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: vsix)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    windsurf_ext_id = plugin_installer.extension_id_for_ide("windsurf")

    def fake_runner(cmd, **_kwargs):
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=windsurf_ext_id, stderr=""
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
    assert '"koruAutopilot.autoConnect": true' in settings_path.read_text(encoding="utf-8")
    assert "reassert rc=0" in result.message
    assert "Developer: Reload Window" in result.message
    assert result.command == ["/usr/bin/windsurf", "--install-extension", str(vsix), "--force"]


def test_install_plugin_reassert_falls_back_when_resolved_vsix_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "koru"
    plugin_dir = root / "plugins" / "koru-autopilot-vscode"
    plugin_dir.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    fallback_vsix = plugin_dir / "koru-autopilot-0.1.62.vsix"
    fallback_vsix.write_text("fallback", encoding="utf-8")
    missing_vsix = plugin_dir / "koru-autopilot-vscode-0.1.66.vsix"

    monkeypatch.setattr(plugin_installer, "_repo_root", lambda: root)
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: missing_vsix)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")

    cursor_ext_id = plugin_installer.extension_id_for_ide("cursor")

    def fake_runner(cmd, **_kwargs):
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(cmd, 0, stdout=cursor_ext_id, stderr="")
        if cmd[1] == "--install-extension" and cmd[2] == str(missing_vsix):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="ENOENT: no such file")
        if cmd[1] == "--install-extension" and cmd[2] == str(fallback_vsix):
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="cursor",
        runner=fake_runner,
    )

    assert result.status == "already_installed"
    assert result.command == [
        "/usr/bin/cursor",
        "--install-extension",
        str(fallback_vsix),
        "--force",
    ]
    assert "reassert fallback rc=0" in result.message


def test_install_plugin_targets_vscodium_from_integrated_terminal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.8.vsix"
    vsix.write_text("fake", encoding="utf-8")
    socket_path = tmp_path / "koru-autopilot-vscodium.sock"
    config_home = tmp_path / "config"

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/snap/codium/current/resources/app")
    monkeypatch.setattr(plugin_installer, "detect_running_ides", lambda: [])
    monkeypatch.setattr(plugin_installer, "detect_terminal_host_ide_id", lambda: "vscodium")
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: vsix)
    monkeypatch.setattr(
        plugin_installer.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"code", "codium"} else None,
    )

    vscodium_ext_id = plugin_installer.extension_id_for_ide("vscodium")

    def fake_runner(cmd, **_kwargs):
        assert cmd[0] == "/usr/bin/codium"
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=vscodium_ext_id, stderr=""
            )
        if cmd[1] == "--install-extension":
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="auto",
        socket_path=socket_path,
        runner=fake_runner,
    )

    settings_path = config_home / "VSCodium" / "User" / "settings.json"
    assert result.status == "already_installed"
    assert result.ide == "vscodium"
    assert result.settings_path == str(settings_path)
    assert f'"{plugin_installer.SOCKET_SETTING_KEY}": "{socket_path}"' in settings_path.read_text(
        encoding="utf-8",
    )


def test_install_plugin_explicit_vscode_does_not_use_codium_hint(
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
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: vsix)
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
    assert result.ide == "vscode"
    assert result.settings_path == str(settings_path)


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
    monkeypatch.setattr(plugin_installer, "resolve_extension_vsix", lambda _ide=None: vsix)
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
    windsurf_ext_id = plugin_installer.extension_id_for_ide("windsurf")

    def fake_runner(cmd, **_kwargs):
        assert cmd[1] == "--list-extensions"
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=windsurf_ext_id + "\n",
            stderr="",
        )

    result = plugin_installer.install_plugin_for_ide(
        ide="windsurf",
        runner=fake_runner,
    )

    assert result.status == "already_installed"


def test_install_plugin_builds_stale_local_vsix_before_reassert(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "koru"
    plugin_dir = root / "plugins" / "koru-autopilot-vscodium"
    (plugin_dir / "src").mkdir(parents=True)
    (root / "plugins" / "koru-autopilot-shared" / "src").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='koru'\n", encoding="utf-8")
    (plugin_dir / "src" / "extension.ts").write_text("new source", encoding="utf-8")
    (plugin_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "koru-autopilot-vscodium",
                "version": "0.2.7",
                "koruAutopilotBuild": {"schema": 1, "sha": "newbuild"},
            }
        ),
        encoding="utf-8",
    )
    vsix = plugin_dir / "koru-autopilot-vscodium-0.2.7.vsix"
    with zipfile.ZipFile(vsix, "w") as archive:
        archive.writestr(
            "extension/package.json",
            json.dumps({"koruAutopilotBuild": {"schema": 1, "sha": "oldbuild"}}),
        )
    os.utime(vsix, (1, 1))

    monkeypatch.setattr(plugin_installer, "_repo_root", lambda: root)
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")
    vscodium_ext_id = plugin_installer.extension_id_for_ide("vscodium")
    calls: list[list[str]] = []

    def fake_runner(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd == ["npm", "run", "package"]:
            assert kwargs.get("cwd") == str(plugin_dir)
            return subprocess.CompletedProcess(cmd, 0, stdout="packed", stderr="")
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(cmd, 0, stdout=vscodium_ext_id, stderr="")
        if cmd[1] == "--install-extension":
            return subprocess.CompletedProcess(cmd, 0, stdout="installed", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="vscodium",
        runner=fake_runner,
    )

    assert result.status == "already_installed"
    assert ["npm", "run", "package"] in calls
    assert ["/usr/bin/codium", "--install-extension", str(vsix.resolve()), "--force"] in calls


def test_install_plugin_removes_conflicting_family_extension(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REASSERT_INSTALL", "0")
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")
    vscodium_ext_id = plugin_installer.extension_id_for_ide("vscodium")
    conflict_ext_id = plugin_installer.extension_id_for_ide("vscode")
    calls: list[list[str]] = []

    def fake_runner(cmd, **_kwargs):
        calls.append(list(cmd))
        if cmd[1] == "--list-extensions":
            stdout = f"{vscodium_ext_id}\n{conflict_ext_id}\n"
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        if cmd[1] == "--uninstall-extension":
            return subprocess.CompletedProcess(cmd, 0, stdout="removed", stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="vscodium",
        runner=fake_runner,
    )

    assert result.status == "already_installed"
    assert result.conflicts_removed == (conflict_ext_id,)
    assert ["/usr/bin/codium", "--uninstall-extension", conflict_ext_id] in calls


@pytest.mark.parametrize(
    ("installed_sha", "expected_sha", "should_reassert", "expected_message"),
    [
        ("abc123", "abc123", False, "build sha match"),
        ("old", "new", True, ""),
        ("old", None, True, ""),
    ],
)
def test_reassert_policy_matrix(
    installed_sha: str,
    expected_sha: str | None,
    should_reassert: bool,
    expected_message: str,
) -> None:
    decision = plugin_installer._decide_reassert_policy(
        dry_run=False,
        reassert_enabled=True,
        installed_sha=installed_sha,
        expected_sha=expected_sha,
    )

    assert decision.should_reassert is should_reassert
    if expected_message:
        assert expected_message in decision.skip_message
    else:
        assert decision.skip_message == ""


def test_should_retry_missing_vsix_only_for_missing_file_errors(tmp_path: Path) -> None:
    missing_vsix = tmp_path / "missing.vsix"
    proc_missing = _cp(
        ["codium", "--install-extension", str(missing_vsix)],
        returncode=1,
        stderr="ENOENT: no such file",
    )
    proc_other = _cp(
        ["codium", "--install-extension", str(missing_vsix)],
        returncode=1,
        stderr="permission denied",
    )

    assert plugin_installer._should_retry_missing_vsix(missing_vsix, proc_missing) is True
    assert plugin_installer._should_retry_missing_vsix(missing_vsix, proc_other) is False


def test_install_plugin_moves_stale_family_extension_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KORU_AUTOPILOT_REASSERT_INSTALL", "0")
    monkeypatch.setattr(plugin_installer.shutil, "which", lambda name: f"/usr/bin/{name}")
    extensions_root = tmp_path / ".vscode-oss" / "extensions"
    extensions_root.mkdir(parents=True)
    active_dir = extensions_root / "semcod.koru-autopilot-vscodium-0.1.78"
    stale_target_dir = extensions_root / "semcod.koru-autopilot-vscodium-0.1.77"
    stale_conflict_dir = extensions_root / "semcod.koru-autopilot-vscode-0.1.77"
    unrelated_dir = extensions_root / "other.extension-1.0.0"
    for path in (active_dir, stale_target_dir, stale_conflict_dir, unrelated_dir):
        path.mkdir()
    (extensions_root / "extensions.json").write_text(
        json.dumps(
            [
                {
                    "identifier": {
                        "id": plugin_installer.extension_id_for_ide("vscodium"),
                    },
                    "relativeLocation": active_dir.name,
                }
            ]
        ),
        encoding="utf-8",
    )
    vscodium_ext_id = plugin_installer.extension_id_for_ide("vscodium")

    def fake_runner(cmd, **_kwargs):
        if cmd[1] == "--list-extensions":
            return subprocess.CompletedProcess(cmd, 0, stdout=vscodium_ext_id, stderr="")
        raise AssertionError(f"unexpected cmd {cmd}")

    result = plugin_installer.install_plugin_for_ide(
        ide="vscodium",
        runner=fake_runner,
    )

    assert result.status == "already_installed"
    assert not stale_target_dir.exists()
    assert not stale_conflict_dir.exists()
    assert active_dir.exists()
    assert unrelated_dir.exists()
    disabled_root = tmp_path / ".vscode-oss" / "extensions-disabled"
    assert (disabled_root / stale_target_dir.name).is_dir()
    assert (disabled_root / stale_conflict_dir.name).is_dir()
    assert len(result.stale_extension_dirs_moved) == 2


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
