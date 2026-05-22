"""Process and port management utilities for the dashboard serve module.

Holds the :class:`ServeConfig` dataclass plus the low-level helpers that
:mod:`koruapi.dashboard_serve` composes together: address-in-use detection,
prior listener takeover, bind retry loop, and endpoint-file I/O. The
``build_server`` / ``bind_serve_server`` / ``write_serve_endpoint_file``
helpers keep their **single-argument** call signatures so that callers and
tests that pre-date the refactor keep working.
"""

from __future__ import annotations

import errno
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
_SERVE_ENDPOINT_REL = Path(".planfile") / ".koru" / "serve-endpoint.json"
_REPLACE_DISABLED = {"1", "true", "yes", "on"}


@dataclass
class ServeConfig:
    project: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    open_browser: bool = True
    queue_name: str | None = None
    auto_port: bool = False
    lan: bool = False
    workspace: Path | None = None


def _address_in_use(exc: BaseException) -> bool:
    if isinstance(exc, OSError):
        if exc.errno in (errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", -1)):
            return True
        if getattr(exc, "winerror", None) == 10048:  # WSAEADDRINUSE
            return True
    return "Address already in use" in str(exc)


def _listener_pids_for_tcp_port(port: int) -> list[int]:
    """Return PIDs listening on *port* (Linux ``ss``); empty if unknown."""
    if sys.platform == "win32":
        return []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-ltnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    pids: list[int] = []
    for match in re.finditer(r"pid=(\d+)", text):
        try:
            pids.append(int(match.group(1)))
        except ValueError:
            continue
    return list(dict.fromkeys(pids))


def _cmdline_suggests_koru_serve_from_bytes(raw: bytes) -> bool:
    """True if *raw* is a ``/proc/*/cmdline`` blob for ``koru … serve`` (not ``mcp-serve``)."""
    text = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").lower()
    if re.search(r"\bmcp-serve\b", text):
        return False
    if re.search(r"-m\s+koru\.cli\s+serve\b", text):
        return True
    return bool(re.search(r"(^|[\s/])koru(\.cli)?\s+serve\b", text))


def _cmdline_suggests_koru_serve(pid: int) -> bool:
    if sys.platform == "win32":
        return False
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return _cmdline_suggests_koru_serve_from_bytes(raw)


def _replace_disabled() -> bool:
    return os.environ.get("KORU_SERVE_NO_REPLACE", "").strip().lower() in _REPLACE_DISABLED


def _kill_prior_listeners(port: int) -> bool:
    killed = False
    for pid in _listener_pids_for_tcp_port(port):
        if pid == os.getpid() or not _cmdline_suggests_koru_serve(pid):
            continue
        try:
            print(
                f"koru serve: port {port} busy — stopping prior listener pid={pid}",
                file=sys.stderr,
            )
            os.kill(pid, signal.SIGTERM)
            killed = True
        except ProcessLookupError:
            continue
    return killed


def _wait_for_prior_listeners_to_exit(port: int) -> None:
    for _ in range(40):
        remaining = [
            pid
            for pid in _listener_pids_for_tcp_port(port)
            if pid != os.getpid() and _cmdline_suggests_koru_serve(pid)
        ]
        if not remaining:
            return
        time.sleep(0.1)


def _try_stop_prior_koru_serve_listener(host: str, port: int) -> bool:
    """SIGTERM prior ``koru serve`` on *port*; return True if we sent a signal."""
    del host  # ss filter is port-centric; 127.0.0.1 vs 0.0.0.0 both match sport
    if _replace_disabled():
        return False
    if not _kill_prior_listeners(port):
        return False
    _wait_for_prior_listeners_to_exit(port)
    return True


def serve_endpoint_path(project: Path) -> Path:
    """JSON path where the last successful ``koru serve`` bind is recorded."""
    return project.resolve() / _SERVE_ENDPOINT_REL


def read_serve_endpoint(project: Path) -> dict[str, Any] | None:
    """Load ``serve-endpoint.json`` if present; return ``None`` on missing/invalid."""
    path = serve_endpoint_path(project)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _build_handler_for(config: ServeConfig) -> type:
    """Lazy import of the request-handler factory to break a circular import."""
    from koruapi.dashboard_routes import build_dashboard_handler

    return build_dashboard_handler(config)


def build_server(config: ServeConfig) -> ThreadingHTTPServer:
    """Construct (but do not start) the dashboard HTTP server."""
    return ThreadingHTTPServer((config.host, config.port), _build_handler_for(config))


def _bind_single(config: ServeConfig, port: int) -> tuple[ThreadingHTTPServer, int]:
    config.port = port
    server = build_server(config)
    actual = int(server.server_address[1])
    config.port = actual
    return server, actual


def _bind_fixed_port(config: ServeConfig) -> tuple[ThreadingHTTPServer, int, int]:
    requested = config.port
    try:
        server, actual = _bind_single(config, requested)
        return server, actual, requested
    except OSError as exc:
        if not _address_in_use(exc):
            raise
        if not _try_stop_prior_koru_serve_listener(config.host, config.port):
            raise
    server, actual = _bind_single(config, requested)
    return server, actual, requested


def _bind_auto_port(config: ServeConfig) -> tuple[ThreadingHTTPServer, int, int]:
    requested = config.port
    ceiling = min(requested + 33, 65536)
    candidates = [requested] + [p for p in range(requested + 1, ceiling) if p != requested]
    last_err: OSError | None = None
    for port in candidates:
        try:
            server, actual = _bind_single(config, port)
            return server, actual, requested
        except OSError as exc:
            last_err = exc
            continue
    try:
        server, actual = _bind_single(config, 0)
    except OSError as exc:
        msg = f"koru serve: cannot bind {config.host} starting from port {requested}"
        if last_err is not None:
            msg += f" — {last_err}"
        raise OSError(msg) from exc
    return server, actual, requested


def bind_serve_server(config: ServeConfig) -> tuple[ThreadingHTTPServer, int, int]:
    """Bind a server; set ``config.port`` to the listening port.

    Returns ``(server, actual_port, requested_port)``.
    """
    if config.auto_port:
        return _bind_auto_port(config)
    return _bind_fixed_port(config)


def _dashboard_urls_for(config: ServeConfig) -> list[str]:
    """Lazy import of the dashboard URL helper."""
    from koruapi.dashboard_state import dashboard_urls

    return dashboard_urls(config.host, config.port)


def write_serve_endpoint_file(config: ServeConfig) -> None:
    """Persist dashboard base URL and port for other tools (``read_serve_endpoint``)."""
    koru_dir = config.project.resolve() / ".planfile" / ".koru"
    koru_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "http_base": f"http://{config.host}:{config.port}",
        "host": config.host,
        "lan": bool(config.lan or config.host in {"0.0.0.0", "::"}),
        "urls": _dashboard_urls_for(config),
        "port": config.port,
        "pid": os.getpid(),
    }
    (koru_dir / "serve-endpoint.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
