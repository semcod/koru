"""One-command autonomous mode for freshly installed koru.

`koru autonomous up` (or `koru autonomous` with the same flags) bootstraps
the project if needed, applies ``--agent-lane`` exports like
``shell-env.sh``, then starts optional background services (autopilot daemon,
WUP ``wup watch`` when auto-detected), and runs an outer loop.

Each cycle (see ``_run_cycle``): ``koru scan --apply`` when ticket sources
include scan, then ``koru --queue --loop``, then optional idle diagnostics
when the queue is idle, a WUP health read if the watcher is running, then
autopilot. ``--no-serve`` is a compatibility no-op (``koru serve`` is not
started here).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .agents import agent_lane_environment
from .autonomous_wup import (
    WupHealthResult,
    WupWatchConfig,  # noqa: F401
    _build_wup_watch_config,
    _start_wup_watch,
    _stop_process,
    _wup_watch_command,  # noqa: F401
)
from .autonomous_wup import (
    _read_wup_health as _read_wup_health_impl,
)
from .autopilot import default_socket_path
from .autopilot.client import AutopilotClient
from .autopilot.daemon import AutopilotDaemon
from .autopilot.plugin_installer import format_plugin_install_result, install_plugin_for_ide
from .init import init_project, resolve_project_agent_lane
from .queue import (
    QueueLoopResult,
    run_planfile_queue_loop,
)
from .queue import (
    default_human_prompt as _default_human_prompt,
)
from .queue import (
    run_api_request as _run_api_request,
)
from .queue import (
    run_llm_request as _run_llm_request,
)
from .queue import (
    run_process as _run_process,
)
from .queue import (
    run_shell_command as _run_shell_command,
)
from .scan import ScanResult, run_scan
from .stdio_events import default_stdio_format_from_env, write_stdio_event
from .tasks import create_nl_task
from .topology import is_component_enabled, is_pipeline_enabled

_VALID_AUTOPILOT_IDE = frozenset({"auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"})
_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


def _stdio_info(msg: str, *, fmt: str) -> None:
    """Human-oriented status; jsonl mode routes to stderr so stdout stays NDJSON-only."""
    print(msg, file=sys.stderr if fmt == "jsonl" else sys.stdout)


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
        help=(
            "Keep the outer loop running when the queue is waiting_input so each "
            "cycle still runs scan/queue/WUP health/autopilot. Without it, the "
            "process exits and the background WUP watcher is stopped."
        ),
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
    args.topology_integration = _env_default_bool("TOPOLOGY_INTEGRATION", args.topology_integration)
    env_wup_watch = os.environ.get("WUP_WATCH")
    if env_wup_watch is not None:
        args.wup_watch = env_wup_watch.strip().lower() in {"1", "true", "yes", "y", "on"}
    elif args.wup_watch is None:
        args.wup_watch = None
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


def _ensure_init(project: Path, *, force: bool, stdio_format: str = "human") -> None:
    config_path = project / ".planfile" / "config.yaml"
    if config_path.exists() and not force:
        return
    report = init_project(project, force=force)
    _stdio_info(
        f"koru autonomous: init {'re-' if force else ''}done at {report.project}", fmt=stdio_format
    )


def _start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
    stdio_format: str = "human",
) -> tuple[AutopilotClient, AutopilotDaemon | None, threading.Thread | None]:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
    if probe.is_running():
        _stdio_info(f"koru autonomous: reusing autopilot daemon on {socket_path}", fmt=stdio_format)
        return AutopilotClient(socket_path=socket_path), None, None

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


def _run_command_check(
    project: Path, check_id: str, command: list[str], *, stdio_format: str = "human"
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
            f"- diagnostic ticket marker exists for {check_id}, skipping create", fmt=stdio_format
        )
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    created = create_nl_task(project, prompt, queue_name=queue_name, priority=priority)
    marker.write_text(created.ticket_id, encoding="utf-8")
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
    profile = profile.lower()
    if profile in {"off", "none"}:
        _stdio_info(
            f"koru autonomous: idle diagnostics disabled (profile={profile})",
            fmt=stdio_format,
        )
        return DiagnosticResult(status="off", failed=[])
    if not _is_topology_enabled(
        project, "idle-diagnostics", fallback=True, enabled=topology_integration
    ):
        _stdio_info("koru autonomous: idle diagnostics disabled in topology", fmt=stdio_format)
        return DiagnosticResult(status="disabled(topology)", failed=[])
    _stdio_info(
        f"koru autonomous: queue idle -> running semcod diagnostics (profile={profile})",
        fmt=stdio_format,
    )
    checks: list[tuple[str, str, list[str]]] = []
    if shutil.which("regix"):
        checks.append(
            (
                "regix",
                "regix compare HEAD --local --format rich",
                ["regix", "compare", "HEAD", "--local", "--format", "rich"],
            )
        )
    if shutil.which("wup") and (project / "wup.yaml").is_file():
        checks.append(("wup", "wup status", ["wup", "status"]))
    if profile in {"full", "deep"}:
        if shutil.which("redup"):
            checks.append(
                (
                    "redup",
                    "redup scan . --min-lines 10",
                    ["redup", "scan", ".", "--min-lines", "10"],
                )
            )
        if shutil.which("testql") and any(project.rglob("*.testql.toon.yaml")):
            checks.append(
                (
                    "testql",
                    "testql suite --pattern *.testql.toon.yaml --output console --fail-fast",
                    [
                        "testql",
                        "suite",
                        "--pattern",
                        "*.testql.toon.yaml",
                        "--output",
                        "console",
                        "--fail-fast",
                    ],
                )
            )
        if shutil.which("redsl"):
            checks.append(("redsl", "redsl gate check .", ["redsl", "gate", "check", "."]))
        if (project / "scripts" / "sumr-refresh.sh").is_file():
            checks.append(
                (
                    "sumr",
                    "bash scripts/sumr-refresh.sh --status",
                    ["bash", "scripts/sumr-refresh.sh", "--status"],
                )
            )
    failed: list[str] = []
    diagnostic_state_dir.mkdir(parents=True, exist_ok=True)
    for check_id, summary, command in checks:
        if not _is_topology_enabled(project, check_id, fallback=True, enabled=topology_integration):
            _stdio_info(f"- {check_id} disabled in topology, skipping", fmt=stdio_format)
            continue
        if _run_command_check(project, check_id, command, stdio_format=stdio_format):
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
    stdio_format: str = "human",
    correlation_id: str = "",
) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    state = state or AutoloopState()

    def _emit(event_type: str, payload: dict, command: str | None = None) -> None:
        if stdio_format == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type=event_type,
                correlation_id=correlation_id,
                payload=payload,
                command=command,
            )

    def _hp(msg: str) -> None:
        if stdio_format == "human":
            print(msg)

    scan_result: ScanResult | None = None

    _emit(
        "CycleStarted",
        {"cycle": cycle, "project": str(project.resolve())},
    )

    if enable_scan:
        if not _is_topology_enabled(
            project, "scan:on-change", fallback=True, enabled=topology_integration
        ):
            _hp("- koru scan --apply skipped (scan:on-change disabled in topology)")
            _emit(
                "ScanSkipped",
                {"cycle": cycle, "reason": "topology:scan:on-change_disabled"},
            )
        else:
            head_now = _current_head(project)
            if (
                scan_skip_if_clean
                and state.scan_clean_streak >= scan_skip_after
                and head_now
                and head_now == state.scan_last_head
            ):
                _hp(
                    f"- koru scan --apply skipped "
                    f"(clean_streak={state.scan_clean_streak}, HEAD unchanged)"
                )
                _emit(
                    "ScanSkipped",
                    {
                        "cycle": cycle,
                        "reason": "clean_git_head_unchanged",
                        "clean_streak": state.scan_clean_streak,
                        "head": head_now,
                    },
                )
            else:
                scan_cmd = "koru scan --apply" + (
                    " --semcod-artifacts" if include_semcod_artifacts else ""
                )
                _hp("+ " + scan_cmd)
                scan_result = run_scan(
                    project=project, apply=True, include_semcod_artifacts=include_semcod_artifacts
                )
                _hp(
                    f"  scan: suggestions={len(scan_result.suggestions)} "
                    f"applied={len(scan_result.applied)} skipped={len(scan_result.skipped)}"
                )
                _emit(
                    "ScanCompleted",
                    {
                        "cycle": cycle,
                        "suggestions_count": len(scan_result.suggestions),
                        "applied_count": len(scan_result.applied),
                        "skipped_count": len(scan_result.skipped),
                        "semcod_artifacts": bool(include_semcod_artifacts),
                    },
                    command=scan_cmd,
                )
                if not scan_result.suggestions:
                    state.scan_clean_streak += 1
                else:
                    state.scan_clean_streak = 0
                state.scan_last_head = head_now

    if not _is_topology_enabled(
        project, "autoloop:queue", fallback=True, enabled=topology_integration
    ):
        _hp("- autoloop queue phase skipped (autoloop:queue disabled in topology)")
        queue_result = QueueLoopResult(0, [], [], [], "disabled", "")
    else:
        qcmd = f"koru --queue --loop --max-iterations {max_iterations}" + (
            " --all-queues" if queue_name is None else f" --queue-name {queue_name}"
        )
        _hp("+ " + qcmd)
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
        _hp(f"  queue: {queue_result.summary()}")
        qname = "__all__" if queue_name is None else queue_name
        _sum_fn = getattr(queue_result, "summary", None)
        if callable(_sum_fn):
            _queue_summary = _sum_fn()
        else:
            _queue_summary = str(_sum_fn or "")
        _emit(
            "QueueIteration",
            {
                "cycle": cycle,
                "queue_name": qname,
                "actor": actor,
                "iterations": int(getattr(queue_result, "iterations", 0)),
                "completed": list(getattr(queue_result, "completed", []) or []),
                "failed": list(getattr(queue_result, "failed", []) or []),
                "waiting": list(getattr(queue_result, "waiting", []) or []),
                "last_status": str(getattr(queue_result, "last_status", "")),
                "last_message": str(getattr(queue_result, "last_message", "")),
                "last_ticket_id": getattr(queue_result, "last_ticket_id", None),
                "summary": _queue_summary,
            },
            command=qcmd,
        )

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
            stdio_format=stdio_format,
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
            _hp(
                f"koru autonomous: WUP health={wup_health.status} "
                f"failing={','.join(wup_health.failing_services) or '-'} "
                f"new_events={wup_health.new_events}"
            )
            if diag_result.status in {"skipped", "off", "ok"} and wup_health.status == "failed":
                diag_result = DiagnosticResult(status="failed", failed=["wup"])
    _emit(
        "WupHealthChanged",
        {
            "cycle": cycle,
            "watcher_enabled": wup_watch_enabled,
            "status": wup_health.status,
            "failing_services": list(wup_health.failing_services),
            "new_events": wup_health.new_events,
        },
    )
    _emit(
        "DiagnosticsCompleted",
        {
            "cycle": cycle,
            "status": diag_result.status,
            "failed": list(diag_result.failed),
        },
    )

    if strict_diagnostics and diag_result.status == "failed":
        _emit(
            "AutonomousStopped",
            {"reason": "strict_diagnostics_failure", "cycle": cycle},
        )
        _stdio_info(
            "koru autonomous: strict diagnostics enabled -> stopping on diagnostics failure",
            fmt=stdio_format,
        )
        raise SystemExit(2)

    autopilot_status = "skipped"
    autopilot_backend: str | None = None
    autopilot_drive_kind: str | None = None
    if enable_autopilot and client is not None:
        if not _is_topology_enabled(
            project, "autopilot:drive", fallback=True, enabled=topology_integration
        ):
            _hp("- autopilot skipped (autopilot:drive disabled in topology)")
            autopilot_status = "skipped(topology)"
        elif autopilot_action == "off":
            _hp("- autopilot action set to off, skipping")
        elif autopilot_on_idle_only and queue_result.last_status != "idle":
            _hp("- autopilot skipped (idle_only)")
            autopilot_status = "skipped(idle_only)"
        elif autopilot_skip_on_diagnostics_fail and diag_result.status == "failed":
            _hp("- autopilot skipped (diagnostics_fail)")
            autopilot_status = "skipped(diagnostics_fail)"
        elif state.stagnation_streak > 0 and _status_in_skip_list(
            queue_result.last_status, autopilot_skip_statuses
        ):
            _hp(
                "- autopilot skipped (stuck_"
                f"{queue_result.last_status}_streak_{state.stagnation_streak})"
            )
            autopilot_status = f"skipped(stuck_{queue_result.last_status})"
        elif autopilot_action == "handoff":
            autopilot_drive_kind = "handoff"
            reply = client.drive(drive_prompt, submit=submit, ide=autopilot_ide)
            ok = bool(reply.get("ok", True))
            autopilot_status = "ok" if ok else "failed"
            autopilot_backend = (
                str(reply.get("backend")) if reply.get("backend") is not None else None
            )
        elif queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
            ticket_prompt = queue_result.last_message.strip() if queue_result.last_message else ""
            if ticket_prompt:
                autopilot_drive_kind = "ticket_prompt"
                reply = client.drive(ticket_prompt, submit=submit, ide=autopilot_ide)
                ok = bool(reply.get("ok", True))
                autopilot_status = "ok" if ok else "failed"
                autopilot_backend = (
                    str(reply.get("backend")) if reply.get("backend") is not None else None
                )
                if ok:
                    backend = reply.get("backend", "?")
                    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
                    _hp(
                        "  autopilot: ok (ticket="
                        f"{waiting_ticket}, ide={autopilot_ide}, backend={backend})"
                    )
                else:
                    message = reply.get("message", "unknown error")
                    _hp(f"  autopilot: failed ({message})")
            else:
                autopilot_drive_kind = "blocked_empty_message"
                _hp(
                    f"  autopilot: skipped (queue_status={queue_result.last_status}, empty message)"
                )
        else:
            autopilot_drive_kind = "drive_prompt"
            reply = client.drive(drive_prompt, submit=submit, ide=autopilot_ide)
            ok = bool(reply.get("ok", True))
            autopilot_status = "ok" if ok else "failed"
            autopilot_backend = (
                str(reply.get("backend")) if reply.get("backend") is not None else None
            )
            if ok:
                backend = reply.get("backend", "?")
                _hp(f"  autopilot: ok (ide={autopilot_ide}, backend={backend})")
            else:
                message = reply.get("message", "unknown error")
                _hp(f"  autopilot: failed ({message})")

    _emit(
        "AutopilotDecision",
        {
            "cycle": cycle,
            "decision": autopilot_status,
            "queue_status": queue_result.last_status,
            "ide": autopilot_ide,
            "backend": autopilot_backend,
            "drive_kind": autopilot_drive_kind,
        },
    )

    _hp(
        f"koru autonomous: cycle={cycle} queue={queue_result.last_status} "
        f"diagnostics={diag_result.status} wup={wup_health.status} autopilot={autopilot_status}"
    )
    _emit(
        "CycleCompleted",
        {
            "cycle": cycle,
            "queue_status": queue_result.last_status,
            "diagnostics_status": diag_result.status,
            "wup_status": wup_health.status,
            "autopilot_status": autopilot_status,
        },
    )

    return scan_result, queue_result, autopilot_status, diag_result


def _action_up(args: argparse.Namespace) -> int:
    _env_apply_autoloop_defaults(args)
    correlation_id = str(uuid.uuid4())
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
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

    lane = _apply_agent_lane_environ(project, args.agent_lane)
    if lane is not None:
        _stdio_info(f"koru autonomous: agent-lane={lane} (env applied)", fmt=args.emit_events)

    client: AutopilotClient | None = None
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
        stdio_format=args.emit_events,
    )

    if args.enable_autopilot and socket_path is not None:
        plugin_result = install_plugin_for_ide(ide=autopilot_ide, socket_path=socket_path)
        _stdio_info(format_plugin_install_result(plugin_result), fmt=args.emit_events)

    cycle = 0
    try:
        while True:
            cycle += 1
            if args.emit_events == "human":
                print(f"\n=== koru autonomous cycle #{cycle} ===")
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
                    try:
                        daemon.stop()
                    except OSError:
                        pass
                if thread is not None:
                    thread.join(timeout=2.0)
                client, daemon, thread = _start_or_reuse_daemon(
                    project=project,
                    socket_path=socket_path,
                    stdio_format=args.emit_events,
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
                autopilot_skip_statuses=args.autopilot_skip_statuses,
                scan_skip_if_clean=args.scan_skip_if_clean,
                scan_skip_after=args.scan_skip_after,
                topology_integration=args.topology_integration,
                stdio_format=args.emit_events,
                correlation_id=correlation_id,
            )

            if (
                args.stop_on_waiting_input
                and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES
            ):
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
                return 0

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
                return 0

            effective_sleep = _compute_backoff_sleep(
                args.sleep_seconds,
                loop_state.stagnation_streak,
                args.max_sleep_seconds,
                args.backoff_on_stagnation,
            )
            _stdio_info(
                f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
                f"waiting={_queue_loop_waiting_ticket_label(queue_result)} "
                f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
                f"autopilot={_autopilot_status} sleep={effective_sleep}s",
                fmt=args.emit_events,
            )
            if effective_sleep > 0:
                time.sleep(effective_sleep)
    except KeyboardInterrupt:
        if args.emit_events == "jsonl":
            write_stdio_event(
                sys.stdout,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": "keyboard_interrupt"},
            )
        _stdio_info("\nkoru autonomous: interrupted", fmt=args.emit_events)
        return 0
    finally:
        if daemon is not None:
            daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)
        _stop_process(wup_process, "WUP watcher", stdio_format=args.emit_events)


def autonomous_main(argv: list[str]) -> int:
    if not argv:
        argv = ["up"]
    elif argv[0] != "up" and argv[0] not in ("-h", "--help"):
        argv = ["up", *argv]
    args = _build_parser().parse_args(argv)
    if args.action == "up":
        return _action_up(args)
    return 2


__all__ = [
    "WupHealthResult",
    "WupWatchConfig",
    "_read_wup_health",
    "_wup_watch_command",
    "autonomous_main",
]
