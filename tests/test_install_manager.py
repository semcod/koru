from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from koru.autopilot import install_manager
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION


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
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: path_koru)
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root, _ide=None: repo_koru)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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


def test_collect_report_accepts_nonlocal_koru_when_editable_source_matches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    path_koru = tmp_path / "global-venv" / "bin" / "koru"
    repo_koru = tmp_path / "repo" / ".venv" / "bin" / "koru"
    path_koru.parent.mkdir(parents=True)
    repo_koru.parent.mkdir(parents=True)
    path_koru.write_text("#!/bin/sh\n", encoding="utf-8")
    repo_koru.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path / "repo")
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: path_koru)
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root, _ide=None: repo_koru)
    monkeypatch.setattr(
        install_manager,
        "_installed_editable_source_root",
        lambda: (tmp_path / "repo").resolve(),
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
    monkeypatch.setattr(
        install_manager,
        "_daemon_status",
        lambda _socket: {"running": False},
    )

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "koru_path_mismatch" not in codes


def test_expected_plugin_version_falls_back_to_bundled_metadata(tmp_path: Path) -> None:
    assert install_manager._expected_plugin_version(tmp_path) == EXPECTED_VSCODE_PLUGIN_VERSION


def test_collect_report_uses_explicit_ide_socket_when_env_is_unset(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.15")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.15",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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


def test_collect_report_auto_prefers_autopilot_instance_over_terminal_hint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.15")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda ide: f"{ide}:0.1.15",
    )
    monkeypatch.setattr(install_manager, "detect_terminal_host_ide_id", lambda: "vscode")
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_terminal_host_ide_id", lambda: "vscode")
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(ide="auto")

    assert report.plugin["ide"] == "vscodium"
    assert report.plugin["installed_version"] == "vscodium:0.1.15"


def test_collect_report_flags_connected_plugin_version_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.11",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.13",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.14")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.14",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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


def test_collect_report_flags_plugin_socket_candidate_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    log = tmp_path / "plugin-debug.log"
    log.write_text(
        '2026-05-21 CONNECT_CANDIDATES {"ide":"vscode",'
        '"override":"/run/user/1000/koru-autopilot-vscodium.sock",'
        '"candidates":["/run/user/1000/koru-autopilot-vscodium.sock"]}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_PLUGIN_DEBUG_LOG", str(log))
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.15")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: "0.1.15",
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
    monkeypatch.setattr(
        install_manager,
        "_daemon_status",
        lambda _socket: {"running": True, "plugins": []},
    )

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=Path("/run/user/1000/koru-autopilot-vscode.sock"),
    )

    issues = {issue.code: issue for issue in report.issues}
    assert "plugin_socket_candidate_mismatch" in issues
    assert issues["plugin_socket_candidate_mismatch"].severity == "error"
    assert "koru-autopilot-vscodium.sock" in issues["plugin_socket_candidate_mismatch"].message
    assert report.ok is False


def test_collect_report_warns_for_pyenv_shim(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(
        install_manager,
        "_path_koru_bin",
        lambda: Path("/home/tom/.pyenv/shims/koru"),
    )
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root, _ide=None: None)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: None,
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": False})

    report = install_manager.collect_install_manager_report(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    assert "koru_pyenv_shim" in codes


def test_collect_report_warns_when_daemon_not_running(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: None)
    monkeypatch.setattr(install_manager, "_repo_koru_bin", lambda _root, _ide=None: None)
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: None,
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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
    assert [action["action"] for action in report.actions] == [
        "install_plugin",
        "start_daemon_for_reconnect",
        "reload_ide_and_reconnect",
        "wait_for_plugin_reconnect",
    ]


def test_repair_installation_skips_daemon_shutdown_when_plugin_already_aligned(
    monkeypatch,
    tmp_path: Path,
) -> None:
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
            daemon={"running": True},
            plugin={
                "ide": "vscode",
                "connected": True,
                "connected_version": "0.1.70",
                "connected_build_sha": "build-a",
                "installed_version": "0.1.70",
                "expected_version": "0.1.70",
                "expected_build_sha": "build-a",
            },
            ides=[],
        ),
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "already_installed"}),
    )

    def _forbidden_shutdown(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("shutdown should not be called when plugin is aligned")

    monkeypatch.setattr(install_manager, "AutopilotClient", _forbidden_shutdown)

    report = install_manager.repair_installation(
        ide="vscode",
        socket_path=tmp_path / "koru.sock",
        dry_run=False,
    )

    assert report.actions[0]["action"] == "install_plugin"
    assert report.actions[0]["result"]["skipped"] is True
    assert report.actions[1]["action"] == "shutdown_daemon_for_reload"
    assert report.actions[1]["result"]["skipped"] is True
    assert not any(action["action"] == "reload_ide_and_reconnect" for action in report.actions)


def test_repair_installation_skips_daemon_shutdown_when_connected_matches_expected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Connected live plugin can be aligned even when ``--list-extensions`` is unknown."""
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
            daemon={"running": True},
            plugin={
                "ide": "cursor",
                "connected": True,
                "connected_version": "0.2.34",
                "connected_build_sha": "build-a",
                "installed_version": None,
                "expected_version": "0.2.34",
                "expected_build_sha": "build-a",
            },
            ides=[],
        ),
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "already_installed"}),
    )

    def _forbidden_shutdown(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("shutdown should not be called when live plugin matches expected")

    monkeypatch.setattr(install_manager, "AutopilotClient", _forbidden_shutdown)

    report = install_manager.repair_installation(
        ide="cursor",
        socket_path=tmp_path / "koru.sock",
        dry_run=False,
    )

    assert report.actions[1]["action"] == "shutdown_daemon_for_reload"
    assert report.actions[1]["result"]["skipped"] is True


def test_repair_installation_shutdowns_daemon_when_build_is_stale(
    monkeypatch,
    tmp_path: Path,
) -> None:
    before = install_manager.InstallManagerReport(
        ok=False,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": True},
        plugin={
            "ide": "vscodium",
            "connected": True,
            "connected_version": "0.2.7",
            "connected_build_sha": "old-build",
            "installed_version": "0.2.7",
            "expected_version": "0.2.7",
            "expected_build_sha": "new-build",
        },
        ides=[],
    )
    after = install_manager.InstallManagerReport(
        ok=True,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": False},
        plugin={"ide": "vscodium", "connected": False},
        ides=[],
    )
    reports = iter([before, after])
    monkeypatch.setattr(
        install_manager,
        "collect_install_manager_report",
        lambda ide, socket_path: next(reports),
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "already_installed"}),
    )

    class _Client:
        def __init__(self, *, socket_path: Path, timeout: float) -> None:
            self.socket_path = socket_path
            self.timeout = timeout

        def shutdown(self) -> dict[str, object]:
            return {"ok": True, "message": "stopped"}

    monkeypatch.setattr(install_manager, "AutopilotClient", _Client)
    monkeypatch.setattr(
        install_manager,
        "_reload_ide_after_plugin_fix",
        lambda *_args, **_kwargs: {"status": "automatic"},
    )
    monkeypatch.setattr(
        install_manager,
        "_start_autopilot_daemon_for_plugin_repair",
        lambda *_args, **_kwargs: {"status": "started", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_wait_for_plugin_reconnect",
        lambda *_args, **_kwargs: {"status": "connected", "ok": True},
    )
    force_env: list[str | None] = []

    def fake_install_plugin_for_ide(**_kwargs):
        force_env.append(os.environ.get("KORU_AUTOPILOT_FORCE_REASSERT_INSTALL"))
        return SimpleNamespace(to_dict=lambda: {"status": "already_installed"})

    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        fake_install_plugin_for_ide,
    )

    report = install_manager.repair_installation(
        ide="vscodium",
        socket_path=tmp_path / "koru.sock",
        dry_run=False,
    )

    assert report.actions[1]["action"] == "shutdown_daemon_for_reload"
    assert report.actions[1]["result"] == {"ok": True, "message": "stopped"}
    assert force_env == ["1"]
    assert report.actions[0]["result"]["forced_reassert"] is True


def test_repair_installation_returns_refreshed_report_after_plugin_fix(
    monkeypatch,
    tmp_path: Path,
) -> None:
    before = install_manager.InstallManagerReport(
        ok=False,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": False},
        plugin={
            "ide": "vscodium",
            "connected": False,
            "installed_version": "0.1.71",
            "expected_version": "0.1.72",
        },
        ides=[],
        issues=[
            install_manager.ManagerIssue(
                code="plugin_installed_version_mismatch",
                severity="error",
                message="old plugin",
            )
        ],
    )
    after = install_manager.InstallManagerReport(
        ok=True,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": False},
        plugin={
            "ide": "vscodium",
            "connected": False,
            "installed_version": "0.1.72",
            "expected_version": "0.1.72",
        },
        ides=[],
    )
    reports = iter([before, after])
    monkeypatch.setattr(
        install_manager,
        "collect_install_manager_report",
        lambda ide, socket_path: next(reports),
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "installed"}),
    )

    report = install_manager.repair_installation(
        ide="vscodium",
        socket_path=tmp_path / "koru.sock",
        dry_run=False,
    )

    assert report.ok is True
    assert report.plugin["installed_version"] == "0.1.72"
    assert report.actions[0] == {"action": "install_plugin", "result": {"status": "installed"}}


def test_wait_for_plugin_reconnect_requires_expected_build(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls = {"n": 0}

    def fake_daemon_status(_socket: Path) -> dict[str, object]:
        calls["n"] += 1
        return {
            "running": True,
            "plugins": [
                {
                    "ide": "vscodium",
                    "version": "0.2.7",
                    "buildSha": "old-build",
                }
            ],
        }

    monkeypatch.setattr(install_manager, "_daemon_status", fake_daemon_status)
    monkeypatch.setattr(install_manager.time, "sleep", lambda _seconds: None)

    result = install_manager._wait_for_plugin_reconnect(
        str(tmp_path / "koru.sock"),
        "vscodium",
        dry_run=False,
        expected_build="new-build",
        timeout_seconds=0.01,
    )

    assert result["ok"] is False
    assert result["status"] == "build_mismatch"
    assert result["build"] == "old-build"
    assert result["expected_build"] == "new-build"


def test_repair_skips_new_window_escalation_without_opt_in(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", raising=False)
    report = install_manager.InstallManagerReport(
        ok=False,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": True},
        plugin={
            "ide": "vscodium",
            "connected": True,
            "connected_version": "0.2.7",
            "connected_build_sha": "old-build",
            "installed_version": "0.2.7",
            "expected_version": "0.2.7",
            "expected_build_sha": "new-build",
        },
        ides=[],
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "installed"}),
    )
    monkeypatch.setattr(
        install_manager,
        "_shutdown_autopilot_daemon",
        lambda _socket: {"ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_start_autopilot_daemon_for_plugin_repair",
        lambda *_args, **_kwargs: {"status": "started", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_reload_ide_after_plugin_fix",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_wait_for_plugin_reconnect",
        lambda *_args, **_kwargs: {"status": "build_mismatch", "ok": False},
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="vscodium",
        dry_run=False,
    )

    assert [step["action"] for step in steps] == [
        "install_plugin",
        "shutdown_daemon_for_reload",
        "start_daemon_for_reconnect",
        "reload_ide_and_reconnect",
        "wait_for_plugin_reconnect",
        "open_new_ide_window_for_plugin_build",
    ]
    assert steps[-1]["result"]["status"] == "skipped"


def test_repair_opens_new_window_after_build_mismatch_with_opt_in(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", "1")
    report = install_manager.InstallManagerReport(
        ok=False,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": True},
        plugin={
            "ide": "vscodium",
            "connected": True,
            "connected_version": "0.2.7",
            "connected_build_sha": "old-build",
            "installed_version": "0.2.7",
            "expected_version": "0.2.7",
            "expected_build_sha": "new-build",
        },
        ides=[],
    )
    wait_results = iter(
        [
            {"status": "build_mismatch", "ok": False, "build": "old-build"},
            {"status": "connected", "ok": True, "build": "new-build"},
        ]
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "installed"}),
    )
    monkeypatch.setattr(
        install_manager,
        "_shutdown_autopilot_daemon",
        lambda _socket: {"ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_start_autopilot_daemon_for_plugin_repair",
        lambda *_args, **_kwargs: {"status": "started", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_reload_ide_after_plugin_fix",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_open_new_ide_window_for_plugin_build",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_wait_for_plugin_reconnect",
        lambda *_args, **_kwargs: next(wait_results),
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="vscodium",
        dry_run=False,
    )

    assert [step["action"] for step in steps] == [
        "install_plugin",
        "shutdown_daemon_for_reload",
        "start_daemon_for_reconnect",
        "reload_ide_and_reconnect",
        "wait_for_plugin_reconnect",
        "open_new_ide_window_for_plugin_build",
        "wait_for_plugin_reconnect",
    ]
    assert steps[-2]["result"]["status"] == "automatic"
    assert steps[-1]["result"]["status"] == "connected"


def test_repair_restarts_ide_when_new_window_still_has_old_build(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", "1")
    monkeypatch.setenv("KORU_AUTOPILOT_RESTART_IDE_ON_PLUGIN_BUILD_MISMATCH", "1")
    report = install_manager.InstallManagerReport(
        ok=False,
        source_root=str(tmp_path),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": True},
        plugin={
            "ide": "vscodium",
            "connected": True,
            "connected_version": "0.2.7",
            "connected_build_sha": "old-build",
            "installed_version": "0.2.7",
            "expected_version": "0.2.7",
            "expected_build_sha": "new-build",
        },
        ides=[],
    )
    wait_results = iter(
        [
            {"status": "build_mismatch", "ok": False, "build": "old-build"},
            {"status": "build_mismatch", "ok": False, "build": "old-build"},
            {"status": "connected", "ok": True, "build": "new-build"},
        ]
    )
    monkeypatch.setattr(
        install_manager,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(to_dict=lambda: {"status": "installed"}),
    )
    monkeypatch.setattr(
        install_manager,
        "_shutdown_autopilot_daemon",
        lambda _socket: {"ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_start_autopilot_daemon_for_plugin_repair",
        lambda *_args, **_kwargs: {"status": "started", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_reload_ide_after_plugin_fix",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_open_new_ide_window_for_plugin_build",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_restart_ide_for_plugin_build",
        lambda *_args, **_kwargs: {"status": "automatic", "ok": True},
    )
    monkeypatch.setattr(
        install_manager,
        "_wait_for_plugin_reconnect",
        lambda *_args, **_kwargs: next(wait_results),
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="vscodium",
        dry_run=False,
    )

    assert [step["action"] for step in steps] == [
        "install_plugin",
        "shutdown_daemon_for_reload",
        "start_daemon_for_reconnect",
        "reload_ide_and_reconnect",
        "wait_for_plugin_reconnect",
        "open_new_ide_window_for_plugin_build",
        "wait_for_plugin_reconnect",
        "restart_ide_for_plugin_build",
        "wait_for_plugin_reconnect",
    ]
    assert steps[-2]["result"]["status"] == "automatic"
    assert steps[-1]["result"]["status"] == "connected"


def test_repair_fix_reload_uses_reuse_window_for_same_workspace(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import koru.ide_adapters.ide_reload as ide_reload

    reload_env: list[dict[str, str | None]] = []

    def _fake_reload(ide: str, *, project: Path):
        assert ide == "vscodium"
        assert project == tmp_path
        reload_env.append(
            {
                "reuse": os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"),
                "palette": os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD"),
            }
        )
        return SimpleNamespace(attempted=True, ok=True, method="reuse-window", detail=None)

    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: False)
    monkeypatch.setattr(ide_reload, "try_reload_vscode_family_ide", _fake_reload)

    result = install_manager._reload_ide_after_plugin_fix(
        "vscodium",
        source_root=tmp_path,
        daemon={
            "plugins": [
                {
                    "ide": "vscodium",
                    "workspaceFolders": [str(tmp_path)],
                }
            ]
        },
        dry_run=False,
    )

    assert result["status"] == "automatic"
    assert reload_env == [{"reuse": "1", "palette": None}]
    assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") is None
    assert os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD") is None


def test_repair_fix_reload_skips_automation_from_integrated_terminal(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import koru.ide_adapters.ide_reload as ide_reload

    reload_env: list[dict[str, str | None]] = []

    def _fake_reload(ide: str, *, project: Path):
        reload_env.append(
            {
                "reuse": os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"),
                "palette": os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD"),
            }
        )
        return SimpleNamespace(attempted=False, ok=False, detail="blocked")

    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: True)
    monkeypatch.setattr(ide_reload, "try_reload_vscode_family_ide", _fake_reload)

    result = install_manager._reload_ide_after_plugin_fix(
        "vscodium",
        source_root=tmp_path,
        daemon={
            "plugins": [
                {
                    "ide": "vscodium",
                    "workspaceFolders": [str(tmp_path)],
                }
            ]
        },
        dry_run=False,
    )

    assert result["status"] == "manual"
    assert reload_env == [{"reuse": None, "palette": None}]


def test_collect_report_for_zed_does_not_require_vsix_plugin(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(
        install_manager,
        "installed_extension_version_for_ide",
        lambda _ide: (_ for _ in ()).throw(AssertionError("Zed should not query VSIX state")),
    )
    monkeypatch.setattr(install_manager, "detect_running_ides", lambda: [])
    monkeypatch.setattr("koruide.ide.detect_running_ides", lambda: [])
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
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setattr(install_manager, "_source_root", lambda: tmp_path)
    monkeypatch.setattr(install_manager, "_source_version", lambda _root, _ide=None: "1.0")
    monkeypatch.setattr(install_manager, "_package_version", lambda: "1.0")
    monkeypatch.setattr(install_manager, "_path_koru_bin", lambda: tmp_path / ".venv/bin/koru")
    monkeypatch.setattr(
        install_manager,
        "_repo_koru_bin",
        lambda _root, _ide=None: tmp_path / ".venv/bin/koru",
    )
    monkeypatch.setattr(install_manager, "_expected_plugin_version", lambda _root, _ide=None: "0.1.13")
    monkeypatch.setattr(install_manager, "installed_extension_version_for_ide", lambda _ide: None)
    # Mock functions at their actual import location in install_manager module
    monkeypatch.setattr("koru.autopilot.install_manager.detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setattr("koru.autopilot.install_manager.detect_running_ides", lambda: [])
    monkeypatch.setattr(install_manager, "_daemon_status", lambda _socket: {"running": True})

    report = install_manager.collect_install_manager_report(
        ide="auto",
        socket_path=tmp_path / "koru.sock",
    )

    codes = {issue.code for issue in report.issues}
    print(f"DEBUG report.plugin: {report.plugin}")
    print(f"DEBUG report.daemon: {report.daemon}")
    print(f"DEBUG codes: {codes}")
    assert "plugin_not_connected" in codes
    assert report.plugin["supported"] is True


def _mismatch_report(tmp_path: Path, *, plugins: list[dict]) -> "install_manager.InstallManagerReport":
    project = tmp_path / "koru"
    project.mkdir(exist_ok=True)
    return install_manager.InstallManagerReport(
        ok=False,
        source_root=str(project),
        package_version="1.0",
        source_version="1.0",
        python="/python",
        path_koru="/bin/koru",
        repo_koru="/repo/.venv/bin/koru",
        socket=str(tmp_path / "koru.sock"),
        daemon={"running": True, "plugins": plugins},
        plugin={
            "ide": "windsurf",
            "connected": True,
            "connected_version": "0.2.0",
            "connected_build_sha": "old",
            "installed_version": "0.2.1",
            "expected_version": "0.2.1",
            "expected_build_sha": "new",
            "workspace_folders": [str(tmp_path / "nexu")],
        },
        ides=[],
    )


def test_repair_refuses_window_ops_on_workspace_mismatch(tmp_path: Path) -> None:
    report = _mismatch_report(
        tmp_path,
        plugins=[{"ide": "windsurf", "workspaceFolders": [str(tmp_path / "nexu")]}],
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="windsurf",
        dry_run=False,
    )

    assert [step["action"] for step in steps] == ["workspace_mismatch"]
    result = steps[0]["result"]
    assert result["status"] == "skipped"
    assert result["ok"] is False
    assert str(tmp_path / "nexu") in result["message"]
    assert str(tmp_path / "koru") in result["message"]


def test_repair_proceeds_when_a_matching_workspace_plugin_exists(tmp_path: Path) -> None:
    project = tmp_path / "koru"
    report = _mismatch_report(
        tmp_path,
        plugins=[
            {"ide": "windsurf", "workspaceFolders": [str(tmp_path / "nexu")]},
            {"ide": "windsurf", "workspaceFolders": [str(project)]},
        ],
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="windsurf",
        dry_run=True,
    )

    assert [step["action"] for step in steps] != ["workspace_mismatch"]
    assert "install_plugin" in [step["action"] for step in steps]


def test_repair_proceeds_when_plugin_workspace_unknown(tmp_path: Path) -> None:
    report = _mismatch_report(
        tmp_path,
        plugins=[{"ide": "windsurf"}],  # no workspaceFolders → unknown, do not block
    )

    steps = install_manager._build_repair_steps(
        report,
        resolved_ide="windsurf",
        dry_run=True,
    )

    assert [step["action"] for step in steps] != ["workspace_mismatch"]
