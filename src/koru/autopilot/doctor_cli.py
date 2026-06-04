"""CLI actions for autopilot diagnostics and host setup."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

from koru.autopilot import host_setup
from koru.autopilot.ide import detect_focused_ide_id, detect_running_ides
from gillm.injection.injector import Injector


def doctor_fix_payload() -> dict[str, object]:
    """Guided remediation payload reused by text and JSON outputs."""
    report = host_setup.build_setup_host_report()
    return {
        "commands": [
            "koru autopilot setup-host",
            "koru autopilot setup-host --install --dry-run",
            "koru autopilot setup-host --install",
            "koru autopilot install-plugin",
        ],
        "automated_apt_suggestion": report.get("automated_apt_suggestion"),
        "human_actions_required": report.get("human_actions_required") or [],
    }


def render_doctor_session_info(injector: Any, selected: str | None) -> None:
    """Render session and selected backend info."""
    print(f"session: {injector.session or 'unknown'}")
    print(f"selected backend: {selected or '(none — install xdotool/wtype/ydotool)'}")


def render_doctor_backends(statuses: list) -> None:
    """Render backend status list."""
    print("backends:")
    for s in statuses:
        mark = "✓" if s.available else "✗"
        print(f"  {mark} {s.name:<10} {s.reason}")


def render_doctor_ides(
    *,
    detect_ides: Callable[[], list] = detect_running_ides,
    detect_focused: Callable[[], str | None] = detect_focused_ide_id,
) -> None:
    """Render running IDEs with focus indicator."""
    ides = detect_ides()
    focused = detect_focused()
    print(f"running IDEs ({len(ides)}):")
    for ide in ides:
        marker = " [focused]" if focused is not None and ide.id == focused else ""
        print(f"  · {ide.label} (pid={ide.pid}){marker}")


def render_doctor_fix_steps(fix_payload: dict[str, object] | None) -> None:
    """Render guided fix steps from payload."""
    if fix_payload is None:
        return
    print("\nnext steps (guided fix):")
    for cmd in fix_payload.get("commands", []):
        print(f"  - {cmd}")
    apt_hint = fix_payload.get("automated_apt_suggestion")
    if isinstance(apt_hint, str) and apt_hint:
        print(f"  - apt suggestion: {apt_hint}")
    human_actions = fix_payload.get("human_actions_required")
    if isinstance(human_actions, list) and human_actions:
        print("human actions still required:")
        for line in human_actions:
            print(f"  - {line}")


def render_doctor_text(
    injector: Any,
    statuses: list,
    selected: str | None,
    fix_payload: dict[str, object] | None,
    *,
    detect_ides: Callable[[], list] = detect_running_ides,
    detect_focused: Callable[[], str | None] = detect_focused_ide_id,
) -> None:
    """Render doctor output in text format."""
    render_doctor_session_info(injector, selected)
    render_doctor_backends(statuses)
    render_doctor_ides(detect_ides=detect_ides, detect_focused=detect_focused)
    render_doctor_fix_steps(fix_payload)


def render_doctor_json(
    injector: Any,
    statuses: list,
    selected: str | None,
    fix_payload: dict[str, object] | None,
    *,
    detect_ides: Callable[[], list] = detect_running_ides,
    detect_focused: Callable[[], str | None] = detect_focused_ide_id,
) -> None:
    """Render doctor output in JSON format."""
    focused = detect_focused()
    payload = {
        "session": injector.session,
        "selected_backend": selected,
        "backends": [s.to_dict() for s in statuses],
        "ides": [i.to_dict() for i in detect_ides()],
        "focused_ide": focused,
    }
    if fix_payload is not None:
        payload["fix"] = fix_payload
    print(json.dumps(payload, indent=2, sort_keys=True))


def action_doctor(
    args: argparse.Namespace,
    *,
    injector_factory: Callable[[], Any] = Injector,
    fix_payload_factory: Callable[[], dict[str, object]] = doctor_fix_payload,
    detect_ides: Callable[[], list] = detect_running_ides,
    detect_focused: Callable[[], str | None] = detect_focused_ide_id,
) -> int:
    injector = injector_factory()
    statuses = injector.probe()
    selected = injector.select_backend()
    fix_payload = fix_payload_factory() if args.fix else None
    if args.output_format == "json":
        render_doctor_json(
            injector,
            statuses,
            selected,
            fix_payload,
            detect_ides=detect_ides,
            detect_focused=detect_focused,
        )
        return 0
    render_doctor_text(
        injector,
        statuses,
        selected,
        fix_payload,
        detect_ides=detect_ides,
        detect_focused=detect_focused,
    )
    return 0 if selected else 1


def action_setup_host(args: argparse.Namespace) -> int:
    return host_setup.run_host_setup(
        output_format=args.output_format,
        install=args.install,
        install_dry_run=args.install_dry_run,
    )
