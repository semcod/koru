"""Local event hub (koru local-serve)."""

from __future__ import annotations

import argparse
import sys

from koru.local_service import LocalServiceConfig, default_local_service_config, run_local_service


def build_local_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru local-serve",
        description="Localhost JSON/NDJSON event hub (see docs/local-service.md).",
    )
    parser.add_argument("--host", default=None, help="Bind host (default from env).")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default 18766).")
    parser.add_argument("--max-events", type=int, default=None, help="Ring buffer size.")
    return parser


def local_main(argv: list[str] | None = None) -> int:
    from koru.activity_log import activity

    args = build_local_parser().parse_args(argv)
    base = default_local_service_config()
    host = (args.host if args.host is not None else base.host).strip() or base.host
    port = base.port if args.port is None else args.port
    max_events = base.max_events if args.max_events is None else args.max_events
    if max_events < 1:
        print("koru local-serve: --max-events must be >= 1", file=sys.stderr)
        return 2
    max_events = min(max_events, 10_000)
    config = LocalServiceConfig(host=host, port=port, max_events=max_events)
    activity("HTTP", f"local-serve http://{host}:{port}/ (max_events={max_events})")
    return run_local_service(config)
