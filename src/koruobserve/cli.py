"""CLI for ``koru observe`` — one-command start/stop/status of observation mesh."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys

from koruobserve.cli_parser import build_observe_parser, project_path
from koruobserve.lifecycle import observe_down, observe_status, observe_up


_OBSERVE_RUNTIME_PACKAGES: tuple[tuple[str, str], ...] = (
    ("websockets", "websockets>=12.0,<16.0"),
    ("mss", "mss>=9.0,<11.0"),
)


def _missing_observe_packages() -> list[tuple[str, str]]:
    return [(name, spec) for name, spec in _OBSERVE_RUNTIME_PACKAGES if importlib.util.find_spec(name) is None]


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
    raise RuntimeError(f"missing observation dependency {names}; {_INSTALL_HINT}")


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
    print(
        f"koru observe: up\n"
        f"  relay     {state.relay_url}   pid={state.relay_pid}\n"
        f"  vision    pid={state.vision_pid}\n"
        f"  dashboard {state.dashboard_url}      pid={state.dashboard_pid}\n"
        f"  open      {state.grid_url}"
    )
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
        print("koru observe: not running (no state file). Run 'koru observe up' first.", file=sys.stderr)
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    print(data.get("grid_url", ""))
    return 0


_HANDLERS = {
    "up": _cmd_up,
    "down": _cmd_down,
    "status": _cmd_status,
    "grid": _cmd_grid,
    "install": _cmd_install,
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
