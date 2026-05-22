"""Post-run verification for planfile tickets closed in a queue loop.

Reads ``queue.post_run_verify`` from the project root ``koru.yaml``. After
``koru --queue --loop`` marks tickets ``done``, optional shell commands (e.g.
pytest, regix) re-validate the repo. On failure the ticket is reopened or
blocked so IDE/MCP work can continue.
"""


import json
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from koru.project_pipeline import load_koru_project_pipeline
from koru.queue.runners import run_shell_command

ShellRunner = Callable[[str, Path], subprocess.CompletedProcess[str]]
PlanfileRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


class _HasIdeVerifyState(Protocol):
    pending_ide_verify_id: str | None
    post_verify_seen: set[str]


@dataclass(frozen=True)
class PostRunVerifyConfig:
    enabled: bool = False
    commands: tuple[str, ...] = ()
    on_failure: str = "reopen"  # reopen | block
    max_output_chars: int = 800
    after_ide_drive: bool = True
    ide_done_window_minutes: float = 30.0


def _truthy_env(name: str) -> bool | None:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return None
    return raw in {"1", "true", "yes", "on"}


def _extract_post_run_verify_block(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate the post_run_verify block from config."""
    queue = raw.get("queue")
    if not isinstance(queue, dict):
        return {}
    block = queue.get("post_run_verify")
    if not isinstance(block, dict):
        return {}
    return block


def _parse_verify_commands(block: dict[str, Any]) -> list[str]:
    """Parse commands from the post_run_verify block."""
    commands_raw = block.get("commands")
    commands: list[str] = []
    if isinstance(commands_raw, list):
        commands = [str(c).strip() for c in commands_raw if c]
    elif isinstance(commands_raw, str) and commands_raw.strip():
        commands = [commands_raw.strip()]
    return commands


def _parse_verify_on_failure(block: dict[str, Any]) -> str:
    """Parse on_failure setting from the block."""
    on_failure = str(block.get("on_failure") or "reopen").strip().lower()
    if on_failure not in {"reopen", "block"}:
        on_failure = "reopen"
    return on_failure


def _parse_verify_max_output(block: dict[str, Any]) -> int:
    """Parse max_output_chars setting from the block."""
    max_out = block.get("max_output_chars", 800)
    try:
        return max(200, int(max_out))
    except (TypeError, ValueError):
        return 800


def _parse_verify_ide_settings(block: dict[str, Any]) -> tuple[bool, float]:
    """Parse after_ide_drive and ide_done_window_minutes settings."""
    after_ide = bool(block.get("after_ide_drive", True))
    try:
        ide_window = float(block.get("ide_done_window_minutes", 30))
    except (TypeError, ValueError):
        ide_window = 30.0
    if ide_window <= 0:
        ide_window = 30.0
    return after_ide, ide_window


def load_post_run_verify_config(project: Path) -> PostRunVerifyConfig | None:
    """Parse ``queue.post_run_verify`` from ``koru.yaml``."""
    env_override = _truthy_env("KORU_POST_RUN_VERIFY")
    raw = load_koru_project_pipeline(project)
    if not isinstance(raw, dict):
        if env_override is False:
            return None
        return PostRunVerifyConfig(enabled=bool(env_override)) if env_override else None

    block = _extract_post_run_verify_block(raw)

    enabled = bool(block.get("enabled", False))
    if env_override is not None:
        enabled = env_override

    commands = _parse_verify_commands(block)
    on_failure = _parse_verify_on_failure(block)
    max_output_chars = _parse_verify_max_output(block)
    after_ide, ide_window = _parse_verify_ide_settings(block)

    if not enabled and not commands:
        return None
    return PostRunVerifyConfig(
        enabled=enabled,
        commands=tuple(commands),
        on_failure=on_failure,
        max_output_chars=max_output_chars,
        after_ide_drive=after_ide,
        ide_done_window_minutes=ide_window,
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def fetch_ticket_status(
    project: Path,
    ticket_id: str,
    *,
    runner: PlanfileRunner,
) -> str | None:
    """Return lowercase planfile status for ``ticket_id``, or None."""
    try:
        result = runner(
            ["planfile", "ticket", "show", ticket_id, "--format", "json"],
            project,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads((result.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return str(payload.get("status") or "").lower() or None


def fetch_recently_done_ticket_ids(
    project: Path,
    *,
    within_minutes: float,
    runner: PlanfileRunner,
) -> list[str]:
    """Ticket ids in ``done`` status updated within the last ``within_minutes``."""
    if within_minutes <= 0:
        return []
    cutoff = datetime.now(UTC) - timedelta(minutes=within_minutes)
    try:
        result = runner(
            ["planfile", "ticket", "list", "--status", "done", "--format", "json"],
            project,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    ids: list[str] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        updated = _parse_iso_datetime(entry.get("updated_at"))
        if updated is None or updated < cutoff:
            continue
        ticket_id = str(entry.get("id") or "").strip()
        if ticket_id:
            ids.append(ticket_id)
    return ids


def _record_verify_outcomes(state: _HasIdeVerifyState, outcomes: Sequence[dict[str, Any]]) -> None:
    for outcome in outcomes:
        if not outcome.get("ok"):
            continue
        ticket_id = str(outcome.get("ticket_id") or "").strip()
        if ticket_id:
            state.post_verify_seen.add(ticket_id)


def verify_after_ide_work(
    project: Path,
    state: _HasIdeVerifyState,
    *,
    config: PostRunVerifyConfig | None,
    planfile_runner: PlanfileRunner,
    shell_runner: ShellRunner | None = None,
) -> list[dict[str, Any]]:
    """Verify tickets the IDE likely closed (pending autopilot target or recent ``done``)."""
    if config is None or not config.enabled or not config.commands or not config.after_ide_drive:
        return []

    to_verify: list[str] = []
    pending = (state.pending_ide_verify_id or "").strip()
    if pending and pending not in state.post_verify_seen:
        status = fetch_ticket_status(project, pending, runner=planfile_runner)
        if status == "done":
            to_verify.append(pending)
            state.pending_ide_verify_id = None

    for ticket_id in fetch_recently_done_ticket_ids(
        project,
        within_minutes=config.ide_done_window_minutes,
        runner=planfile_runner,
    ):
        if ticket_id in state.post_verify_seen or ticket_id in to_verify:
            continue
        to_verify.append(ticket_id)

    if not to_verify:
        return []

    outcomes = verify_completed_tickets(
        project,
        to_verify,
        config=config,
        planfile_runner=planfile_runner,
        shell_runner=shell_runner,
    )
    _record_verify_outcomes(state, outcomes)
    return outcomes


def run_verify_commands(
    project: Path,
    commands: Sequence[str],
    *,
    shell_runner: ShellRunner | None = None,
) -> tuple[bool, str, int | None]:
    """Run verification commands in order. Returns (ok, detail, last_exit_code)."""
    runner = shell_runner or run_shell_command
    last_code: int | None = None
    for cmd in commands:
        if not cmd.strip():
            continue
        result = runner(cmd, project)
        last_code = int(getattr(result, "returncode", 1))
        if last_code != 0:
            detail = (
                getattr(result, "stderr", None) or getattr(result, "stdout", None) or ""
            ).strip()
            if not detail:
                detail = f"exit {last_code}"
            return False, detail, last_code
    return True, "", last_code


def _truncate(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3]}..."


def apply_verify_failure(
    project: Path,
    ticket_id: str,
    *,
    config: PostRunVerifyConfig,
    detail: str,
    exit_code: int | None,
    runner: PlanfileRunner,
) -> str:
    """Reopen or block a ticket after failed verification. Returns action label."""
    reason = _truncate(
        f"post_run_verify failed (exit {exit_code}): {detail}",
        config.max_output_chars,
    )
    if config.on_failure == "block":
        runner(
            ["planfile", "ticket", "block", ticket_id, "--reason", reason],
            project,
        )
        return "blocked"
    runner(
        [
            "planfile",
            "ticket",
            "update",
            ticket_id,
            "--status",
            "open",
            "--note",
            reason,
        ],
        project,
    )
    return "reopened"


def verify_completed_tickets(
    project: Path,
    ticket_ids: Sequence[str],
    *,
    config: PostRunVerifyConfig | None,
    planfile_runner: PlanfileRunner,
    shell_runner: ShellRunner | None = None,
) -> list[dict[str, Any]]:
    """Run post-run verify once per completed ticket; mutate planfile on failure."""
    if not ticket_ids or config is None or not config.enabled or not config.commands:
        return []

    ok, detail, exit_code = run_verify_commands(
        project,
        config.commands,
        shell_runner=shell_runner,
    )
    if ok:
        return [
            {"ticket_id": ticket_id, "ok": True, "action": "verified"} for ticket_id in ticket_ids
        ]

    outcomes: list[dict[str, Any]] = []
    for ticket_id in ticket_ids:
        action = apply_verify_failure(
            project,
            ticket_id,
            config=config,
            detail=detail,
            exit_code=exit_code,
            runner=planfile_runner,
        )
        outcomes.append(
            {
                "ticket_id": ticket_id,
                "ok": False,
                "action": action,
                "detail": detail,
                "exit_code": exit_code,
            },
        )
    return outcomes


__all__ = [
    "PostRunVerifyConfig",
    "apply_verify_failure",
    "fetch_recently_done_ticket_ids",
    "fetch_ticket_status",
    "load_post_run_verify_config",
    "run_verify_commands",
    "verify_after_ide_work",
    "verify_completed_tickets",
]
