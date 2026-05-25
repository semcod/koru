"""CLI for ``koru api`` / ``koru-api``."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Callable

from .dashboard import dashboard_main
from .integrations import list_integrations
from .invoke import InvokeError, invoke_integration
from .local import local_main
from .mcp import mcp_main
from .server import DEFAULT_HOST as API_DEFAULT_HOST
from .server import DEFAULT_PORT as API_DEFAULT_PORT
from .server import serve as api_serve


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru api",
        description="HTTP API and CLI for all koru integrations.",
    )
    parser.add_argument("--version", action="version", version=f"koru-api {_cli_version()}")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root (default: cwd).",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="List integration catalog (JSON).")

    invoke = sub.add_parser("invoke", help="Invoke one integration.")
    invoke.add_argument("integration_id", help="Integration id, e.g. scan.apply")
    invoke.add_argument("--method", default="run", help="Method name (integration-specific).")
    invoke.add_argument(
        "--body",
        default="{}",
        help="JSON object with arguments (or @file.json).",
    )

    for name, help_text in (
        ("http", "Start integration HTTP API (port 8790)."),
        ("serve", "Alias for http (integration API)."),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--host", default=API_DEFAULT_HOST)
        p.add_argument("--port", type=int, default=API_DEFAULT_PORT)
    sub.add_parser("dashboard", help="Start HTML dashboard (port 8765, same as koru serve).")
    sub.add_parser("mcp", help="Start MCP stdio server (same as koru mcp-serve).")
    sub.add_parser("local", help="Start local event hub (port 18766).")

    return parser


def _cli_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _parse_body(raw: str) -> dict:
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text(encoding="utf-8"))
    return json.loads(raw or "{}")


def _action_list(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    payload = [
        {
            "id": s.id,
            "title": s.title,
            "transport": s.transport,
            "methods": list(s.methods),
            "cli_equivalent": s.cli_equivalent,
        }
        for s in list_integrations()
    ]
    sys.stdout.write(json.dumps({"integrations": payload}, indent=2) + "\n")
    return 0


def _action_invoke(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    from koru.activity_log import activity

    try:
        body = _parse_body(args.body)
    except json.JSONDecodeError as exc:
        print(f"koru api invoke: invalid --body JSON: {exc}", file=sys.stderr)
        return 2
    activity(
        "API",
        f"invoke {args.integration_id} method={args.method} project={project}",
    )
    try:
        result = invoke_integration(
            args.integration_id,
            project=project,
            method=args.method,
            body=body,
        )
    except InvokeError as exc:
        activity("API", f"invoke failed: {exc}")
        print(f"koru api invoke: {exc}", file=sys.stderr)
        return 1
    activity("API", f"invoke ok {args.integration_id}")
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    return 0


def _action_serve(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    api_serve(project=project, host=args.host, port=args.port)
    return 0


def _action_dashboard(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    return dashboard_main(rest)


def _action_mcp(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    return mcp_main(rest)


def _action_local(args: argparse.Namespace, rest: list[str], project: Path) -> int:
    return local_main(rest)


# Dispatch table: action name -> handler. Single source of truth for routing.
_ACTIONS: dict[str, Callable[[argparse.Namespace, list[str], Path], int]] = {
    "list": _action_list,
    "invoke": _action_invoke,
    "http": _action_serve,
    "serve": _action_serve,
    "dashboard": _action_dashboard,
    "mcp": _action_mcp,
    "local": _action_local,
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args, rest = parser.parse_known_args(argv)
    project = args.project.resolve()

    handler = _ACTIONS.get(args.action)
    if handler is None:
        return 2
    return handler(args, rest, project)


if __name__ == "__main__":
    raise SystemExit(main())
