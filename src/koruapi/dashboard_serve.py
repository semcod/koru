"""Minimal local dashboard server for koru (canonical: :mod:`koruapi.dashboard_serve`).

Serves a small HTML page that calls back into ``build_context`` to show
the live LLM brief (active ticket, policy, agent lanes, gates). No
external dependencies — uses ``http.server`` from the stdlib.

This module owns the *lifecycle* (bind retry, ``serve_forever``,
``KeyboardInterrupt`` shutdown, ``serve-endpoint.json``); the per-route
implementations live in :mod:`koruapi.dashboard_routes`
(``build_dashboard_handler``), the port/bind helpers live in
:mod:`koruapi.dashboard_serve_utils`, and the HTML template lives in
``koruapi/dashboard_template.html`` (loaded once via ``@lru_cache``).

TCP port defaults to ``8765``. Use ``--auto-port`` or set
``KORU_SERVE_AUTO_PORT=1`` to try the next ports (then an ephemeral
port) when the preferred port is busy. The resolved URL is written to
``.planfile/.koru/serve-endpoint.json`` for other tooling
(``read_serve_endpoint``).

When the preferred port is busy with a **previous** ``koru serve`` listener
(same host/port), a second ``koru serve`` sends **SIGTERM** to that PID and
retries the bind once (Linux: uses ``ss``). Other processes (e.g. planfile
on :8765) are left untouched. Set ``KORU_SERVE_NO_REPLACE=1`` to disable.

Endpoints:
    GET  /              -> HTML dashboard (auto-refreshing)
    GET  /api/context   -> JSON brief (``build_context`` output)
    GET  /api/handoff   -> raw markdown handoff (``render_markdown_handoff``)
    GET  /api/topology  -> merged topology JSON (defaults + persisted overrides)
    POST /api/topology  -> persist topology enable/disable edits
    GET  /grid          -> observation mesh screenshot grid (served by korumesh)
    GET  /api/mesh/frames -> JSON frames published by ``koru observe`` peers
    GET  /health        -> ``{"ok": true}``

Bound to ``127.0.0.1`` by default — never exposed to the network unless
``--bind`` is explicitly set otherwise.
"""

from __future__ import annotations

import contextlib
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from koru.events import emit_management_event
from koruapi.dashboard_routes import build_dashboard_handler
from koruapi.dashboard_serve_utils import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ServeConfig,
    _address_in_use,
    _cmdline_suggests_koru_serve,
    _cmdline_suggests_koru_serve_from_bytes,
    _listener_pids_for_tcp_port,
    _try_stop_prior_koru_serve_listener,
    bind_serve_server,
    build_server,
    read_serve_endpoint,
    serve_endpoint_path,
    write_serve_endpoint_file,
)
from koruapi.dashboard_state import dashboard_urls

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "ServeConfig",
    "_address_in_use",
    "_cmdline_suggests_koru_serve",
    "_cmdline_suggests_koru_serve_from_bytes",
    "_listener_pids_for_tcp_port",
    "_try_stop_prior_koru_serve_listener",
    "bind_serve_server",
    "build_server",
    "read_serve_endpoint",
    "serve",
    "serve_endpoint_path",
    "start_serve_background",
    "write_serve_endpoint_file",
]


def _dashboard_urls(config: ServeConfig) -> list[str]:
    """All visible URLs for the dashboard given ``config`` (local + LAN)."""
    return dashboard_urls(config.host, config.port)


def _build_handler(config: ServeConfig) -> type[BaseHTTPRequestHandler]:
    """Backwards-compatible alias for :func:`build_dashboard_handler`."""
    return build_dashboard_handler(config)


@dataclass(frozen=True)
class _BoundDashboard:
    server: ThreadingHTTPServer
    bound_port: int
    requested: int
    url: str
    urls: list[str]


def _emit_serve_event(
    config: ServeConfig,
    *,
    url: str,
    requested: int,
    background: bool = False,
) -> None:
    details: dict[str, Any] = {
        "project": str(config.project),
        "open_browser": config.open_browser,
        "port": config.port,
        "requested_port": requested,
    }
    if background:
        details["background"] = True
    emit_management_event(
        tool="koru.serve",
        action="started",
        status="running",
        message=url,
        queue=config.queue_name,
        details=details,
    )


def _schedule_browser_open(url: str) -> None:
    def _open_later() -> None:
        with contextlib.suppress(Exception):  # pragma: no cover — best-effort
            webbrowser.open(url, new=2)

    threading.Timer(0.3, _open_later).start()


def _log_bind_summary(
    config: ServeConfig,
    *,
    bound: _BoundDashboard,
    log: Callable[[str], None],
) -> None:
    if config.auto_port and bound.requested != 0 and bound.bound_port != bound.requested:
        log(f"koru serve: port {bound.requested} busy — bound to {bound.bound_port} instead")
    log(f"koru serve: dashboard at {bound.url}")
    if len(bound.urls) > 1:
        log("koru serve: LAN URLs:")
        for visible_url in bound.urls:
            log(f"  {visible_url}")
    log(f"koru serve: project = {config.project}")


def _prepare_bound_dashboard(config: ServeConfig) -> _BoundDashboard:
    server, bound_port, requested = bind_serve_server(config)
    write_serve_endpoint_file(config)
    return _BoundDashboard(
        server=server,
        bound_port=bound_port,
        requested=requested,
        url=f"http://{config.host}:{config.port}/",
        urls=_dashboard_urls(config),
    )


def _announce_bound_dashboard(
    config: ServeConfig,
    *,
    bound: _BoundDashboard,
    log: Callable[[str], None],
    background: bool = False,
) -> None:
    _log_bind_summary(config, bound=bound, log=log)
    _emit_serve_event(
        config,
        url=bound.url,
        requested=bound.requested,
        background=background,
    )
    if config.open_browser:
        _schedule_browser_open(bound.url)


def _bind_or_print(config: ServeConfig) -> _BoundDashboard | None:
    try:
        return _prepare_bound_dashboard(config)
    except OSError as exc:
        if config.auto_port:
            print(str(exc), file=sys.stderr)
        else:
            print(f"koru serve: cannot bind {config.host}:{config.port} — {exc}", file=sys.stderr)
        return None


def serve(config: ServeConfig) -> int:
    """Start the dashboard server and block until Ctrl-C.

    Returns the process exit code (0 on clean shutdown).
    """
    bound = _bind_or_print(config)
    if bound is None:
        return 1

    _announce_bound_dashboard(config, bound=bound, log=print)
    print("koru serve: Ctrl-C to stop")

    try:
        bound.server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru serve: stopping")
    finally:
        bound.server.server_close()
    return 0


def start_serve_background(
    config: ServeConfig,
    *,
    log: Callable[[str], None] = print,
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Bind the dashboard, write ``serve-endpoint.json``, and run ``serve_forever`` on a thread.

    The caller should ``shutdown()`` the server, ``server_close()``, and
    ``join()`` the returned thread when tearing down (e.g. ``koru autonomous``).
    """
    bound = _prepare_bound_dashboard(config)
    _announce_bound_dashboard(config, bound=bound, log=log, background=True)

    thread = threading.Thread(
        target=bound.server.serve_forever,
        name="koru-serve-bg",
        daemon=True,
    )
    thread.start()
    time.sleep(0.05)
    return bound.server, thread
