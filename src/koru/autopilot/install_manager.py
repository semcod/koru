"""Installation inventory and repair helpers for autopilot runtime pieces."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import tomllib
import urllib.parse
from contextlib import contextmanager
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
from koru.ide_adapters.ide_reload import new_window_reload_enabled
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
_check_plugin_installed_ok_but_not_connected_issue = (
    check_plugin_installed_ok_but_not_connected_issue
)
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


def _resolve_source_root(project: Path | None = None) -> Path:
    from koru.autonomous_runtime import normalize_project_root

    if project is not None:
        normalized = normalize_project_root(project)
        if normalized is not None:
            return normalized
        return project.expanduser().resolve()
    for candidate in (Path.cwd(), Path(sys.prefix)):
        normalized = normalize_project_root(candidate)
        if normalized is not None and (normalized / "pyproject.toml").is_file():
            return normalized
    fallback = normalize_project_root(Path(__file__).resolve().parents[3])
    return fallback if fallback is not None else Path(__file__).resolve().parents[3]


def _source_root() -> Path:
    return _resolve_source_root(None)


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
    project: Path | None = None,
) -> InstallManagerReport:
    # Prefer the simplified helper when no explicit project is provided so
    # tests and callers can monkeypatch `_source_root` for deterministic
    # behavior. If `project` is given, resolve it directly.
    root = _resolve_source_root(project) if project is not None else _source_root()
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
    project: Path | None = None,
    dry_run: bool = False,
) -> InstallManagerReport:
    # Call the collector using the historical public signature (ide, socket_path)
    # so tests that monkeypatch a lambda accepting only those args continue
    # to work. The `project` arg remains accepted by the collector itself.
    report = collect_install_manager_report(ide=ide, socket_path=socket_path)
    resolved_ide = str(report.plugin.get("ide") or ide)
    repair_steps = _build_repair_steps(report, resolved_ide=resolved_ide, dry_run=dry_run)
    return _apply_repair_steps(
        report,
        repair_steps,
        resolved_ide=resolved_ide,
        dry_run=dry_run,
    )


def _build_repair_steps(
    report: InstallManagerReport,
    *,
    resolved_ide: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if unsupported_step := _unsupported_plugin_repair_step(report.plugin, resolved_ide):
        return [unsupported_step]

    if mismatch_step := _plugin_workspace_mismatch_repair_step(report, resolved_ide):
        return [mismatch_step]

    steps = [
        step
        for step in (
            {
                "action": "install_plugin",
                "result": _install_plugin_repair_result(
                    report,
                    resolved_ide=resolved_ide,
                    dry_run=dry_run,
                ),
            },
            _shutdown_daemon_for_plugin_repair_action(report, dry_run=dry_run),
            _start_daemon_for_plugin_repair_action(report, resolved_ide, dry_run=dry_run),
            _reload_ide_reconnect_action(report, resolved_ide, dry_run=dry_run),
            _wait_for_plugin_reconnect_action(report, resolved_ide, dry_run=dry_run),
        )
        if step is not None
    ]
    steps.extend(
        _build_plugin_build_mismatch_escalation_steps(
            report,
            steps,
            resolved_ide=resolved_ide,
            dry_run=dry_run,
        )
    )
    return steps


def _build_plugin_build_mismatch_escalation_steps(
    report: InstallManagerReport,
    steps: list[dict[str, Any]],
    *,
    resolved_ide: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    wait_result = _latest_action_result(steps, "wait_for_plugin_reconnect")
    if wait_result.get("status") != "build_mismatch":
        return []
    if dry_run:
        return [
            {
                "action": "open_new_ide_window_for_plugin_build",
                "result": {
                    "status": "dry_run",
                    "message": (
                        "would open a fresh IDE window when "
                        "KORU_AUTOPILOT_NEW_WINDOW_RELOAD=1"
                    ),
                },
            }
        ]
    if not new_window_reload_enabled() and not _restart_ide_on_build_mismatch_enabled():
        return [
            {
                "action": "open_new_ide_window_for_plugin_build",
                "result": {
                    "status": "skipped",
                    "ok": False,
                    "message": (
                        "connected plugin still reports an old build; set "
                        "KORU_AUTOPILOT_NEW_WINDOW_RELOAD=1 to open a fresh "
                        "IDE window and start a new extension host"
                    ),
                },
            }
        ]
    escalation_steps: list[dict[str, Any]] = []
    if new_window_reload_enabled():
        escalation_steps.append(
            _open_new_ide_window_for_plugin_build_action(
                report,
                resolved_ide=resolved_ide,
                dry_run=dry_run,
            )
        )
        if wait_step := _wait_for_plugin_reconnect_action(
            report,
            resolved_ide,
            dry_run=dry_run,
        ):
            escalation_steps.append(wait_step)
    if (
        _restart_ide_on_build_mismatch_enabled()
        and _latest_action_result([*steps, *escalation_steps], "wait_for_plugin_reconnect").get(
            "status"
        )
        == "build_mismatch"
    ):
        escalation_steps.append(
            _restart_ide_for_plugin_build_action(
                report,
                resolved_ide=resolved_ide,
                dry_run=dry_run,
            )
        )
        if wait_step := _wait_for_plugin_reconnect_action(
            report,
            resolved_ide,
            dry_run=dry_run,
        ):
            escalation_steps.append(wait_step)
    return escalation_steps


def _latest_action_result(
    steps: list[dict[str, Any]],
    action: str,
) -> dict[str, Any]:
    for step in reversed(steps):
        if step.get("action") != action:
            continue
        result = step.get("result")
        return result if isinstance(result, dict) else {}
    return {}


def _restart_ide_on_build_mismatch_enabled() -> bool:
    raw = os.environ.get(
        "KORU_AUTOPILOT_RESTART_IDE_ON_PLUGIN_BUILD_MISMATCH",
        "",
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _unsupported_plugin_repair_step(
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


@contextmanager
def _force_reassert_install_when(enabled: bool):
    previous = os.environ.get("KORU_AUTOPILOT_FORCE_REASSERT_INSTALL")
    if enabled:
        os.environ["KORU_AUTOPILOT_FORCE_REASSERT_INSTALL"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("KORU_AUTOPILOT_FORCE_REASSERT_INSTALL", None)
        else:
            os.environ["KORU_AUTOPILOT_FORCE_REASSERT_INSTALL"] = previous


def _plugin_connected_build_stale(plugin: dict[str, Any]) -> bool:
    live_build = str(plugin.get("connected_build_sha") or "").strip()
    expected_build = str(plugin.get("expected_build_sha") or "").strip()
    return bool(live_build and expected_build and live_build != expected_build)


def _install_plugin_repair_result(
    report: InstallManagerReport,
    *,
    resolved_ide: str,
    dry_run: bool,
) -> dict[str, Any]:
    if _plugin_already_aligned(report.plugin):
        return {
            "status": "already_installed",
            "ok": True,
            "skipped": True,
            "message": "live plugin already matches expected version/build",
        }
    force_reassert = _plugin_connected_build_stale(report.plugin)
    with _force_reassert_install_when(force_reassert):
        result = install_plugin_for_ide(
            ide=resolved_ide,
            dry_run=dry_run,
            socket_path=Path(report.socket),
        ).to_dict()
    if force_reassert:
        result["forced_reassert"] = True
        result["reassert_reason"] = "connected_plugin_build_mismatch"
    return result


def _versions_aligned(
    live_version: str,
    installed_version: str,
    expected_version: str,
    live_build: str,
    expected_build: str,
) -> bool:
    """Return True when all provided version/build fields are consistent."""
    build_aligned = not expected_build or (live_build and live_build == expected_build)
    if live_version and expected_version and live_version == expected_version and build_aligned:
        if not installed_version or installed_version == live_version:
            return True
    return bool(
        live_version
        and installed_version
        and live_version == installed_version
        and build_aligned
    )


def _plugin_already_aligned(plugin: dict[str, Any]) -> bool:
    if not plugin.get("connected"):
        return False
    return _versions_aligned(
        str(plugin.get("connected_version") or "").strip(),
        str(plugin.get("installed_version") or "").strip(),
        str(plugin.get("expected_version") or "").strip(),
        str(plugin.get("connected_build_sha") or "").strip(),
        str(plugin.get("expected_build_sha") or "").strip(),
    )


def _shutdown_daemon_for_plugin_repair_action(
    report: InstallManagerReport,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if _plugin_already_aligned(report.plugin):
        return _skipped_shutdown_daemon_action()
    if not report.daemon.get("running") or dry_run:
        return None
    return {
        "action": "shutdown_daemon_for_reload",
        "result": _shutdown_autopilot_daemon(report.socket),
    }


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


def _start_daemon_for_plugin_repair_action(
    report: InstallManagerReport,
    resolved_ide: str,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if _plugin_already_aligned(report.plugin):
        return None
    return {
        "action": "start_daemon_for_reconnect",
        "result": _start_autopilot_daemon_for_plugin_repair(
            report,
            resolved_ide,
            dry_run=dry_run,
        ),
    }


def _start_autopilot_daemon_for_plugin_repair(
    report: InstallManagerReport,
    resolved_ide: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "message": "would start idempotent autopilot daemon before plugin reconnect",
        }
    if _daemon_status(Path(report.socket)).get("running"):
        return {"status": "already_running", "ok": True, "socket": report.socket}

    root = Path(report.source_root)
    log_dir = root / ".planfile" / ".koru"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"autopilot-manage-repair-{resolved_ide}.log"
    koru_bin = report.repo_koru or report.path_koru or "koru"
    env = os.environ.copy()
    env["KORU_AUTOPILOT_INSTANCE"] = resolved_ide
    env["KORU_AUTOPILOT_IDE"] = resolved_ide
    env["KORU_AUTOPILOT_SOCKET"] = report.socket
    cmd = [
        str(koru_bin),
        "autopilot",
        "daemon",
        "--idempotent",
        "--project",
        str(root),
    ]
    try:
        with log_path.open("ab") as stream:
            proc = subprocess.Popen(
                cmd,
                cwd=root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except OSError as exc:
        return {"status": "failed", "ok": False, "message": str(exc), "command": cmd}

    deadline = time.monotonic() + 5.0
    running = False
    while time.monotonic() < deadline:
        if _daemon_status(Path(report.socket)).get("running"):
            running = True
            break
        time.sleep(0.2)
    return {
        "status": "started" if running else "starting",
        "ok": running,
        "pid": proc.pid,
        "socket": report.socket,
        "log": str(log_path),
        "command": cmd,
    }


def _reload_ide_reconnect_action(
    report: InstallManagerReport,
    resolved_ide: str,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if _plugin_already_aligned(report.plugin):
        return None
    return {
        "action": "reload_ide_and_reconnect",
        "result": _reload_ide_after_plugin_fix(
            resolved_ide,
            source_root=Path(report.source_root),
            daemon=report.daemon,
            dry_run=dry_run,
        ),
    }


def _wait_for_plugin_reconnect_action(
    report: InstallManagerReport,
    resolved_ide: str,
    *,
    dry_run: bool,
) -> dict[str, Any] | None:
    if _plugin_already_aligned(report.plugin):
        return None
    return {
        "action": "wait_for_plugin_reconnect",
        "result": _wait_for_plugin_reconnect(
            report.socket,
            resolved_ide,
            expected_build=str(report.plugin.get("expected_build_sha") or "") or None,
            dry_run=dry_run,
        ),
    }


def _open_new_ide_window_for_plugin_build_action(
    report: InstallManagerReport,
    *,
    resolved_ide: str,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "action": "open_new_ide_window_for_plugin_build",
        "result": _open_new_ide_window_for_plugin_build(
            resolved_ide,
            source_root=Path(report.source_root),
            dry_run=dry_run,
        ),
    }


def _open_new_ide_window_for_plugin_build(
    ide: str,
    *,
    source_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "message": "would open a fresh IDE window for the updated plugin build",
        }
    try:
        from koru.ide_adapters.ide_reload import try_open_vscode_family_ide_new_window

        outcome = try_open_vscode_family_ide_new_window(ide, project=source_root)
    except Exception as exc:  # pragma: no cover - defensive around GUI adapters
        return {
            "status": "failed",
            "ok": False,
            "message": "failed to open a fresh IDE window for plugin activation",
            "detail": str(exc),
        }
    return {
        "status": "automatic" if outcome.ok else "failed",
        "ok": bool(outcome.ok),
        "attempted": bool(outcome.attempted),
        "method": outcome.method,
        "message": (
            "Opened a fresh IDE window to start a new extension host"
            if outcome.ok
            else "Could not open a fresh IDE window for plugin activation"
        ),
        "detail": outcome.detail,
    }


def _restart_ide_for_plugin_build_action(
    report: InstallManagerReport,
    *,
    resolved_ide: str,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "action": "restart_ide_for_plugin_build",
        "result": _restart_ide_for_plugin_build(
            resolved_ide,
            source_root=Path(report.source_root),
            dry_run=dry_run,
        ),
    }


def _restart_ide_for_plugin_build(
    ide: str,
    *,
    source_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "message": "would restart the IDE so the updated plugin build is loaded",
        }
    running = [entry for entry in detect_running_ides() if entry.id == ide]
    if not running:
        return {
            "status": "failed",
            "ok": False,
            "message": f"no running {ide} process found to restart",
        }
    terminate_results = [_terminate_process(entry.pid) for entry in running]
    if not all(result.get("ok") for result in terminate_results):
        return {
            "status": "failed",
            "ok": False,
            "message": f"could not stop all running {ide} processes",
            "terminated": terminate_results,
        }
    try:
        from koru.ide_adapters.ide_reload import reload_via_new_window

        outcome = reload_via_new_window(ide, source_root)
    except Exception as exc:  # pragma: no cover - defensive around GUI adapters
        return {
            "status": "failed",
            "ok": False,
            "message": f"stopped {ide}, but failed to reopen it",
            "terminated": terminate_results,
            "detail": str(exc),
        }
    return {
        "status": "automatic" if outcome.ok else "failed",
        "ok": bool(outcome.ok),
        "attempted": bool(outcome.attempted),
        "method": outcome.method,
        "message": (
            f"Restarted {ide} to start a fresh extension host"
            if outcome.ok
            else f"Stopped {ide}, but could not reopen the project"
        ),
        "terminated": terminate_results,
        "detail": outcome.detail,
    }


def _terminate_process(pid: int, *, timeout_seconds: float = 8.0) -> dict[str, Any]:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"pid": pid, "ok": True, "status": "already_stopped"}
    except OSError as exc:
        return {"pid": pid, "ok": False, "status": "failed", "message": str(exc)}

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return {"pid": pid, "ok": True, "status": "stopped"}
        time.sleep(0.2)
    return {"pid": pid, "ok": False, "status": "timeout"}


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _timeout_result(
    last_status: dict[str, Any],
    resolved_ide: str,
    socket: str,
    expected_build: str | None,
) -> dict[str, Any]:
    """Build the timeout/failure result dict for _wait_for_plugin_reconnect."""
    last_build = str(last_status.get("_last_plugin_build") or "").strip()
    expected = str(last_status.get("_expected_plugin_build") or expected_build or "").strip()
    status = (
        "build_mismatch"
        if expected and last_build and last_build != expected
        else "not_connected"
    )
    return {
        "status": status,
        "ok": False,
        "ide": resolved_ide,
        "socket": socket,
        "message": (
            "plugin did not reconnect with the expected build after repair; "
            "reload the IDE window and run "
            "`koru: Connect autopilot daemon`"
        ),
        "build": last_build or None,
        "expected_build": expected or None,
        "daemon_running": bool(last_status.get("running")),
    }


def _wait_for_plugin_reconnect(
    socket: str,
    resolved_ide: str,
    *,
    dry_run: bool,
    expected_build: str | None = None,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    if dry_run:
        return {"status": "dry_run", "message": "would wait for plugin reconnect"}
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    last_status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_status = _daemon_status(Path(socket))
        plugin = _plugin_for_ide(last_status, resolved_ide)
        if plugin is not None:
            build = str(plugin.get("buildSha") or "").strip()
            if expected_build and build != expected_build:
                last_status = {
                    **last_status,
                    "_last_plugin_build": build,
                    "_expected_plugin_build": expected_build,
                }
                time.sleep(0.25)
                continue
            return {
                "status": "connected",
                "ok": True,
                "ide": resolved_ide,
                "version": plugin.get("version"),
                "build": build or None,
            }
        time.sleep(0.25)
    return _timeout_result(last_status, resolved_ide, socket, expected_build)


def _apply_repair_steps(
    report: InstallManagerReport,
    repair_steps: list[dict[str, Any]],
    *,
    resolved_ide: str,
    dry_run: bool,
) -> InstallManagerReport:
    if not dry_run:
        refreshed = collect_install_manager_report(
            ide=resolved_ide,
            socket_path=Path(report.socket),
        )
        refreshed.actions = repair_steps
        return refreshed
    report.actions = repair_steps
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
        from koru.ide_adapters.ide_reload import (
            apply_temporary_repair_reload_env,
            detached_reload_enabled,
            restore_reload_env,
            spawn_detached_ide_reload,
            try_reload_vscode_family_ide,
        )
        from koruide.ide import detect_terminal_host_ide_id

        snapshot = apply_temporary_repair_reload_env(
            same_workspace=_daemon_has_plugin_workspace(daemon, ide, source_root),
        )
        try:
            terminal_ide = detect_terminal_host_ide_id()
            if terminal_ide is not None and terminal_ide == ide and detached_reload_enabled():
                reload = spawn_detached_ide_reload(ide, project=source_root)
            else:
                reload = try_reload_vscode_family_ide(ide, project=source_root)
        finally:
            restore_reload_env(snapshot)
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


def _resolved_folder_key(folder: str) -> str:
    try:
        return str(Path(folder).resolve())
    except OSError:
        return folder


def _plugin_workspace_folders(plugin: Any, ide: str) -> list[str]:
    """String workspace folders for ``plugin`` when it targets ``ide``."""
    if not isinstance(plugin, dict):
        return []
    wanted = ide.strip().lower()
    plugin_ide = str(plugin.get("ide") or "").strip().lower()
    if wanted not in {"", "auto"} and plugin_ide != wanted:
        return []
    folders = plugin.get("workspaceFolders")
    if not isinstance(folders, list):
        return []
    return [folder for folder in folders if isinstance(folder, str)]


def _daemon_other_workspace_plugin_folders(
    daemon: dict[str, Any] | None,
    ide: str,
    source_root: Path,
) -> list[str]:
    """Workspace folders of connected ``ide`` plugins that do NOT match ``source_root``.

    Returns the folders reported by plugins bound to a *different* workspace.
    Plugins that match the project, or that report no workspace at all, are
    ignored — so an empty result means "no evidence of a wrong-workspace plugin".
    """
    if not isinstance(daemon, dict):
        return []
    plugins = daemon.get("plugins")
    if not isinstance(plugins, list):
        return []
    source_key = _resolved_folder_key(str(source_root))
    mismatched: list[str] = []
    for plugin in plugins:
        folders = _plugin_workspace_folders(plugin, ide)
        if not folders:
            continue
        if not any(_resolved_folder_key(folder) == source_key for folder in folders):
            mismatched.extend(folders)
    return mismatched


def _plugin_workspace_mismatch_repair_step(
    report: InstallManagerReport,
    resolved_ide: str,
) -> dict[str, Any] | None:
    """Refuse window-opening repair when the only connected plugin for this IDE
    belongs to a different workspace.

    The drive router (:mod:`koruide.plugin_router`) already declines to inject
    into a wrong-workspace window. The repair path is otherwise IDE-only and
    would reload / open / restart windows for whichever ``ide`` window happens
    to be running — disturbing the user's unrelated session. Mirror the router's
    rule here so ``coru`` never spawns or hijacks a window for the wrong project.
    """
    if resolved_ide in ("", "auto"):
        return None
    source_root = Path(report.source_root)
    if _daemon_has_plugin_workspace(report.daemon, resolved_ide, source_root):
        return None
    mismatched = _daemon_other_workspace_plugin_folders(
        report.daemon,
        resolved_ide,
        source_root,
    )
    if not mismatched:
        return None
    shown = ", ".join(dict.fromkeys(mismatched))[:200]
    return {
        "action": "workspace_mismatch",
        "result": {
            "status": "skipped",
            "ok": False,
            "message": (
                f"A {resolved_ide} plugin is connected for a different workspace "
                f"({shown}), not this project ({source_root}). Refusing to reload "
                f"or open {resolved_ide} windows so the open session is left intact. "
                f"Open {source_root} in {resolved_ide}, or run coru from the project "
                f"that is already open, so the autopilot drives the matching window."
            ),
        },
    }


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
        if result.get("skipped"):
            status = "skipped"
        else:
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
