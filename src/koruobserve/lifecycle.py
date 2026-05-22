"""Start, stop, and inspect background processes for the observation mesh."""

from __future__ import annotations

import errno
import json
import os
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

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["project"] = str(self.project)
        data["key_path"] = str(self.key_path)
        return data


def _resolve_serve_settings(config: dict[str, Any]) -> tuple[str, int]:
    serve = config.get("serve") if isinstance(config.get("serve"), dict) else {}
    host = str(serve.get("host") or "127.0.0.1")
    port = int(serve.get("port") or 8765)
    return host, port


def _pick_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
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
    proc = subprocess.Popen(  # noqa: S603 — caller-controlled koru CLI
        args,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        cwd=str(project),
        start_new_session=True,
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


def _koru_cmd(*args: str) -> list[str]:
    return [sys.executable, "-m", "koru", *args]


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
    runtime_dir(project).mkdir(parents=True, exist_ok=True)
    config = ensure_observe_config(project)
    key_path = ensure_mesh_key(project, config)

    serve_host, serve_port = _resolve_serve_settings(config)
    host = dashboard_host or serve_host
    port = _pick_free_port(dashboard_port or serve_port)
    relay_port_resolved = _pick_free_port(relay_port)

    relay_pid = _spawn(
        "relay",
        _koru_cmd(
            "mesh",
            "relay",
            "--host",
            relay_host,
            "--port",
            str(relay_port_resolved),
            "--key-file",
            str(key_path),
        ),
        project,
    )
    relay_url = f"ws://{relay_host}:{relay_port_resolved}"

    vision_args = _koru_cmd(
        "vision",
        "agent",
        "--project",
        str(project),
        "--publish-mesh",
        "--mesh-url",
        relay_url,
        "--peer-id",
        socket.gethostname(),
        "--key-file",
        str(key_path),
    )
    if interval_seconds is not None:
        vision_args.extend(["--interval", str(interval_seconds)])
    vision_pid = _spawn("vision", vision_args, project)

    dashboard_pid = _spawn(
        "dashboard",
        _koru_cmd(
            "serve",
            "--project",
            str(project),
            "--host",
            host,
            "--port",
            str(port),
            "--no-open",
        ),
        project,
    )

    dashboard_url = f"http://{host}:{port}"
    state = ObserveProcesses(
        project=project,
        relay_pid=relay_pid,
        vision_pid=vision_pid,
        dashboard_pid=dashboard_pid,
        relay_url=relay_url,
        dashboard_url=dashboard_url,
        grid_url=f"{dashboard_url}/grid",
        key_path=key_path,
    )
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
    return state


def observe_down(project: Path) -> dict[str, bool]:
    project = project.expanduser().resolve()
    stopped = {name: _stop_pid(project, name) for name in _PROCESSES}
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
