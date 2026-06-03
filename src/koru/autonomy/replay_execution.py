"""Replay action execution and validation."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from koru.autonomy.replay_handlers import ReplayCommandHandlers, ReplayQueryHandlers
from koru.autonomy.replay_types import ReplayAction, ReplayResult, ValidationResult

_REPLAY_QUERIES = ReplayQueryHandlers()
_REPLAY_COMMANDS = ReplayCommandHandlers()
_REPLAY_EXECUTORS: dict[str, Any] = {}


def _register_executor(domain: str, verb: str):
    """Decorator to register a replay action executor."""

    def decorator(func):
        _REPLAY_EXECUTORS[f"{domain}.{verb}"] = func
        return func

    return decorator


@_register_executor("trace", "show-decisions")
def _exec_trace_show_decisions(action: ReplayAction, *, project: Path) -> ReplayResult:
    return _REPLAY_QUERIES.show_decisions(action, project=project)


@_register_executor("trace", "show-interfaces")
def _exec_trace_show_interfaces(action: ReplayAction, *, project: Path) -> ReplayResult:
    return _REPLAY_QUERIES.show_interfaces(action, project=project)


@_register_executor("ticket", "input")
def _exec_ticket_input(action: ReplayAction, *, project: Path) -> ReplayResult:
    return _REPLAY_COMMANDS.ticket_input(action, project=project)


@_register_executor("ticket", "open")
def _exec_ticket_open(action: ReplayAction, *, project: Path) -> ReplayResult:
    ticket_id = action.positional[0] if action.positional else ""
    raw_url = action.args.get("url", "http://127.0.0.1:8765")
    if not ticket_id:
        return ReplayResult(ok=False, output=raw_url, returncode=2, action=action)
    if "tab=tickets" in raw_url:
        url = f"{raw_url.split('#', 1)[0]}#{ticket_id}"
    else:
        url = f"{raw_url.rstrip('/')}/?tab=tickets#{ticket_id}"
    return ReplayResult(
        ok=bool(ticket_id),
        output=url,
        returncode=0 if ticket_id else 2,
        action=action,
    )


@_register_executor("scan", "force")
def _exec_scan_force(action: ReplayAction, *, project: Path) -> ReplayResult:
    return _REPLAY_COMMANDS.scan_force(action, project=project)


@_register_executor("autopilot", "retry-drive")
def _exec_autopilot_retry_drive(action: ReplayAction, *, project: Path) -> ReplayResult:
    return _REPLAY_COMMANDS.retry_drive(action, project=project)


def execute_replay_action(action: ReplayAction, *, project: Path) -> ReplayResult:
    """Execute a replay action. Returns result with ok/output/returncode."""
    executor = _REPLAY_EXECUTORS.get(action.key)
    if executor is None:
        if not action.replayable:
            return ReplayResult(
                ok=False,
                output=f"action {action.key} requires manual intervention: {action.label}",
                action=action,
            )
        return ReplayResult(
            ok=False,
            output=f"no executor registered for {action.key}",
            action=action,
        )
    return executor(action, project=project)


def validate_replay_action(action: ReplayAction, *, project: Path) -> ValidationResult:
    """Check if a replay action's effect was achieved."""
    if not action.validate_cmd:
        return ValidationResult(
            passed=True,
            reason="no validation command defined",
            action=action,
        )
    result = subprocess.run(
        ["bash", "-lc", action.validate_cmd],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return ValidationResult(
            passed=True,
            reason=result.stdout.strip()[:200],
            action=action,
        )
    return ValidationResult(
        passed=False,
        reason=result.stderr.strip()[:200] or result.stdout.strip()[:200] or "validation failed",
        action=action,
        regression_point=action.key,
    )


__all__ = ["execute_replay_action", "validate_replay_action"]
