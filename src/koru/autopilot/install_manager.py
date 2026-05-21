"""Installation inventory and repair helpers for autopilot runtime pieces."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autopilot.client import AutopilotClient
from koru.autopilot.ide import detect_running_ides, detect_terminal_host_ide_id
from koru.autopilot.plugin_installer import install_plugin_for_ide
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


def _expected_plugin_version(root: Path) -> str | None:
    package_json = root / "plugins" / "koru-autopilot-vscode" / "package.json"
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = data.get("version")
    return str(version) if version else None


def _resolve_ide(raw: str) -> str:
    requested = (raw or "auto").strip().lower()
    if requested != "auto":
        return "jetbrains" if requested == "pycharm" else requested
    env_ide = (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip().lower()
    if env_ide:
        return "jetbrains" if env_ide == "pycharm" else env_ide
    terminal = detect_terminal_host_ide_id()
    if terminal:
        return terminal
    detected = detect_running_ides()
    return detected[0].id if detected else "auto"


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
    path_koru: Path | None,
    repo_koru: Path | None,
    daemon: dict[str, Any],
    plugin: dict[str, Any],
    ide: str,
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
                f"Use `{repo_koru}` or put `{repo_koru.parent}` before other koru installs in PATH.",
            ),
        )
    if source_version and package_version and source_version != package_version:
        issues.append(
            ManagerIssue(
                "koru_version_mismatch",
                "warning",
                f"Imported package version is {package_version}, source pyproject is {source_version}.",
                "Reinstall editable from the source checkout or use the matching virtualenv.",
            ),
        )
    if daemon.get("running") and plugin.get("connected") and not plugin.get("version"):
        issues.append(
            ManagerIssue(
                "plugin_version_missing",
                "warning",
                f"Connected {ide} plugin did not report a version.",
                "Reload the IDE window after installing the current VSIX, then reconnect autopilot.",
            ),
        )
    if daemon.get("running") and not plugin.get("connected"):
        issues.append(
            ManagerIssue(
                "plugin_not_connected",
                "error",
                f"Autopilot daemon is running, but no plugin is connected for ide={ide}.",
                "Run the IDE command `koru: Connect autopilot daemon`.",
            ),
        )
    return issues


def collect_install_manager_report(
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
) -> InstallManagerReport:
    root = _source_root()
    resolved_ide = _resolve_ide(ide)
    sock = socket_path or default_socket_path()
    daemon = _daemon_status(sock)
    connected_plugin = _plugin_for_ide(daemon, resolved_ide) if daemon.get("running") else None
    expected_plugin = _expected_plugin_version(root)
    plugin = {
        "ide": resolved_ide,
        "connected": connected_plugin is not None,
        "connected_version": connected_plugin.get("version") if connected_plugin else None,
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
