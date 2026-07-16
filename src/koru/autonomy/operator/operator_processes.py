"""Process management utilities for autonomous mode.

Handles detection, termination, and management of existing autonomous
and WUP watch processes.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


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


@dataclass
class AutonomousStartLock:
    path: Path | None
    fd: int | None

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            import fcntl

            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None


@dataclass(frozen=True)
class _PsRow:
    pid: int
    ppid: int
    command: str


def _command_project(command: str, *, relative_to: Path | None = None) -> Path | None:
    """Best-effort parse of ``--project`` from a process command line.

    A relative ``--project`` value (most commonly ``.``, e.g. ``koru
    autonomous up --project . --replace-existing``) must be resolved
    relative to *that process's own* working directory (``relative_to``,
    from ``_process_cwd(pid)``) — not the cwd of whichever process happens
    to be running this check. Resolving against the checker's own cwd
    (``Path(value).resolve()``) made two *different* projects' relative
    ``--project .`` collapse onto the same absolute path whenever the
    checking process's cwd happened to match, causing
    ``--replace-existing`` to kill an unrelated project's autonomous loop
    (reproduced 2026-07-05: a `koru fleet` child for project A killed a
    long-running, unrelated instance for project B this way).
    """
    parts = command.split()
    raw: str | None = None
    for idx, part in enumerate(parts):
        if part == "--project" and idx + 1 < len(parts):
            raw = parts[idx + 1]
            break
        if part.startswith("--project="):
            raw = part.split("=", 1)[1]
            break
    if raw is None:
        return None
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    base = relative_to or Path.cwd()
    return (base / path).resolve()


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
    from koru.autonomy.operator.operator_parser import looks_like_autonomous_up_command

    return looks_like_autonomous_up_command(command)


def _ps_rows(stdout: str) -> list[_PsRow]:
    rows: list[_PsRow] = []
    for raw_line in stdout.splitlines():
        row = _parse_ps_row(raw_line)
        if row is not None:
            rows.append(row)
    return rows


def _parse_ps_row(raw_line: str) -> _PsRow | None:
    line = raw_line.strip()
    if not line:
        return None
    pid_text, _pid_separator, rest = line.partition(" ")
    ppid_text, _ppid_separator, command = rest.strip().partition(" ")
    try:
        return _PsRow(pid=int(pid_text), ppid=int(ppid_text), command=command)
    except ValueError:
        return None


def _autonomous_process_matches_project(
    row: _PsRow,
    project: Path,
    *,
    any_project: bool,
    excluded: set[int],
) -> ExistingAutonomousProcess | None:
    if row.pid in excluded:
        return None
    if not _looks_like_autonomous_up_command(row.command):
        return None

    cwd = _process_cwd(row.pid)
    cmd_project = _command_project(row.command, relative_to=cwd)
    if not (any_project or cwd == project or cmd_project == project):
        return None
    return ExistingAutonomousProcess(pid=row.pid, command=row.command, cwd=cwd)


def _wup_process_matches_project(
    row: _PsRow,
    project: Path,
    *,
    excluded: set[int],
) -> ExistingManagedProcess | None:
    if row.pid in excluded:
        return None
    if "wup" not in row.command or " watch " not in f" {row.command} ":
        return None
    cwd = _process_cwd(row.pid)
    if cwd == project or str(project) in row.command:
        return ExistingManagedProcess(
            pid=row.pid,
            kind="wup-watch",
            command=row.command,
            cwd=cwd,
        )
    return None


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
    for row in _ps_rows(result.stdout):
        match = _autonomous_process_matches_project(
            row,
            project,
            any_project=any_project,
            excluded=excluded,
        )
        if match is not None:
            matches.append(match)
    return matches


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
    for row in _ps_rows(result.stdout):
        match = _wup_process_matches_project(row, project, excluded=excluded)
        if match is not None:
            matches.append(match)
    return matches


def _as_managed(proc: ExistingAutonomousProcess) -> ExistingManagedProcess:
    return ExistingManagedProcess(
        pid=proc.pid,
        kind="autonomous-loop",
        command=proc.command,
        cwd=proc.cwd,
    )


def autonomous_start_lock_wanted() -> bool:
    raw = os.environ.get("KORU_AUTONOMOUS_START_LOCK", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def try_acquire_autonomous_start_lock(project: Path) -> AutonomousStartLock | None:
    """Try to serialize the whole autonomous loop for one project.

    Process scans are advisory and race when two IDEs start ``koru -a`` at the
    same time. This lock is the atomic gate; keep the fd open until the loop
    exits.
    """
    if not autonomous_start_lock_wanted() or os.name != "posix":
        return AutonomousStartLock(path=None, fd=None)

    import fcntl

    lock_dir = project.resolve() / ".planfile" / ".koru"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "autonomous-loop.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    try:
        os.ftruncate(fd, 0)
        os.write(fd, f"pid={os.getpid()}\ncwd={Path.cwd().resolve()}\n".encode())
    except OSError:
        pass
    return AutonomousStartLock(path=lock_path, fd=fd)


def _stdio_info(msg: str, *, fmt: str) -> None:
    """Human-oriented status; jsonl mode routes to stderr so stdout stays NDJSON-only."""
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


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
    user_choice = input("Stop existing process(es) and start this one? [y/N] ").strip().lower()
    return user_choice in {"y", "yes", "t", "tak"}


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


def _wup_processes_for_replace(
    args: argparse.Namespace,
    project: Path,
) -> list[ExistingManagedProcess]:
    """WUP watchers are only ours to stop when this run will manage WUP itself.

    With an explicit ``--no-wup-watch`` the operator runs ``wup watch``
    externally (e.g. as its own systemd unit) — sweeping it up here silently
    killed the external watcher (SIGTERM, which ``Restart=on-failure`` units
    deliberately do not restart from).
    """
    if getattr(args, "wup_watch", None) is False:
        return []
    return _find_existing_wup_processes(project)


def guard_existing_autonomous_processes(args: argparse.Namespace, project: Path) -> int:
    if args.allow_duplicate:
        return 0
    existing = [
        *(_as_managed(proc) for proc in _find_existing_autonomous_processes(project)),
        *_wup_processes_for_replace(args, project),
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
                *_wup_processes_for_replace(args, project),
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


__all__ = [
    "ExistingAutonomousProcess",
    "ExistingManagedProcess",
    "AutonomousStartLock",
    "stop_prior_autonomous_for_auto_start",
    "guard_existing_autonomous_processes",
    "autonomous_start_lock_wanted",
    "try_acquire_autonomous_start_lock",
    "_find_existing_autonomous_processes",
    "_find_existing_wup_processes",
    "_as_managed",
    "_terminate_existing_processes",
]
