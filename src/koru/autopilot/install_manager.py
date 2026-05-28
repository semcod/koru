"""Installation inventory and repair helpers for autopilot runtime pieces."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import sys
import tomllib
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autopilot.client import AutopilotClient
from koru.autopilot.ide import (
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    supports_vscode_extension_plugin,
)
from koru.autopilot.install_checks import (
    ManagerIssue,
    check_daemon_issues,
    check_koru_path_issues,
    check_plugin_build_mismatch_issue,
    check_plugin_build_missing_issue,
    check_plugin_installed_ok_but_not_connected_issue,
    check_plugin_installed_version_mismatch_issue,
    check_plugin_live_host_stale_issue,
    check_plugin_not_connected_issue,
    check_plugin_socket_candidate_mismatch_issue,
    check_plugin_version_mismatch_issue,
    check_plugin_version_missing_issue,
    check_pyenv_shim_issue,
    check_version_mismatch_issue,
    is_pyenv_shim,
    plugin_debug_log_path,
    recent_socket_candidate_mismatch,
)
from koru.autopilot.plugin_installer import (
    install_plugin_for_ide,
    installed_extension_version_for_ide,
)
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION
from koruide.socket import default_socket_path

# Legacy aliases preserved for backward compatibility (tests/CLI mocks may
# monkeypatch the private names on this module).
_is_pyenv_shim = is_pyenv_shim
_plugin_debug_log_path = plugin_debug_log_path
_recent_socket_candidate_mismatch = recent_socket_candidate_mismatch
_check_koru_path_issues = check_koru_path_issues
_check_pyenv_shim_issue = check_pyenv_shim_issue
_check_version_mismatch_issue = check_version_mismatch_issue
_check_daemon_issues = check_daemon_issues
_check_plugin_version_missing_issue = check_plugin_version_missing_issue
_check_plugin_build_missing_issue = check_plugin_build_missing_issue
_check_plugin_installed_version_mismatch_issue = check_plugin_installed_version_mismatch_issue
_check_plugin_installed_ok_but_not_connected_issue = check_plugin_installed_ok_but_not_connected_issue
_check_plugin_live_host_stale_issue = check_plugin_live_host_stale_issue
_check_plugin_socket_candidate_mismatch_issue = check_plugin_socket_candidate_mismatch_issue
_check_plugin_version_mismatch_issue = check_plugin_version_mismatch_issue
_check_plugin_build_mismatch_issue = check_plugin_build_mismatch_issue
_check_plugin_not_connected_issue = check_plugin_not_connected_issue

_ANSI_YELLOW = "\033[33m"
_ANSI_RESET = "\033[0m"


def _supports_color() -> bool:
    return (
        os.environ.get("NO_COLOR") is None
        and hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
    )


def _yellow(text: str, *, enabled: bool) -> str:
    return f"{_ANSI_YELLOW}{text}{_ANSI_RESET}" if enabled else text


@dataclass
class InstallManagerReport:
    ok: bool
    source_root: str
    package_version: str | None
    source_version: str | None
    python: str
    path_koru: str | None
    repo_koru: str | None
    socket: str
    daemon: dict[str, Any]
    plugin: dict[str, Any]
    ides: list[dict[str, Any]]
    issues: list[ManagerIssue] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source_root": self.source_root,
            "package_version": self.package_version,
            "source_version": self.source_version,
            "python": self.python,
            "path_koru": self.path_koru,
            "repo_koru": self.repo_koru,
            "socket": self.socket,
            "daemon": self.daemon,
            "plugin": self.plugin,
            "ides": self.ides,
            "issues": [issue.to_dict() for issue in self.issues],
            "actions": self.actions,
        }


def _source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _source_version(root: Path) -> str | None:
    try:
        raw = (root / "pyproject.toml").read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
        version = data.get("project", {}).get("version")
        return str(version) if version else None
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _package_version() -> str | None:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return None


def _repo_koru_bin(root: Path) -> Path | None:
    candidates = [
        root / ".venv" / "bin" / "koru",
        root / "venv" / "bin" / "koru",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _path_koru_bin() -> Path | None:
    resolved = shutil.which("koru")
    return Path(resolved).resolve() if resolved else None


def _installed_editable_source_root() -> Path | None:
    try:
        dist = importlib.metadata.distribution("koru")
        raw = dist.read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    dir_info = data.get("dir_info") if isinstance(data, dict) else None
    if not isinstance(dir_info, dict) or not dir_info.get("editable"):
        return None
    url = str(data.get("url") or "")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "file":
        return None
    return Path(urllib.parse.unquote(parsed.path)).resolve()


def _expected_plugin_version(root: Path, ide_id: str | None = None) -> str | None:
    """Resolve the expected VSIX version for ``ide_id``.

    Cursor uses its dedicated ``plugins/koru-autopilot-cursor`` build;
    sibling IDEs share the umbrella VS Code-family VSIX. Falls back to
    the static ``EXPECTED_PLUGIN_VERSIONS`` table when no live
    ``package.json`` is available.
    """

    from koruide.plugin_installer import plugin_dir_names_for_ide

    for dir_name in plugin_dir_names_for_ide(ide_id):
        package_json = root / "plugins" / dir_name / "package.json"
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        version = data.get("version")
        if version:
            return str(version)
    from koruide.plugin_version import expected_plugin_version_for_ide

    return expected_plugin_version_for_ide(ide_id) or EXPECTED_VSCODE_PLUGIN_VERSION


def _expected_plugin_build_sha(root: Path, ide_id: str | None = None) -> str | None:
    from koruide.plugin_installer import plugin_dir_names_for_ide

    for dir_name in plugin_dir_names_for_ide(ide_id):
        package_json = root / "plugins" / dir_name / "package.json"
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        build = data.get("koruAutopilotBuild")
        if isinstance(build, dict) and isinstance(build.get("sha"), str):
            return build["sha"]
    return None


def _resolve_ide(raw: str) -> str:
    requested = normalize_ide_id(raw) or "auto"
    if requested != "auto":
        return requested
    env_ide = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_IDE"))
    if env_ide:
        return env_ide
    instance_ide = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_INSTANCE"))
    if instance_ide:
        return instance_ide
    terminal = detect_terminal_host_ide_id()
    if terminal:
        return terminal
    detected = detect_running_ides()
    return detected[0].id if detected else "auto"


def _manager_socket_path(ide: str, socket_path: Path | None) -> Path:
    if socket_path is not None:
        return socket_path
    if (
        ide != "auto"
        and not (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
        and not (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    ):
        previous_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
        try:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = ide
            return default_socket_path()
        finally:
            if previous_instance is None:
                os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
            else:
                os.environ["KORU_AUTOPILOT_INSTANCE"] = previous_instance
    return default_socket_path()


def _daemon_status(socket_path: Path) -> dict[str, Any]:
    client = AutopilotClient(socket_path=socket_path, timeout=1.5)
    if not client.is_running():
        return {"running": False}
    try:
        status = client.status()
    except (OSError, RuntimeError) as exc:
        return {"running": False, "error": str(exc)}
    status["running"] = bool(status.get("ok", True))
    return status


def _plugin_for_ide(status: dict[str, Any], ide: str) -> dict[str, Any] | None:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return None
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        if ide == "auto" or plugin.get("ide") == ide:
            return plugin
    return None


def _issue_list(
    *,
    source_version: str | None,
    package_version: str | None,
    source_root: Path,
    path_koru: Path | None,
    repo_koru: Path | None,
    daemon: dict[str, Any],
    plugin: dict[str, Any],
    ide: str,
    socket_path: Path,
) -> list[ManagerIssue]:
    issues: list[ManagerIssue] = []
    issues.extend(
        _check_koru_path_issues(
            path_koru,
            repo_koru,
            source_root=source_root,
            editable_source_root=_installed_editable_source_root(),
        )
    )
    issues.extend(_check_pyenv_shim_issue(path_koru))
    issues.extend(_check_version_mismatch_issue(source_version, package_version))
    issues.extend(_check_daemon_issues(daemon))
    if ide != "auto":
        if not supports_vscode_extension_plugin(ide):
            return issues
    issues.extend(_check_plugin_version_missing_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_build_missing_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_installed_version_mismatch_issue(plugin, ide))
    issues.extend(_check_plugin_live_host_stale_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_socket_candidate_mismatch_issue(daemon, plugin, ide, socket_path))
    issues.extend(_check_plugin_installed_ok_but_not_connected_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_version_mismatch_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_build_mismatch_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_not_connected_issue(daemon, plugin, ide))
    return issues


def _build_plugin_info_dict(
    root: Path,
    resolved_ide: str,
    daemon: dict[str, Any],
) -> dict[str, Any]:
    connected_plugin = _plugin_for_ide(daemon, resolved_ide) if daemon.get("running") else None
    plugin_supported = resolved_ide == "auto" or supports_vscode_extension_plugin(resolved_ide)
    expected_plugin = _expected_plugin_version(root, resolved_ide) if plugin_supported else None
    expected_build = _expected_plugin_build_sha(root, resolved_ide) if plugin_supported else None
    installed_plugin = (
        installed_extension_version_for_ide(resolved_ide) if plugin_supported else None
    )
    plugin = {
        "ide": resolved_ide,
        "supported": plugin_supported,
        "connected": connected_plugin is not None,
        "connected_version": connected_plugin.get("version") if connected_plugin else None,
        "connected_build_sha": connected_plugin.get("buildSha") if connected_plugin else None,
        "installed_version": installed_plugin,
        "expected_version": expected_plugin,
        "expected_build_sha": expected_build,
    }
    if connected_plugin:
        plugin["fd"] = connected_plugin.get("fd")
        plugin["workspace_folders"] = connected_plugin.get("workspaceFolders")
    return plugin


def _resolve_install_environment(
    root: Path,
) -> tuple[Path | None, Path | None, str | None, str | None]:
    path_koru = _path_koru_bin()
    repo_koru = _repo_koru_bin(root)
    source_version = _source_version(root)
    package_version = _package_version()
    return path_koru, repo_koru, source_version, package_version


def collect_install_manager_report(
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
) -> InstallManagerReport:
    root = _source_root()
    resolved_ide = _resolve_ide(ide)
    sock = _manager_socket_path(resolved_ide, socket_path)
    daemon = _daemon_status(sock)
    plugin = _build_plugin_info_dict(root, resolved_ide, daemon)
    path_koru, repo_koru, source_version, package_version = _resolve_install_environment(root)
    ides = [ide_obj.to_dict() for ide_obj in detect_running_ides()]
    issues = _issue_list(
        source_version=source_version,
        package_version=package_version,
        source_root=root,
        path_koru=path_koru,
        repo_koru=repo_koru,
        daemon=daemon,
        plugin=plugin,
        ide=resolved_ide,
        socket_path=sock,
    )
    return InstallManagerReport(
        ok=not any(issue.severity == "error" for issue in issues),
        source_root=str(root),
        package_version=package_version,
        source_version=source_version,
        python=sys.executable,
        path_koru=str(path_koru) if path_koru else None,
        repo_koru=str(repo_koru) if repo_koru else None,
        socket=str(sock),
        daemon=daemon,
        plugin=plugin,
        ides=ides,
        issues=issues,
    )


def repair_installation(
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
    dry_run: bool = False,
) -> InstallManagerReport:
    report = collect_install_manager_report(ide=ide, socket_path=socket_path)
    resolved_ide = str(report.plugin.get("ide") or ide)

    if unsupported_action := _unsupported_plugin_repair_action(report.plugin, resolved_ide):
        report.actions = [unsupported_action]
        return report

    actions = [
        action
        for action in (
            {
                "action": "install_plugin",
                "result": install_plugin_for_ide(
                    ide=resolved_ide,
                    dry_run=dry_run,
                    socket_path=Path(report.socket),
                ).to_dict(),
            },
            _shutdown_daemon_for_plugin_repair_action(report, dry_run=dry_run),
            _reload_ide_reconnect_action(report, resolved_ide, dry_run=dry_run),
        )
        if action is not None
    ]

    return _repair_report_with_actions(
        report,
        actions,
        resolved_ide=resolved_ide,
        dry_run=dry_run,
    )


def _unsupported_plugin_repair_action(
    plugin: dict[str, Any],
    resolved_ide: str,
) -> dict[str, Any] | None:
    if plugin.get("supported") is not False:
        return None
    return {
        "action": "install_plugin",
        "result": {
            "status": "skipped",
            "message": f"ide={resolved_ide} does not use the VS Code-family plugin",
        },
    }


def _plugin_already_aligned(plugin: dict[str, Any]) -> bool:
    live_version = str(plugin.get("connected_version") or "").strip()
    installed_version = str(plugin.get("installed_version") or "").strip()
    live_build = str(plugin.get("connected_build_sha") or "").strip()
    expected_build = str(plugin.get("expected_build_sha") or "").strip()
    build_aligned = not expected_build or (live_build and live_build == expected_build)
    return bool(live_version and installed_version and live_version == installed_version and build_aligned)


def _shutdown_daemon_for_plugin_repair_action(
    report: InstallManagerReport,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if _plugin_already_aligned(report.plugin):
        return _skipped_shutdown_daemon_action()
    if not report.daemon.get("running") or dry_run:
        return None
    return {"action": "shutdown_daemon_for_reload", "result": _shutdown_autopilot_daemon(report.socket)}


def _skipped_shutdown_daemon_action() -> dict[str, Any]:
    return {
        "action": "shutdown_daemon_for_reload",
        "result": {
            "ok": True,
            "skipped": True,
            "message": "daemon kept running: live plugin version already matches installed VSIX",
        },
    }


def _shutdown_autopilot_daemon(socket: str) -> dict[str, Any]:
    try:
        return AutopilotClient(socket_path=Path(socket), timeout=1.5).shutdown()
    except (OSError, RuntimeError) as exc:
        return {"ok": False, "message": str(exc)}


def _reload_ide_reconnect_action(
    report: InstallManagerReport,
    resolved_ide: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "action": "reload_ide_and_reconnect",
        "result": _reload_ide_after_plugin_fix(
            resolved_ide,
            source_root=Path(report.source_root),
            daemon=report.daemon,
            dry_run=dry_run,
        ),
    }


def _repair_report_with_actions(
    report: InstallManagerReport,
    actions: list[dict[str, Any]],
    *,
    resolved_ide: str,
    dry_run: bool,
) -> InstallManagerReport:
    if not dry_run:
        refreshed = collect_install_manager_report(ide=resolved_ide, socket_path=Path(report.socket))
        refreshed.actions = actions
        return refreshed
    report.actions = actions
    return report


def _reload_ide_after_plugin_fix(
    ide: str,
    *,
    source_root: Path,
    daemon: dict[str, Any] | None = None,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "manual",
            "message": (
                "Reload the IDE window, then run `koru: Connect autopilot daemon` "
                "so the live extension matches the installed VSIX."
            ),
        }
    try:
        from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

        snapshot = _temporary_reuse_window_reload_if_same_workspace(
            daemon,
            ide,
            source_root,
        )
        try:
            reload = try_reload_vscode_family_ide(ide, project=source_root)
        finally:
            _restore_reuse_window_reload(snapshot)
    except Exception as exc:  # pragma: no cover - defensive around GUI adapters
        return {
            "status": "manual",
            "ok": False,
            "message": (
                "Automatic IDE reload failed; run `Developer: Reload Window`, "
                "then `koru: Connect autopilot daemon`."
            ),
            "detail": str(exc),
        }
    if getattr(reload, "attempted", False) and getattr(reload, "ok", False):
        return {
            "status": "automatic",
            "ok": True,
            "method": getattr(reload, "method", None),
            "message": (
                "Requested IDE Reload Window automatically; reconnect the "
                "plugin if it does not reconnect by itself."
            ),
        }
    return {
        "status": "manual",
        "ok": False,
        "method": getattr(reload, "method", None),
        "detail": getattr(reload, "detail", None),
        "message": (
            "Reload the IDE window with `Developer: Reload Window`, then run "
            "`koru: Connect autopilot daemon` so the live extension matches "
            "the installed VSIX."
        ),
    }


def _temporary_reuse_window_reload_if_same_workspace(
    daemon: dict[str, Any] | None,
    ide: str,
    source_root: Path,
) -> tuple[bool, str | None] | None:
    if os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"):
        return None
    if not _daemon_has_plugin_workspace(daemon, ide, source_root):
        return None
    previous = os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD")
    os.environ["KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"] = "1"
    return True, previous


def _restore_reuse_window_reload(snapshot: tuple[bool, str | None] | None) -> None:
    if snapshot is None:
        return
    _changed, previous = snapshot
    if previous is None:
        os.environ.pop("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", None)
    else:
        os.environ["KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"] = previous


def _daemon_has_plugin_workspace(
    daemon: dict[str, Any] | None,
    ide: str,
    source_root: Path,
) -> bool:
    if not isinstance(daemon, dict):
        return False
    plugins = daemon.get("plugins")
    if not isinstance(plugins, list):
        return False
    wanted = ide.strip().lower()
    try:
        source_key = str(source_root.resolve())
    except OSError:
        source_key = str(source_root)
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if wanted not in {"", "auto"} and plugin_ide != wanted:
            continue
        folders = plugin.get("workspaceFolders")
        if not isinstance(folders, list):
            continue
        for folder in folders:
            if not isinstance(folder, str):
                continue
            try:
                if str(Path(folder).resolve()) == source_key:
                    return True
            except OSError:
                continue
    return False


def format_install_manager_report(report: InstallManagerReport) -> str:
    data = report.to_dict()
    color = _supports_color()
    lines = _install_manager_base_lines(data)
    lines.extend(_install_manager_issue_lines(report, color=color))
    lines.extend(_install_manager_action_lines(report))
    return "\n".join(lines)


def _install_manager_base_lines(data: dict[str, Any]) -> list[str]:
    return [
        "koru autopilot manage",
        f"  ok: {str(data['ok']).lower()}",
        f"  source: {data['source_root']} (pyproject={data['source_version']})",
        f"  package: {data['package_version']} via {data['python']}",
        f"  PATH koru: {data['path_koru'] or '-'}",
        f"  repo koru: {data['repo_koru'] or '-'}",
        f"  socket: {data['socket']}",
        f"  daemon: {'running' if data['daemon'].get('running') else 'stopped'}",
        (
            "  plugin: "
            f"ide={data['plugin'].get('ide')} connected={data['plugin'].get('connected')} "
            f"version={data['plugin'].get('connected_version') or '-'} "
            f"build={data['plugin'].get('connected_build_sha') or '-'} "
            f"installed={data['plugin'].get('installed_version') or '-'} "
            f"expected={data['plugin'].get('expected_version') or '-'} "
            f"expected_build={data['plugin'].get('expected_build_sha') or '-'}"
        ),
    ]


def _install_manager_issue_lines(report: InstallManagerReport, *, color: bool) -> list[str]:
    if not report.issues:
        return []
    lines = ["  issues:"]
    for issue in report.issues:
        lines.append(f"    - [{issue.severity}] {issue.code}: {issue.message}")
        if issue.fix:
            lines.append(_yellow(f"      fix: {issue.fix}", enabled=color))
    return lines


def _install_manager_action_lines(report: InstallManagerReport) -> list[str]:
    if not report.actions:
        return []
    lines = ["  actions:"]
    for action in report.actions:
        result = action.get("result", {})
        status = result.get("status") or result.get("ok")
        lines.append(f"    - {action.get('action')}: {status}")
    return lines


__all__ = [
    "InstallManagerReport",
    "ManagerIssue",
    "collect_install_manager_report",
    "format_install_manager_report",
    "repair_installation",
]
