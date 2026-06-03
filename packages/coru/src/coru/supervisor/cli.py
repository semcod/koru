"""CLI entrypoints for ``coru supervisor``."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from coru.supervisor.paths import registry_path, supervisor_url
from coru.supervisor.registry import (
    active_lane_pair,
    load_registry,
    register_lane,
    remove_lane,
    set_active_lane,
)
from coru.supervisor.service import (
    SupervisorService,
    read_supervisor_pid,
    stop_supervisor_process,
    supervisor_running,
)
from coru.supervisor.systemd_unit import action_install_unit


def _resolve_koru_argv(koru_argv: Sequence[str] | None) -> list[str]:
    if koru_argv:
        return list(koru_argv)
    binary = __import__("shutil").which("koru")
    if binary:
        return [binary]
    return ["koru"]


def _print_lanes_human(registry) -> None:
    active = registry.active_lane or "-"
    print(f"active_lane: {active}")
    if not registry.lanes:
        print("lanes: (none)")
        return
    print("lanes:")
    for instance, lane in sorted(registry.lanes.items()):
        mark = "*" if instance == registry.active_lane else " "
        health = lane.health
        print(
            f"  {mark} {instance}: ide={lane.ide} socket={lane.socket_path} "
            f"daemon={'up' if health.daemon_running else 'down'} "
            f"plugins={health.plugin_count}"
        )


def cmd_start(args: argparse.Namespace, *, koru_argv: Sequence[str] | None = None) -> int:
    if supervisor_running() and not args.force:
        pid = read_supervisor_pid()
        print(f"coru supervisor: already running (pid={pid})", file=sys.stderr)
        print(f"coru supervisor: url {supervisor_url()}", file=sys.stderr)
        return 0

    service = SupervisorService(
        koru_argv=_resolve_koru_argv(koru_argv),
        verbose=bool(args.verbose),
        refresh_interval=float(args.refresh_interval),
    )
    if args.register_active:
        ide = str(args.ide or os.environ.get("KORU_AUTOPILOT_IDE") or "cursor").strip().lower()
        instance = str(
            args.instance or os.environ.get("KORU_AUTOPILOT_INSTANCE") or ide
        ).strip()
        project = str(args.project or os.getcwd()).strip()
        register_lane(ide=ide, instance=instance, project=project, set_active=True)

    if args.foreground:
        return service.run(foreground=True, watch=not args.no_watch)

    argv = [
        sys.executable,
        "-m",
        "coru.supervisor.cli",
        "start",
        "--foreground",
        f"--refresh-interval={args.refresh_interval}",
    ]
    if args.verbose:
        argv.append("--verbose")
    if args.no_watch:
        argv.append("--no-watch")
    env = dict(os.environ)
    env["CORU_SUPERVISOR_DAEMONIZED"] = "1"
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )
    pid_path = service.registry_path.parent / "supervisor.pid"
    # child writes pid; wait briefly
    for _ in range(30):
        if supervisor_running():
            print(f"coru supervisor: started pid={read_supervisor_pid()} url={supervisor_url()}")
            return 0
        if proc.poll() is not None:
            print("coru supervisor: failed to start", file=sys.stderr)
            return 1
        __import__("time").sleep(0.1)
    print(f"coru supervisor: starting (child pid={proc.pid})", file=sys.stderr)
    return 0


def cmd_stop(_args: argparse.Namespace) -> int:
    ok, detail = stop_supervisor_process()
    if ok:
        print(f"coru supervisor: {detail}")
        return 0
    print(f"coru supervisor: {detail}", file=sys.stderr)
    return 1 if supervisor_running() else 0


def cmd_status(_args: argparse.Namespace) -> int:
    running = supervisor_running()
    pid = read_supervisor_pid()
    registry = load_registry()
    print(f"running: {running}")
    print(f"pid: {pid or '-'}")
    print(f"url: {supervisor_url()}")
    print(f"registry: {registry_path()}")
    _print_lanes_human(registry)
    return 0 if running or registry.lanes else 1


def cmd_lanes(args: argparse.Namespace) -> int:
    registry = load_registry()
    if args.json:
        print(json.dumps(registry.to_dict(), indent=2, sort_keys=True))
        return 0
    _print_lanes_human(registry)
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    try:
        record = register_lane(
            ide=args.ide.strip().lower(),
            instance=args.instance.strip(),
            project=args.project,
            set_active=bool(args.set_active),
            editor_cli=args.editor_cli,
        )
    except FileNotFoundError as exc:
        print(f"coru supervisor: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"registered lane {record.instance} ide={record.ide} socket={record.socket_path}")
        if args.set_active:
            print(f"active_lane: {record.instance}")
    return 0


def cmd_active(args: argparse.Namespace) -> int:
    if args.instance:
        record = set_active_lane(args.instance.strip())
        if args.json:
            print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
        else:
            print(f"active_lane: {record.instance}")
        return 0
    pair = active_lane_pair()
    if pair is None:
        print("active_lane: (none)", file=sys.stderr)
        return 1
    ide, instance = pair
    if args.json:
        registry = load_registry()
        record = registry.lanes.get(instance)
        print(json.dumps(record.to_dict() if record else {"ide": ide, "instance": instance}, indent=2))
    else:
        print(f"active_lane: {instance} (ide={ide})")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    if not remove_lane(args.instance.strip()):
        print(f"unknown lane: {args.instance}", file=sys.stderr)
        return 1
    print(f"removed lane: {args.instance}")
    return 0


def cmd_refresh(args: argparse.Namespace, *, koru_argv: Sequence[str] | None = None) -> int:
    service = SupervisorService(koru_argv=_resolve_koru_argv(koru_argv))
    if args.instance:
        record = load_registry().lanes.get(args.instance.strip())
        if record is None:
            print(f"unknown lane: {args.instance}", file=sys.stderr)
            return 1
        health = service.refresh_lane_health(record)
        print(json.dumps(health.to_dict(), indent=2, sort_keys=True))
        return 0
    service.refresh_all_health()
    registry = load_registry()
    if args.json:
        print(json.dumps(registry.to_dict(), indent=2, sort_keys=True))
    else:
        _print_lanes_human(registry)
    return 0


def cmd_daemon(args: argparse.Namespace, *, koru_argv: Sequence[str] | None = None) -> int:
    service = SupervisorService(koru_argv=_resolve_koru_argv(koru_argv))
    instance = args.instance.strip()
    if args.action == "start":
        ok, detail = service.start_lane_daemon(instance)
    else:
        ok, detail = service.stop_lane_daemon(instance)
    if ok:
        print(detail)
        return 0
    print(detail, file=sys.stderr)
    return 1


def cmd_reconnect(args: argparse.Namespace, *, koru_argv: Sequence[str] | None = None) -> int:
    service = SupervisorService(koru_argv=_resolve_koru_argv(koru_argv))
    ok, detail = service.reconnect_lane(args.instance.strip())
    if ok:
        print(detail)
        return 0
    print(detail, file=sys.stderr)
    return 1


def _register_start_command(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    start = sub.add_parser("start", help="start supervisor HTTP service")
    start.add_argument("--foreground", action="store_true", help="run in foreground (default when daemonized)")
    start.add_argument("--force", action="store_true", help="start even if pid file exists")
    start.add_argument("--verbose", action="store_true")
    start.add_argument("--no-watch", action="store_true", help="disable periodic health refresh")
    start.add_argument("--refresh-interval", type=float, default=30.0)
    start.add_argument("--register-active", action="store_true", help="register env/current lane before start")
    start.add_argument("--ide")
    start.add_argument("--instance")
    start.add_argument("--project")


def _register_registry_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    sub.add_parser("stop", help="stop background supervisor")
    sub.add_parser("status", help="supervisor process + registry summary")

    lanes = sub.add_parser("lanes", help="list registered lanes")
    lanes.add_argument("--json", action="store_true")

    reg = sub.add_parser("register", help="register or update a lane")
    reg.add_argument("ide")
    reg.add_argument("instance")
    reg.add_argument("--project")
    reg.add_argument("--editor-cli")
    reg.add_argument("--set-active", action="store_true")
    reg.add_argument("--json", action="store_true")

    active = sub.add_parser("active", help="get/set active lane")
    active.add_argument("instance", nargs="?")
    active.add_argument("--json", action="store_true")

    remove = sub.add_parser("remove", help="remove a lane from registry")
    remove.add_argument("instance")

    refresh = sub.add_parser("refresh", help="refresh lane health probes")
    refresh.add_argument("instance", nargs="?")
    refresh.add_argument("--json", action="store_true")


def _register_daemon_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    daemon = sub.add_parser("daemon", help="start/stop autopilot daemon for a lane")
    daemon.add_argument("action", choices=("start", "stop"))
    daemon.add_argument("instance")

    reconnect = sub.add_parser("reconnect", help="restart lane daemon and refresh health")
    reconnect.add_argument("instance")


def _register_install_unit_command(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    install_unit = sub.add_parser("install-unit", help="install coru-supervisor systemd --user unit")
    install_unit.add_argument("--dest", type=Path)
    install_unit.add_argument("--force", action="store_true")
    install_unit.add_argument("--print-only", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coru supervisor")
    sub = parser.add_subparsers(dest="command", required=True)

    _register_start_command(sub)
    _register_registry_commands(sub)
    _register_daemon_commands(sub)
    _register_install_unit_command(sub)

    return parser


def main(argv: Sequence[str] | None = None, *, koru_argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if os.environ.get("CORU_SUPERVISOR_DAEMONIZED") == "1" and args.command == "start":
        args.foreground = True
    handlers = {
        "start": lambda: cmd_start(args, koru_argv=koru_argv),
        "stop": lambda: cmd_stop(args),
        "status": lambda: cmd_status(args),
        "lanes": lambda: cmd_lanes(args),
        "register": lambda: cmd_register(args),
        "active": lambda: cmd_active(args),
        "remove": lambda: cmd_remove(args),
        "refresh": lambda: cmd_refresh(args, koru_argv=koru_argv),
        "daemon": lambda: cmd_daemon(args, koru_argv=koru_argv),
        "reconnect": lambda: cmd_reconnect(args, koru_argv=koru_argv),
        "install-unit": lambda: action_install_unit(args),
    }
    return handlers[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
