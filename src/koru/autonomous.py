"""One-command autonomous mode for freshly installed koru.

`koru auto` and `koru autonomous up` (or bare `koru autonomous`) bootstrap
the project if needed, applies ``--agent-lane`` exports like
``shell-env.sh``, then starts optional background services (autopilot daemon,
WUP ``wup watch`` when auto-detected), and runs an outer loop.

Each cycle (see ``_run_cycle``): ``koru scan --apply`` when ticket sources
include scan, then ``koru --queue --loop``, then optional idle diagnostics
when the queue is idle, a WUP health read if the watcher is running, then
autopilot. ``--no-serve`` is a compatibility no-op (``koru serve`` is not
started here).
"""


import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koruide.daemon import AutopilotDaemon
from koruide.os_injector import OsInjectorError, inject_with_profile, load_profile

from koru import autonomous_cycle as _autonomous_cycle_module
from koru.agents import agent_lane_environment
from koru.autonomous_cycle import (
    AutoloopState,
    DiagnosticResult,
)
from koru.autonomous_env import (
    apply_autonomous_env_overrides as _env_apply_autoloop_defaults,
)
from koru.autonomous_env import (
    effective_ticket_source_flags as _effective_flags,
)
from koru.autonomous_startup import (
    build_startup_probe,
    format_post_startup_operator_hints,
    format_startup_banner,
    resolve_autopilot_ide_for_autonomous,
)
from koru.autonomous_startup import (
    resolve_agent_lane_id as _resolve_agent_lane_id,
)
from koru.autonomous_wup import (
    WupHealthResult,
    WupWatchConfig,  # noqa: F401
    _build_wup_watch_config,
    _start_wup_watch,
    _stop_process,
    _wup_watch_command,  # noqa: F401
)
from koru.autonomous_wup import (
    _read_wup_health as _read_wup_health_impl,
)
from koru.autonomy.ide_work import release_in_progress_tickets, resolve_idle_drive_prompt
from koru.autonomy.operator_pipeline import run_startup_operator_pipeline
from koru.autonomy.prompts import build_prompt
from koru.autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
from koru.autopilot import default_socket_path
from koru.autopilot.plugin_installer import format_plugin_install_result, install_plugin_for_ide
from koru.ide_client import IDEControlClient, build_ide_client
from koru.ide_router import resolve_ide_route
from koru.init import init_project, resolve_project_agent_lane
from koru.queue import (
    QueueLoopResult,
    run_planfile_queue_loop,
)
from koru.queue import (
    default_human_prompt as _default_human_prompt,
)
from koru.queue import (
    run_api_request as _run_api_request,
)
from koru.queue import (
    run_llm_request as _run_llm_request,
)
from koru.queue import (
    run_process as _run_process,
)
from koru.queue import (
    run_shell_command as _run_shell_command,
)
from koru.scan import ScanResult, run_scan
from koru.stdio_events import default_stdio_format_from_env, write_stdio_event
from koru.tasks import create_nl_task
from koru.topology import is_component_enabled, is_pipeline_enabled

_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Best-effort global fallback via coordinate profile.

    Enabled only when ``KORU_OS_INJECTOR_PROFILE`` is set.
    """
    profile_id = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile_id:
        return None
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    try:
        profile = load_profile(profile_id, config_path=cfg)
        return inject_with_profile(profile=profile, text=prompt, submit=submit, dry_run=False)
    except OsInjectorError as exc:
        return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


def _stdio_info(msg: str, *, fmt: str) -> None:
    """Human-oriented status; jsonl mode routes to stderr so stdout stays NDJSON-only."""
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def _daemon_activity_log(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity

    if msg.startswith("drive"):
        activity("DAEMON", msg, fmt=fmt)
    else:
        activity("DAEMON", msg, fmt=fmt)


def _allow_keyboard_autopilot_fallback() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ExistingAutonomousProcess:
    pid: int
    command: str
    cwd: Path | None = None


@dataclass(frozen=True)
class ExistingManagedProcess:
    pid: int
    kind: str
    command: str
    cwd: Path | None = None


def _resolve_autopilot_ide(cli_value: str) -> str:
    """Resolve autopilot ``--ide`` via :mod:`koru.ide_router` (headless + env merge)."""
    return resolve_ide_route(cli_autopilot_ide=cli_value).autopilot_ide


def _apply_agent_lane_environ(project: Path, agent_lane: str) -> str | None:
    """Set lane exports in ``os.environ``; returns lane id or ``None`` if skipped."""
    lane, _source = _resolve_agent_lane_id(
        project,
        agent_lane,
        resolve_project_lane=resolve_project_agent_lane,
    )
    if lane is None:
        return None
    for key, val in agent_lane_environment(lane).items():
        os.environ[key] = val
    return lane


def _command_project(command: str) -> Path | None:
    """Best-effort parse of ``--project`` from a process command line."""
    parts = command.split()
    for idx, part in enumerate(parts):
        if part == "--project" and idx + 1 < len(parts):
            return Path(parts[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return None


def _process_cwd(pid: int) -> Path | None:
    proc_cwd = Path("/proc") / str(pid) / "cwd"
    try:
        return proc_cwd.resolve()
    except OSError:
        return None


def _ancestor_pids(pid: int) -> set[int]:
    """Return best-effort parent chain for ``pid`` on Linux."""
    ancestors: set[int] = set()
    current = pid
    while current > 1:
        stat_path = Path("/proc") / str(current) / "stat"
        try:
            stat_text = stat_path.read_text(encoding="utf-8")
        except OSError:
            break
        parts = stat_text.split()
        if len(parts) < 4:
            break
        try:
            parent = int(parts[3])
        except ValueError:
            break
        if parent <= 1 or parent in ancestors:
            break
        ancestors.add(parent)
        current = parent
    return ancestors


def _looks_like_autonomous_up_command(command: str) -> bool:
    from koru.autonomous_parser import looks_like_autonomous_up_command

    return looks_like_autonomous_up_command(command)


def _find_existing_autonomous_processes(
    project: Path,
    *,
    any_project: bool = False,
) -> list[ExistingAutonomousProcess]:
    """Return running koru autonomous/auto processes except this PID tree."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,command="],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []

    current_pid = os.getpid()
    excluded = {current_pid, *_ancestor_pids(current_pid)}
    project = project.resolve()
    matches: list[ExistingAutonomousProcess] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pid_text, _, rest = line.partition(" ")
        ppid_text, _, command = rest.strip().partition(" ")
        try:
            pid = int(pid_text)
            int(ppid_text)
        except ValueError:
            continue
        if pid in excluded:
            continue
        if not _looks_like_autonomous_up_command(command):
            continue

        cwd = _process_cwd(pid)
        cmd_project = _command_project(command)
        if any_project or cwd == project or cmd_project == project:
            matches.append(ExistingAutonomousProcess(pid=pid, command=command, cwd=cwd))
    return matches


def stop_prior_autonomous_for_auto_start(
    project: Path,
    *,
    stdio_format: str = "human",
) -> None:
    """Stop koru autonomous/auto loops (any project) and WUP watch for ``project``."""
    project = project.resolve()
    existing = [
        *(
            _as_managed(proc)
            for proc in _find_existing_autonomous_processes(project, any_project=True)
        ),
        *_find_existing_wup_processes(project),
    ]
    if not existing:
        return
    _stdio_info(
        f"koru auto: stopping {len(existing)} prior managed process(es) "
        "(koru autonomous/auto, wup watch)",
        fmt=stdio_format,
    )
    _terminate_existing_processes(existing, stdio_format=stdio_format)


def _find_existing_wup_processes(project: Path) -> list[ExistingManagedProcess]:
    """Return stale/running ``wup watch`` processes for ``project`` except this tree."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,command="],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []

    current_pid = os.getpid()
    excluded = {current_pid, *_ancestor_pids(current_pid)}
    project = project.resolve()
    matches: list[ExistingManagedProcess] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        first, _, rest = line.partition(" ")
        second, _, command = rest.strip().partition(" ")
        try:
            pid = int(first)
            int(second)
        except ValueError:
            continue
        if pid in excluded:
            continue
        if "wup" not in command or " watch " not in f" {command} ":
            continue
        cwd = _process_cwd(pid)
        if cwd == project or str(project) in command:
            matches.append(
                ExistingManagedProcess(pid=pid, kind="wup-watch", command=command, cwd=cwd),
            )
    return matches


def _as_managed(proc: ExistingAutonomousProcess) -> ExistingManagedProcess:
    return ExistingManagedProcess(
        pid=proc.pid,
        kind="autonomous-loop",
        command=proc.command,
        cwd=proc.cwd,
    )


def _terminate_existing_processes(
    processes: list[ExistingManagedProcess],
    *,
    stdio_format: str,
) -> None:
    for proc in processes:
        _stdio_info(
            f"koru autonomous: stopping existing {proc.kind} pid={proc.pid}",
            fmt=stdio_format,
        )
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError:
            _stdio_info(
                f"koru autonomous: no permission to stop existing {proc.kind} pid={proc.pid}",
                fmt=stdio_format,
            )

    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        alive = []
        for proc in processes:
            try:
                os.kill(proc.pid, 0)
            except ProcessLookupError:
                continue
            alive.append(proc)
        if not alive:
            return
        time.sleep(0.2)

    for proc in processes:
        try:
            os.kill(proc.pid, signal.SIGKILL)
            _stdio_info(
                f"koru autonomous: force-stopped existing {proc.kind} pid={proc.pid}",
                fmt=stdio_format,
            )
        except (ProcessLookupError, PermissionError):
            pass


def _confirm_replace_existing(processes: list[ExistingManagedProcess]) -> bool:
    print("koru autonomous: existing managed process(es) for this project are already running:")
    for proc in processes:
        where = f" cwd={proc.cwd}" if proc.cwd else ""
        print(f"  {proc.kind} pid={proc.pid}{where} :: {proc.command}")
    answer = input("Stop existing process(es) and start this one? [y/N] ").strip().lower()
    return answer in {"y", "yes", "t", "tak"}


def _guard_existing_autonomous_processes(args: argparse.Namespace, project: Path) -> int:
    if args.allow_duplicate:
        return 0
    existing = [
        *(_as_managed(proc) for proc in _find_existing_autonomous_processes(project)),
        *_find_existing_wup_processes(project),
    ]
    if not existing:
        return 0
    if args.replace_existing:
        if getattr(args, "replace_existing_global", False):
            existing = [
                *(
                    _as_managed(proc)
                    for proc in _find_existing_autonomous_processes(project, any_project=True)
                ),
                *_find_existing_wup_processes(project),
            ]
        _terminate_existing_processes(existing, stdio_format=args.emit_events)
        return 0
    if args.emit_events == "human" and sys.stdin.isatty():
        if _confirm_replace_existing(existing):
            _terminate_existing_processes(existing, stdio_format=args.emit_events)
            return 0
        _stdio_info(
            "koru autonomous: keeping existing process(es); not starting a duplicate. "
            "Use --allow-duplicate to override.",
            fmt=args.emit_events,
        )
        return 2
    _stdio_info(
        "koru autonomous: another managed process is already running for this project; "
        "use --replace-existing to stop it first or --allow-duplicate to run anyway.",
        fmt=args.emit_events,
    )
    for proc in existing:
        _stdio_info(
            f"  existing {proc.kind} pid={proc.pid}: {proc.command}",
            fmt=args.emit_events,
        )
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autonomous",
        description=(
            "Bootstrap and run koru in autonomous mode: optional init, "
            "scan intake, queue drain, and autopilot drive loop."
        ),
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help=(
            "Autopilot daemon socket path (default: $XDG_RUNTIME_DIR/koru-autopilot.sock; "
            "override with KORU_AUTOPILOT_SOCKET or KORU_AUTOPILOT_INSTANCE — see docs)."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    up = sub.add_parser("up", help="Configure and start autonomous loop.")
    up.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    up.add_argument(
        "--replace-existing",
        action="store_true",
        help=(
            "If another `koru autonomous up` is already running for this project, "
            "terminate it before starting this instance."
        ),
    )
    up.add_argument(
        "--allow-duplicate",
        action="store_true",
        help=(
            "Allow multiple autonomous loops for the same project. This can duplicate "
            "scan/WUP/autopilot work and should be used only deliberately."
        ),
    )
    up.add_argument(
        "--agent-lane",
        default="auto",
        metavar="LANE",
        help=(
            "Set KORU_AUTOPILOT_* / queue actor env for this lane before the "
            "loop (auto|cursor|windsurf|local|…); same rules as koru --init. "
            "Use none to use the current process environment as-is. Default: auto."
        ),
    )
    up.add_argument("--actor", default="koru-shell", help="Queue actor id.")
    up.add_argument(
        "--queue-name",
        default="default",
        help="Execution queue name (ignored when ticket-sources=all).",
    )
    up.add_argument(
        "--ticket-sources",
        choices=("queue", "scan", "all"),
        default="all",
        help=(
            "queue: only existing queue tickets; scan: add `koru scan --apply`; "
            "all: scan + all queues. "
            "Env TICKET_SOURCES=queue|scan|all overrides when set; invalid values "
            "fail `koru --doctor` and are ignored at autonomous runtime (stderr)."
        ),
    )
    up.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Max queue tickets per cycle (default: 50).",
    )
    up.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="Outer loop cycles (0 = infinite, default).",
    )
    up.add_argument(
        "--sleep-seconds",
        type=float,
        default=30.0,
        help="Sleep between cycles (default: 30s).",
    )
    up.add_argument(
        "--autopilot-ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help="IDE target for autopilot drive (default: auto).",
    )
    up.add_argument(
        "--autopilot-plugin-wait-seconds",
        type=float,
        default=5.0,
        help="Wait this many seconds for the IDE autopilot plugin before the first drive.",
    )
    up.add_argument(
        "--drive-prompt",
        default="continue with the next ticket",
        help="Prompt sent in each autopilot drive step.",
    )
    up.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Type prompt but do not press submit key.",
    )
    up.add_argument(
        "--no-autopilot",
        dest="enable_autopilot",
        action="store_false",
        help="Disable autopilot drive step.",
    )
    up.add_argument(
        "--no-serve",
        dest="enable_serve",
        action="store_false",
        help="Compatibility flag; serve mode was removed from autonomous up.",
    )
    up.add_argument(
        "--keep-waiting-input",
        dest="stop_on_waiting_input",
        action="store_false",
        help=(
            "Keep the outer loop running when the queue is waiting_input so each "
            "cycle still runs scan/queue/WUP health/autopilot (default)."
        ),
    )
    up.add_argument(
        "--stop-on-waiting-input",
        dest="stop_on_waiting_input",
        action="store_true",
        help=("Stop the outer loop when the queue reports waiting_input (legacy behavior)."),
    )
    up.add_argument(
        "--force-init",
        action="store_true",
        help="Force `koru --init` re-initialization if project is already initialized.",
    )
    up.add_argument(
        "--semcod-artifacts",
        action="store_true",
        default=None,
        help=(
            "Include semcod quality artifacts in `koru scan` "
            "(jscpd, code2llm/SUMR refactor analysis, testql export, redup). "
            "Enabled by default in autonomous mode."
        ),
    )
    up.add_argument(
        "--no-semcod-artifacts",
        dest="semcod_artifacts",
        action="store_false",
        help="Disable semcod artifact scanning.",
    )
    up.add_argument(
        "--idle-diagnostics",
        choices=("off", "quick", "full", "deep"),
        default="off",
        help="Run package-native diagnostics when queue is idle.",
    )
    up.add_argument(
        "--diagnostic-tickets",
        action="store_true",
        help="Create deduplicated planfile tickets for failed idle diagnostics.",
    )
    up.add_argument(
        "--diagnostic-ticket-queue",
        default="default",
        help="Queue for diagnostic tickets.",
    )
    up.add_argument(
        "--diagnostic-ticket-priority",
        default="high",
        help="Priority for diagnostic tickets.",
    )
    up.add_argument(
        "--diagnostic-state-dir",
        default=".planfile/.koru/autoloop-diag",
        help="Directory for diagnostic failure dedup markers.",
    )
    up.add_argument(
        "--strict-diagnostics",
        action="store_true",
        help="Stop with exit code 2 when idle diagnostics fail.",
    )
    up.add_argument(
        "--autopilot-on-idle-only",
        action="store_true",
        help="Run autopilot only when queue is idle.",
    )
    up.add_argument(
        "--autopilot-action",
        choices=("drive", "handoff", "off"),
        default="drive",
        help="Autopilot action for each cycle.",
    )
    up.add_argument(
        "--autopilot-skip-on-diagnostics-fail",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip autopilot when diagnostics fail.",
    )
    up.add_argument(
        "--autopilot-skip-statuses",
        default="waiting_input",
        help="Comma-separated statuses skipped after repeated same waiting signature.",
    )
    up.add_argument(
        "--autopilot-skip-drive-idle-streak",
        type=int,
        default=0,
        help=(
            "When >0, skip autopilot drive after this many consecutive identical "
            "queue signatures while last_status is idle (0 = disabled; same counter "
            "as stagnation backoff)."
        ),
    )
    up.add_argument(
        "--backoff-on-stagnation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exponential sleep backoff when queue status and waiting ticket repeat.",
    )
    up.add_argument(
        "--max-sleep-seconds",
        type=float,
        default=900.0,
        help="Maximum sleep after stagnation backoff; 0 disables the cap.",
    )
    up.add_argument(
        "--scan-skip-if-clean",
        action="store_true",
        help="Skip scan when previous scans were clean and git HEAD is unchanged.",
    )
    up.add_argument(
        "--scan-skip-after",
        type=int,
        default=1,
        help="Clean scan streak required before scan skip can apply.",
    )
    up.add_argument(
        "--scan-after-idle-queue",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "After the queue drain reports idle, run `koru scan --apply` once per cycle "
            "(e.g. with ticket-sources=queue: refresh code2llm / semcod-driven tickets)."
        ),
    )
    up.add_argument(
        "--scan-after-idle-min-interval",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=(
            "Minimum wall-clock seconds between scan-after-idle-queue runs (0 = no limit). "
            "Reduces repeated scans when the queue stays idle."
        ),
    )
    up.add_argument(
        "--topology-integration",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Respect .koru/topology.yaml component and pipeline toggles.",
    )
    up.add_argument(
        "--wup-watch",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Start WUP watcher in autonomous mode (default: auto-enable when "
            "wup.yaml and `wup` binary are present). Use --no-wup-watch to disable."
        ),
    )
    up.add_argument(
        "--wup-mode",
        choices=("default", "testql"),
        default="testql",
        help="WUP watch mode. testql runs selective TestQL scenarios for changed services.",
    )
    up.add_argument(
        "--wup-deps",
        default="deps.json",
        help="Dependency map file passed to wup watch --deps.",
    )
    up.add_argument(
        "--wup-scenarios-dir",
        default="testql-scenarios",
        help="Scenario directory passed to wup watch --scenarios-dir in testql mode.",
    )
    up.add_argument(
        "--wup-testql-bin",
        default="testql",
        help="TestQL binary passed to wup watch --testql-bin.",
    )
    up.add_argument(
        "--wup-track-dir",
        default=".wup/tracks",
        help="Track directory passed to wup watch --track-dir.",
    )
    up.add_argument(
        "--wup-debounce",
        type=int,
        default=2,
        help="Debounce seconds passed to wup watch.",
    )
    up.add_argument(
        "--wup-cooldown",
        type=int,
        default=300,
        help="Cooldown seconds passed to wup watch.",
    )
    up.add_argument(
        "--wup-cpu-throttle",
        type=float,
        default=0.8,
        help="CPU throttle passed to wup watch.",
    )
    up.add_argument(
        "--wup-quick-limit",
        type=int,
        default=3,
        help="Maximum quick TestQL scenarios passed to wup watch --quick-limit.",
    )
    up.add_argument(
        "--wup-config",
        type=Path,
        default=None,
        help="Optional config path passed to wup watch --config.",
    )
    up.add_argument(
        "--wup-diagnostic-tickets",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create high-priority planfile tickets when WUP reports failing services.",
    )
    up.add_argument(
        "--wup-ticket-queue",
        default="default",
        help="Queue for WUP regression tickets.",
    )
    up.add_argument(
        "--emit-events",
        choices=("human", "jsonl"),
        default=default_stdio_format_from_env(),
        help=(
            "Stdout format: human log lines (default) or NDJSON control-plane events. "
            "Default follows KORU_STDIO_FORMAT=human|jsonl when set. "
            "jsonl: structured events on stdout; incidental status on stderr."
        ),
    )
    up.add_argument(
        "--operator-pipeline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "After startup, print numbered operator steps and create planfile "
            "tickets on --operator-ticket-queue (human + task koru:* shell steps)."
        ),
    )
    up.add_argument(
        "--operator-tickets",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create [OPERATOR] planfile tickets for pending pipeline steps.",
    )
    up.add_argument(
        "--operator-ticket-queue",
        default="operator",
        help="Planfile queue for operator-pipeline tickets (default: operator).",
    )
    up.add_argument(
        "--operator-ticket-priority",
        default="high",
        help="Priority for operator-pipeline tickets.",
    )
    up.set_defaults(
        submit=True,
        enable_autopilot=True,
        enable_serve=True,
        stop_on_waiting_input=False,
        semcod_artifacts=True,
        operator_pipeline=True,
        operator_tickets=True,
    )

    return parser


def _ensure_init(project: Path, *, force: bool, stdio_format: str = "human") -> None:
    config_path = project / ".planfile" / "config.yaml"
    if config_path.exists() and not force:
        return
    report = init_project(project, force=force)
    _stdio_info(
        f"koru autonomous: init {'re-' if force else ''}done at {report.project}",
        fmt=stdio_format,
    )


def _start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
    stdio_format: str = "human",
) -> tuple[IDEControlClient, AutopilotDaemon | None, threading.Thread | None]:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    probe = build_ide_client(socket_path=socket_path, timeout=0.5)
    if probe.is_running():
        _stdio_info(f"koru autonomous: reusing autopilot daemon on {socket_path}", fmt=stdio_format)
        return build_ide_client(socket_path=socket_path), None, None

    daemon = AutopilotDaemon(
        socket_path=socket_path,
        project=project,
        log=lambda m: _stdio_info(m, fmt=stdio_format),
    )
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    _stdio_info(f"koru autonomous: started autopilot daemon on {socket_path}", fmt=stdio_format)
    return build_ide_client(socket_path=socket_path), daemon, thread


def _status_has_autopilot_plugin(status: Mapping[str, Any], ide: str) -> bool:
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return False
    for plugin in plugins:
        if not isinstance(plugin, Mapping):
            continue
        plugin_ide = plugin.get("ide")
        if plugin_ide == ide or ide == "auto":
            return True
    return False


def _wait_for_autopilot_plugin(
    client: IDEControlClient,
    ide: str,
    *,
    timeout_seconds: float,
    interval_seconds: float = 0.25,
) -> bool:
    if timeout_seconds <= 0:
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if _status_has_autopilot_plugin(client.status(), ide):
                return True
        except OSError:
            pass
        time.sleep(interval_seconds)
    try:
        return _status_has_autopilot_plugin(client.status(), ide)
    except OSError:
        return False


def _queue_loop_waiting_ticket_label(queue_result: QueueLoopResult) -> str:
    """Last ticket id in ``waiting`` (terminal queue state), or ``-`` if unknown."""
    waiting = getattr(queue_result, "waiting", None) or []
    return waiting[-1] if waiting else "-"


def _is_topology_enabled(project: Path, key: str, *, fallback: bool, enabled: bool) -> bool:
    if not enabled:
        return fallback
    try:
        if key in {"idle-diagnostics", "autoloop:queue", "scan:on-change", "autopilot:drive"}:
            return is_pipeline_enabled(project, key)
        return is_component_enabled(project, key)
    except Exception:
        return fallback


def _current_head(project: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _compute_backoff_sleep(base: float, streak: int, cap: float, enabled: bool) -> float:
    if streak <= 0 or not enabled:
        return base
    candidate = base * (2 ** min(streak, 10))
    if cap > 0:
        return min(candidate, cap)
    return candidate


def _load_loop_checkpoint(
    path: Path,
    *,
    state: AutoloopState,
    stdio_format: str = "human",
) -> int | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    try:
        cycle = int(payload.get("cycle", 0))
    except (TypeError, ValueError):
        cycle = 0
    state_payload = payload.get("state")
    if isinstance(state_payload, dict):
        for key in (
            "previous_signature",
            "stagnation_streak",
            "scan_clean_streak",
            "scan_last_head",
            "wup_seen_events",
            "last_message_sent_ts",
            "telemetry_autopilot_idle_streak_skips",
            "telemetry_scan_after_idle_runs",
            "telemetry_scan_after_idle_tickets_applied",
            "last_scan_after_idle_ts",
        ):
            if key in state_payload:
                setattr(state, key, state_payload[key])
        events = state_payload.get("autopilot_events")
        if isinstance(events, list):
            state.autopilot_events = [ev for ev in events if isinstance(ev, dict)]
    if cycle > 0:
        _stdio_info(f"koru autonomous: restored checkpoint cycle={cycle}", fmt=stdio_format)
        return cycle
    return None


def _save_loop_checkpoint(
    path: Path,
    *,
    cycle: int,
    state: AutoloopState,
    queue_status: str,
    waiting_ticket: str,
) -> None:
    payload = {
        "cycle": cycle,
        "saved_at": time.time(),
        "queue_status": queue_status,
        "waiting_ticket": waiting_ticket,
        "state": {
            "previous_signature": state.previous_signature,
            "stagnation_streak": state.stagnation_streak,
            "scan_clean_streak": state.scan_clean_streak,
            "scan_last_head": state.scan_last_head,
            "wup_seen_events": state.wup_seen_events,
            "autopilot_events": list(state.autopilot_events)[-50:],
            "last_message_sent_ts": state.last_message_sent_ts,
            "telemetry_autopilot_idle_streak_skips": state.telemetry_autopilot_idle_streak_skips,
            "telemetry_scan_after_idle_runs": state.telemetry_scan_after_idle_runs,
            "telemetry_scan_after_idle_tickets_applied": (
                state.telemetry_scan_after_idle_tickets_applied
            ),
            "last_scan_after_idle_ts": state.last_scan_after_idle_ts,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _status_in_skip_list(status: str, skip_statuses: str) -> bool:
    return status.lower() in {
        item.strip().lower() for item in skip_statuses.split(",") if item.strip()
    }


def _run_command_check(
    project: Path,
    check_id: str,
    command: list[str],
    *,
    stdio_format: str = "human",
) -> bool:
    _stdio_info("+ " + " ".join(command), fmt=stdio_format)
    result = subprocess.run(command, cwd=project, check=False)
    if result.returncode != 0:
        _stdio_info(f"! {check_id} failed (continuing loop)", fmt=stdio_format)
        return False
    return True


def _create_diagnostic_ticket(
    *,
    stdio_format: str = "human",
    project: Path,
    check_id: str,
    summary: str,
    cycle: int,
    queue_status: str,
    queue_name: str,
    priority: str,
    state_dir: Path,
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    marker = state_dir / f"{check_id}.failed"
    if marker.exists():
        _stdio_info(
            f"- diagnostic ticket marker exists for {check_id}, skipping create",
            fmt=stdio_format,
        )
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    from koru.activity_log import activity

    activity("TICKET", f"[AUTO-DIAG] tworzę ticket dla {check_id}", preview=prompt)
    created = create_nl_task(project, prompt, queue_name=queue_name, priority=priority)
    marker.write_text(created.ticket_id, encoding="utf-8")
    activity("TICKET", f"[AUTO-DIAG] {check_id} → {created.ticket_id} (queue={queue_name})")
    _stdio_info(
        f"+ created diagnostic ticket {created.ticket_id} for {check_id} (queue={queue_name})",
        fmt=stdio_format,
    )


def _clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    (state_dir / f"{check_id}.failed").unlink(missing_ok=True)


def _read_wup_health(
    *,
    project: Path,
    state: AutoloopState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
) -> WupHealthResult:
    return _read_wup_health_impl(
        project=project,
        state=state,
        diagnostic_tickets=diagnostic_tickets,
        ticket_queue=ticket_queue,
        state_dir=state_dir,
        create_diagnostic_ticket=_create_diagnostic_ticket,
    )


def _run_idle_diagnostics(
    *,
    stdio_format: str = "human",
    project: Path,
    profile: str,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> DiagnosticResult:
    from koru import autonomous_diagnostics as diag

    def create_ticket(**kwargs: Any) -> None:
        _create_diagnostic_ticket(stdio_format=stdio_format, **kwargs)

    return diag.run_idle_diagnostics(
        stdio_info=_stdio_info,
        is_topology_enabled=_is_topology_enabled,
        run_command=_run_command_check,
        clear_marker=_clear_diagnostic_marker,
        create_ticket=create_ticket,
        make_result=lambda status, failed: DiagnosticResult(status=status, failed=failed),
        stdio_format=stdio_format,
        project=project,
        profile=profile,
        cycle=cycle,
        queue_status=queue_status,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        topology_integration=topology_integration,
    )


def _run_cycle(
    *,
    cycle: int,
    project: Path,
    actor: str,
    queue_name: str | None,
    enable_scan: bool,
    max_iterations: int,
    enable_autopilot: bool,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    include_semcod_artifacts: bool | None,
    client: IDEControlClient | None,
    state: AutoloopState | None = None,
    idle_diagnostics: str = "off",
    diagnostic_tickets: bool = False,
    diagnostic_ticket_queue: str = "default",
    diagnostic_ticket_priority: str = "high",
    diagnostic_state_dir: Path | None = None,
    wup_watch_enabled: bool = False,
    wup_diagnostic_tickets: bool = True,
    wup_ticket_queue: str = "default",
    strict_diagnostics: bool = False,
    autopilot_action: str = "drive",
    autopilot_on_idle_only: bool = False,
    autopilot_skip_on_diagnostics_fail: bool = True,
    autopilot_skip_drive_idle_streak: int = 0,
    autopilot_skip_statuses: str = "waiting_input",
    scan_skip_if_clean: bool = False,
    scan_skip_after: int = 1,
    scan_after_idle_queue: bool = False,
    scan_after_idle_min_interval_seconds: float = 0.0,
    topology_integration: bool = True,
    stdio_format: str = "human",
    correlation_id: str = "",
) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    # Keep historical monkeypatch points on ``koru.autonomous`` working by
    # forwarding the current module callables into the canonical cycle module.
    _autonomous_cycle_module.time = time
    _autonomous_cycle_module.run_scan = run_scan
    _autonomous_cycle_module.run_planfile_queue_loop = run_planfile_queue_loop
    _autonomous_cycle_module._run_process = _run_process
    _autonomous_cycle_module._run_shell_command = _run_shell_command
    _autonomous_cycle_module._run_api_request = _run_api_request
    _autonomous_cycle_module._run_llm_request = _run_llm_request
    _autonomous_cycle_module._default_human_prompt = _default_human_prompt
    _autonomous_cycle_module.resolve_idle_drive_prompt = resolve_idle_drive_prompt
    _autonomous_cycle_module.build_prompt = build_prompt
    _autonomous_cycle_module.write_autonomy_cycle_telemetry = write_autonomy_cycle_telemetry
    _autonomous_cycle_module.create_nl_task = create_nl_task
    _autonomous_cycle_module.is_component_enabled = is_component_enabled
    _autonomous_cycle_module.is_pipeline_enabled = is_pipeline_enabled
    _autonomous_cycle_module._run_idle_diagnostics = _run_idle_diagnostics
    _autonomous_cycle_module._try_os_injector_fallback = _try_os_injector_fallback

    return _autonomous_cycle_module.run_cycle(
        cycle=cycle,
        project=project,
        actor=actor,
        queue_name=queue_name,
        enable_scan=enable_scan,
        max_iterations=max_iterations,
        enable_autopilot=enable_autopilot,
        autopilot_ide=autopilot_ide,
        drive_prompt=drive_prompt,
        submit=submit,
        include_semcod_artifacts=include_semcod_artifacts,
        client=client,
        state=state,
        idle_diagnostics=idle_diagnostics,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_watch_enabled=wup_watch_enabled,
        wup_diagnostic_tickets=wup_diagnostic_tickets,
        wup_ticket_queue=wup_ticket_queue,
        strict_diagnostics=strict_diagnostics,
        autopilot_action=autopilot_action,
        autopilot_on_idle_only=autopilot_on_idle_only,
        autopilot_skip_on_diagnostics_fail=autopilot_skip_on_diagnostics_fail,
        autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
        autopilot_skip_statuses=autopilot_skip_statuses,
        scan_skip_if_clean=scan_skip_if_clean,
        scan_skip_after=scan_skip_after,
        scan_after_idle_queue=scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
        topology_integration=topology_integration,
        stdio_format=stdio_format,
        correlation_id=correlation_id,
    )


def _setup_autonomous_session(
    args: argparse.Namespace,
) -> tuple[str, Path, int]:
    """Initialize autonomous session and return correlation_id, project path, and guard_rc."""
    _env_apply_autoloop_defaults(args)
    correlation_id = str(uuid.uuid4())
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    guard_rc = _guard_existing_autonomous_processes(args, project)
    os.environ["KORU_STDIO_FORMAT"] = args.emit_events
    if args.emit_events == "jsonl":
        write_stdio_event(
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
    _ensure_init(project, force=args.force_init, stdio_format=args.emit_events)
    return correlation_id, project, guard_rc


def _setup_autopilot_daemon(
    args: argparse.Namespace,
    project: Path,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None, Path | None]:
    """Setup autopilot daemon if enabled."""
    client: IDEControlClient | None = None
    daemon: AutopilotDaemon | None = None
    thread: threading.Thread | None = None
    socket_path: Path | None = None
    if args.enable_autopilot:
        socket_path = (args.socket or default_socket_path()).resolve()
        client, daemon, thread = _start_or_reuse_daemon(
            project=project,
            socket_path=socket_path,
            stdio_format=args.emit_events,
        )
    return client, daemon, thread, socket_path


def _configure_loop_state(
    args: argparse.Namespace,
    project: Path,
) -> tuple[bool, str | None, str, AutoloopState, Path, int]:
    """Configure queue flags, autopilot IDE, and loop state."""
    enable_scan, use_all_queues = _effective_flags(args.ticket_sources)
    queue_name = None if use_all_queues else args.queue_name
    lane = _apply_agent_lane_environ(project, args.agent_lane)
    autopilot_ide, _autopilot_ide_source = resolve_autopilot_ide_for_autonomous(
        args.autopilot_ide,
        lane,
        resolve_ide_route_fn=resolve_ide_route,
    )
    loop_state = AutoloopState()
    checkpoint_path = (project / ".planfile/.koru/autonomous-state.json").resolve()
    restored_cycle = _load_loop_checkpoint(
        checkpoint_path,
        state=loop_state,
        stdio_format=args.emit_events,
    )
    return enable_scan, queue_name, autopilot_ide, loop_state, checkpoint_path, restored_cycle


def _run_mcp_provision(project: Path, stdio_format: str) -> bool:
    """Run MCP workspace provision and return True if it ran."""
    mcp_provision_ran = False
    try:
        from koru.mcp_provision import ensure_koru_mcp_not_disabled

        for row in ensure_koru_mcp_not_disabled(project):
            mcp_provision_ran = True
            _stdio_info(
                f"koru autonomous: {row['action']} → {row['path']}",
                fmt=stdio_format,
            )
    except (OSError, TypeError, ValueError) as exc:
        _stdio_info(
            f"koru autonomous: mcp workspace refresh skipped ({exc})",
            fmt=stdio_format,
        )
    return mcp_provision_ran


def _setup_autopilot_plugin(
    args: argparse.Namespace,
    autopilot_ide: str,
    socket_path: Path | None,
    client: IDEControlClient | None,
) -> bool | None:
    """Install and wait for autopilot plugin if enabled."""
    plugin_connected: bool | None = None
    if args.enable_autopilot and socket_path is not None:
        plugin_result = install_plugin_for_ide(ide=autopilot_ide, socket_path=socket_path)
        _stdio_info(format_plugin_install_result(plugin_result), fmt=args.emit_events)
        if client is not None and not _allow_keyboard_autopilot_fallback():
            plugin_ready = _wait_for_autopilot_plugin(
                client,
                autopilot_ide,
                timeout_seconds=max(0.0, args.autopilot_plugin_wait_seconds),
            )
            plugin_connected = plugin_ready
            if plugin_ready:
                _stdio_info(
                    f"koru autonomous: autopilot plugin connected ide={autopilot_ide}",
                    fmt=args.emit_events,
                )
            else:
                _stdio_info(
                    "koru autonomous: no connected autopilot plugin "
                    f"for ide={autopilot_ide} after "
                    f"{max(0.0, args.autopilot_plugin_wait_seconds):.1f}s; continuing",
                    fmt=args.emit_events,
                )
    return plugin_connected


def _run_operator_pipeline(
    args: argparse.Namespace,
    project: Path,
    startup_probe: Any,
    plugin_connected: bool | None,
    mcp_provision_ran: bool,
    correlation_id: str,
) -> None:
    """Run operator pipeline if enabled."""
    for hint in format_post_startup_operator_hints(
        startup_probe,
        plugin_connected=plugin_connected,
    ):
        _stdio_info(hint, fmt=args.emit_events)

    if args.operator_pipeline:
        run_startup_operator_pipeline(
            project=project,
            probe=startup_probe,
            plugin_connected=plugin_connected,
            stdio_format=args.emit_events,
            create_tickets=args.operator_tickets,
            ticket_queue=args.operator_ticket_queue,
            ticket_priority=args.operator_ticket_priority,
            mcp_already_bootstrapped=mcp_provision_ran,
            correlation_id=correlation_id,
        )


def _unblock_queue_if_needed(project: Path, stdio_format: str) -> None:
    """Release in-progress tickets if KORU_QUEUE_UNBLOCK is set."""
    if os.environ.get("KORU_QUEUE_UNBLOCK", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        released = release_in_progress_tickets(project, runner=_run_process)
        if released:
            _stdio_info(
                f"koru autonomous: queue unblock — reopened {released} in_progress ticket(s)",
                fmt=stdio_format,
            )


def _restart_daemon_if_needed(
    args: argparse.Namespace,
    client: IDEControlClient | None,
    socket_path: Path | None,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    autopilot_socket_observed_at_boot: bool,
    project: Path,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None]:
    """Restart daemon if socket is missing."""
    if (
        args.enable_autopilot
        and client is not None
        and socket_path is not None
        and not socket_path.exists()
        and (autopilot_socket_observed_at_boot or daemon is not None or thread is not None)
    ):
        _stdio_info(
            f"koru autonomous: autopilot socket missing at {socket_path}; "
            "restarting or taking over daemon…",
            fmt=args.emit_events,
        )
        if daemon is not None:
            with contextlib.suppress(OSError):
                daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        client, daemon, thread = _start_or_reuse_daemon(
            project=project,
            socket_path=socket_path,
            stdio_format=args.emit_events,
        )
    return client, daemon, thread


def _handle_cycle_exit_conditions(
    args: argparse.Namespace,
    queue_result: Any,
    cycle: int,
    correlation_id: str,
) -> bool:
    """Check if we should exit the cycle loop. Returns True if should exit."""
    if args.stop_on_waiting_input and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
        if args.emit_events == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": "waiting_input", "cycle": cycle},
            )
        _stdio_info(
            "koru autonomous: queue is waiting_input; stopping until "
            "human/manual ticket recovery marks it ready or done",
            fmt=args.emit_events,
        )
        return True

    if args.max_cycles > 0 and cycle >= args.max_cycles:
        if args.emit_events == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={
                    "reason": "max_cycles",
                    "cycle": cycle,
                    "max_cycles": args.max_cycles,
                },
            )
        _stdio_info(
            f"koru autonomous: reached max-cycles={args.max_cycles}; stopping",
            fmt=args.emit_events,
        )
        return True
    return False


def _cleanup_autonomous_session(
    previous_stdio_format_env: str | None,
    previous_sigterm: Any,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    wup_process: Any,
    stdio_format: str,
) -> None:
    """Clean up autonomous session resources."""
    if previous_stdio_format_env is None:
        os.environ.pop("KORU_STDIO_FORMAT", None)
    else:
        os.environ["KORU_STDIO_FORMAT"] = previous_stdio_format_env
    signal.signal(signal.SIGTERM, previous_sigterm)
    if daemon is not None:
        daemon.stop()
    if thread is not None:
        thread.join(timeout=2.0)
    _stop_process(wup_process, "WUP watcher", stdio_format=stdio_format)


def _run_autonomous_cycle(
    *,
    cycle: int,
    args: argparse.Namespace,
    project: Path,
    client: object,
    daemon: object,
    thread: threading.Thread,
    socket_path: Path,
    autopilot_socket_observed_at_boot: bool,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    loop_state: object,
    checkpoint_path: Path,
    diagnostic_state_dir: Path,
    wup_process: subprocess.Popen | None,
    correlation_id: str,
) -> bool:
    """Run one autonomous cycle. Returns True if the loop should exit."""
    if args.emit_events == "human":
        print(f"\n=== koru autonomous cycle #{cycle} ===")
    client, daemon, thread = _restart_daemon_if_needed(
        args,
        client,
        socket_path,
        daemon,
        thread,
        autopilot_socket_observed_at_boot,
        project,
    )
    _scan_result, queue_result, _autopilot_status, diag_result = _run_cycle(
        cycle=cycle,
        project=project,
        actor=args.actor,
        queue_name=queue_name,
        enable_scan=enable_scan,
        max_iterations=args.max_iterations,
        enable_autopilot=args.enable_autopilot,
        autopilot_ide=autopilot_ide,
        drive_prompt=args.drive_prompt,
        submit=args.submit,
        include_semcod_artifacts=args.semcod_artifacts,
        client=client,
        state=loop_state,
        idle_diagnostics=args.idle_diagnostics,
        diagnostic_tickets=args.diagnostic_tickets,
        diagnostic_ticket_queue=args.diagnostic_ticket_queue,
        diagnostic_ticket_priority=args.diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_watch_enabled=wup_process is not None,
        wup_diagnostic_tickets=args.wup_diagnostic_tickets,
        wup_ticket_queue=args.wup_ticket_queue,
        strict_diagnostics=args.strict_diagnostics,
        autopilot_action=args.autopilot_action,
        autopilot_on_idle_only=args.autopilot_on_idle_only,
        autopilot_skip_on_diagnostics_fail=args.autopilot_skip_on_diagnostics_fail,
        autopilot_skip_drive_idle_streak=args.autopilot_skip_drive_idle_streak,
        autopilot_skip_statuses=args.autopilot_skip_statuses,
        scan_skip_if_clean=args.scan_skip_if_clean,
        scan_skip_after=args.scan_skip_after,
        scan_after_idle_queue=args.scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=args.scan_after_idle_min_interval,
        topology_integration=args.topology_integration,
        stdio_format=args.emit_events,
        correlation_id=correlation_id,
    )
    _save_loop_checkpoint(
        checkpoint_path,
        cycle=cycle,
        state=loop_state,
        queue_status=queue_result.last_status,
        waiting_ticket=_queue_loop_waiting_ticket_label(queue_result),
    )

    if _handle_cycle_exit_conditions(args, queue_result, cycle, correlation_id):
        return True

    effective_sleep = _compute_backoff_sleep(
        args.sleep_seconds,
        loop_state.stagnation_streak,
        args.max_sleep_seconds,
        args.backoff_on_stagnation,
    )
    if (
        queue_result.last_status == "idle"
        and loop_state.last_message_sent_ts > 0
        and time.time() - loop_state.last_message_sent_ts < 120.0
    ):
        effective_sleep = min(effective_sleep, 15.0)
    _stdio_info(
        f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
        f"waiting={_queue_loop_waiting_ticket_label(queue_result)} "
        f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
        f"autopilot={_autopilot_status} sleep={effective_sleep}s",
        fmt=args.emit_events,
    )
    if effective_sleep > 0:
        time.sleep(effective_sleep)
    return False


def _action_up(args: argparse.Namespace) -> int:
    previous_stdio_format_env = os.environ.get("KORU_STDIO_FORMAT")
    correlation_id, project, guard_rc = _setup_autonomous_session(args)
    if guard_rc:
        return guard_rc

    _apply_agent_lane_environ(project, args.agent_lane)
    startup_probe = build_startup_probe(
        project,
        agent_lane_cli=args.agent_lane,
        autopilot_ide_cli=args.autopilot_ide,
        resolve_project_lane=resolve_project_agent_lane,
    )
    for line in format_startup_banner(startup_probe):
        _stdio_info(line, fmt=args.emit_events)

    client, daemon, thread, socket_path = _setup_autopilot_daemon(args, project)
    autopilot_socket_observed_at_boot = (
        bool(socket_path and socket_path.exists()) if args.enable_autopilot else False
    )

    enable_scan, queue_name, autopilot_ide, loop_state, checkpoint_path, restored_cycle = (
        _configure_loop_state(args, project)
    )

    diagnostic_state_dir = (project / args.diagnostic_state_dir).resolve()
    wup_config = _build_wup_watch_config(args, project)
    wup_process = _start_wup_watch(
        wup_config,
        topology_integration=args.topology_integration,
        stdio_format=args.emit_events,
    )

    stopped_by_sigterm = False

    def _sigterm_to_interrupt(_signo: int, _frame: object) -> None:
        nonlocal stopped_by_sigterm
        stopped_by_sigterm = True
        _stdio_info(
            "koru autonomous: SIGTERM received (typical: OOM killer, systemd stop, "
            "`kill`, cgroup memory limit, or IDE tool timeout) — cleaning up",
            fmt=args.emit_events,
        )
        raise KeyboardInterrupt()

    previous_sigterm = signal.signal(signal.SIGTERM, _sigterm_to_interrupt)
    try:
        mcp_provision_ran = _run_mcp_provision(project, args.emit_events)
        plugin_connected = _setup_autopilot_plugin(args, autopilot_ide, socket_path, client)
        _run_operator_pipeline(
            args, project, startup_probe, plugin_connected, mcp_provision_ran, correlation_id
        )
        _unblock_queue_if_needed(project, args.emit_events)

        cycle = restored_cycle or 0
        while True:
            cycle += 1
            should_exit = _run_autonomous_cycle(
                cycle=cycle,
                args=args,
                project=project,
                client=client,
                daemon=daemon,
                thread=thread,
                socket_path=socket_path,
                autopilot_socket_observed_at_boot=autopilot_socket_observed_at_boot,
                queue_name=queue_name,
                enable_scan=enable_scan,
                autopilot_ide=autopilot_ide,
                loop_state=loop_state,
                checkpoint_path=checkpoint_path,
                diagnostic_state_dir=diagnostic_state_dir,
                wup_process=wup_process,
                correlation_id=correlation_id,
            )
            if should_exit:
                return 0
    except KeyboardInterrupt:
        stop_reason = "sigterm" if stopped_by_sigterm else "keyboard_interrupt"
        if args.emit_events == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": stop_reason},
            )
        if stopped_by_sigterm:
            _stdio_info(
                "\nkoru autonomous: stopped after SIGTERM (WUP watcher stopped; "
                "if scan was heavy, try --no-semcod-artifacts or "
                "KORU_SCAN_SEMCOD_ARTIFACTS=0)",
                fmt=args.emit_events,
            )
        else:
            _stdio_info("\nkoru autonomous: interrupted (Ctrl+C)", fmt=args.emit_events)
        return 0
    finally:
        _cleanup_autonomous_session(
            previous_stdio_format_env,
            previous_sigterm,
            daemon,
            thread,
            wup_process,
            args.emit_events,
        )


def autonomous_main(argv: list[str], *, invoked_as_auto: bool = False) -> int:
    if not argv:
        argv = ["up"]
    elif argv[0] == "safe-up":
        argv = [
            "up",
            "--ticket-sources",
            "queue",
            "--idle-diagnostics",
            "quick",
            "--diagnostic-tickets",
            "--autopilot-action",
            "off",
            "--no-autopilot",
            "--max-cycles",
            "1",
            "--no-semcod-artifacts",
            *argv[1:],
        ]
    elif argv[0] != "up" and argv[0] not in ("-h", "--help"):
        argv = ["up", *argv]
    args = _build_parser().parse_args(argv)
    if invoked_as_auto:
        args.replace_existing_global = True
        if not args.allow_duplicate and not args.replace_existing:
            args.replace_existing = True
    elif not hasattr(args, "replace_existing_global"):
        args.replace_existing_global = False
    if args.action == "up":
        return _action_up(args)
    return 2


__all__ = [
    "WupHealthResult",
    "WupWatchConfig",
    "_read_wup_health",
    "_wup_watch_command",
    "autonomous_main",
    "stop_prior_autonomous_for_auto_start",
]
