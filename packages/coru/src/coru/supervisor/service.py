"""Supervisor runtime: health refresh loop and daemon orchestration."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path
from typing import Callable, Sequence

from coru.supervisor.daemon_ctl import start_daemon, stop_daemon
from coru.supervisor.models import LaneHealth, LaneRecord
from coru.supervisor.paths import default_http_host, default_http_port, pid_path, registry_path
from coru.supervisor.probe import probe_lane_health
from coru.supervisor.registry import load_registry, save_registry, update_lane_health


class SupervisorService:
    def __init__(
        self,
        *,
        registry_file: Path | None = None,
        koru_argv: Sequence[str] | None = None,
        verbose: bool = False,
        refresh_interval: float = 30.0,
    ) -> None:
        self.registry_path = registry_file or registry_path()
        self.koru_argv = list(koru_argv or ("koru",))
        self.verbose = verbose
        self.refresh_interval = max(5.0, refresh_interval)
        self.pid = os.getpid()
        self._http: SupervisorHTTPServer | None = None
        self._stop = False

    @property
    def url(self) -> str:
        if self._http is None:
            registry = load_registry(path=self.registry_path)
            return f"http://{registry.http_host}:{registry.http_port}"
        return self._http.url

    def _record_for(self, instance: str) -> LaneRecord | None:
        registry = load_registry(path=self.registry_path)
        return registry.lanes.get(instance)

    def refresh_lane_health(self, record: LaneRecord) -> LaneHealth:
        health = probe_lane_health(record, koru_argv=self.koru_argv)
        update_lane_health(record.instance, health, path=self.registry_path)
        return health

    def refresh_all_health(self) -> None:
        registry = load_registry(path=self.registry_path)
        for record in registry.lanes.values():
            self.refresh_lane_health(record)

    def start_lane_daemon(self, instance: str) -> tuple[bool, str]:
        record = self._record_for(instance)
        if record is None:
            return False, f"unknown lane: {instance}"
        ok, detail = start_daemon(record, koru_argv=self.koru_argv)
        if ok:
            self.refresh_lane_health(record)
        return ok, detail

    def stop_lane_daemon(self, instance: str) -> tuple[bool, str]:
        record = self._record_for(instance)
        if record is None:
            return False, f"unknown lane: {instance}"
        ok, detail = stop_daemon(record, koru_argv=self.koru_argv)
        if ok:
            self.refresh_lane_health(record)
        return ok, detail

    def reconnect_lane(self, instance: str) -> tuple[bool, str]:
        """Restart a lane daemon to force a fresh plugin reconnect path."""
        record = self._record_for(instance)
        if record is None:
            return False, f"unknown lane: {instance}"

        stop_ok, stop_detail = stop_daemon(record, koru_argv=self.koru_argv)
        start_ok, start_detail = start_daemon(record, koru_argv=self.koru_argv)

        if start_ok:
            self.refresh_lane_health(record)
            if stop_ok:
                return True, f"reconnected: stop={stop_detail}; start={start_detail}"
            return True, f"reconnected (stop warning: {stop_detail}); start={start_detail}"

        if stop_ok:
            return False, f"reconnect failed after stop: {start_detail}"
        return False, f"reconnect failed: stop={stop_detail}; start={start_detail}"

    def ensure_http(self) -> object:
        if self._http is not None:
            return self._http
        from coru.supervisor.http_server import SupervisorHTTPServer

        registry = load_registry(path=self.registry_path)
        host = registry.http_host or default_http_host()
        port = registry.http_port or default_http_port()
        self._http = SupervisorHTTPServer(self, host=host, port=port)
        registry.http_host = self._http.host
        registry.http_port = self._http.port
        save_registry(registry, path=self.registry_path)
        return self._http

    def write_pid_file(self) -> None:
        target = pid_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(self.pid), encoding="utf-8")

    def remove_pid_file(self) -> None:
        with __import__("contextlib").suppress(OSError):
            pid_path().unlink(missing_ok=True)

    def run(
        self,
        *,
        foreground: bool = True,
        watch: bool = True,
    ) -> int:
        self.write_pid_file()
        http = self.ensure_http()
        if foreground:
            http.start_background()
            print(f"coru supervisor: listening on {http.url}", flush=True)
            print(f"coru supervisor: registry {self.registry_path}", flush=True)

        def _handle_stop(_signo: int, _frame: object) -> None:
            self._stop = True

        signal.signal(signal.SIGTERM, _handle_stop)
        signal.signal(signal.SIGINT, _handle_stop)

        try:
            self.refresh_all_health()
            while not self._stop:
                if watch:
                    self.refresh_all_health()
                time.sleep(self.refresh_interval)
        finally:
            if self._http is not None:
                self._http.shutdown()
            self.remove_pid_file()
        return 0


def read_supervisor_pid() -> int | None:
    target = pid_path()
    if not target.is_file():
        return None
    raw = target.read_text(encoding="utf-8").strip()
    if not raw.isdigit():
        return None
    return int(raw)


def supervisor_running() -> bool:
    pid = read_supervisor_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def stop_supervisor_process(*, timeout: float = 5.0) -> tuple[bool, str]:
    pid = read_supervisor_pid()
    if pid is None:
        return False, "supervisor is not running (no pid file)"
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return False, str(exc)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            with __import__("contextlib").suppress(OSError):
                pid_path().unlink(missing_ok=True)
            return True, "supervisor stopped"
        time.sleep(0.1)
    return False, f"supervisor pid {pid} did not stop within {timeout:.0f}s"
