"""Preflight gates for autonomous / coru runs: runtime, daemon, plugin, socket."""

from __future__ import annotations

import os
import shutil
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from koru.autonomous_daemon import daemon_status_compatible
from koru.autonomy.environment import probe_socket_health
from koru.autonomy.heal import remove_stale_socket
from koru.autopilot.lane_context import instance_from_socket_path
from koru.doctor_runtime_checks import (
    _check_python_venv_alignment,
    _installed_koru_version,
    _koru_path_version_issues,
    _read_project_version,
)
from koruide.daemon.metadata import daemon_metadata_path, read_daemon_metadata
from koruide.ide import canonical_autopilot_ide_id, detect_terminal_host_ide_id, normalize_ide_id

Severity = Literal["fail", "warn"]


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    severity: Severity
    message: str
    fix_command: str | None = None


@dataclass(frozen=True)
class ReadinessResult:
    ok: bool
    issues: tuple[ReadinessIssue, ...]
    primary_fix: str | None = None
    repair_actions: tuple[str, ...] = ()

    @property
    def fail_messages(self) -> list[str]:
        return [i.message for i in self.issues if i.severity == "fail"]

    @property
    def warn_messages(self) -> list[str]:
        return [i.message for i in self.issues if i.severity == "warn"]


@dataclass(frozen=True)
class _TerminalLaneContext:
    wanted: str
    lane: str
    terminal: str | None
    terminal_integrated: bool | None
    terminal_kind: str | None


def _project_venv_roots(project: Path) -> list[Path]:
    roots: list[Path] = []
    for name in (".venv", "venv"):
        candidate = project / name
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def _project_venv_python(project: Path) -> Path | None:
    for venv_root in _project_venv_roots(project):
        for python_name in ("python3", "python"):
            candidate = venv_root / "bin" / python_name
            if candidate.is_file():
                return candidate
    return None


def _project_venv_koru(project: Path) -> Path | None:
    for venv_root in _project_venv_roots(project):
        candidate = venv_root / "bin" / "koru"
        if candidate.is_file():
            return candidate
    return None


def _safe_path_for_compare(path: str | Path) -> Path:
    raw = os.fspath(path)
    try:
        return Path(raw).expanduser().resolve()
    except Exception:
        return Path(os.path.abspath(os.path.expanduser(raw)))


def _python_executables_equivalent(left: str | Path, right: str | Path) -> bool:
    left_path = _safe_path_for_compare(left)
    right_path = _safe_path_for_compare(right)
    if left_path == right_path:
        return True
    return (
        left_path.parent == right_path.parent
        and left_path.name in {"python", "python3"}
        and right_path.name in {"python", "python3"}
    )


def _runtime_issue_severity(strict: bool) -> Severity:
    return "fail" if strict else "warn"


def _first_fix_command(issues: list[ReadinessIssue]) -> str | None:
    return next((issue.fix_command for issue in issues if issue.fix_command), None)


def _python_executable_mismatch_issue(
    project: Path,
    launcher: str | Path,
    venv_python: Path | None,
    *,
    strict: bool,
) -> ReadinessIssue | None:
    if venv_python is None:
        return None
    launcher_path = _safe_path_for_compare(launcher)
    venv_path = _safe_path_for_compare(venv_python)
    if launcher_path == venv_path:
        return None
    if (
        launcher_path.parent == venv_path.parent
        and launcher_path.name in {"python", "python3"}
        and venv_path.name in {"python", "python3"}
    ):
        return None
    return ReadinessIssue(
        code="python_executable_mismatch",
        severity=_runtime_issue_severity(strict),
        message=f"active Python {launcher_path} != repo .venv {venv_path}",
        fix_command=(
            f"PATH=\"{project / '.venv' / 'bin'}:$PATH\" "
            f"{project / '.venv' / 'bin' / 'koru'} auto"
        ),
    )


def _venv_alignment_fix(project: Path) -> str | None:
    if not (project / ".venv").exists():
        return None
    return f"source {project / '.venv' / 'bin' / 'activate'} && hash -r"


def _venv_alignment_issue(project: Path, *, strict: bool) -> ReadinessIssue | None:
    status, detail = _check_python_venv_alignment(project)
    if status == "pass":
        return None
    return ReadinessIssue(
        code="venv_alignment",
        severity=_runtime_issue_severity(strict),
        message=detail,
        fix_command=_venv_alignment_fix(project),
    )


def _koru_runtime_identity_issue(
    project_koru: Path | None,
    path_koru: str | None,
    package_version: str | None,
    source_version: str | None,
    *,
    strict: bool,
) -> ReadinessIssue | None:
    if project_koru is None:
        return None
    status, bits = _koru_path_version_issues(
        project_koru,
        path_koru,
        package_version,
        source_version,
    )
    if status == "pass":
        return None
    fix = next((bit.removeprefix("fix=") for bit in bits if bit.startswith("fix=")), None)
    return ReadinessIssue(
        code="koru_runtime_identity",
        severity=_runtime_issue_severity(strict),
        message="; ".join(
            [
                f"package={package_version or '-'}",
                f"pyproject={source_version or '-'}",
                f"path_koru={path_koru or '-'}",
                *bits,
            ]
        ),
        fix_command=fix,
    )


def _editable_install_fix(project: Path) -> str:
    pip = project / ".venv" / "bin" / "pip"
    return f"{pip} install -e {project}" if pip.is_file() else f"pip install -e {project}"


def _package_version_drift_issue(
    project: Path,
    package_version: str | None,
    source_version: str | None,
    *,
    strict: bool,
) -> ReadinessIssue | None:
    if not (package_version and source_version and package_version != source_version):
        return None
    return ReadinessIssue(
        code="koru_package_version_drift",
        severity=_runtime_issue_severity(strict),
        message=f"imported koru {package_version} != pyproject {source_version}",
        fix_command=_editable_install_fix(project),
    )


def _append_issue(
    issues: list[ReadinessIssue],
    issue: ReadinessIssue | None,
) -> None:
    if issue is not None:
        issues.append(issue)


def check_runtime_consistency(
    project: Path,
    *,
    launcher_executable: str | Path | None = None,
    strict: bool = False,
) -> ReadinessResult:
    """Compare Python/koru executables and package version to repo ``.venv``."""
    project = project.resolve()
    issues: list[ReadinessIssue] = []

    venv_python = _project_venv_python(project)
    project_koru = _project_venv_koru(project)
    launcher = Path(launcher_executable or sys.executable)
    package_version = _installed_koru_version()
    source_version = _read_project_version(project / "pyproject.toml")
    path_koru = shutil.which("koru")

    _append_issue(
        issues,
        _python_executable_mismatch_issue(
            project,
            launcher,
            venv_python,
            strict=strict,
        ),
    )
    _append_issue(issues, _venv_alignment_issue(project, strict=strict))
    _append_issue(
        issues,
        _koru_runtime_identity_issue(
            project_koru,
            path_koru,
            package_version,
            source_version,
            strict=strict,
        ),
    )
    _append_issue(
        issues,
        _package_version_drift_issue(
            project,
            package_version,
            source_version,
            strict=strict,
        ),
    )

    ok = not any(i.severity == "fail" for i in issues)
    primary_fix = _first_fix_command(issues)
    return ReadinessResult(ok=ok, issues=tuple(issues), primary_fix=primary_fix)


def _check_daemon_version_issue(status: Mapping[str, Any] | None) -> ReadinessIssue | None:
    compatible, reason = daemon_status_compatible(status)
    if compatible:
        return None
    fix_command = (
        f"KORU_AUTOPILOT_INSTANCE={os.environ.get('KORU_AUTOPILOT_INSTANCE', '')} "
        "koru autopilot shutdown && koru auto"
        if os.environ.get("KORU_AUTOPILOT_INSTANCE")
        else "koru autopilot shutdown && koru auto"
    )
    return ReadinessIssue(
        code="daemon_version_mismatch",
        severity="fail",
        message=reason,
        fix_command=fix_command,
    )


def _check_daemon_meta_project_python_issues(
    status: Mapping[str, Any] | None,
    project: Path,
    socket_path: Path,
) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []
    meta = _effective_daemon_metadata(status, project, socket_path)
    if not meta:
        return issues
    meta_project = str(meta.get("project") or "").strip()
    if meta_project:
        from koru.autonomous_runtime import projects_equivalent

        try:
            if not projects_equivalent(meta_project, project):
                issues.append(
                    ReadinessIssue(
                        code="daemon_project_mismatch",
                        severity="fail",
                        message=(
                            f"daemon metadata project={meta_project} "
                            f"!= {project.resolve()}"
                        ),
                        fix_command="koru autopilot shutdown && koru auto",
                    )
                )
        except OSError:
            pass
    meta_py = str(meta.get("python_executable") or "").strip()
    if meta_py and not _python_executables_equivalent(meta_py, sys.executable):
        issues.append(
            ReadinessIssue(
                code="daemon_python_mismatch",
                severity="warn",
                message=(
                    f"daemon python={meta_py} != "
                    f"client python={sys.executable}"
                ),
                fix_command="koru autopilot shutdown && koru auto",
            )
        )
    return issues


def check_daemon_client_alignment(
    status: Mapping[str, Any] | None,
    *,
    project: Path | None = None,
    socket_path: Path | None = None,
) -> ReadinessResult:
    """Detect daemon version/build drift vs the current koru process."""
    issues: list[ReadinessIssue] = []
    version_issue = _check_daemon_version_issue(status)
    if version_issue is not None:
        issues.append(version_issue)

    if project is not None and socket_path is not None:
        issues.extend(_check_daemon_meta_project_python_issues(status, project, socket_path))

    ok = not any(i.severity == "fail" for i in issues)
    fix = issues[0].fix_command if issues else None
    return ReadinessResult(ok=ok, issues=tuple(issues), primary_fix=fix)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _socket_inode(path: Path) -> int | None:
    try:
        return path.stat().st_ino
    except OSError:
        return None


def _metadata_socket_matches(meta: Mapping[str, Any], socket_path: Path) -> bool:
    raw = str(meta.get("socket") or "").strip()
    if not raw:
        return False
    try:
        return Path(raw).expanduser().resolve() == socket_path.expanduser().resolve()
    except OSError:
        return raw == str(socket_path)


def _status_daemon_metadata(
    status: Mapping[str, Any] | None,
    socket_path: Path,
) -> dict[str, Any] | None:
    if not isinstance(status, Mapping):
        return None
    meta = status.get("daemon_metadata")
    if isinstance(meta, dict) and _metadata_socket_matches(meta, socket_path):
        return meta
    return None


def _effective_daemon_metadata(
    status: Mapping[str, Any] | None,
    project: Path,
    socket_path: Path,
) -> dict[str, Any] | None:
    """Prefer metadata returned by the live daemon status over stale project sidecars."""
    meta = _status_daemon_metadata(status, socket_path)
    if meta is not None:
        return meta
    sidecar = read_daemon_metadata(daemon_metadata_path(None, socket_path))
    if sidecar and _metadata_socket_matches(sidecar, socket_path):
        return sidecar
    return read_daemon_metadata(daemon_metadata_path(project, socket_path))


def _find_project_in_workspace_folders(
    folders: list[Any], project_path: str, connected: list[str]
) -> bool:
    for folder in folders:
        if not isinstance(folder, str):
            continue
        try:
            if str(Path(folder).resolve()) == project_path:
                return True
        except OSError:
            continue
        connected.append(folder)
    return False


def plugin_workspace_covers_project(
    status: Mapping[str, Any] | None,
    autopilot_ide: str,
    project: Path,
) -> tuple[bool, str]:
    """Return whether a connected plugin lists ``project`` in workspaceFolders."""
    if not isinstance(status, dict):
        return False, "daemon status unavailable"
    plugins = status.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return False, "no connected plugin"
    wanted = autopilot_ide.strip().lower()
    project_path = str(project.resolve())
    connected: list[str] = []
    for row in plugins:
        if not isinstance(row, dict):
            continue
        ide = str(row.get("ide") or "").strip().lower()
        if wanted not in {"", "auto"} and ide != wanted:
            continue
        folders = row.get("workspaceFolders")
        if not isinstance(folders, list):
            continue
        if _find_project_in_workspace_folders(folders, project_path, connected):
            return True, ""
    if connected:
        return False, (
            "plugin connected but workspaceFolders do not include project root "
            f"({project_path}); plugin folders={connected!r}"
        )
    return False, "connected plugin has no workspaceFolders"


def _check_socket_health_issues(
    socket_health: Any, socket_path: Path, status_available: bool
) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []
    if socket_health.stale and status_available:
        issues.append(
            ReadinessIssue(
                code="socket_probe_stale_with_status",
                severity="warn",
                message=(
                    f"socket probe reports no listener at {socket_path}, "
                    "but daemon status is available; keeping socket in place"
                ),
            )
        )
    elif socket_health.stale:
        issues.append(
            ReadinessIssue(
                code="socket_stale",
                severity="fail",
                message=f"stale autopilot socket (no listener): {socket_path}",
                fix_command=f"rm -f {socket_path} && koru autopilot shutdown",
            )
        )
    elif socket_health.exists and not socket_health.listening:
        issues.append(
            ReadinessIssue(
                code="socket_not_listening",
                severity="warn",
                message=f"socket exists but is not accepting connections: {socket_path}",
                fix_command=f"rm -f {socket_path}",
            )
        )
    return issues


def _check_daemon_meta_issues(
    meta: dict[str, Any] | None,
    socket_health: Any,
    socket_path: Path,
    meta_path: Path,
) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []
    if not meta:
        return issues
    meta_pid = meta.get("pid")
    if isinstance(meta_pid, int) and socket_health.listening and not _pid_alive(meta_pid):
        issues.append(
            ReadinessIssue(
                code="daemon_pid_dead",
                severity="fail",
                message=f"daemon metadata pid={meta_pid} is not alive",
                fix_command=f"rm -f {socket_path} {meta_path}",
            )
        )
    meta_inode = meta.get("socket_inode")
    live_inode = _socket_inode(socket_path)
    if (
        isinstance(meta_inode, int)
        and live_inode is not None
        and meta_inode != live_inode
    ):
        issues.append(
            ReadinessIssue(
                code="socket_inode_drift",
                severity="fail",
                message=(
                    f"socket inode {live_inode} != metadata inode {meta_inode}"
                ),
                fix_command=f"rm -f {socket_path}",
            )
        )
    return issues


def _check_plugin_workspace_issues(
    status: Mapping[str, Any] | None,
    autopilot_ide: str,
    project: Path,
) -> list[ReadinessIssue]:
    issues: list[ReadinessIssue] = []
    if not isinstance(status, dict) or not status.get("plugins"):
        return issues
    ok_ws, ws_reason = plugin_workspace_covers_project(status, autopilot_ide, project)
    if not ok_ws:
        issues.append(
            ReadinessIssue(
                code="plugin_workspace_mismatch",
                severity="fail",
                message=ws_reason,
                fix_command=(
                    f"open {project} in {autopilot_ide}, then "
                    "'koru: Connect autopilot daemon'"
                ),
            )
        )
    return issues


def check_workspace_socket_ownership(
    project: Path,
    socket_path: Path,
    status: Mapping[str, Any] | None,
    *,
    autopilot_ide: str,
) -> ReadinessResult:
    """Detect stale sockets, dead daemon PIDs, and workspace mismatches."""
    project = project.resolve()
    socket_health = probe_socket_health(socket_path)
    status_available = isinstance(status, Mapping)

    issues: list[ReadinessIssue] = []
    issues.extend(_check_socket_health_issues(socket_health, socket_path, status_available))
    issues.extend(
        _check_daemon_meta_issues(
            _effective_daemon_metadata(status, project, socket_path),
            socket_health,
            socket_path,
            daemon_metadata_path(project, socket_path),
        )
    )
    issues.extend(_check_plugin_workspace_issues(status, autopilot_ide, project))

    ok = not any(i.severity == "fail" for i in issues)
    fix = next((i.fix_command for i in issues if i.fix_command), None)
    return ReadinessResult(ok=ok, issues=tuple(issues), primary_fix=fix)


def apply_socket_ownership_repairs(
    project: Path,
    socket_path: Path,
    readiness: ReadinessResult,
    *,
    dry_run: bool = False,
) -> ReadinessResult:
    """Apply safe repairs for socket ownership issues (unlink stale socket)."""
    actions: list[str] = []
    codes = {i.code for i in readiness.issues}
    if codes.intersection({"socket_stale", "socket_inode_drift", "daemon_pid_dead"}):
        health = probe_socket_health(socket_path)
        if health.stale or "socket_inode_drift" in codes or "daemon_pid_dead" in codes:
            result = remove_stale_socket(health, dry_run=dry_run)
            actions.append(f"{result.action}:{result.status}:{result.detail}")
            meta_path = daemon_metadata_path(project, socket_path)
            if not dry_run and meta_path.is_file():
                try:
                    meta_path.unlink()
                except OSError as exc:
                    actions.append(f"remove_metadata:failed:{exc}")
    return ReadinessResult(
        ok=readiness.ok,
        issues=readiness.issues,
        primary_fix=readiness.primary_fix,
        repair_actions=tuple(actions),
    )


def attempt_plugin_gate_recovery(
    client: Any,
    autopilot_ide: str,
    project: Path,
    *,
    plugin_ok_fn: Callable[[], tuple[bool, str]],
    reload_window: Callable[[], bool],
    wait_connected: Callable[[float], bool],
    attempts: int = 3,
    base_timeout_seconds: float = 12.0,
) -> tuple[bool, str]:
    """Reload IDE + poll plugin status; return post-recovery (ok, reason)."""
    ok, reason = plugin_ok_fn()
    if ok:
        return True, reason
    if run_plugin_reconnect_pipeline(
        reload_window=reload_window,
        wait_connected=wait_connected,
        attempts=attempts,
        base_timeout_seconds=base_timeout_seconds,
    ):
        return plugin_ok_fn()
    return False, reason


def _canonical_target_ide(autopilot_ide: str) -> str:
    return canonical_autopilot_ide_id(normalize_ide_id(autopilot_ide) or autopilot_ide)


def _lane_instance_value(lane_instance: str | None) -> str:
    return (lane_instance or os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()


def _terminal_context(
    terminal_ide: str | None,
    terminal_integrated: bool | None,
    terminal_kind: str | None,
) -> tuple[str | None, bool | None, str | None]:
    if terminal_ide is None:
        terminal_ide = detect_terminal_host_ide_id()
    terminal = normalize_ide_id(terminal_ide)
    ctx_kind = terminal_kind
    if terminal_integrated is None or ctx_kind is None:
        from koruide.ide import detect_terminal_host_context

        ctx = detect_terminal_host_context()
        if terminal_integrated is None:
            terminal_integrated = ctx.integrated
        if ctx_kind is None:
            ctx_kind = ctx.kind
    return terminal, terminal_integrated, ctx_kind


def _terminal_lane_context(
    *,
    autopilot_ide: str,
    lane_instance: str | None,
    terminal_ide: str | None,
    terminal_integrated: bool | None,
    terminal_kind: str | None,
) -> _TerminalLaneContext:
    terminal, integrated, kind = _terminal_context(
        terminal_ide,
        terminal_integrated,
        terminal_kind,
    )
    return _TerminalLaneContext(
        wanted=_canonical_target_ide(autopilot_ide),
        lane=_lane_instance_value(lane_instance),
        terminal=terminal,
        terminal_integrated=integrated,
        terminal_kind=kind,
    )


def _terminal_lane_mismatch_issues(
    ctx: _TerminalLaneContext,
) -> tuple[list[ReadinessIssue], str | None]:
    if not (ctx.wanted and ctx.terminal and ctx.terminal != ctx.wanted):
        return [], None

    from koru.autonomy.ide_operator_guidance import (
        ide_label,
        lane_mismatch_operator_steps,
        terminal_kind_label,
    )

    severity: Severity = "warn"
    kind_label = terminal_kind_label(ctx.terminal_kind) if ctx.terminal_kind else "unknown shell"
    operator_steps = lane_mismatch_operator_steps(
        terminal_ide=ctx.terminal,
        target_ide=ctx.wanted,
        terminal_kind=ctx.terminal_kind or "system",
        lane=ctx.lane or None,
    )
    message = (
        f"terminal host is {ctx.terminal} ({kind_label}), "
        f"but autopilot target is {ide_label(ctx.wanted)}"
        + (f" (lane={ctx.lane})" if ctx.lane else "")
    )
    fix_command = (
        f"run `coru {ctx.wanted} auto` from {ide_label(ctx.wanted)}'s integrated terminal, "
        f"or export KORU_AUTOPILOT_INSTANCE={ctx.wanted}, "
        f"or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1"
    )
    issues = [
        ReadinessIssue(
            code="terminal_lane_mismatch",
            severity=severity,
            message=message,
            fix_command=fix_command,
        )
    ]
    issues.extend(
        ReadinessIssue(
            code="terminal_lane_operator_hint",
            severity="warn",
            message=step,
        )
        for step in operator_steps[:3]
    )
    return issues, fix_command


def _lane_ide_mismatch_issue(ctx: _TerminalLaneContext) -> ReadinessIssue | None:
    if not (ctx.wanted and ctx.lane):
        return None
    lane_ide = canonical_autopilot_ide_id(ctx.lane)
    if not lane_ide or lane_ide == ctx.wanted:
        return None
    return ReadinessIssue(
        code="lane_ide_mismatch",
        severity="fail",
        message=(
            f"lane instance {ctx.lane!r} resolves to ide={lane_ide}, "
            f"but autopilot target is {ctx.wanted}"
        ),
        fix_command=(
            f"export KORU_AUTOPILOT_INSTANCE={ctx.wanted}-main "
            f"and restart koru auto / coru"
        ),
    )


def _socket_lane_mismatch_issue(
    socket_path: Path | None,
    ctx: _TerminalLaneContext,
) -> ReadinessIssue | None:
    if socket_path is None or not ctx.lane:
        return None
    socket_instance = instance_from_socket_path(socket_path) or ""
    if not socket_instance or socket_instance == ctx.lane.strip().lower():
        return None
    return ReadinessIssue(
        code="socket_lane_mismatch",
        severity="fail",
        message=(
            f"socket {socket_path.name} is lane {socket_instance!r}, "
            f"but configured instance is {ctx.lane!r}"
        ),
        fix_command="koru autopilot shutdown && koru auto",
    )
def check_lane_terminal_socket_alignment(
    *,
    autopilot_ide: str,
    lane_instance: str | None,
    socket_path: Path | None,
    terminal_ide: str | None = None,
    terminal_integrated: bool | None = None,
    terminal_kind: str | None = None,
) -> ReadinessResult:
    """Warn when terminal host, lane instance, and socket target diverge."""
    from koru.autonomy.env import allow_cross_ide_autopilot

    if allow_cross_ide_autopilot():
        return ReadinessResult(ok=True, issues=())

    ctx = _terminal_lane_context(
        autopilot_ide=autopilot_ide,
        lane_instance=lane_instance,
        terminal_ide=terminal_ide,
        terminal_integrated=terminal_integrated,
        terminal_kind=terminal_kind,
    )
    issues, primary_fix = _terminal_lane_mismatch_issues(ctx)
    _append_issue(issues, _lane_ide_mismatch_issue(ctx))
    _append_issue(issues, _socket_lane_mismatch_issue(socket_path, ctx))

    ok = not any(i.severity == "fail" for i in issues)
    fix = next((i.fix_command for i in issues if i.fix_command), None)
    return ReadinessResult(ok=ok, issues=tuple(issues), primary_fix=primary_fix or fix)


def check_queue_runner_contention(project: Path) -> ReadinessResult:
    """Detect another process holding the per-project queue runner lock."""
    issues: list[ReadinessIssue] = []
    if os.name != "posix":
        return ReadinessResult(ok=True, issues=())
    from koru.queue.locking import queue_lock_wanted

    if not queue_lock_wanted():
        return ReadinessResult(ok=True, issues=())

    lock_path = project.resolve() / ".planfile" / ".koru" / "queue-runner.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    import fcntl

    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            issues.append(
                ReadinessIssue(
                    code="queue_runner_lock_held",
                    severity="warn",
                    message=(
                        "another process holds the planfile queue runner lock; "
                        "parallel koru auto loops may fight over tickets"
                    ),
                    fix_command=(
                        "stop duplicate koru auto for this project "
                        "(--replace-existing) or set KORU_QUEUE_RUNNER_LOCK=0"
                    ),
                )
            )
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)

    ok = not any(i.severity == "fail" for i in issues)
    fix = next((i.fix_command for i in issues if i.fix_command), None)
    return ReadinessResult(ok=ok, issues=tuple(issues), primary_fix=fix)


def warn_pre_drive_queue_without_plugin(
    queue_status: str,
    *,
    plugin_required: bool,
    plugin_ok: bool,
    plugin_reason: str,
) -> str | None:
    """Return a warning when queue is waiting_input but the plugin bridge is down."""
    if not plugin_required or plugin_ok:
        return None
    if str(queue_status or "").strip() != "waiting_input":
        return None
    return (
        "queue is waiting_input but autopilot plugin is not connected "
        f"({plugin_reason}); drive will be skipped until plugin reconnects"
    )


def run_plugin_reconnect_pipeline(
    *,
    reload_window: Callable[[], bool],
    wait_connected: Callable[[float], bool],
    attempts: int = 3,
    base_timeout_seconds: float = 12.0,
    backoff_cap_seconds: float = 4.0,
    poll_interval_seconds: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> bool:
    """Reload IDE window + poll plugin connection with exponential backoff."""
    for attempt in range(1, max(1, attempts) + 1):
        reload_window()
        timeout = base_timeout_seconds * (1.0 + 0.25 * (attempt - 1))
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            if wait_connected(poll_interval_seconds):
                return True
            sleep(poll_interval_seconds)
        if attempt < attempts:
            sleep(min(1.5 * attempt, backoff_cap_seconds))
    return False


def evaluate_autonomous_readiness(
    project: Path,
    socket_path: Path | None,
    status: Mapping[str, Any] | None,
    *,
    autopilot_ide: str,
    lane_instance: str | None = None,
    strict_runtime: bool = False,
    include_lane_alignment: bool = True,
    include_queue_contention: bool = True,
) -> ReadinessResult:
    """Run runtime + daemon + socket/workspace gates."""
    merged: list[ReadinessIssue] = []
    primary: str | None = None

    runtime = check_runtime_consistency(project, strict=strict_runtime)
    merged.extend(runtime.issues)
    primary = primary or runtime.primary_fix

    if status is not None:
        daemon = check_daemon_client_alignment(
            status,
            project=project,
            socket_path=socket_path,
        )
        merged.extend(daemon.issues)
        primary = primary or daemon.primary_fix

    if socket_path is not None:
        socket = check_workspace_socket_ownership(
            project,
            socket_path,
            status,
            autopilot_ide=autopilot_ide,
        )
        merged.extend(socket.issues)
        primary = primary or socket.primary_fix

    if include_lane_alignment:
        lane = check_lane_terminal_socket_alignment(
            autopilot_ide=autopilot_ide,
            lane_instance=lane_instance,
            socket_path=socket_path,
        )
        merged.extend(lane.issues)
        primary = primary or lane.primary_fix

    if include_queue_contention:
        queue = check_queue_runner_contention(project)
        merged.extend(queue.issues)
        primary = primary or queue.primary_fix

    ok = not any(i.severity == "fail" for i in merged)
    return ReadinessResult(ok=ok, issues=tuple(merged), primary_fix=primary)


def format_readiness_lines(result: ReadinessResult, *, prefix: str = "") -> list[str]:
    """Human-readable lines for stdio logging."""
    head = prefix or "readiness"
    lines: list[str] = []
    for issue in result.issues:
        tag = "FAIL" if issue.severity == "fail" else "WARN"
        lines.append(f"{head}: [{tag}] {issue.code}: {issue.message}")
        if issue.fix_command:
            lines.append(f"{head}: fix → {issue.fix_command}")
    if result.primary_fix and result.ok is False:
        lines.append(f"{head}: primary fix → {result.primary_fix}")
    for action in result.repair_actions:
        lines.append(f"{head}: [REPAIR] {action}")
    return lines


__all__ = [
    "ReadinessIssue",
    "ReadinessResult",
    "apply_socket_ownership_repairs",
    "attempt_plugin_gate_recovery",
    "check_daemon_client_alignment",
    "check_lane_terminal_socket_alignment",
    "check_queue_runner_contention",
    "check_runtime_consistency",
    "check_workspace_socket_ownership",
    "evaluate_autonomous_readiness",
    "format_readiness_lines",
    "plugin_workspace_covers_project",
    "run_plugin_reconnect_pipeline",
    "warn_pre_drive_queue_without_plugin",
]
