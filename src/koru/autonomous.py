"""One-command autonomous mode for freshly installed koru.

`koru autonomous up` (or `koru autonomous` with the same flags) bootstraps
the project if needed, applies ``--agent-lane`` exports like
``shell-env.sh``, then runs scan + queue + autopilot in a loop.
By default it also starts ``koru serve`` in the background so the local
dashboard (auto-refresh ~5s) tracks queue/context; use ``--no-serve`` to skip.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .autopilot import default_socket_path
from .autopilot.client import AutopilotClient
from .autopilot.daemon import AutopilotDaemon
from .autopilot.plugin_installer import format_plugin_install_result, install_plugin_for_ide
from .agents import agent_lane_environment
from .init import init_project, resolve_project_agent_lane
from .queue import (
    QueueLoopResult,
    default_human_prompt as _default_human_prompt,
    run_api_request as _run_api_request,
    run_llm_request as _run_llm_request,
    run_planfile_queue_loop,
    run_process as _run_process,
    run_shell_command as _run_shell_command,
)
from .scan import ScanResult, run_scan
from .tasks import create_nl_task
from .topology import is_component_enabled, is_pipeline_enabled

_VALID_AUTOPILOT_IDE = frozenset({"auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"})
_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


@dataclass(frozen=True)
class DiagnosticResult:
    status: str
    failed: list[str]


@dataclass
class AutoloopState:
    previous_signature: str = ""
    stagnation_streak: int = 0
    scan_clean_streak: int = 0
    scan_last_head: str = ""
    wup_seen_events: int = 0


@dataclass(frozen=True)
class WupWatchConfig:
    enabled: bool
    mode: str
    project: Path
    deps_file: str
    scenarios_dir: str
    testql_bin: str
    track_dir: str
    debounce: int
    cooldown: int
    cpu_throttle: float
    quick_limit: int
    config: Path | None


@dataclass(frozen=True)
class WupHealthResult:
    status: str
    failing_services: list[str]
    new_events: int


def _resolve_autopilot_ide(cli_value: str) -> str:
    """``KORU_AUTOPILOT_IDE`` overrides CLI when set to a specific IDE (not 'auto')."""
    raw = os.environ.get("KORU_AUTOPILOT_IDE", "").strip().lower()
    # env 'auto' should not override explicit CLI value
    if raw in _VALID_AUTOPILOT_IDE and raw != "auto":
        return raw
    return cli_value


def _apply_agent_lane_environ(project: Path, agent_lane: str) -> str | None:
    """Set lane exports in ``os.environ``; returns lane id or ``None`` if skipped."""
    lane = resolve_project_agent_lane(project, agent_lane)
    if lane is None:
        return None
    for key, val in agent_lane_environment(lane).items():
        os.environ[key] = val
    return lane


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
            "all: scan + all queues."
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
        help="Continue autonomous loop even when queue status is waiting_input.",
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
        "--topology-integration",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Respect .koru/topology.yaml component and pipeline toggles.",
    )
    up.add_argument(
        "--wup-watch",
        action="store_true",
        help="Start WUP watcher in autonomous mode and monitor its health output.",
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
    up.set_defaults(
        submit=True,
        enable_autopilot=True,
        enable_serve=True,
        stop_on_waiting_input=True,
        semcod_artifacts=True,
    )

    return parser


def _env_default_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_apply_autoloop_defaults(args: argparse.Namespace) -> None:
    args.idle_diagnostics = os.environ.get(
        "IDLE_DIAGNOSTICS_PROFILE",
        "full" if _env_default_bool("ENABLE_IDLE_DIAGNOSTICS", False) else args.idle_diagnostics,
    )
    args.diagnostic_tickets = _env_default_bool(
        "ENABLE_DIAGNOSTIC_TICKETS", args.diagnostic_tickets
    )
    args.diagnostic_ticket_queue = os.environ.get(
        "DIAGNOSTIC_TICKET_QUEUE", args.diagnostic_ticket_queue
    )
    args.diagnostic_ticket_priority = os.environ.get(
        "DIAGNOSTIC_TICKET_PRIORITY", args.diagnostic_ticket_priority
    )
    args.diagnostic_state_dir = os.environ.get("DIAG_STATE_DIR", args.diagnostic_state_dir)
    args.strict_diagnostics = _env_default_bool("STRICT_DIAGNOSTICS", args.strict_diagnostics)
    args.autopilot_action = os.environ.get("AUTOPILOT_ACTION", args.autopilot_action).lower()
    if args.autopilot_action not in {"drive", "handoff", "off"}:
        args.autopilot_action = "drive"
    args.autopilot_on_idle_only = _env_default_bool(
        "AUTOPILOT_ON_IDLE_ONLY", args.autopilot_on_idle_only
    )
    args.autopilot_skip_on_diagnostics_fail = _env_default_bool(
        "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL", args.autopilot_skip_on_diagnostics_fail
    )
    args.autopilot_skip_statuses = os.environ.get(
        "AUTOPILOT_SKIP_STATUSES", args.autopilot_skip_statuses
    )
    args.backoff_on_stagnation = _env_default_bool(
        "BACKOFF_ON_STAGNATION", args.backoff_on_stagnation
    )
    args.scan_skip_if_clean = _env_default_bool("SCAN_SKIP_IF_CLEAN", args.scan_skip_if_clean)
    args.topology_integration = _env_default_bool(
        "TOPOLOGY_INTEGRATION", args.topology_integration
    )
    args.wup_watch = _env_default_bool("WUP_WATCH", args.wup_watch)
    args.wup_mode = os.environ.get("WUP_MODE", args.wup_mode).lower()
    if args.wup_mode not in {"default", "testql"}:
        args.wup_mode = "testql"
    args.wup_deps = os.environ.get("WUP_DEPS", args.wup_deps)
    args.wup_scenarios_dir = os.environ.get("WUP_SCENARIOS_DIR", args.wup_scenarios_dir)
    args.wup_testql_bin = os.environ.get("WUP_TESTQL_BIN", args.wup_testql_bin)
    args.wup_track_dir = os.environ.get("WUP_TRACK_DIR", args.wup_track_dir)
    args.wup_diagnostic_tickets = _env_default_bool(
        "WUP_DIAGNOSTIC_TICKETS", args.wup_diagnostic_tickets
    )
    args.wup_ticket_queue = os.environ.get("WUP_TICKET_QUEUE", args.wup_ticket_queue)


def _ensure_init(project: Path, *, force: bool) -> None:
    config_path = project / ".planfile" / "config.yaml"
    if config_path.exists() and not force:
        return
    report = init_project(project, force=force)
    print(f"koru autonomous: init {'re-' if force else ''}done at {report.project}")


def _start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
) -> tuple[AutopilotClient, AutopilotDaemon | None, threading.Thread | None]:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
    if probe.is_running():
        print(f"koru autonomous: reusing autopilot daemon on {socket_path}")
        return AutopilotClient(socket_path=socket_path), None, None

    daemon = AutopilotDaemon(socket_path=socket_path, project=project, log=print)
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    print(f"koru autonomous: started autopilot daemon on {socket_path}")
    return AutopilotClient(socket_path=socket_path), daemon, thread


def _effective_flags(ticket_sources: str) -> tuple[bool, bool]:
    if ticket_sources == "queue":
        return False, False
    if ticket_sources == "scan":
        return True, False
    return True, True


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


def _status_in_skip_list(status: str, skip_statuses: str) -> bool:
    return status.lower() in {
        item.strip().lower() for item in skip_statuses.split(",") if item.strip()
    }


def _run_command_check(project: Path, check_id: str, command: list[str]) -> bool:
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=project, check=False)
    if result.returncode != 0:
        print(f"! {check_id} failed (continuing loop)")
        return False
    return True


def _create_diagnostic_ticket(
    *,
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
        print(f"- diagnostic ticket marker exists for {check_id}, skipping create")
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    created = create_nl_task(project, prompt, queue_name=queue_name, priority=priority)
    marker.write_text(created.ticket_id, encoding="utf-8")
    print(f"+ created diagnostic ticket {created.ticket_id} for {check_id} (queue={queue_name})")


def _clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    (state_dir / f"{check_id}.failed").unlink(missing_ok=True)


def _build_wup_watch_config(args: argparse.Namespace, project: Path) -> WupWatchConfig:
    return WupWatchConfig(
        enabled=bool(args.wup_watch),
        mode=args.wup_mode,
        project=project,
        deps_file=args.wup_deps,
        scenarios_dir=args.wup_scenarios_dir,
        testql_bin=args.wup_testql_bin,
        track_dir=args.wup_track_dir,
        debounce=args.wup_debounce,
        cooldown=args.wup_cooldown,
        cpu_throttle=args.wup_cpu_throttle,
        quick_limit=args.wup_quick_limit,
        config=args.wup_config,
    )


def _wup_watch_command(config: WupWatchConfig) -> list[str]:
    command = [
        "wup",
        "watch",
        str(config.project),
        "--deps",
        config.deps_file,
        "--cpu-throttle",
        str(config.cpu_throttle),
        "--debounce",
        str(config.debounce),
        "--cooldown",
        str(config.cooldown),
        "--mode",
        config.mode,
    ]
    if config.mode == "testql":
        command.extend(
            [
                "--scenarios-dir",
                config.scenarios_dir,
                "--testql-bin",
                config.testql_bin,
                "--track-dir",
                config.track_dir,
                "--quick-limit",
                str(config.quick_limit),
            ]
        )
    if config.config is not None:
        command.extend(["--config", str(config.config)])
    return command


def _start_wup_watch(config: WupWatchConfig, *, topology_integration: bool) -> subprocess.Popen | None:
    if not config.enabled:
        return None
    if not _is_topology_enabled(
        config.project, "gate:wup", fallback=True, enabled=topology_integration
    ):
        print("koru autonomous: WUP watch disabled in topology")
        return None
    if shutil.which("wup") is None:
        print("koru autonomous: WUP watch requested but `wup` is not in PATH")
        return None
    if not (config.project / "wup.yaml").is_file() and config.config is None:
        print("koru autonomous: WUP watch requested but no wup.yaml found")
        return None
    command = _wup_watch_command(config)
    print("+ " + " ".join(command))
    process = subprocess.Popen(command, cwd=config.project)
    print(f"koru autonomous: started WUP watcher pid={process.pid} mode={config.mode}")
    return process


def _stop_process(process: subprocess.Popen | None, label: str) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    print(f"koru autonomous: stopped {label}")


def _read_wup_health(
    *,
    project: Path,
    state: AutoloopState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
) -> WupHealthResult:
    health_path = project / ".wup" / "service-health.json"
    events_path = project / ".wup" / "service-health-events.jsonl"
    health: dict[str, dict] = {}
    if health_path.is_file():
        try:
            payload = json.loads(health_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                health = {str(k): v for k, v in payload.items() if isinstance(v, dict)}
        except (OSError, json.JSONDecodeError):
            health = {}
    failing = [
        service
        for service, data in sorted(health.items())
        if str(data.get("status", "")).lower() in {"down", "failed", "failure", "error"}
    ]
    if diagnostic_tickets:
        for service in failing:
            data = health.get(service, {})
            stage = str(data.get("stage") or "wup")
            message = str(data.get("message") or "WUP reported failing service")
            track_file = str(data.get("track_file") or "")
            _create_diagnostic_ticket(
                project=project,
                check_id=f"wup-{service}",
                summary=f"WUP service={service} stage={stage} message={message} track={track_file}",
                cycle=0,
                queue_status="wup_failure",
                queue_name=ticket_queue,
                priority="high",
                state_dir=state_dir,
            )
    event_count = 0
    if events_path.is_file():
        try:
            with events_path.open("r", encoding="utf-8") as handle:
                event_count = sum(1 for line in handle if line.strip())
        except OSError:
            event_count = state.wup_seen_events
    new_events = max(0, event_count - state.wup_seen_events)
    state.wup_seen_events = max(state.wup_seen_events, event_count)
    status = "failed" if failing else ("changed" if new_events else "ok")
    return WupHealthResult(status=status, failing_services=failing, new_events=new_events)


def _run_idle_diagnostics(
    *,
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
    profile = profile.lower()
    if profile in {"off", "none"}:
        print("koru autonomous: idle diagnostics profile=off (skipping)")
        return DiagnosticResult(status="off", failed=[])
    if not _is_topology_enabled(
        project, "idle-diagnostics", fallback=True, enabled=topology_integration
    ):
        print("koru autonomous: idle diagnostics disabled in topology")
        return DiagnosticResult(status="disabled(topology)", failed=[])
    print(f"koru autonomous: queue idle -> running semcod diagnostics (profile={profile})")
    checks: list[tuple[str, str, list[str]]] = []
    if shutil.which("regix"):
        checks.append(("regix", "regix compare HEAD --local --format rich", ["regix", "compare", "HEAD", "--local", "--format", "rich"]))
    if shutil.which("wup") and (project / "wup.yaml").is_file():
        checks.append(("wup", "wup status", ["wup", "status"]))
    if profile in {"full", "deep"}:
        if shutil.which("redup"):
            checks.append(("redup", "redup scan . --min-lines 10", ["redup", "scan", ".", "--min-lines", "10"]))
        if shutil.which("testql") and any(project.rglob("*.testql.toon.yaml")):
            checks.append(("testql", "testql suite --pattern *.testql.toon.yaml --output console --fail-fast", ["testql", "suite", "--pattern", "*.testql.toon.yaml", "--output", "console", "--fail-fast"]))
        if shutil.which("redsl"):
            checks.append(("redsl", "redsl gate check .", ["redsl", "gate", "check", "."]))
        if (project / "scripts" / "sumr-refresh.sh").is_file():
            checks.append(("sumr", "bash scripts/sumr-refresh.sh --status", ["bash", "scripts/sumr-refresh.sh", "--status"]))
    failed: list[str] = []
    diagnostic_state_dir.mkdir(parents=True, exist_ok=True)
    for check_id, summary, command in checks:
        if not _is_topology_enabled(project, check_id, fallback=True, enabled=topology_integration):
            print(f"- {check_id} disabled in topology, skipping")
            continue
        if _run_command_check(project, check_id, command):
            _clear_diagnostic_marker(diagnostic_state_dir, check_id)
            continue
        failed.append(check_id)
        if diagnostic_tickets:
            _create_diagnostic_ticket(
                project=project,
                check_id=check_id,
                summary=summary,
                cycle=cycle,
                queue_status=queue_status,
                queue_name=diagnostic_ticket_queue,
                priority=diagnostic_ticket_priority,
                state_dir=diagnostic_state_dir,
            )
    return DiagnosticResult(status="failed" if failed else "ok", failed=failed)


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
    client: AutopilotClient | None,
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
    autopilot_skip_statuses: str = "waiting_input",
    scan_skip_if_clean: bool = False,
    scan_skip_after: int = 1,
    topology_integration: bool = True,
) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    state = state or AutoloopState()
    scan_result: ScanResult | None = None
    if enable_scan:
        if not _is_topology_enabled(project, "scan:on-change", fallback=True, enabled=topology_integration):
            print("- koru scan --apply skipped (scan:on-change disabled in topology)")
        else:
            head_now = _current_head(project)
            if (
                scan_skip_if_clean
                and state.scan_clean_streak >= scan_skip_after
                and head_now
                and head_now == state.scan_last_head
            ):
                print(
                    f"- koru scan --apply skipped "
                    f"(clean_streak={state.scan_clean_streak}, HEAD unchanged)"
                )
            else:
                print("+ koru scan --apply" + (" --semcod-artifacts" if include_semcod_artifacts else ""))
                scan_result = run_scan(
                    project=project, apply=True, include_semcod_artifacts=include_semcod_artifacts
                )
                print(
                    f"  scan: suggestions={len(scan_result.suggestions)} "
                    f"applied={len(scan_result.applied)} skipped={len(scan_result.skipped)}"
                )
                if not scan_result.suggestions:
                    state.scan_clean_streak += 1
                else:
                    state.scan_clean_streak = 0
                state.scan_last_head = head_now

    if not _is_topology_enabled(project, "autoloop:queue", fallback=True, enabled=topology_integration):
        print("- autoloop queue phase skipped (autoloop:queue disabled in topology)")
        queue_result = QueueLoopResult(0, [], [], [], "disabled", "")
    else:
        print(
            "+ koru --queue --loop "
            f"--max-iterations {max_iterations}"
            + (" --all-queues" if queue_name is None else f" --queue-name {queue_name}")
        )
        queue_result = run_planfile_queue_loop(
            project=project,
            actor=actor,
            queue_name=queue_name,
            max_iterations=max_iterations,
            planfile_runner=_run_process,
            shell_runner=_run_shell_command,
            api_runner=_run_api_request,
            llm_runner=_run_llm_request,
            prompt_runner=_default_human_prompt,
        )
        print(f"  queue: {queue_result.summary()}")

    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    signature = f"{queue_result.last_status}:{waiting_ticket}"
    if state.previous_signature and state.previous_signature == signature:
        state.stagnation_streak += 1
    else:
        state.stagnation_streak = 0
    state.previous_signature = signature

    diag_result = DiagnosticResult(status="skipped", failed=[])
    if queue_result.last_status == "idle" and idle_diagnostics not in {"off", "none"}:
        diag_result = _run_idle_diagnostics(
            project=project,
            profile=idle_diagnostics,
            cycle=cycle,
            queue_status=queue_result.last_status,
            diagnostic_tickets=diagnostic_tickets,
            diagnostic_ticket_queue=diagnostic_ticket_queue,
            diagnostic_ticket_priority=diagnostic_ticket_priority,
            diagnostic_state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
            topology_integration=topology_integration,
        )
    wup_health = WupHealthResult(status="skipped", failing_services=[], new_events=0)
    if wup_watch_enabled:
        wup_health = _read_wup_health(
            project=project,
            state=state,
            diagnostic_tickets=wup_diagnostic_tickets,
            ticket_queue=wup_ticket_queue,
            state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
        )
        if wup_health.status != "ok":
            print(
                f"koru autonomous: WUP health={wup_health.status} "
                f"failing={','.join(wup_health.failing_services) or '-'} "
                f"new_events={wup_health.new_events}"
            )
            if diag_result.status in {"skipped", "off", "ok"} and wup_health.status == "failed":
                diag_result = DiagnosticResult(status="failed", failed=["wup"])
    if strict_diagnostics and diag_result.status == "failed":
        print("koru autonomous: strict diagnostics enabled -> stopping on diagnostics failure")
        raise SystemExit(2)

    autopilot_status = "skipped"
    if enable_autopilot and client is not None:
        if not _is_topology_enabled(project, "autopilot:drive", fallback=True, enabled=topology_integration):
            print("- autopilot skipped (autopilot:drive disabled in topology)")
            autopilot_status = "skipped(topology)"
        elif autopilot_action == "off":
            print("- autopilot action set to off, skipping")
        elif autopilot_on_idle_only and queue_result.last_status != "idle":
            print("- autopilot skipped (idle_only)")
            autopilot_status = "skipped(idle_only)"
        elif autopilot_skip_on_diagnostics_fail and diag_result.status == "failed":
            print("- autopilot skipped (diagnostics_fail)")
            autopilot_status = "skipped(diagnostics_fail)"
        elif state.stagnation_streak > 0 and _status_in_skip_list(
            queue_result.last_status, autopilot_skip_statuses
        ):
            print(f"- autopilot skipped (stuck_{queue_result.last_status}_streak_{state.stagnation_streak})")
            autopilot_status = f"skipped(stuck_{queue_result.last_status})"
        elif autopilot_action == "handoff":
            reply = client.drive(drive_prompt, submit=submit, ide=autopilot_ide)
            ok = bool(reply.get("ok", True))
            autopilot_status = "ok" if ok else "failed"
        elif queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
            # Queue needs human/LLM attention — drive the actual ticket
            # content instead of the generic drive_prompt so the IDE's LLM
            # knows exactly what to work on.
            ticket_prompt = queue_result.last_message.strip() if queue_result.last_message else ""
            if ticket_prompt:
                reply = client.drive(ticket_prompt, submit=submit, ide=autopilot_ide)
                ok = bool(reply.get("ok", True))
                autopilot_status = "ok" if ok else "failed"
                if ok:
                    backend = reply.get("backend", "?")
                    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
                    print(
                        f"  autopilot: ok (ticket={waiting_ticket}, ide={autopilot_ide}, backend={backend})"
                    )
                else:
                    message = reply.get("message", "unknown error")
                    print(f"  autopilot: failed ({message})")
            else:
                print(f"  autopilot: skipped (queue_status={queue_result.last_status}, empty message)")
        else:
            reply = client.drive(drive_prompt, submit=submit, ide=autopilot_ide)
            ok = bool(reply.get("ok", True))
            autopilot_status = "ok" if ok else "failed"
            if ok:
                backend = reply.get("backend", "?")
                print(f"  autopilot: ok (ide={autopilot_ide}, backend={backend})")
            else:
                message = reply.get("message", "unknown error")
                print(f"  autopilot: failed ({message})")

    print(
        f"koru autonomous: cycle={cycle} queue={queue_result.last_status} "
        f"diagnostics={diag_result.status} wup={wup_health.status} autopilot={autopilot_status}"
    )
    return scan_result, queue_result, autopilot_status, diag_result


def _action_up(args: argparse.Namespace) -> int:
    _env_apply_autoloop_defaults(args)
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    _ensure_init(project, force=args.force_init)

    lane = _apply_agent_lane_environ(project, args.agent_lane)
    if lane is not None:
        print(f"koru autonomous: agent-lane={lane} (env applied)")

    client: AutopilotClient | None = None
    daemon: AutopilotDaemon | None = None
    thread: threading.Thread | None = None
    socket_path: Path | None = None
    if args.enable_autopilot:
        socket_path = (args.socket or default_socket_path()).resolve()
        client, daemon, thread = _start_or_reuse_daemon(project=project, socket_path=socket_path)

    # Avoid reconnect noise in tests / misconfigured hosts where no socket ever
    # existed; still recover when the socket disappears after a healthy boot.
    autopilot_socket_observed_at_boot = (
        bool(socket_path and socket_path.exists()) if args.enable_autopilot else False
    )

    enable_scan, use_all_queues = _effective_flags(args.ticket_sources)
    queue_name = None if use_all_queues else args.queue_name
    autopilot_ide = _resolve_autopilot_ide(args.autopilot_ide)
    loop_state = AutoloopState()
    diagnostic_state_dir = (project / args.diagnostic_state_dir).resolve()
    wup_config = _build_wup_watch_config(args, project)
    wup_process = _start_wup_watch(
        wup_config,
        topology_integration=args.topology_integration,
    )

    if args.enable_autopilot and socket_path is not None:
        plugin_result = install_plugin_for_ide(ide=autopilot_ide, socket_path=socket_path)
        print(format_plugin_install_result(plugin_result))

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n=== koru autonomous cycle #{cycle} ===")
            if (
                args.enable_autopilot
                and client is not None
                and socket_path is not None
                and not socket_path.exists()
                and (
                    autopilot_socket_observed_at_boot
                    or daemon is not None
                    or thread is not None
                )
            ):
                print(
                    f"koru autonomous: autopilot socket missing at {socket_path}; "
                    "restarting or taking over daemon…"
                )
                if daemon is not None:
                    try:
                        daemon.stop()
                    except OSError:
                        pass
                if thread is not None:
                    thread.join(timeout=2.0)
                client, daemon, thread = _start_or_reuse_daemon(
                    project=project, socket_path=socket_path
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
                wup_watch_enabled=args.wup_watch,
                wup_diagnostic_tickets=args.wup_diagnostic_tickets,
                wup_ticket_queue=args.wup_ticket_queue,
                strict_diagnostics=args.strict_diagnostics,
                autopilot_action=args.autopilot_action,
                autopilot_on_idle_only=args.autopilot_on_idle_only,
                autopilot_skip_on_diagnostics_fail=args.autopilot_skip_on_diagnostics_fail,
                autopilot_skip_statuses=args.autopilot_skip_statuses,
                scan_skip_if_clean=args.scan_skip_if_clean,
                scan_skip_after=args.scan_skip_after,
                topology_integration=args.topology_integration,
            )

            if (
                args.stop_on_waiting_input
                and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES
            ):
                print(
                    "koru autonomous: queue is waiting_input; stopping until "
                    "human/manual ticket recovery marks it ready or done"
                )
                return 0

            if args.max_cycles > 0 and cycle >= args.max_cycles:
                print(f"koru autonomous: reached max-cycles={args.max_cycles}; stopping")
                return 0

            effective_sleep = _compute_backoff_sleep(
                args.sleep_seconds,
                loop_state.stagnation_streak,
                args.max_sleep_seconds,
                args.backoff_on_stagnation,
            )
            print(
                f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
                f"waiting={_queue_loop_waiting_ticket_label(queue_result)} "
                f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
                f"autopilot={_autopilot_status} sleep={effective_sleep}s"
            )
            if effective_sleep > 0:
                time.sleep(effective_sleep)
    except KeyboardInterrupt:
        print("\nkoru autonomous: interrupted")
        return 0
    finally:
        if daemon is not None:
            daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        _stop_process(wup_process, "WUP watcher")


def autonomous_main(argv: list[str]) -> int:
    if not argv:
        argv = ["up"]
    elif argv[0] != "up" and argv[0] not in ("-h", "--help"):
        argv = ["up", *argv]
    args = _build_parser().parse_args(argv)
    if args.action == "up":
        return _action_up(args)
    return 2


__all__ = ["autonomous_main"]
