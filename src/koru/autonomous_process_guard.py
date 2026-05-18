from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from collections.abc import Callable
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


def looks_like_autonomous_up_command(command: str) -> bool:
    if re.search(r"koru.{0,120}autonomous", command):
        return True
    parts = command.split()
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


def find_existing_autonomous_processes(
    project: Path, *, any_project: bool = False
) -> list[ExistingAutonomousProcess]:
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
    excluded = {current_pid, *ancestor_pids(current_pid)}
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
        if not looks_like_autonomous_up_command(command):
            continue

        cwd = process_cwd(pid)
        cmd_project = command_project(command)
        if any_project or cwd == project or cmd_project == project:
            matches.append(ExistingAutonomousProcess(pid=pid, command=command, cwd=cwd))
    return matches


def find_existing_wup_processes(project: Path) -> list[ExistingManagedProcess]:
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
    excluded = {current_pid, *ancestor_pids(current_pid)}
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
        cwd = process_cwd(pid)
        if cwd == project or str(project) in command:
            matches.append(
                ExistingManagedProcess(pid=pid, kind="wup-watch", command=command, cwd=cwd)
            )
    return matches


def as_managed(proc: ExistingAutonomousProcess) -> ExistingManagedProcess:
    return ExistingManagedProcess(
        pid=proc.pid,
        kind="autonomous-loop",
        command=proc.command,
        cwd=proc.cwd,
    )


def terminate_existing_processes(
    processes: list[ExistingManagedProcess], *, stdio_format: str, stdio_info: Callable[[str], None]
) -> None:
    for proc in processes:
        stdio_info(f"koru autonomous: stopping existing {proc.kind} pid={proc.pid}")
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError:
            stdio_info(
                f"koru autonomous: no permission to stop existing {proc.kind} pid={proc.pid}"
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
