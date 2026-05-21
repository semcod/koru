from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from koru.autopilot import install_manager


def test_collect_report_flags_path_mismatch_and_plugin_version_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    path_koru = tmp_path / "bin" / "koru"
    repo_koru = tmp_path / "repo" / ".venv" / "bin" / "koru"
    path_koru.parent.mkdir(parents=True)
    repo_koru.parent.mkdir(parents=True)
    path_koru.write_text("#!/bin/sh\n", encoding="utf-8")
    repo_koru.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path / "repo")
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: path_koru)
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root: repo_koru)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(
        install_manager,
        "_daemon_status",
        lambda _socket: {
            "running": True,
            "plugins": [{"ide": "vscode", "fd": 6}],
        },
    )

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "koru_path_mismatch" in codes
    assert "plugin_version_missing" in codes
    assert report.plugin["connected"] is True
    assert report.plugin["expected_version"] == "0.1.13"


def test_collect_report_uses_explicit_ide_socket_when_env_is_unset(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.15")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.15",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    checked: list[Path] = []

    def fake_daemon_status(socket: Path) -> dict[str, object]:
        checked.append(socket)
        return {"running": False}

    monkeypatch.setattr(install_manager, "_daemon_status", fake_daemon_status)

    report = install_manager.collect_install_manager_report(ide="vscode")

    expected_socket = tmp_path / "koru-autopilot-vscode.sock"
    assert checked == [expected_socket]
    assert report.socket == str(expected_socket)
    assert os.environ.get("KORU_AUTOPILOT_INSTANCE") is None


def test_collect_report_flags_connected_plugin_version_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(
        install_manager,
        "_daemon_status",
        lambda _socket: {
            "running": True,
            "plugins": [{"ide": "vscode", "fd": 6, "version": "0.1.11"}],
        },
    )

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "plugin_version_mismatch" in codes
    assert report.ok is False


def test_collect_report_flags_installed_plugin_version_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.11",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "plugin_installed_version_mismatch" in codes
    assert report.ok is False


def test_collect_report_marks_installed_ok_but_not_connected_as_info(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    issues = {issue.code: issue for issue in report.issues}
    assert "plugin_installed_ok_but_not_connected" in issues
    assert issues["plugin_installed_ok_but_not_connected"].severity == "info"
    assert report.ok is True


def test_collect_report_flags_stale_live_extension_host(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.14")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.14",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(
        install_manager,
        "_daemon_status",
        lambda _socket: {
            "running": True,
            "plugins": [],
            "rejected_plugins": [
                {"ide": "vscode", "version": "0.1.11", "expected_version": "0.1.14"},
                {"ide": "vscode", "version": "0.1.13", "expected_version": "0.1.14"},
            ],
        },
    )

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    issues = {issue.code: issue for issue in report.issues}
    assert "plugin_live_host_stale" in issues
    assert issues["plugin_live_host_stale"].severity == "error"
    assert "0.1.11, 0.1.13" in issues["plugin_live_host_stale"].message
    assert report.ok is False


def test_collect_report_warns_for_pyenv_shim(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(
        install_manager,
        "_path_koru_bin",
        lambda: Path("/home/tom/.pyenv/shims/koru"),
    )
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root: None)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: None,
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "koru_pyenv_shim" in codes


def test_collect_report_warns_when_daemon_not_running(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: None)
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root: None)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: None,
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "daemon_not_running" in codes
    assert "koru_not_in_path" in codes


def test_repair_installation_records_plugin_action(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        install_manager,
        "collect_install_manager_report",
        lambda ide, socket_path: install_manager.InstallManagerReport(
            ok=True,
            source_root=str(tmp_path),
            package_version="1.0",
            source_version="1.0",
            python="/python",
            path_koru="/bin/koru",
            repo_koru="/repo/.venv/bin/koru",
            socket=str(tmp_path / "koru.sock"),
            daemon={"running": False},
            plugin={"ide": "vscode", "connected": False, "expected_version": "0.1.13"},
            ides=[],
        ),
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "dry_run"}),
    )

    report = install_manager.repair_installation(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
        dry_run=True,
    )

    assert report.actions[0] == {"action": "install_plugin", "result": {"status": "dry_run"}}
    assert report.actions[1]["action"] == "reload_ide_and_reconnect"


def test_collect_report_for_zed_does_not_require_vsix_plugin(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: (_ for _ in ()).throw(AssertionError("Zed should not query VSIX state")),
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": True})

    report = install_manager.collect_install_manager_report(
        ide="zed",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "plugin_not_connected" not in codes
    assert report.plugin["supported"] is False


def test_collect_report_auto_still_checks_plugin_connection(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root: "0.1.13")
    monkeypatch.setattr(install_manager, "installed_extension_version_for_ide", lambda _ide: None)
    monkeypatch.setattr(install_manager, "detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": True})

    report = install_manager.collect_install_manager_report(
        ide="auto",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "plugin_not_connected" in codes
    assert report.plugin["supported"] is True
