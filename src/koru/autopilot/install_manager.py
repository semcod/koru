"""Installation inventory and repair helpers for autopilot runtime pieces."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import sys
import tomllib
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
from koru.autopilot.plugin_installer import (
    install_plugin_for_ide,
    installed_extension_version_for_ide,
)
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION
from koruide.socket import default_socket_path


@dataclass
class ManagerIssue:
    code: str
    severity: str
    message: str
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {"code": self.code, "severity": self.severity, "message": self.message}
        if self.fix:
            out["fix"] = self.fix
        return out


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


def _is_pyenv_shim(path: Path | None) -> bool:
    return bool(path and ".pyenv" in path.parts and "shims" in path.parts)


def _expected_plugin_version(root: Path) -> str | None:
    package_json = root / "plugins" / "koru-autopilot-vscode" / "package.json"
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return EXPECTED_VSCODE_PLUGIN_VERSION
    version = data.get("version")
    return str(version) if version else None


def _resolve_ide(raw: str) -> str:
    requested = normalize_ide_id(raw) or "auto"
    if requested != "auto":
        return requested
    env_ide = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_IDE"))
    if env_ide:
        return env_ide
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


def _check_koru_path_issues(
    path_koru: Path | None, repo_koru: Path | None
) -> list[ManagerIssue]:
    issues: list[ManagerIssue] = []
    if path_koru is None:
        issues.append(
            ManagerIssue(
                "koru_not_in_path",
                "error",
                "`koru` is not available in PATH.",
                "Install the package or use the repo-local .venv/bin/koru explicitly.",
            ),
        )
    elif repo_koru is not None and path_koru != repo_koru:
        issues.append(
            ManagerIssue(
                "koru_path_mismatch",
                "warning",
                f"PATH resolves koru to {path_koru}, but repo-local koru is {repo_koru}.",
                (
                    f"Use `{repo_koru}` or put `{repo_koru.parent}` before other "
                    "koru installs in PATH."
                ),
            ),
        )
    return issues


def _check_pyenv_shim_issue(path_koru: Path | None) -> list[ManagerIssue]:
    if _is_pyenv_shim(path_koru):
        return [
            ManagerIssue(
                "koru_pyenv_shim",
                "warning",
                f"PATH resolves koru through a pyenv shim ({path_koru}).",
                (
                    "Run `pyenv which koru` and `pyenv rehash`, or call the intended "
                    "virtualenv binary explicitly while debugging autopilot installs."
                ),
            ),
        ]
    return []


def _check_version_mismatch_issue(
    source_version: str | None, package_version: str | None
) -> list[ManagerIssue]:
    if source_version and package_version and source_version != package_version:
        return [
            ManagerIssue(
                "koru_version_mismatch",
                "warning",
                (
                    f"Imported package version is {package_version}, "
                    f"source pyproject is {source_version}."
                ),
                "Reinstall editable from the source checkout or use the matching virtualenv.",
            ),
        ]
    return []


def _check_daemon_issues(daemon: dict[str, Any]) -> list[ManagerIssue]:
    if not daemon.get("running"):
        return [
            ManagerIssue(
                "daemon_not_running",
                "warning",
                "Autopilot daemon is not running for this socket.",
                "Start it with `koru autopilot daemon` or let `koru autonomous up` start it.",
            ),
        ]
    return []


def _check_plugin_version_missing_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    if daemon.get("running") and plugin.get("connected") and not plugin.get("connected_version"):
        return [
            ManagerIssue(
                "plugin_version_missing",
                "warning",
                f"Connected {ide} plugin did not report a version.",
                (
                    "Reload the IDE window after installing the current VSIX, "
                    "then reconnect autopilot."
                ),
            ),
        ]
    return []


def _check_plugin_installed_version_mismatch_issue(
    plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    installed_version = plugin.get("installed_version")
    expected_version = plugin.get("expected_version")
    if installed_version and expected_version and installed_version != expected_version:
        return [
            ManagerIssue(
                "plugin_installed_version_mismatch",
                "error",
                (
                    f"Installed {ide} extension is {installed_version}, "
                    f"but the source VSIX/package is {expected_version}."
                ),
                f"Run `koru autopilot manage --ide {ide} --fix`.",
            ),
        ]
    return []


def _check_plugin_installed_ok_but_not_connected_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    if plugin.get("connected"):
        return []
    installed_version = plugin.get("installed_version")
    expected_version = plugin.get("expected_version")
    installed_matches_expected = (
        bool(installed_version) and bool(expected_version) and installed_version == expected_version
    )
    if not installed_matches_expected:
        return []
    fix = (
        f"Start the daemon with `KORU_AUTOPILOT_INSTANCE={ide} koru autopilot daemon`, "
        "reload the IDE window, then run `koru: Connect autopilot daemon`."
    )
    if not daemon.get("running"):
        fix = (
            "Let `koru autonomous up` start the daemon, or start it manually with "
            f"`KORU_AUTOPILOT_INSTANCE={ide} koru autopilot daemon`; then reload the IDE "
            "window and run `koru: Connect autopilot daemon`."
        )
    return [
        ManagerIssue(
            "plugin_installed_ok_but_not_connected",
            "info",
            (
                f"{ide} extension is installed at the expected version "
                f"({installed_version}), but no live plugin is connected to this daemon."
            ),
            fix,
        ),
    ]


def _check_plugin_live_host_stale_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    installed_version = plugin.get("installed_version")
    expected_version = plugin.get("expected_version")
    if not daemon.get("running") or not installed_version or installed_version != expected_version:
        return []
    rejected = [
        row
        for row in daemon.get("rejected_plugins", [])
        if isinstance(row, dict)
        and row.get("ide") == ide
        and row.get("version")
        and row.get("version") != expected_version
    ]
    if not rejected:
        return []
    seen_versions = sorted({str(row.get("version")) for row in rejected if row.get("version")})
    versions = ", ".join(seen_versions)
    return [
        ManagerIssue(
            "plugin_live_host_stale",
            "error",
            (
                f"{ide} extension is installed at {installed_version}, but the live IDE "
                f"extension host is still reconnecting with stale version(s): {versions}."
            ),
            (
                "Reload the IDE window with `Developer: Reload Window`, then run "
                "`koru: Connect autopilot daemon`. If stale reconnects continue, fully "
                "close that IDE window and open the project again."
            ),
        ),
    ]


def _plugin_debug_log_path() -> Path:
    return Path(os.environ.get("KORU_PLUGIN_DEBUG_LOG", "/tmp/koru-plugin-debug.log"))


def _recent_socket_candidate_mismatch(
    ide: str,
    expected_socket: Path,
) -> dict[str, Any] | None:
    try:
        lines = _plugin_debug_log_path().read_text(encoding="utf-8").splitlines()[-200:]
    except OSError:
        return None

    expected = str(expected_socket)
    for line in reversed(lines):
        if "CONNECT_CANDIDATES" not in line:
            continue
        _, _, payload = line.partition("CONNECT_CANDIDATES")
        try:
            data = json.loads(payload.strip())
        except json.JSONDecodeError:
            continue
        if data.get("ide") != ide:
            continue
        candidates = [str(item) for item in data.get("candidates", []) if isinstance(item, str)]
        override = str(data.get("override") or "")
        if expected not in candidates:
            return {"override": override, "candidates": candidates}
    return None


def _check_plugin_socket_candidate_mismatch_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str, socket_path: Path
) -> list[ManagerIssue]:
    if not daemon.get("running") or plugin.get("connected"):
        return []
    installed_version = plugin.get("installed_version")
    expected_version = plugin.get("expected_version")
    if not installed_version or installed_version != expected_version:
        return []

    mismatch = _recent_socket_candidate_mismatch(ide, socket_path)
    if not mismatch:
        return []

    candidates = ", ".join(mismatch["candidates"]) or "<empty>"
    override = mismatch["override"] or "<unset>"
    return [
        ManagerIssue(
            "plugin_socket_candidate_mismatch",
            "error",
            (
                f"{ide} extension is installed at {installed_version}, but the live "
                f"extension host is probing socket candidate(s) {candidates} instead "
                f"of {socket_path} (override={override})."
            ),
            (
                "Reload the IDE window with `Developer: Reload Window` or run "
                "`Developer: Restart Extension Host`, then run "
                "`koru: Connect autopilot daemon`."
            ),
        ),
    ]


def _check_plugin_version_mismatch_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    connected_version = plugin.get("connected_version")
    expected_version = plugin.get("expected_version")
    if (
        daemon.get("running")
        and plugin.get("connected")
        and connected_version
        and expected_version
        and connected_version != expected_version
    ):
        return [
            ManagerIssue(
                "plugin_version_mismatch",
                "error",
                (
                    f"Connected {ide} plugin is {connected_version}, "
                    f"but the source VSIX/package is {expected_version}."
                ),
                (
                    f"Run `koru autopilot manage --ide {ide} --fix`, fully reload the IDE "
                    "window, then run `koru: Connect autopilot daemon`."
                ),
            ),
        ]
    return []


def _check_plugin_not_connected_issue(
    daemon: dict[str, Any], plugin: dict[str, Any], ide: str
) -> list[ManagerIssue]:
    if daemon.get("running") and not plugin.get("connected"):
        return [
            ManagerIssue(
                "plugin_not_connected",
                "error",
                f"Autopilot daemon is running, but no plugin is connected for ide={ide}.",
                "Run the IDE command `koru: Connect autopilot daemon`.",
            ),
        ]
    return []


def _issue_list(
    *,
    source_version: str | None,
    package_version: str | None,
    path_koru: Path | None,
    repo_koru: Path | None,
    daemon: dict[str, Any],
    plugin: dict[str, Any],
    ide: str,
    socket_path: Path,
) -> list[ManagerIssue]:
    issues: list[ManagerIssue] = []
    issues.extend(_check_koru_path_issues(path_koru, repo_koru))
    issues.extend(_check_pyenv_shim_issue(path_koru))
    issues.extend(_check_version_mismatch_issue(source_version, package_version))
    issues.extend(_check_daemon_issues(daemon))
    if ide != "auto" and not supports_vscode_extension_plugin(ide):
        return issues
    issues.extend(_check_plugin_version_missing_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_installed_version_mismatch_issue(plugin, ide))
    issues.extend(_check_plugin_live_host_stale_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_socket_candidate_mismatch_issue(daemon, plugin, ide, socket_path))
    issues.extend(_check_plugin_installed_ok_but_not_connected_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_version_mismatch_issue(daemon, plugin, ide))
    issues.extend(_check_plugin_not_connected_issue(daemon, plugin, ide))
    return issues


def collect_install_manager_report(
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
) -> InstallManagerReport:
    root = _source_root()
    resolved_ide = _resolve_ide(ide)
    sock = _manager_socket_path(resolved_ide, socket_path)
    daemon = _daemon_status(sock)
    connected_plugin = _plugin_for_ide(daemon, resolved_ide) if daemon.get("running") else None
    plugin_supported = resolved_ide == "auto" or supports_vscode_extension_plugin(resolved_ide)
    expected_plugin = _expected_plugin_version(root) if plugin_supported else None
    installed_plugin = (
        installed_extension_version_for_ide(resolved_ide) if plugin_supported else None
    )
    plugin = {
        "ide": resolved_ide,
        "supported": plugin_supported,
        "connected": connected_plugin is not None,
        "connected_version": connected_plugin.get("version") if connected_plugin else None,
        "installed_version": installed_plugin,
        "expected_version": expected_plugin,
    }
    if connected_plugin:
        plugin["fd"] = connected_plugin.get("fd")
    path_koru = _path_koru_bin()
    repo_koru = _repo_koru_bin(root)
    source_version = _source_version(root)
    package_version = _package_version()
    ides = [ide_obj.to_dict() for ide_obj in detect_running_ides()]
    issues = _issue_list(
        source_version=source_version,
        package_version=package_version,
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
    actions: list[dict[str, Any]] = []
    if report.plugin.get("supported") is False:
        actions.append(
            {
                "action": "install_plugin",
                "result": {
                    "status": "skipped",
                    "message": f"ide={resolved_ide} does not use the VS Code-family plugin",
                },
            }
        )
        report.actions = actions
        return report
    plugin_result = install_plugin_for_ide(
        ide=resolved_ide,
        dry_run=dry_run,
        socket_path=Path(report.socket),
    )
    actions.append({"action": "install_plugin", "result": plugin_result.to_dict()})
    if report.daemon.get("running") and not dry_run:
        try:
            shutdown = AutopilotClient(socket_path=Path(report.socket), timeout=1.5).shutdown()
        except (OSError, RuntimeError) as exc:
            shutdown = {"ok": False, "message": str(exc)}
        actions.append({"action": "shutdown_daemon_for_reload", "result": shutdown})
    actions.append(
        {
            "action": "reload_ide_and_reconnect",
            "result": {
                "status": "manual",
                "message": (
                    "Reload the IDE window, then run `koru: Connect autopilot daemon` "
                    "so the live extension matches the installed VSIX."
                ),
            },
        },
    )
    report.actions = actions
    return report


def format_install_manager_report(report: InstallManagerReport) -> str:
    data = report.to_dict()
    lines = [
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
            f"installed={data['plugin'].get('installed_version') or '-'} "
            f"expected={data['plugin'].get('expected_version') or '-'}"
        ),
    ]
    if report.issues:
        lines.append("  issues:")
        for issue in report.issues:
            lines.append(f"    - [{issue.severity}] {issue.code}: {issue.message}")
            if issue.fix:
                lines.append(f"      fix: {issue.fix}")
    if report.actions:
        lines.append("  actions:")
        for action in report.actions:
            result = action.get("result", {})
            status = result.get("status") or result.get("ok")
            lines.append(f"    - {action.get('action')}: {status}")
    return "\n".join(lines)


__all__ = [
    "InstallManagerReport",
    "ManagerIssue",
    "collect_install_manager_report",
    "format_install_manager_report",
    "repair_installation",
]
