"""Runtime session setup helpers for ``koru autonomous``."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.activity_log import activity, configure_nfo_activity_log
from koru.doctor_runtime_checks import _installed_koru_version, _read_project_version
from koru.env_flags import env_disabled as _env_disabled, env_truthy as _env_truthy


def setup_autonomous_session(
    args: Any,
    *,
    apply_env_defaults: Any,
    uuid_factory: Any,
    guard_existing_processes: Any,
    ensure_init: Any,
    stdio_info: Any,
    write_event: Any,
) -> tuple[str, Path, int]:
    apply_env_defaults(args)
    correlation_id = str(uuid_factory())
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    nfo_path = configure_nfo_activity_log(project)
    if nfo_path is not None:
        stdio_info(
            f"koru autonomous: nfo structured log -> {nfo_path}",
            fmt=args.emit_events,
        )
    activity(
        "RUNTIME",
        "autonomous session context",
        fmt=args.emit_events,
        data={
            "project": str(project),
            "argv": list(sys.argv),
            "python": sys.executable,
            "prefix": sys.prefix,
            "base_prefix": getattr(sys, "base_prefix", ""),
            "virtual_env": os.environ.get("VIRTUAL_ENV", ""),
            "reexeced": bool(os.environ.get("KORU_AUTONOMOUS_REEXECED")),
            "nfo_path": str(nfo_path) if nfo_path is not None else "",
        },
    )
    if reexec_argv := project_venv_reexec_argv(project):
        env = project_venv_reexec_env(project)
        env["KORU_AUTONOMOUS_REEXECED"] = "1"
        stdio_info(
            f"koru autonomous: switching to project venv: {' '.join(reexec_argv)}",
            fmt=args.emit_events,
        )
        os.execvpe(reexec_argv[0], reexec_argv, env)
    for line in project_venv_warning_lines(project):
        stdio_info(line, fmt=args.emit_events)
    _log_runtime_readiness_gate(args, project, stdio_info=stdio_info)
    guard_rc = guard_existing_processes(args, project)
    os.environ["KORU_STDIO_FORMAT"] = args.emit_events
    if args.emit_events == "jsonl":
        write_event(
            sys.stdout,
            event_type="SessionStarted",
            correlation_id=correlation_id,
            payload={
                "project": str(project),
                "ticket_sources": args.ticket_sources,
                "max_cycles": args.max_cycles,
                "max_iterations": args.max_iterations,
                "sleep_seconds": args.sleep_seconds,
            },
        )
    ensure_init(project, force=args.force_init, stdio_format=args.emit_events)
    return correlation_id, project, guard_rc


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def normalize_project_root(path: Path | str | None) -> Path | None:
    """Walk up from ``path`` to the nearest git repo root with ``pyproject.toml``."""
    if path is None:
        return None
    try:
        current = Path(path).expanduser().resolve()
    except OSError:
        return None
    if not current.exists():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / ".git").exists():
            return candidate
    return current


def projects_equivalent(left: Path | str | None, right: Path | str | None) -> bool:
    """True when two paths refer to the same project root after normalization."""
    left_norm = normalize_project_root(left)
    right_norm = normalize_project_root(right)
    if left_norm is None or right_norm is None:
        return False
    return left_norm == right_norm


def resolve_cli_project(raw_args: list[str], *, cwd: Path | None = None) -> Path:
    """Resolve ``--project`` from argv or fall back to cwd."""
    for idx, part in enumerate(raw_args):
        if part == "--project" and idx + 1 < len(raw_args):
            resolved = normalize_project_root(raw_args[idx + 1])
            return resolved if resolved is not None else Path(raw_args[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            raw = part.split("=", 1)[1]
            resolved = normalize_project_root(raw)
            return resolved if resolved is not None else Path(raw).expanduser().resolve()
    base = (cwd or Path.cwd()).resolve()
    resolved = normalize_project_root(base)
    return resolved if resolved is not None else base


def _project_venv_roots(project: Path) -> list[Path]:
    roots: list[Path] = []
    for name in (".venv", "venv"):
        candidate = project / name
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def _local_project_koru(project: Path) -> Path | None:
    for venv_root in _project_venv_roots(project):
        local_koru = (venv_root / "bin" / "koru").resolve()
        if local_koru.is_file() and os.access(local_koru, os.X_OK):
            return local_koru
    return None


def running_outside_project_venv(project: Path) -> bool:
    """True when this Python was not launched from a repo-local virtualenv."""
    local_venvs = _project_venv_roots(project)
    if not local_venvs:
        return False
    executable = Path(sys.executable).expanduser()
    prefix = Path(sys.prefix).expanduser()
    for local_venv in local_venvs:
        if _path_is_relative_to(executable, local_venv) or _path_is_relative_to(prefix, local_venv):
            return False
    return _local_project_koru(project) is not None


def cli_should_reexec(raw_args: list[str]) -> bool:
    """Whether the CLI should prefer the repo-local ``.venv/bin/koru`` entrypoint."""
    if _env_disabled("KORU_CLI_NO_REEXEC") or _env_disabled("KORU_AUTO_REEXEC"):
        return False
    if not raw_args:
        return True
    if raw_args[0].startswith("-"):
        return "--doctor" in raw_args
    return True


def project_venv_reexec_argv(project: Path) -> list[str] | None:
    """Return argv for re-execing inside the repo-local venv when outside it."""
    if os.environ.get("KORU_CLI_REEXECED") or os.environ.get("KORU_AUTONOMOUS_REEXECED"):
        return None
    if _env_disabled("KORU_CLI_NO_REEXEC") or _env_disabled("KORU_AUTO_REEXEC"):
        return None
    local_koru = _local_project_koru(project)
    if local_koru is None or not running_outside_project_venv(project):
        return None
    return [str(local_koru), *sys.argv[1:]]


def maybe_sync_project_koru_package(project: Path) -> str | None:
    """Editable-install koru when import version lags ``pyproject.toml`` (once per process)."""
    if os.environ.get("KORU_CLI_SYNC_DONE") or _env_truthy("KORU_CLI_NO_SYNC"):
        return None
    if running_outside_project_venv(project):
        return None
    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return None
    source_version = _read_project_version(pyproject)
    installed_version = _installed_koru_version()
    if not source_version or not installed_version or source_version == installed_version:
        return None
    pip = project / ".venv" / "bin" / "pip"
    if not pip.is_file():
        return None
    os.environ["KORU_CLI_SYNC_DONE"] = "1"
    proc = subprocess.run(
        [str(pip), "install", "-e", str(project.resolve())],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else f"exit {proc.returncode}"
        return (
            f"koru: package sync failed ({installed_version} != {source_version} in pyproject): {tail}"
        )
    new_version = _installed_koru_version() or source_version
    return (
        f"koru: synced editable package {installed_version} -> {new_version} "
        f"(pyproject {source_version})"
    )


def project_venv_reexec_env(
    project: Path,
    *,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return an env aligned with the repo-local virtualenv for ``execvpe``."""
    env = dict(os.environ if base_env is None else base_env)
    local_venv = (project / ".venv").resolve()
    local_bin = local_venv / "bin"
    old_path = env.get("PATH", "")
    parts = [part for part in old_path.split(os.pathsep) if part and part != str(local_bin)]
    env["VIRTUAL_ENV"] = str(local_venv)
    env["PATH"] = os.pathsep.join([str(local_bin), *parts])
    return env


def project_venv_warning_lines(project: Path) -> list[str]:
    """Warn when ``koru auto`` is running outside the repo-local virtualenv."""
    local_venv = (project / ".venv").resolve()
    local_koru = local_venv / "bin" / "koru"
    if not local_koru.exists():
        return []

    executable = Path(sys.executable).expanduser()
    if _path_is_relative_to(executable, local_venv) or _path_is_relative_to(
        Path(sys.prefix).expanduser(),
        local_venv,
    ):
        return []

    return [
        "koru autonomous: [!] wykryto lokalne repo .venv, ale ten proces działa z "
        f"Python={executable}",
        "koru autonomous: [!] użyj lokalnego środowiska projektu, np. "
        f"PATH=\"{local_venv / 'bin'}:$PATH\" koru auto",
    ]


@dataclass(frozen=True)
class AutopilotSocketDecision:
    lane: str | None
    autopilot_ide: str
    socket_path: Path
    socket_source: str
    env_socket: str
    env_instance_before: str


def _resolve_autopilot_lane(
    args: Any,
    *,
    resolve_autopilot_ide: Any,
    resolve_ide_route_fn: Any,
) -> tuple[str | None, str]:
    lane = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip() or None
    autopilot_ide, _ = resolve_autopilot_ide(
        args.autopilot_ide,
        lane,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    if autopilot_ide and autopilot_ide != "auto":
        if not lane or lane == "auto":
            os.environ["KORU_AUTOPILOT_INSTANCE"] = autopilot_ide
            lane = autopilot_ide
        elif lane == autopilot_ide or lane.startswith(f"{autopilot_ide}-"):
            pass
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = autopilot_ide
            lane = autopilot_ide
    return lane, autopilot_ide


def _autopilot_socket_source(
    args: Any,
    *,
    autopilot_ide: str,
    env_socket: str,
    env_instance_before: str,
) -> str:
    if args.socket:
        return "cli --socket"
    if env_socket:
        return "env:KORU_AUTOPILOT_SOCKET"
    if env_instance_before:
        return f"env:KORU_AUTOPILOT_INSTANCE={env_instance_before}"
    if autopilot_ide:
        return f"resolved autopilot_ide={autopilot_ide}"
    return "default socket"


def _decide_autopilot_socket(
    args: Any,
    *,
    resolve_autopilot_ide: Any,
    resolve_ide_route_fn: Any,
    default_socket_path: Any,
) -> AutopilotSocketDecision:
    lane, autopilot_ide = _resolve_autopilot_lane(
        args,
        resolve_autopilot_ide=resolve_autopilot_ide,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    env_socket = (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    env_instance_before = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    socket_source = _autopilot_socket_source(
        args,
        autopilot_ide=autopilot_ide,
        env_socket=env_socket,
        env_instance_before=env_instance_before,
    )
    socket_path = (args.socket or default_socket_path()).resolve()
    return AutopilotSocketDecision(
        lane=lane,
        autopilot_ide=autopilot_ide,
        socket_path=socket_path,
        socket_source=socket_source,
        env_socket=env_socket,
        env_instance_before=env_instance_before,
    )


def _log_autopilot_socket_decision(
    args: Any,
    decision: AutopilotSocketDecision,
    *,
    stdio_info: Any,
) -> None:
    stdio_info(
        "koru autonomous: autopilot socket decision: "
        f"lane={decision.lane} ide={decision.autopilot_ide} "
        f"source={decision.socket_source} path={decision.socket_path}",
        fmt=args.emit_events,
    )
    activity(
        "AUTOPILOT",
        "socket decision",
        fmt=args.emit_events,
        data={
            "lane": decision.lane,
            "ide": decision.autopilot_ide,
            "source": decision.socket_source,
            "socket_path": str(decision.socket_path),
            "env_socket": decision.env_socket,
            "env_instance_before": decision.env_instance_before,
        },
    )


def setup_autopilot_daemon(
    args: Any,
    project: Path,
    *,
    apply_agent_lane_environ: Any,
    resolve_autopilot_ide: Any,
    resolve_ide_route_fn: Any,
    default_socket_path: Any,
    start_or_reuse_daemon: Any,
    stdio_info: Any,
) -> tuple[Any | None, Any | None, Any | None, Path | None]:
    client = None
    daemon = None
    thread = None
    socket_path: Path | None = None
    if not args.enable_autopilot:
        return client, daemon, thread, socket_path

    # apply_agent_lane_environ is already called in build_and_log_startup_probe
    # so we can read the lane directly from the environment
    decision = _decide_autopilot_socket(
        args,
        resolve_autopilot_ide=resolve_autopilot_ide,
        resolve_ide_route_fn=resolve_ide_route_fn,
        default_socket_path=default_socket_path,
    )
    socket_path = decision.socket_path
    _log_autopilot_socket_decision(args, decision, stdio_info=stdio_info)
    client, daemon, thread = start_or_reuse_daemon(
        project=project,
        socket_path=socket_path,
        stdio_format=args.emit_events,
    )
    _apply_autopilot_readiness_after_daemon(
        args,
        project,
        socket_path,
        client,
        decision.autopilot_ide,
        stdio_info=stdio_info,
    )
    return client, daemon, thread, socket_path


def _log_runtime_readiness_gate(
    args: Any,
    project: Path,
    *,
    stdio_info: Any,
) -> None:
    from koru.autonomous_readiness import check_runtime_consistency, format_readiness_lines

    strict = os.environ.get("KORU_READINESS_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    runtime = check_runtime_consistency(project, strict=strict)
    for line in format_readiness_lines(runtime, prefix="koru autonomous"):
        stdio_info(line, fmt=args.emit_events)


def _apply_autopilot_readiness_after_daemon(
    args: Any,
    project: Path,
    socket_path: Path,
    client: Any | None,
    autopilot_ide: str,
    *,
    stdio_info: Any,
) -> None:
    from koru.autonomous_readiness import (
        apply_socket_ownership_repairs,
        check_daemon_client_alignment,
        check_workspace_socket_ownership,
        format_readiness_lines,
    )

    status: dict[str, Any] | None = None
    if client is not None:
        try:
            status = client.status()
        except (OSError, RuntimeError, TimeoutError):
            status = None

    daemon = check_daemon_client_alignment(status, project=project, socket_path=socket_path)
    socket = check_workspace_socket_ownership(
        project,
        socket_path,
        status,
        autopilot_ide=autopilot_ide,
    )
    readiness_issues = list(daemon.issues) + list(socket.issues)
    from koru.autonomous_readiness import ReadinessResult

    readiness = ReadinessResult(
        ok=daemon.ok and socket.ok,
        issues=tuple(readiness_issues),
        primary_fix=daemon.primary_fix or socket.primary_fix,
    )
    readiness = apply_socket_ownership_repairs(project, socket_path, readiness)

    for line in format_readiness_lines(readiness, prefix="koru autonomous"):
        stdio_info(line, fmt=args.emit_events)


def cleanup_autonomous_session(
    previous_stdio_format_env: str | None,
    previous_sigterm: Any,
    daemon: Any | None,
    thread: Any | None,
    wup_process: Any,
    stdio_format: str,
    *,
    stop_process: Any,
) -> None:
    if previous_stdio_format_env is None:
        os.environ.pop("KORU_STDIO_FORMAT", None)
    else:
        os.environ["KORU_STDIO_FORMAT"] = previous_stdio_format_env
    signal.signal(signal.SIGTERM, previous_sigterm)
    if daemon is not None:
        daemon.stop()
    if thread is not None:
        thread.join(timeout=2.0)
    stop_process(wup_process, "WUP watcher", stdio_format=stdio_format)


def setup_autonomous_env_vars() -> tuple[str | None, dict[str, tuple[bool, str | None]]]:
    """Setup and save environment variables for autonomous mode."""
    previous_stdio_format_env = os.environ.get("KORU_STDIO_FORMAT")
    strict_env = {
        key: (key in os.environ, os.environ.get(key))
        for key in ("KORU_STRICT_PLUGIN_VERSION", "KORU_STRICT_PLUGIN_ACK")
    }
    return previous_stdio_format_env, strict_env


def restore_autonomous_env_vars(snapshot: dict[str, tuple[bool, str | None]]) -> None:
    """Restore environment variables after autonomous mode."""
    for key, (was_set, value) in snapshot.items():
        if was_set:
            os.environ[key] = value or ""
        else:
            os.environ.pop(key, None)


@dataclass
class StopSignalState:
    stopped_by_sigterm: bool = False


def build_and_log_startup_probe(
    args: Any,
    project: Path,
    *,
    apply_agent_lane_environ: Any,
    build_startup_probe: Any,
    format_startup_banner: Any,
    resolve_project_lane: Any,
    stdio_info: Any,
) -> object:
    apply_agent_lane_environ(project, args.agent_lane)
    startup_probe = build_startup_probe(
        project,
        agent_lane_cli=args.agent_lane,
        autopilot_ide_cli=args.autopilot_ide,
        resolve_project_lane=resolve_project_lane,
    )
    # Keep later socket computations aligned with the resolved lane, not stale koruenv overlay.
    instance = getattr(startup_probe, "resolved_lane", None) or getattr(
        startup_probe, "resolved_autopilot_ide", None
    )
    ide = getattr(startup_probe, "resolved_autopilot_ide", None)
    if instance:
        os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
    if ide:
        os.environ["KORU_AUTOPILOT_IDE"] = ide
    expected_socket = getattr(startup_probe, "socket_path", None)
    if expected_socket:
        os.environ["KORU_AUTOPILOT_SOCKET"] = str(expected_socket)
    for line in format_startup_banner(startup_probe):
        stdio_info(line, fmt=args.emit_events)
    return startup_probe


def install_sigterm_interrupt_handler(
    args: Any,
    stop_state: StopSignalState,
    *,
    stdio_info: Any,
) -> Any:
    def _sigterm_to_interrupt(_signo: int, _frame: object) -> None:
        stop_state.stopped_by_sigterm = True
        stdio_info(
            "koru autonomous: SIGTERM received (typical: OOM killer, systemd stop, "
            "`kill`, cgroup memory limit, or IDE tool timeout) - cleaning up",
            fmt=args.emit_events,
        )
        raise KeyboardInterrupt()

    return signal.signal(signal.SIGTERM, _sigterm_to_interrupt)


def handle_autonomous_interrupt(
    args: Any,
    *,
    correlation_id: str,
    stopped_by_sigterm: bool,
    write_event: Any,
    stdio_info: Any,
) -> int:
    stop_reason = "sigterm" if stopped_by_sigterm else "keyboard_interrupt"
    if args.emit_events == "jsonl":
        write_event(
            sys.stdout,
            event_type="AutonomousStopped",
            correlation_id=correlation_id,
            payload={"reason": stop_reason},
        )
    if stopped_by_sigterm:
        stdio_info(
            "\nkoru autonomous: stopped after SIGTERM (WUP watcher stopped; "
            "if scan was heavy, try --no-semcod-artifacts or "
            "KORU_SCAN_SEMCOD_ARTIFACTS=0)",
            fmt=args.emit_events,
        )
    else:
        stdio_info("\nkoru autonomous: interrupted (Ctrl+C)", fmt=args.emit_events)
    return 0


__all__ = [
    "StopSignalState",
    "build_and_log_startup_probe",
    "cli_should_reexec",
    "maybe_sync_project_koru_package",
    "normalize_project_root",
    "projects_equivalent",
    "project_venv_reexec_argv",
    "project_venv_reexec_env",
    "resolve_cli_project",
    "running_outside_project_venv",
    "project_venv_warning_lines",
    "setup_autonomous_session",
    "setup_autopilot_daemon",
    "setup_autonomous_env_vars",
    "restore_autonomous_env_vars",
    "install_sigterm_interrupt_handler",
    "handle_autonomous_interrupt",
    "cleanup_autonomous_session",
]
