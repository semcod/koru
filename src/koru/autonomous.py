"""One-command autonomous mode for freshly installed koru.

`koru autonomous up` (or `koru autonomous` with the same flags) bootstraps
the project if needed, applies ``--agent-lane`` exports like
``shell-env.sh``, then runs scan + queue + autopilot in a loop.
By default it also starts ``koru serve`` in the background so the local
dashboard (auto-refresh ~5s) tracks queue/context; use ``--no-serve`` to skip.
"""

from __future__ import annotations

import argparse
import os
import threading
import time
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

_VALID_AUTOPILOT_IDE = frozenset({"auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"})
_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


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
    up.set_defaults(
        submit=True,
        enable_autopilot=True,
        enable_serve=True,
        stop_on_waiting_input=True,
        semcod_artifacts=True,
    )

    return parser


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
) -> tuple[ScanResult | None, QueueLoopResult, str]:
    scan_result: ScanResult | None = None
    if enable_scan:
        print("+ koru scan --apply" + (" --semcod-artifacts" if include_semcod_artifacts else ""))
        scan_result = run_scan(
            project=project, apply=True, include_semcod_artifacts=include_semcod_artifacts
        )
        print(
            f"  scan: suggestions={len(scan_result.suggestions)} "
            f"applied={len(scan_result.applied)} skipped={len(scan_result.skipped)}"
        )

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

    autopilot_status = "skipped"
    if enable_autopilot and client is not None:
        if queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
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
                    print(f"  autopilot: ok (ticket={queue_result.ticket_id}, ide={autopilot_ide}, backend={backend})")
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
        f"autopilot={autopilot_status}"
    )
    return scan_result, queue_result, autopilot_status


def _action_up(args: argparse.Namespace) -> int:
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
            _scan_result, queue_result, _autopilot_status = _run_cycle(
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

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
    except KeyboardInterrupt:
        print("\nkoru autonomous: interrupted")
        return 0
    finally:
        if daemon is not None:
            daemon.stop()
        if thread is not None:
            thread.join(timeout=2.0)


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
