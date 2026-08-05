"""``koru autopilot route`` — render gillm's solution router for a lane.

Answers "which control path would drive this IDE from THIS host, and why"
before anything touches the keyboard: connected plugin and vdisplay rank
as verified routes, keyboard injection is guarded/blind depending on what
the compositor lets us verify (see :mod:`gillm.routing`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path


def _plugin_connected(client_factory: Callable, args: argparse.Namespace, ide: str) -> bool:
    """True when the lane daemon reports a connected plugin for ``ide``."""
    try:
        info = client_factory(args).status()
    except Exception:
        return False
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    for row in plugins:
        if not isinstance(row, dict):
            continue
        row_ide = str(row.get("ide") or row.get("id") or "").strip().lower()
        if ide in ("", "auto") or row_ide == ide:
            return True
    return False


def _render_plan_text(plan) -> None:
    env = plan.environment
    print(f"environment: session={env.session or 'unknown'} desktop={env.desktop or '-'}")
    print(
        f"  keyboard={', '.join(env.keyboard_backends) or '-'}; "
        f"focus_detection={env.focus_detection}; vdisplay={env.vdisplay_available}; "
        f"blind_opt_in={env.blind_opt_in}"
    )
    print(
        f"app: {plan.app.app_id or '-'} "
        f"(calibration={plan.app.has_calibration}, plugin={plan.app.plugin_connected})"
    )
    print("solutions:")
    for solution in plan.solutions:
        mark = "→" if plan.selected is solution else ("✓" if solution.viable else "✗")
        ext = " [external]" if solution.external else ""
        print(f"  {mark} {solution.solution_id:<28} {solution.confidence:<9}{ext} {solution.reason}")
    if plan.selected is None:
        print("no viable control route — see reasons above")


def action_route(args: argparse.Namespace, *, client_factory: Callable) -> int:
    try:
        from gillm.routing import route_for
    except ImportError:
        print(
            "koru autopilot route: requires gillm>=0.1.22 — pip install -U gillm",
            file=sys.stderr,
        )
        return 2

    from koruide.ide import canonical_autopilot_ide_id

    from koru.autopilot.lane_context import resolve_lane_context

    requested = getattr(args, "ide", None) or "auto"
    project = getattr(args, "project", None)
    ctx = resolve_lane_context(
        requested_ide=requested,
        project=Path(project) if project else None,
    )
    ide = ctx.ide or canonical_autopilot_ide_id(requested) or "auto"

    plan = route_for(ide, plugin_connected=_plugin_connected(client_factory, args, ide))

    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(plan.to_dict(), indent=2))
    else:
        _render_plan_text(plan)
    return 0 if plan.selected else 1


__all__ = ["action_route"]
