"""CLI for ``koru observe`` — one-command start/stop/status of observation mesh."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys

from koruobserve.cli_parser import build_observe_parser, project_path
from koruobserve.lifecycle import observe_down, observe_status, observe_up
from koruobserve.providers_cli import (
    cmd_providers_list,
    cmd_providers_reset,
    cmd_providers_test,
)

_OBSERVE_RUNTIME_PACKAGES: tuple[tuple[str, str], ...] = (
    ("websockets", "websockets>=12.0,<16.0"),
    ("mss", "mss>=9.0,<11.0"),
)


def _missing_observe_packages() -> list[tuple[str, str]]:
    return [
        (name, spec)
        for name, spec in _OBSERVE_RUNTIME_PACKAGES
        if importlib.util.find_spec(name) is None
    ]


_INSTALL_HINT = (
    "install with one of:\n"
    "  koru observe install        # auto pip install\n"
    "  pip install 'koru[observe]' # PyPI install\n"
    "  pip install -e '.[observe]' # editable install"
)


def _require_observe_runtime() -> None:
    missing = _missing_observe_packages()
    if not missing:
        return
    names = ", ".join(name for name, _ in missing)
    print(
        f"koru observe: missing observation dependency {names}. "
        "Attempting automatic installation..."
    )
    specs = [spec for _, spec in missing]
    rc = _pip_install(specs)
    if rc != 0:
        raise RuntimeError(
            f"automatic installation of {names} failed with exit code {rc}; {_INSTALL_HINT}"
        )
    print("koru observe: dependencies installed successfully!")


def _pip_install(specs: list[str]) -> int:
    if not specs:
        print("koru observe: dependencies already installed")
        return 0
    cmd = [sys.executable, "-m", "pip", "install", *specs]
    print(f"koru observe: $ {' '.join(cmd)}")
    return subprocess.call(cmd)  # noqa: S603 — user-invoked


def _cmd_install(_args: argparse.Namespace) -> int:
    missing = _missing_observe_packages()
    specs = [spec for _, spec in missing]
    return _pip_install(specs)


def _cmd_up(args: argparse.Namespace) -> int:
    _require_observe_runtime()
    state = observe_up(
        project_path(args),
        relay_host=args.relay_host,
        relay_port=args.relay_port,
        dashboard_host=args.dashboard_host,
        dashboard_port=args.dashboard_port,
        interval_seconds=args.interval,
    )
    lines = [
        "koru observe: up",
        f"  relay     {state.relay_url}   pid={state.relay_pid}",
        f"  vision    pid={state.vision_pid}",
        f"  dashboard {state.dashboard_url}      pid={state.dashboard_pid}",
        f"  open      {state.grid_url}",
    ]
    if state.python != sys.executable:
        lines.append(f"  python    {state.python}  (KORU_OBSERVE_PYTHON or capture probe)")
    print("\n".join(lines))
    return 0


def _cmd_down(args: argparse.Namespace) -> int:
    stopped = observe_down(project_path(args))
    for name, killed in stopped.items():
        print(f"koru observe: {name} stopped={killed}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    status = observe_status(project_path(args))
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if all(item["alive"] for item in status.values()) else 1


def _cmd_grid(args: argparse.Namespace) -> int:
    from koruobserve.paths import state_file

    path = state_file(project_path(args))
    if not path.is_file():
        print(
            "koru observe: not running (no state file). Run 'koru observe up' first.",
            file=sys.stderr,
        )
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    print(data.get("grid_url", ""))
    return 0


def _cmd_trace(args: argparse.Namespace) -> int:
    from koru.cqrs.event_store import JsonlEventStore
    from koru.observability_dsl import (
        OBSERVABILITY_CONTEXT,
        render_observability_path,
        stored_event_to_compact_line,
        stored_event_to_dsl,
    )
    from koru.observability_writer import observability_event_store_path

    project = project_path(args)
    store = JsonlEventStore(observability_event_store_path(project))
    events = [
        event
        for event in store.all_events(context=OBSERVABILITY_CONTEXT)
        if _trace_event_matches(event.payload, corr=args.corr, ticket=args.ticket)
    ]
    limit = int(args.limit or 50)
    if limit > 0:
        events = events[-limit:]
    if args.format == "json":
        print(
            json.dumps(
                {
                    "project": str(project),
                    "count": len(events),
                    "events": [
                        {
                            "sequence": event.sequence,
                            "event_type": event.event_type,
                            "occurred_at": event.occurred_at,
                            "aggregate_id": event.aggregate_id,
                            "payload": event.payload,
                        }
                        for event in events
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not events:
        print(f"koru observe trace: no observability events for {project}")
        return 0
    if args.format == "path":
        print(render_observability_path(events))
        return 0
    renderer = stored_event_to_dsl if args.format == "dsl" else stored_event_to_compact_line
    separator = "\n\n" if args.format == "dsl" else "\n"
    print(separator.join(renderer(event) for event in events))
    return 0


def _trace_event_matches(
    payload: dict[str, object],
    *,
    corr: str | None,
    ticket: str | None,
) -> bool:
    if corr and str(payload.get("corr") or "") != corr:
        return False
    if ticket and str(payload.get("ticket") or "") != ticket:
        return False
    return True


def _cmd_providers(args: argparse.Namespace) -> int:
    project = project_path(args)
    json_out = bool(getattr(args, "json", False))
    sub = getattr(args, "providers_command", None)
    if sub == "list":
        return cmd_providers_list(project, json_out=json_out)
    if sub == "test":
        return cmd_providers_test(
            project,
            getattr(args, "name", None),
            json_out=json_out,
            scale=float(getattr(args, "scale", 0.2) or 0.2),
        )
    if sub == "reset":
        return cmd_providers_reset(project, json_out=json_out)
    print(f"koru observe providers: unknown subcommand {sub!r}", file=sys.stderr)
    return 2


_HANDLERS = {
    "up": _cmd_up,
    "down": _cmd_down,
    "status": _cmd_status,
    "grid": _cmd_grid,
    "trace": _cmd_trace,
    "install": _cmd_install,
    "providers": _cmd_providers,
}


def observe_main(argv: list[str] | None = None) -> int:
    args = build_observe_parser().parse_args(argv)
    handler = _HANDLERS.get(args.command)
    if handler is None:
        print(f"koru observe: unknown command {args.command!r}", file=sys.stderr)
        return 2
    try:
        return handler(args)
    except RuntimeError as exc:
        print(f"koru observe: {exc}", file=sys.stderr)
        return 2
