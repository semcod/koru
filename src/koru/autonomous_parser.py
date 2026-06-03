from __future__ import annotations

import argparse
import re
from pathlib import Path


def _add_socket_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help=(
            "Autopilot daemon socket path (default: $XDG_RUNTIME_DIR/koru-autopilot.sock; "
            "override with KORU_AUTOPILOT_SOCKET or KORU_AUTOPILOT_INSTANCE — see docs)."
        ),
    )


def _add_maintenance_subcommands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    doctor = sub.add_parser(
        "doctor",
        help="Probe autodetect: IDE / MCP / autopilot socket. Read-only.",
    )
    doctor.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")

    heal = sub.add_parser(
        "self-heal",
        help="Apply safe automatic repairs (stale sockets, etc).",
    )
    heal.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    heal.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be repaired; do not mutate state.",
    )


def _add_up_core_args(up: argparse.ArgumentParser) -> None:
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


def _add_up_autopilot_args(up: argparse.ArgumentParser) -> None:
    up.add_argument(
        "--autopilot-ide",
        default="auto",
        choices=(
            "auto",
            "antigravity",
            "windsurf",
            "vscode",
            "vscodium",
            "cursor",
            "jetbrains",
            "zed",
        ),
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
        "--path",
        dest="paths",
        action="append",
        default=[],
        help=(
            "Limit `koru scan` and scoped code2llm discovery to a file or directory. "
            "Repeatable; also sets KORU_SCAN_PATHS for the autonomous session."
        ),
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


def _add_up_backoff_and_scan_args(up: argparse.ArgumentParser) -> None:
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
            "(e.g. with ticket-sources=queue)."
        ),
    )
    up.add_argument(
        "--scan-after-idle-min-interval",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Minimum seconds between scan-after-idle-queue runs (0 = no limit).",
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


def _add_up_wup_args(up: argparse.ArgumentParser) -> None:
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


def _add_up_output_operator_args(up: argparse.ArgumentParser, *, default_stdio_format: str) -> None:
    up.add_argument(
        "--emit-events",
        choices=("human", "jsonl"),
        default=default_stdio_format,
        help=(
            "Stdout format: human log lines (default) or NDJSON control-plane events. "
            "Default follows KORU_STDIO_FORMAT=human|jsonl when set. "
            "jsonl: structured events on stdout; incidental status on stderr."
        ),
    )
    up.add_argument(
        "--onboarding",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Enable/disable interactive onboarding wizard (IDE/project/strategy selection). "
            "Default: auto-enabled for interactive `koru auto` sessions."
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


def _set_up_defaults(up: argparse.ArgumentParser) -> None:
    up.set_defaults(
        submit=True,
        enable_autopilot=True,
        enable_serve=True,
        stop_on_waiting_input=False,
        semcod_artifacts=True,
        operator_pipeline=True,
        operator_tickets=True,
    )


def _add_up_subcommand(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    default_stdio_format: str,
) -> None:
    up = sub.add_parser("up", help="Configure and start autonomous loop.")
    _add_up_core_args(up)
    _add_up_autopilot_args(up)
    _add_up_backoff_and_scan_args(up)
    _add_up_wup_args(up)
    _add_up_output_operator_args(up, default_stdio_format=default_stdio_format)
    _set_up_defaults(up)


def _build_parser_impl(*, default_stdio_format: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autonomous",
        description=(
            "Bootstrap and run koru in autonomous mode (alias: ``koru auto``): "
            "optional init, scan intake, queue drain, autopilot daemon thread, "
            "optional WUP watch, and IDE drive loop."
        ),
    )
    _add_socket_arg(parser)
    sub = parser.add_subparsers(dest="action", required=True)
    _add_maintenance_subcommands(sub)
    _add_up_subcommand(sub, default_stdio_format=default_stdio_format)

    return parser


def build_parser(*, default_stdio_format: str) -> argparse.ArgumentParser:
    """Public parser factory for ``koru autonomous`` CLI."""
    return _build_parser_impl(default_stdio_format=default_stdio_format)


def _match_koru_auto_parts(parts: list[str]) -> bool:
    """Check if command parts indicate an autonomous/auto loop."""
    for idx, part in enumerate(parts):
        if Path(part).name == "koru" and idx + 1 < len(parts) and parts[idx + 1] == "auto":
            return True
        if Path(part).name == "koru" and parts[idx + 1 : idx + 3] == ["autonomous", "up"]:
            return True
        if part == "-m" and idx + 2 < len(parts) and parts[idx + 1] == "koru.cli":
            sub = parts[idx + 2]
            if sub == "auto":
                return True
            if sub == "autonomous" and idx + 3 < len(parts) and parts[idx + 3] == "up":
                return True
    return False


def looks_like_autonomous_up_command(command: str) -> bool:
    """Match koru autonomous/auto loops (cf. ``pkill -f 'koru.*autonomous'`` and ``koru auto``)."""
    if re.search(r"koru.{0,120}autonomous", command):
        return True
    return _match_koru_auto_parts(command.split())
