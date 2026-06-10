"""Argument parser construction for ``koru autopilot``."""

from __future__ import annotations

import argparse
from pathlib import Path

from koru.autopilot import tail_cli

IDE_CHOICES = (
    "auto",
    "antigravity",
    "windsurf",
    "vscode",
    "vscodium",
    "cursor",
    "jetbrains",
    "zed",
)

PLUGIN_INSTALL_IDE_CHOICES = (*IDE_CHOICES, "pycharm")


def build_autopilot_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autopilot",
        description=(
            "Drive an IDE's LLM chat panel from the terminal. "
            "Run `koru autopilot daemon` once in a background terminal, "
            "then `koru autopilot drive '<text>'` from anywhere to type "
            "into the focused IDE."
        ),
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help=(
            "Unix-socket path (default from KORU_AUTOPILOT_SOCKET / "
            "KORU_AUTOPILOT_INSTANCE / XDG_RUNTIME_DIR - see koru autopilot docs)."
        ),
    )
    parser.add_argument(
        "--log-format",
        choices=("human", "jsonl"),
        default=None,
        help="logging format for structured CLI events (default: human)",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    _add_daemon_parser(sub)
    _add_drive_parser(sub)
    _add_calibrate_parser(sub)
    _add_session_start_parser(sub)
    _add_status_parser(sub)
    _add_env_parser(sub)
    _add_snapshot_parser(sub)
    sub.add_parser("shutdown", help="Ask a running daemon to stop.")
    _add_trace_parser(sub)
    sub.add_parser("ide-list", help="List currently running IDEs (process scan).")
    _add_doctor_parser(sub)
    _add_setup_host_parser(sub)
    _add_manage_parser(sub)
    _add_install_plugin_parser(sub)
    _add_install_plugin_jetbrains_parser(sub)
    _add_handoff_parser(sub)
    _add_install_unit_parser(sub)
    _add_tail_parser(sub)
    return parser


def _add_daemon_parser(sub: argparse._SubParsersAction) -> None:
    daemon = sub.add_parser("daemon", help="Run the autopilot broker.")
    daemon.add_argument(
        "--idempotent",
        action="store_true",
        help="If a healthy daemon already runs, exit 0 instead of failing.",
    )
    daemon.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the koru brief on session.ended (default: cwd).",
    )
    handoff_group = daemon.add_mutually_exclusive_group()
    handoff_group.add_argument(
        "--handoff",
        dest="handoff",
        action="store_true",
        default=True,
        help="On session.ended from a plugin, type the koru brief back into the chat (default).",
    )
    handoff_group.add_argument(
        "--no-handoff",
        dest="handoff",
        action="store_false",
        help="Disable auto-handoff; just ack session events.",
    )
    daemon.add_argument(
        "--handoff-cooldown",
        type=float,
        default=2.0,
        help="Seconds to wait after typing before reacting to session.ended (anti-loop).",
    )


def _add_drive_parser(sub: argparse._SubParsersAction) -> None:
    drive = sub.add_parser("drive", help="Type text into the active IDE chat.")
    drive.add_argument(
        "text",
        nargs="*",
        default=[],
        help="Text to type (joined with spaces). Omit when using --prompt.",
    )
    drive.add_argument(
        "--prompt",
        "-p",
        default=None,
        metavar="TEXT",
        help="Full prompt string (alternative to positional words; avoids quoting issues).",
    )
    drive.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="Read the full prompt from PATH; used by replayable drive DSL lines.",
    )
    drive.add_argument(
        "--ide",
        default="auto",
        choices=IDE_CHOICES,
        help=(
            "Target IDE for keyboard fallback (default: auto). "
            "With --direct and without --os-profile, this is also the OS-injector "
            "profile key in ide-os-injector.json."
        ),
    )
    drive.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Do not press the submit key after typing.",
    )
    drive.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be typed and exit without touching the keyboard.",
    )
    drive.add_argument(
        "--require-plugin",
        action="store_true",
        help=(
            "Require a connected IDE plugin; fail instead of falling back to global "
            "keyboard injection."
        ),
    )
    drive.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the daemon and inject directly via local backends.",
    )
    drive.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "With --direct, include DIR/.koru/ide-os-injector.json first in "
            "OS-injector profile search (default: cwd-only + home; same order "
            "as the daemon when given --project)."
        ),
    )
    drive.add_argument(
        "--os-profile",
        default=None,
        metavar="IDE",
        help=(
            "With --direct, force OS-injector profile id in ide-os-injector.json "
            "(e.g. windsurf). When unset, the profile key matches --ide "
            "(including auto-detect)."
        ),
    )
    drive.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="With --direct, wait before injection so you can focus the target IDE window.",
    )


def _add_calibrate_parser(sub: argparse._SubParsersAction) -> None:
    calibrate = sub.add_parser(
        "calibrate",
        help="Capture chat input coordinates after a short delay and save an OS-injector profile.",
    )
    calibrate.add_argument(
        "--ide",
        default="auto",
        metavar="IDE",
        help=(
            "Profile id (windsurf, vscode, vscodium, cursor, ...). Default auto: "
            "same detection as `drive --direct --ide auto` (focused IDE when known, "
            "else first running)."
        ),
    )
    calibrate.add_argument(
        "--delay-seconds",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Seconds to wait before capturing the mouse position (default: 5).",
    )
    calibrate.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional ide-os-injector.json path (default: ~/.koru/ide-os-injector.json).",
    )
    calibrate.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Project root whose env2llm registry is refreshed after calibration (default: cwd).",
    )
    calibrate.add_argument(
        "--prompt",
        default=None,
        metavar="TEXT",
        help="Optional smoke prompt injected immediately after saving the profile.",
    )


def _add_session_start_parser(sub: argparse._SubParsersAction) -> None:
    session_start = sub.add_parser(
        "session-start",
        help="Calibrate one or more IDE profiles in sequence and optionally send a smoke prompt.",
    )
    session_start.add_argument(
        "--ides",
        default="auto",
        metavar="LIST",
        help="Comma-separated ids or 'auto' for all running IDE ids (default: auto).",
    )
    session_start.add_argument(
        "--delay-seconds",
        type=float,
        default=6.0,
        metavar="SECONDS",
        help="Delay before each capture (default: 6).",
    )
    session_start.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional ide-os-injector.json path (default: ~/.koru/ide-os-injector.json).",
    )
    session_start.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Project root whose env2llm registry is refreshed after calibration (default: cwd).",
    )
    session_start.add_argument(
        "--prompt",
        default=None,
        metavar="TEXT",
        help="Optional smoke prompt after each profile is saved.",
    )


def _add_status_parser(sub: argparse._SubParsersAction) -> None:
    status = sub.add_parser("status", help="Print daemon health + connected plugins.")
    status.add_argument(
        "--ide",
        default="auto",
        choices=IDE_CHOICES,
        help=(
            "IDE lane whose daemon socket should be inspected (default: auto from env, "
            "terminal host, focused IDE, or the default socket)."
        ),
    )
    status.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    status.add_argument(
        "--explain",
        action="store_true",
        help="When plugins are empty, print IDE bridge hypotheses (koru ide doctor).",
    )
    status.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for workspace settings checks with --explain.",
    )
    status.add_argument(
        "--format",
        choices=("json", "systemmap"),
        default="json",
        help="Output format: raw daemon status (json) or nlp2uri URI index (systemmap).",
    )


def _add_env_parser(sub: argparse._SubParsersAction) -> None:
    env = sub.add_parser(
        "env",
        help="Print shell exports for the resolved autopilot lane (eval in bash/zsh).",
    )
    env.add_argument(
        "--ide",
        default="auto",
        choices=IDE_CHOICES,
        help="IDE to resolve (default: auto from settings, supervisor, or daemon metadata).",
    )
    env.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for workspace settings and daemon metadata lookup.",
    )
    env.add_argument(
        "--format",
        choices=("shell", "json"),
        default="shell",
        help="Output shell exports or JSON payload (default: shell).",
    )
    env.add_argument(
        "--explain",
        action="store_true",
        help="With --format shell, print resolution source on stderr.",
    )


def _add_snapshot_parser(sub: argparse._SubParsersAction) -> None:
    snapshot = sub.add_parser(
        "snapshot",
        help="Print copy-pasteable shell OQL/DSL for current daemon/autonomy/runtime state.",
    )
    snapshot.add_argument(
        "--ide",
        default="auto",
        choices=IDE_CHOICES,
        help="IDE lane to inspect (default: auto).",
    )
    snapshot.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root for telemetry, DSL, and env2llm slices.",
    )
    snapshot.add_argument(
        "--ticket",
        default=None,
        metavar="ID",
        help="Optional ticket id to filter observability path lines.",
    )
    snapshot.add_argument(
        "--limit",
        type=int,
        default=12,
        help="How many recent drive/obs lines to include (default: 12).",
    )
    snapshot.add_argument(
        "--include-env2llm",
        action="store_true",
        help="Append env2llm desktop registry lines (#007).",
    )


def _add_trace_parser(sub: argparse._SubParsersAction) -> None:
    trace = sub.add_parser(
        "trace",
        help="Print the structured decision trace ring buffer (last 10 cycles).",
    )
    trace.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project whose `.planfile/.koru/autonomy-telemetry.json` to read.",
    )
    trace.add_argument(
        "--format",
        choices=("text", "json", "dsl", "drive-dsl"),
        default="text",
        help="Output format (default: text - one compact line per record).",
    )
    trace.add_argument(
        "--limit",
        type=int,
        default=10,
        help="How many of the most-recent records to show (default: 10).",
    )


def _add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    doctor = sub.add_parser("doctor", help="Report which injection backends are available.")
    doctor.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    doctor.add_argument(
        "--fix",
        action="store_true",
        help="Show guided remediation and next commands (including optional package auto-install).",
    )


def _add_setup_host_parser(sub: argparse._SubParsersAction) -> None:
    setup_host = sub.add_parser(
        "setup-host",
        help=(
            "Probe injector tools, list apt install hints, and optional apt install "
            "(Debian/Ubuntu). Separates automated steps from human (uinput, IDE plugin)."
        ),
    )
    setup_host.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    setup_host.add_argument(
        "--install",
        action="store_true",
        help="Run sudo apt-get install -y for missing xdotool/wtype/ydotool (requires apt).",
    )
    setup_host.add_argument(
        "--dry-run",
        dest="install_dry_run",
        action="store_true",
        help="With --install, print the apt-get command but do not run it.",
    )


def _add_manage_parser(sub: argparse._SubParsersAction) -> None:
    manage = sub.add_parser(
        "manage",
        help=(
            "Inventory and repair the autopilot installation: koru binary, daemon, "
            "socket, IDE plugin and VSIX version."
        ),
    )
    manage.add_argument(
        "--ide",
        default="auto",
        choices=PLUGIN_INSTALL_IDE_CHOICES,
        help="IDE to inspect or repair (default: auto-detect).",
    )
    manage.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project root for daemon repair and workspace checks (default: cwd or koru source).",
    )
    manage.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    manage.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Best-effort repair: install/reassert the current plugin and stop the daemon "
            "so the IDE can reconnect cleanly."
        ),
    )
    manage.add_argument(
        "--dry-run",
        action="store_true",
        help="With --fix, show the planned plugin install without executing it.",
    )
    manage.add_argument(
        "--allow-unconnected",
        action="store_true",
        help="Exit 0 even if the plugin remains unconnected (useful during automated syncs where manual reload is expected).",
    )


def _add_install_plugin_parser(sub: argparse._SubParsersAction) -> None:
    install_plugin = sub.add_parser(
        "install-plugin",
        help=(
            "Install the koru autopilot editor extension for the current IDE "
            "(auto-detect from terminal/focus/running IDEs)."
        ),
    )
    install_plugin.add_argument(
        "--ide",
        default="auto",
        choices=PLUGIN_INSTALL_IDE_CHOICES,
        help="Target editor CLI (default: auto-detect current IDE).",
    )
    install_plugin.add_argument(
        "--vsix",
        type=Path,
        default=None,
        help=(
            "Path to .vsix package (default: newest plugins/koru-autopilot-vscode/"
            "koru-autopilot-*.vsix)."
        ),
    )
    install_plugin.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to the editor extension installer.",
    )
    install_plugin.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved install command without executing it.",
    )
    install_plugin.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )


def _add_install_plugin_jetbrains_parser(sub: argparse._SubParsersAction) -> None:
    install_plugin_jetbrains = sub.add_parser(
        "install-plugin-jetbrains",
        help=(
            "Build the JetBrains plugin package (ZIP) and print installation hint "
            "for PyCharm/IntelliJ."
        ),
    )
    install_plugin_jetbrains.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        help=(
            "Path to plugins/koru-autopilot-jetbrains directory "
            "(default: repository copy)."
        ),
    )
    install_plugin_jetbrains.add_argument(
        "--gradle-bin",
        default="gradle",
        help="Gradle executable to use (default: gradle).",
    )
    install_plugin_jetbrains.add_argument(
        "--gradle-task",
        default="buildPlugin",
        help="Gradle task used to build plugin package (default: buildPlugin).",
    )
    install_plugin_jetbrains.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved Gradle command without executing it.",
    )
    install_plugin_jetbrains.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )


def _add_handoff_parser(sub: argparse._SubParsersAction) -> None:
    handoff = sub.add_parser(
        "handoff",
        help="Build the koru brief for --project and type it into the IDE chat.",
    )
    handoff.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the brief (default: cwd).",
    )
    handoff.add_argument(
        "--ide",
        default="auto",
        choices=IDE_CHOICES,
        help="Target IDE (default: auto-detect the focused one).",
    )
    handoff.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Type the brief but do not press the submit key.",
    )
    handoff.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the brief and exit; do not contact the daemon.",
    )
    handoff.add_argument(
        "--require-plugin",
        action="store_true",
        help=(
            "Require a connected IDE plugin; fail instead of falling back to global "
            "keyboard injection."
        ),
    )


def _add_install_unit_parser(sub: argparse._SubParsersAction) -> None:
    install_unit = sub.add_parser(
        "install-unit",
        help="Install the systemd --user service unit (P2.6).",
    )
    install_unit.add_argument(
        "--dest",
        type=Path,
        default=None,
        help=(
            "Override destination (default: "
            "$XDG_CONFIG_HOME/systemd/user/koru-autopilot.service)."
        ),
    )
    install_unit.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing unit file.",
    )
    install_unit.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="Print the rendered unit to stdout instead of writing.",
    )


def _add_tail_parser(sub: argparse._SubParsersAction) -> None:
    tail = sub.add_parser(
        "tail",
        help="Pretty-print the persistent audit log (P2.7/P2.8).",
    )
    tail.add_argument(
        "-n",
        "--lines",
        type=int,
        default=20,
        help="Number of trailing entries to show (default: 20).",
    )
    tail.add_argument(
        "--log",
        type=Path,
        default=None,
        help=f"Log file path (default: {tail_cli.default_log_path()}).",
    )
    tail.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )


_build_parser = build_autopilot_parser


__all__ = ["IDE_CHOICES", "PLUGIN_INSTALL_IDE_CHOICES", "build_autopilot_parser"]
