"""Dashboard HTTP server (koru serve) — canonical CLI in :mod:`koruapi`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from koru.events import emit_management_event
from koruapi.dashboard_serve import DEFAULT_HOST, DEFAULT_PORT, ServeConfig, serve


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _argv_has_flag(argv: list[str], *names: str) -> bool:
    return any(arg == name or arg.startswith(f"{name}=") for arg in argv for name in names)


def build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru serve",
        description=(
            "Run the koru dashboard (live LLM brief, tickets, topology). "
            "Canonical implementation: koruapi.dashboard."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--queue-name",
        default=None,
        help="Queue used when selecting the active ticket.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address (default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Expose the dashboard on the local network (binds 0.0.0.0).",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root used for project discovery in the dashboard.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port (default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Try next ports if busy (also when KORU_SERVE_AUTO_PORT=1).",
    )
    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        default=True,
        help="Open dashboard in browser (default).",
    )
    open_group.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser tab.",
    )
    return parser


def _resolve_serve_config(
    args: argparse.Namespace,
    raw_argv: list[str],
    saved: dict,
    project: "Path",
) -> "ServeConfig":
    saved_serve = saved.get("serve") if isinstance(saved.get("serve"), dict) else {}
    lan = _resolve_serve_lan(args, raw_argv, saved_serve)
    host = _resolve_serve_host(args, raw_argv, saved_serve, lan=lan)
    port = _resolve_serve_port(args, raw_argv, saved_serve)
    queue_name = _resolve_serve_queue_name(args, saved)
    workspace = _resolve_serve_workspace(args, saved)
    auto_port = _resolve_serve_auto_port(args, raw_argv, saved_serve)
    return ServeConfig(
        project=project,
        host=host,
        port=port,
        open_browser=args.open_browser,
        queue_name=queue_name,
        auto_port=auto_port,
        lan=lan,
        workspace=workspace.resolve() if workspace else None,
    )


def _resolve_serve_lan(
    args: argparse.Namespace,
    raw_argv: list[str],
    saved_serve: dict,
) -> bool:
    lan_from_config = bool(saved_serve.get("lan")) and not _argv_has_flag(
        raw_argv, "--lan", "--host"
    )
    return bool(args.lan) or lan_from_config


def _resolve_serve_host(
    args: argparse.Namespace,
    raw_argv: list[str],
    saved_serve: dict,
    *,
    lan: bool,
) -> str:
    host = args.host
    if not _argv_has_flag(raw_argv, "--host"):
        host = str(saved_serve.get("host") or host)
    if lan and host == DEFAULT_HOST:
        return "0.0.0.0"
    return host


def _resolve_serve_port(
    args: argparse.Namespace,
    raw_argv: list[str],
    saved_serve: dict,
) -> int:
    if _argv_has_flag(raw_argv, "--port"):
        return args.port
    return int(saved_serve.get("port") or args.port)


def _resolve_serve_queue_name(args: argparse.Namespace, saved: dict) -> str | None:
    if args.queue_name is not None:
        return args.queue_name
    return str(saved.get("queue_name") or "") or None


def _resolve_serve_workspace(args: argparse.Namespace, saved: dict) -> Path | None:
    if args.workspace is not None:
        return args.workspace
    if saved.get("workspace"):
        return Path(str(saved["workspace"]))
    return None


def _resolve_serve_auto_port(
    args: argparse.Namespace,
    raw_argv: list[str],
    saved_serve: dict,
) -> bool:
    auto_port = bool(args.auto_port) or _env_truthy("KORU_SERVE_AUTO_PORT")
    if _argv_has_flag(raw_argv, "--auto-port"):
        return auto_port
    return auto_port or bool(saved_serve.get("auto_port"))


def dashboard_main(argv: list[str] | None = None) -> int:
    """Entry point for ``koru serve`` and ``koru api dashboard``."""
    from koru.activity_log import activity
    from koru.configurator import load_project_config
    from koru.dotenv_loader import load_dotenv

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_serve_parser().parse_args(raw_argv)
    project = args.project.resolve()
    load_dotenv(project)
    saved = load_project_config(project)
    config = _resolve_serve_config(args, raw_argv, saved, project)
    activity(
        "HTTP",
        f"dashboard start project={config.project} http://{config.host}:{config.port}/",
    )
    exit_code = serve(config)
    emit_management_event(
        tool="koru.serve",
        action="completed" if exit_code == 0 else "failed",
        status="completed" if exit_code == 0 else "failed",
        level="info" if exit_code == 0 else "error",
        message=f"exit={exit_code}",
        queue=config.queue_name,
    )
    return exit_code
