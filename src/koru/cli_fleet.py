"""``koru fleet`` — supervise koru autonomous loops for every project on this
machine from a single long-running process.

``koru autonomous up`` drives exactly one project (``--project``); running
it for N projects has meant hand-configuring N systemd units, one per
project, each independently subject to ``systemctl stop``/restarts. That's
brittle to operate and gives no single place to see "is koru working on
anything right now?" across the whole machine.

``koru fleet up`` is a thin supervisor: it discovers every project that has
opted into koru's LLM-agent policy (``.planfile/.koru/policy.yaml``,
written by ``koru --init``) under a workspace root, and runs one supervised
``koru autonomous up`` *child process* per project — a single broker-style
service coordinating many project "topics" (one child per project), restart
policy and lifecycle centralized in one place, rather than N independent
systemd units that only know about themselves.

Process-level isolation is deliberate: each project's autonomous loop keeps
its own crash/resource blast radius (matching how ``--replace-existing`` /
``--allow-duplicate`` already reason about one loop per project), so a
runaway or crashing project can't take down every other project's loop.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from typing import Any
import time
from pathlib import Path
from typing import Any

_JUNK_PATH_SEGMENTS = frozenset(
    {
        "test-data",
        "tests",
        "test",
        "examples",
        "plugins",
        "archive",
        "rebuild",
        "node_modules",
        ".git",
        "build",
        "dist",
        "__pycache__",
        ".venv",
        "venv",
    }
)

_POLICY_MARKER_PARTS = (".planfile", ".koru", "policy.yaml")
_DEFAULT_RESTART_BACKOFF_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 2.0


def discover_projects(workspace: Path) -> list[Path]:
    """Find every project under *workspace* with a koru LLM-agent policy.

    Prunes obvious non-project noise (test fixtures, plugin subpackages,
    build artifacts, VCS/venv dirs) during the walk rather than filtering
    a fully-collected list afterward.
    """
    found: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(workspace):
        dirnames[:] = [d for d in dirnames if d not in _JUNK_PATH_SEGMENTS and not d.startswith(".")]
        base = Path(dirpath)
        candidate = base
        for part in _POLICY_MARKER_PARTS[:-1]:
            candidate = candidate / part
        marker = candidate / _POLICY_MARKER_PARTS[-1]
        if marker.is_file():
            found.append(base)
    return sorted(found)


class _ManagedProject:
    """One supervised ``koru autonomous up`` child for a single project."""

    def __init__(self, project: Path, extra_args: list[str]) -> None:
        self.project = project
        self.extra_args = extra_args
        self.process: subprocess.Popen[bytes] | None = None
        self.next_restart_at: float = 0.0
        self.restart_count = 0

    def command(self) -> list[str]:
        koru_bin = sys.argv[0] if sys.argv and sys.argv[0].endswith("koru") else "koru"
        return [
            koru_bin,
            "autonomous",
            "up",
            "--project",
            str(self.project),
            "--replace-existing",
            *self.extra_args,
        ]

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, *, log: Any) -> None:
        cmd = self.command()
        log(f"koru fleet: starting {self.project} -> {' '.join(cmd)}")
        env = dict(os.environ)
        env["KORU_CLI_NO_REEXEC"] = env.get("KORU_CLI_NO_REEXEC", "1")
        self.process = subprocess.Popen(cmd, cwd=str(self.project), env=env)

    def poll_and_maybe_restart(self, *, now: float, backoff_seconds: float, log: Any) -> None:
        if self.process is None:
            if now >= self.next_restart_at:
                self.start(log=log)
            return
        code = self.process.poll()
        if code is None:
            return  # still running
        self.restart_count += 1
        log(
            f"koru fleet: {self.project} exited (code={code}); "
            f"restart #{self.restart_count} in {backoff_seconds:.0f}s"
        )
        self.process = None
        self.next_restart_at = now + backoff_seconds

    def terminate(self, *, log: Any) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        log(f"koru fleet: stopping {self.project} (pid={self.process.pid})")
        self.process.terminate()


def _default_workspace() -> Path:
    raw = os.environ.get("KORU_FLEET_WORKSPACE", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "github"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru fleet",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="fleet_command", required=True)

    up = sub.add_parser("up", help="Discover and supervise autonomous loops for every koru project.")
    up.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Root to discover koru-managed projects under "
        "(default: $KORU_FLEET_WORKSPACE or ~/github).",
    )
    up.add_argument(
        "--restart-backoff-seconds",
        type=float,
        default=_DEFAULT_RESTART_BACKOFF_SECONDS,
        help=f"Delay before restarting a project's loop after it exits (default: {_DEFAULT_RESTART_BACKOFF_SECONDS}).",
    )
    up.add_argument(
        "--rescan-interval-seconds",
        type=float,
        default=300.0,
        help="How often to re-discover projects under --workspace, so newly "
        "koru-init'd projects join the fleet without a restart (default: 300).",
    )
    up.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded verbatim to every `koru autonomous up` "
        "child (e.g. -- --ide claude --ticket-sources all).",
    )

    ls = sub.add_parser("ls", help="List discovered koru-managed projects and exit.")
    ls.add_argument("--workspace", type=Path, default=None)

    return parser


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _fleet_extra_args(args: argparse.Namespace) -> list[str]:
    extra_args = list(args.extra_args)
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def _fleet_bootstrap_managed(
    workspace: Path, extra_args: list[str]
) -> dict[Path, _ManagedProject] | None:
    projects = discover_projects(workspace)
    if not projects:
        _log(f"koru fleet: no koru-managed projects found under {workspace}")
        return None
    _log(f"koru fleet: managing {len(projects)} project(s) under {workspace}:")
    managed: dict[Path, _ManagedProject] = {}
    for p in projects:
        _log(f"  - {p}")
        managed[p] = _ManagedProject(p, extra_args)
    return managed


def _fleet_rescan(
    managed: dict[Path, _ManagedProject],
    *,
    workspace: Path,
    extra_args: list[str],
) -> None:
    for p in discover_projects(workspace):
        if p not in managed:
            _log(f"koru fleet: new project discovered -> {p}")
            managed[p] = _ManagedProject(p, extra_args)


def _fleet_shutdown(
    managed: dict[Path, _ManagedProject],
    *,
    previous_sigterm: Any,
    previous_sigint: Any,
) -> None:
    _log("koru fleet: shutting down — stopping all managed loops")
    for mp in managed.values():
        mp.terminate(log=_log)
    deadline = time.monotonic() + 30.0
    for mp in managed.values():
        remaining = max(0.0, deadline - time.monotonic())
        if mp.process is not None:
            try:
                mp.process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                _log(f"koru fleet: force-killing {mp.project} (pid={mp.process.pid})")
                mp.process.kill()
    signal.signal(signal.SIGTERM, previous_sigterm)
    signal.signal(signal.SIGINT, previous_sigint)


def _run_fleet_up(args: argparse.Namespace) -> int:
    workspace = args.workspace or _default_workspace()
    extra_args = _fleet_extra_args(args)
    stopped = {"flag": False}

    def _handle_stop(_signo: int, _frame: object) -> None:
        stopped["flag"] = True

    previous_sigterm = signal.signal(signal.SIGTERM, _handle_stop)
    previous_sigint = signal.signal(signal.SIGINT, _handle_stop)

    managed = _fleet_bootstrap_managed(workspace, extra_args)
    if managed is None:
        return 1

    last_rescan = time.monotonic()
    try:
        while not stopped["flag"]:
            now = time.monotonic()
            for mp in managed.values():
                mp.poll_and_maybe_restart(
                    now=now, backoff_seconds=args.restart_backoff_seconds, log=_log
                )
            if now - last_rescan >= args.rescan_interval_seconds:
                last_rescan = now
                _fleet_rescan(managed, workspace=workspace, extra_args=extra_args)
            time.sleep(_POLL_INTERVAL_SECONDS)
    finally:
        _fleet_shutdown(
            managed,
            previous_sigterm=previous_sigterm,
            previous_sigint=previous_sigint,
        )
    return 0


def _run_fleet_ls(args: argparse.Namespace) -> int:
    workspace = args.workspace or _default_workspace()
    projects = discover_projects(workspace)
    if not projects:
        print(f"No koru-managed projects found under {workspace}")
        return 1
    print(f"{len(projects)} koru-managed project(s) under {workspace}:")
    for p in projects:
        print(f"  {p}")
    return 0


def fleet_main(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.fleet_command == "up":
        return _run_fleet_up(args)
    if args.fleet_command == "ls":
        return _run_fleet_ls(args)
    parser.error(f"unknown fleet command: {args.fleet_command}")
    return 2


__all__ = ["discover_projects", "fleet_main"]
