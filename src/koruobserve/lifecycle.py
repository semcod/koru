"""Start, stop, and inspect background processes for the observation mesh."""

from __future__ import annotations

import contextlib
import errno
import json
import os
import re
import signal
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koruobserve.bootstrap import ensure_mesh_key, ensure_observe_config
from koruobserve.paths import logfile, pidfile, runtime_dir, state_file
from koruvision.capture_probe import resolve_observe_python


_PROCESSES: tuple[str, ...] = ("relay", "vision", "dashboard")


@dataclass(frozen=True)
class ObserveProcesses:
    project: Path
    relay_pid: int | None
    vision_pid: int | None
    dashboard_pid: int | None
    relay_url: str
    dashboard_url: str
    grid_url: str
    key_path: Path
    python: str

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["project"] = str(self.project)
        data["key_path"] = str(self.key_path)
        return data


@dataclass(frozen=True)
class _ObserveLaunchConfig:
    project: Path
    relay_host: str
    relay_port: int
    dashboard_host: str
    dashboard_port: int
    interval_seconds: float | None
    key_path: Path
    python: str


def _resolve_serve_settings(config: dict[str, Any]) -> tuple[str, int]:
    serve = config.get("serve") if isinstance(config.get("serve"), dict) else {}
    host = str(serve.get("host") or "127.0.0.1")
    port = int(serve.get("port") or 8765)
    return host, port


def _pick_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if preferred <= 0:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


def _spawn(name: str, args: list[str], project: Path) -> int:
    log_path = logfile(project, name)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab", buffering=0)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["KORU_MESH_FRAME_STORE"] = str(runtime_dir(project) / "mesh-frames.jsonl")
    proc = subprocess.Popen(  # noqa: S603 — caller-controlled koru CLI
        args,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        cwd=str(project),
        start_new_session=True,
        env=env,
    )
    pidfile(project, name).write_text(str(proc.pid) + "\n", encoding="utf-8")
    return proc.pid


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def _read_pid(project: Path, name: str) -> int | None:
    path = pidfile(project, name)
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _stop_pid(project: Path, name: str) -> bool:
    pid = _read_pid(project, name)
    path = pidfile(project, name)
    if pid is None:
        path.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    path.unlink(missing_ok=True)
    return True


def _pids_matching_koru_cmdline(project: Path, needle: str) -> list[int]:
    """Return PIDs for ``python -m koru …`` whose cmdline contains *needle* and *project*."""
    if sys.platform == "win32":
        return []
    project_s = str(project.resolve())
    try:
        proc = subprocess.run(
            ["pgrep", "-af", "koru"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    text = proc.stdout or ""
    pids: list[int] = []
    for line in text.splitlines():
        if project_s not in line or needle not in line:
            continue
        match = re.match(r"(\d+)\s", line)
        if not match:
            continue
        try:
            pid = int(match.group(1))
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        pids.append(pid)
    return list(dict.fromkeys(pids))


def _stop_orphan_observe_processes(project: Path) -> None:
    """SIGTERM stale observe children when pidfiles are missing (e.g. after crash)."""
    needles = {
        "relay": " mesh relay ",
        "vision": " vision ",
        "dashboard": " serve ",
    }
    for name, needle in needles.items():
        for pid in _pids_matching_koru_cmdline(project, needle):
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGTERM)
        pidfile(project, name).unlink(missing_ok=True)


def _koru_cmd(python: str, *args: str) -> list[str]:
    return [python, "-m", "koru", *args]


def observe_up(
    project: Path,
    *,
    relay_host: str = "127.0.0.1",
    relay_port: int = 9876,
    dashboard_host: str | None = None,
    dashboard_port: int | None = None,
    interval_seconds: float | None = None,
) -> ObserveProcesses:
    project = project.expanduser().resolve()
    observe_down(project)
    runtime_dir(project).mkdir(parents=True, exist_ok=True)
    launch = _prepare_observe_launch(
        project,
        relay_host=relay_host,
        relay_port=relay_port,
        dashboard_host=dashboard_host,
        dashboard_port=dashboard_port,
        interval_seconds=interval_seconds,
    )
    state = _spawn_observe_processes(launch)
    _write_observe_state(project, state)
    return state


def _prepare_observe_launch(
    project: Path,
    *,
    relay_host: str,
    relay_port: int,
    dashboard_host: str | None,
    dashboard_port: int | None,
    interval_seconds: float | None,
) -> _ObserveLaunchConfig:
    config = ensure_observe_config(project)
    key_path = ensure_mesh_key(project, config)
    serve_host, serve_port = _resolve_serve_settings(config)
    return _ObserveLaunchConfig(
        project=project,
        relay_host=relay_host,
        relay_port=_pick_free_port(relay_port),
        dashboard_host=dashboard_host or serve_host,
        dashboard_port=_pick_free_port(dashboard_port or serve_port),
        interval_seconds=interval_seconds,
        key_path=key_path,
        python=resolve_observe_python(),
    )


def _spawn_observe_processes(launch: _ObserveLaunchConfig) -> ObserveProcesses:
    relay_pid = _spawn(
        "relay",
        _koru_cmd(
            launch.python,
            "mesh",
            "relay",
            "--host",
            launch.relay_host,
            "--port",
            str(launch.relay_port),
            "--key-file",
            str(launch.key_path),
        ),
        launch.project,
    )
    relay_url = f"ws://{launch.relay_host}:{launch.relay_port}"

    vision_args = _koru_cmd(
        launch.python,
        "vision",
        "agent",
        "--publish-mesh",
        "--mesh-url",
        relay_url,
        "--peer-id",
        socket.gethostname(),
        "--key-file",
        str(launch.key_path),
    )
    if launch.interval_seconds is not None:
        vision_args.extend(["--interval", str(launch.interval_seconds)])
    vision_pid = _spawn("vision", vision_args, launch.project)

    dashboard_pid = _spawn(
        "dashboard",
        _koru_cmd(
            launch.python,
            "serve",
            "--project",
            str(launch.project),
            "--host",
            launch.dashboard_host,
            "--port",
            str(launch.dashboard_port),
            "--no-open",
        ),
        launch.project,
    )

    dashboard_url = f"http://{launch.dashboard_host}:{launch.dashboard_port}"
    return ObserveProcesses(
        project=launch.project,
        relay_pid=relay_pid,
        vision_pid=vision_pid,
        dashboard_pid=dashboard_pid,
        relay_url=relay_url,
        dashboard_url=dashboard_url,
        grid_url=f"{dashboard_url}/grid",
        key_path=launch.key_path,
        python=launch.python,
    )


def _write_observe_state(project: Path, state: ObserveProcesses) -> None:
    state_file(project).write_text(
        json.dumps(
            {
                **state.to_json(),
                "started_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def observe_down(project: Path) -> dict[str, bool]:
    project = project.expanduser().resolve()
    stopped = {name: _stop_pid(project, name) for name in _PROCESSES}
    _stop_orphan_observe_processes(project)
    state_file(project).unlink(missing_ok=True)
    return stopped


def observe_status(project: Path) -> dict[str, dict[str, Any]]:
    project = project.expanduser().resolve()
    status: dict[str, dict[str, Any]] = {}
    for name in _PROCESSES:
        pid = _read_pid(project, name)
        alive = bool(pid and _is_alive(pid))
        status[name] = {
            "pid": pid,
            "alive": alive,
            "log": str(logfile(project, name)),
        }
    return status
