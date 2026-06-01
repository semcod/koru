
import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from koru.autonomous_parser import looks_like_autonomous_up_command


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


@dataclass(frozen=True)
class _PsRow:
    pid: int
    ppid: int
    command: str


def command_project(command: str) -> Path | None:
    parts = command.split()
    for idx, part in enumerate(parts):
        if part == "--project" and idx + 1 < len(parts):
            return Path(parts[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return None


def process_cwd(pid: int) -> Path | None:
    proc_cwd = Path("/proc") / str(pid) / "cwd"
    try:
        return proc_cwd.resolve()
    except OSError:
        return None


def ancestor_pids(pid: int) -> set[int]:
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


def _parse_ps_row(raw_line: str) -> _PsRow | None:
    line = raw_line.strip()
    if not line:
        return None
    parts = line.split(maxsplit=2)
    if len(parts) < 3:
        return None
    pid_text, ppid_text, command = parts
    try:
        return _PsRow(pid=int(pid_text), ppid=int(ppid_text), command=command)
    except ValueError:
        return None


def _ps_rows(stdout: str) -> list[_PsRow]:
    rows: list[_PsRow] = []
    for raw_line in stdout.splitlines():
        row = _parse_ps_row(raw_line)
        if row is not None:
            rows.append(row)
    return rows


def _live_ps_rows() -> list[_PsRow]:
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
    return _ps_rows(result.stdout)


def _autonomous_process_match(
    row: _PsRow,
    project: Path,
    *,
    any_project: bool,
    excluded: set[int],
) -> ExistingAutonomousProcess | None:
    if row.pid in excluded:
        return None
    if not looks_like_autonomous_up_command(row.command):
        return None

    cwd = process_cwd(row.pid)
    cmd_project = command_project(row.command)
    if any_project or cwd == project or cmd_project == project:
        return ExistingAutonomousProcess(pid=row.pid, command=row.command, cwd=cwd)
    return None


def _matching_autonomous_processes(
    rows: list[_PsRow],
    project: Path,
    *,
    any_project: bool,
    excluded: set[int],
) -> list[ExistingAutonomousProcess]:
    return [
        match
        for row in rows
        if (
            match := _autonomous_process_match(
                row,
                project,
                any_project=any_project,
                excluded=excluded,
            )
        )
        is not None
    ]


def find_existing_autonomous_processes(
    project: Path,
    *,
    any_project: bool = False,
) -> list[ExistingAutonomousProcess]:
    current_pid = os.getpid()
    return _matching_autonomous_processes(
        _live_ps_rows(),
        project.resolve(),
        any_project=any_project,
        excluded={current_pid, *ancestor_pids(current_pid)},
    )


def _wup_process_match(
    row: _PsRow,
    project: Path,
    *,
    excluded: set[int],
) -> ExistingManagedProcess | None:
    if row.pid in excluded:
        return None
    if "wup" not in row.command or " watch " not in f" {row.command} ":
        return None

    cwd = process_cwd(row.pid)
    if cwd == project or str(project) in row.command:
        return ExistingManagedProcess(
            pid=row.pid,
            kind="wup-watch",
            command=row.command,
            cwd=cwd,
        )
    return None


def _matching_wup_processes(
    rows: list[_PsRow],
    project: Path,
    *,
    excluded: set[int],
) -> list[ExistingManagedProcess]:
    return [
        match
        for row in rows
        if (match := _wup_process_match(row, project, excluded=excluded)) is not None
    ]


def find_existing_wup_processes(project: Path) -> list[ExistingManagedProcess]:
    current_pid = os.getpid()
    return _matching_wup_processes(
        _live_ps_rows(),
        project.resolve(),
        excluded={current_pid, *ancestor_pids(current_pid)},
    )


def as_managed(proc: ExistingAutonomousProcess) -> ExistingManagedProcess:
    return ExistingManagedProcess(
        pid=proc.pid,
        kind="autonomous-loop",
        command=proc.command,
        cwd=proc.cwd,
    )


def terminate_existing_processes(
    processes: list[ExistingManagedProcess],
    *,
    stdio_format: str,
    stdio_info: Callable[[str], None],
) -> None:
    for proc in processes:
        stdio_info(f"koru autonomous: stopping existing {proc.kind} pid={proc.pid}")
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError:
            stdio_info(
                f"koru autonomous: no permission to stop existing {proc.kind} pid={proc.pid}",
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
            stdio_info(f"koru autonomous: force-stopped existing {proc.kind} pid={proc.pid}")
        except (ProcessLookupError, PermissionError):
            pass


def confirm_replace_existing(processes: list[ExistingManagedProcess]) -> bool:
    print("koru autonomous: existing managed process(es) for this project are already running:")
    for proc in processes:
        where = f" cwd={proc.cwd}" if proc.cwd else ""
        print(f"  {proc.kind} pid={proc.pid}{where} :: {proc.command}")
    answer = input("Stop existing process(es) and start this one? [y/N] ").strip().lower()
    return answer in {"y", "yes", "t", "tak"}
