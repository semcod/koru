"""Interactive onboarding bridge for ``koru auto``.

This module intentionally delegates interactive logic to ``koru.wizard`` so
there is only one implementation of:

- IDE discovery (running processes + install locations),
- project selection,
- JSON-driven strategy tree,
- optional llx dynamic branch expansion,
- first ticket creation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from koru.wizard.cli import StdinPrompter, run_wizard
from koru.wizard.ide import DetectedIDE, discover_installed_ides
from koru.wizard.llx import llx_available
from koru.wizard.tree import StrategyTree, load_tree
from koruide.ide import normalize_ide_id


@dataclass(frozen=True)
class OnboardingOutcome:
    """Summary returned after the wizard-driven onboarding flow."""

    changed_args: bool
    selected_ide: str | None
    selected_project: Path
    strategy_path: tuple[str, ...]
    created_ticket_id: str | None
    created_ticket_title: str


def _env_truthy(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_strategies_path(project: Path) -> Path | None:
    """Resolve optional project-local strategy tree override file."""
    for candidate in (
        project / ".koru" / "strategies.json",
        project / "strategies.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _koru_project_dir(project: Path) -> Path:
    return project.resolve() / ".koru"


def has_project_onboarding_state(project: Path) -> bool:
    """Return True when the project already has koru-owned local state."""
    project = project.resolve()
    if _koru_project_dir(project).is_dir():
        return True
    return (project / ".planfile" / ".koru").is_dir()


def ensure_project_state(project: Path, *, source: str) -> None:
    """Create/update the project-local `.koru` state directory."""
    project = project.resolve()
    koru_dir = _koru_project_dir(project)
    koru_dir.mkdir(parents=True, exist_ok=True)
    path = koru_dir / "project.json"
    previous: dict[str, object] = {}
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    now = datetime.now(UTC).isoformat()
    payload = {
        "schema": "koru.project/v1",
        "project": str(project),
        "runtime_dir": ".planfile/.koru",
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
        "source": source,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_project_history(project: Path, event: dict[str, object]) -> None:
    koru_dir = _koru_project_dir(project)
    koru_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **event,
    }
    with (koru_dir / "history.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_onboarding_state(project: Path, outcome: OnboardingOutcome) -> None:
    koru_dir = _koru_project_dir(project)
    koru_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "koru.onboarding/v1",
        "project": str(project.resolve()),
        "selected_ide": outcome.selected_ide,
        "strategy_path": list(outcome.strategy_path),
        "created_ticket_id": outcome.created_ticket_id,
        "created_ticket_title": outcome.created_ticket_title,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    path = koru_dir / "onboarding.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _append_project_history(
        project,
        {
            "event": "onboarding.completed",
            "selected_ide": outcome.selected_ide,
            "strategy_path": list(outcome.strategy_path),
            "ticket_id": outcome.created_ticket_id,
        },
    )


def should_run_interactive_onboarding(args: argparse.Namespace) -> bool:
    """Return True when onboarding should run for this invocation."""
    if getattr(args, "action", "") != "up":
        return False
    explicit = getattr(args, "onboarding", None)
    if explicit is False:
        return False
    if args.emit_events != "human":
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    if explicit is True:
        return True
    project = getattr(args, "project", None)
    if project is not None and has_project_onboarding_state(Path(project)):
        return False
    return bool(getattr(args, "_invoked_as_auto", False))


def discover_ide_candidates() -> list[DetectedIDE]:
    """Expose wizard IDE detection for callers and tests."""
    return discover_installed_ides()


def load_strategy_tree(project: Path) -> StrategyTree:
    """Load onboarding strategy tree (project override or packaged default)."""
    source = _resolve_strategies_path(project.resolve())
    return load_tree(source)


def run_interactive_onboarding(
    args: argparse.Namespace,
    *,
    stdio_info: Callable[[str], None],
) -> OnboardingOutcome | None:
    """Run wizard onboarding and update autonomous args in-place."""
    if not should_run_interactive_onboarding(args):
        return None

    project = args.project.resolve()
    strategies_path = _resolve_strategies_path(project)
    use_llx = _env_truthy("KORU_ONBOARDING_LLX", True) and llx_available()
    create_ticket = _env_truthy("KORU_ONBOARDING_CREATE_TICKET", True)

    stdio_info("koru auto onboarding: start (wizard)")
    result = run_wizard(
        prompter=StdinPrompter(stream_in=sys.stdin, stream_out=sys.stdout),
        strategies_path=strategies_path,
        project_override=project,
        create=create_ticket,
        use_llx=use_llx,
    )

    changed_args = False
    selected_ide = result.chosen_ide.id if result.chosen_ide is not None else None
    if selected_ide and selected_ide != normalize_ide_id(args.autopilot_ide):
        args.autopilot_ide = selected_ide
        changed_args = True
    if selected_ide and selected_ide != normalize_ide_id(args.agent_lane):
        args.agent_lane = selected_ide
        changed_args = True

    selected_project = result.chosen_project.resolve()
    if selected_project != args.project.resolve():
        args.project = selected_project
        changed_args = True

    if result.ticket_id:
        stdio_info(
            f"koru auto onboarding: created ticket {result.ticket_id} ({result.ticket_title})"
        )

    outcome = OnboardingOutcome(
        changed_args=changed_args,
        selected_ide=selected_ide,
        selected_project=selected_project,
        strategy_path=tuple(result.path),
        created_ticket_id=result.ticket_id,
        created_ticket_title=result.ticket_title,
    )
    _write_onboarding_state(selected_project, outcome)
    return outcome


__all__ = [
    "OnboardingOutcome",
    "discover_ide_candidates",
    "ensure_project_state",
    "has_project_onboarding_state",
    "load_strategy_tree",
    "run_interactive_onboarding",
    "should_run_interactive_onboarding",
]
