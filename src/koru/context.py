"""Build self-service briefs for LLM agents working in a koru project.

The output of ``build_context()`` is a deterministic JSON object the
LLM agent reads at the start of each iteration. It contains everything
needed to act autonomously *within the policy*:

- the next runnable ticket (or one named via ``--ticket``);
- the resolved policy (so violations are detectable client-side);
- environment fingerprint (git branch, dirty state, planfile sprint);
- the explicit command vocabulary (claim / start / complete / fail /
  input) so the LLM doesn't have to guess CLI shapes;
- a list of human-readable instructions reiterating the contract.

``render_markdown_handoff()`` turns the same data into a Markdown
brief suitable for pasting into an LLM IDE chat panel.

This module never mutates state: pure read + format. Side effects (run
log writes, ticket lifecycle calls) live elsewhere.
"""

import contextlib
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any, NamedTuple

from koru.agents import detect_agent_environment
from koru.autonomy.telemetry_snapshot import build_autonomy_loop_brief
from koru.context_render import (
    _compact_ticket_error,  # noqa: F401
    render_markdown_handoff,  # noqa: F401
)
from koru.context_render import (
    render_active_ticket as _render_active_ticket,  # noqa: F401
)
from koru.context_render import (
    render_agent_lanes as _render_agent_lanes,  # noqa: F401
)
from koru.context_render import (
    render_ai_tool_support_2026 as _render_ai_tool_support_2026,  # noqa: F401
)
from koru.context_render import (
    render_autonomous_mode as _render_autonomous_mode,  # noqa: F401
)
from koru.context_render import (
    render_autonomy_loop_brief as _render_autonomy_loop_brief,  # noqa: F401
)
from koru.context_render import (
    render_dashboard as _render_dashboard,  # noqa: F401
)
from koru.context_render import (
    render_environment as _render_environment,  # noqa: F401
)
from koru.context_render import (
    render_gates as _render_gates,  # noqa: F401
)
from koru.context_render import (
    render_header as _render_header,  # noqa: F401
)
from koru.context_render import (
    render_no_active_ticket as _render_no_active_ticket,  # noqa: F401
)
from koru.context_render import (
    render_policy as _render_policy,  # noqa: F401
)
from koru.context_render import (
    render_project_pipeline as _render_project_pipeline,  # noqa: F401
)
from koru.context_render import (
    render_rules as _render_rules,  # noqa: F401
)
from koru.context_render import (
    render_self_service as _render_self_service,  # noqa: F401
)
from koru.context_render import (
    render_semcod_tools as _render_semcod_tools,  # noqa: F401
)
from koru.context_render import (
    render_setup_required as _render_setup_required,  # noqa: F401
)
from koru.context_rules import (
    _build_instructions as _build_instructions,  # noqa: F401
)
from koru.context_rules import (
    _build_policy_rules as _build_policy_rules,  # noqa: F401
)
from koru.context_rules import (
    _build_self_service as _build_self_service,  # noqa: F401
)
from koru.context_rules import (
    _build_setup_instructions as _build_setup_instructions,  # noqa: F401
)
from koru.context_rules import (
    _build_shared_rules as _build_shared_rules,  # noqa: F401
)
from koru.context_rules import (
    _build_ticket_rules as _build_ticket_rules,  # noqa: F401
)
from koru.context_sprint import (
    _SPRINT_YAML_CACHE as _SPRINT_YAML_CACHE,  # noqa: F401
)
from koru.context_sprint import (
    _auto_promote_blocking_tickets as _auto_promote_blocking_tickets,  # noqa: F401
)
from koru.context_sprint import (
    _fast_yaml_load as _fast_yaml_load,  # noqa: F401
)
from koru.context_sprint import (
    _find_blocking_tickets as _find_blocking_tickets,  # noqa: F401
)
from koru.context_sprint import (
    _load_sprint_data as _load_sprint_data,  # noqa: F401
)
from koru.context_sprint import (
    _promote_blocking_to_critical as _promote_blocking_to_critical,  # noqa: F401
)
from koru.context_sprint import (
    _promote_bug_priority as _promote_bug_priority,  # noqa: F401
)
from koru.context_sprint import (
    _write_sprint_data as _write_sprint_data,  # noqa: F401
)
from koru.dotenv_loader import load_dotenv as _load_dotenv_impl
from koru.git_attribution import (
    KORU_AGENT_COAUTHOR_TRAILER as KORU_AGENT_COAUTHOR_TRAILER,  # noqa: F401
)
from koru.planfile_compat import PlanfileCompatibilityReport, merge_missing_ticket_records
from koru.policy import Policy, load_policy
from koru.project_pipeline import build_project_pipeline_brief
from koru.runtime import planfile_dir

# Cache so we only load `.env` once per project per process (multiple
# `build_context` calls — e.g. dashboard auto-refresh — would otherwise
# re-read the file on every 5-second tick).
_DOTENV_LOADED: set[Path] = set()


# Labels that mark a ticket as test/dryrun infrastructure rather than
# real work. Tickets carrying ANY of these labels are filtered out of
# `koru --context` by default to prevent the queue surface from getting
# clouded by planfile/koru self-test fixtures.
#
# This addresses the c2004 PLF-koru #4 issue where `koru --context`
# happily pointed an agent at `PLF-083 Test blocked ticket` (label
# `test, blocked`) — a planfile workflow test fixture, not real work.
#
# Opt out per invocation with `--include-fixtures` or the env var
# `KORU_INCLUDE_FIXTURES=true` (useful when explicitly testing fixture
# rendering itself).
FIXTURE_LABELS: frozenset[str] = frozenset(
    {
        "test-only",
        "dryrun",
        "dry-run",
        "synthetic",
        "auto-close",
    },
)


def _is_fixture_ticket(ticket: dict[str, Any]) -> bool:
    """Return True when the ticket's labels mark it as a test fixture."""
    labels = ticket.get("labels") or []
    if not isinstance(labels, list):
        return False
    label_set = {str(label).strip().lower() for label in labels}
    return bool(label_set & FIXTURE_LABELS)


def _resolve_include_fixtures(explicit: bool | None) -> bool:
    """Resolve the include-fixtures decision from CLI flag + env var.

    Explicit CLI value (``--include-fixtures`` / ``--no-include-fixtures``)
    always wins; falls back to ``KORU_INCLUDE_FIXTURES`` env (``true``,
    ``1``, ``yes`` enable it). Default: exclude fixtures.
    """
    if explicit is not None:
        return explicit
    raw = os.environ.get("KORU_INCLUDE_FIXTURES", "").strip().lower()
    return raw in ("true", "1", "yes", "on")


def _load_project_dotenv(project: Path) -> None:
    if project in _DOTENV_LOADED:
        return
    with contextlib.suppress(Exception):  # pragma: no cover — never break the brief over .env
        _load_dotenv_impl(project)
    _DOTENV_LOADED.add(project)


# ---------------------------------------------------------------------------
# planfile helpers (mirror of planfile_queue's resolution but read-only)
# ---------------------------------------------------------------------------


def _planfile_command_base() -> list[str]:
    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        return shlex.split(configured)
    if find_spec("planfile") is not None:
        return [sys.executable, "-m", "planfile.cli"]
    return ["planfile"]


def _planfile_env() -> dict[str, str]:
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb", "PYTHONWARNINGS": "ignore"}


def _fetch_all_tickets(
    project: Path,
    *,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
    include_fixtures: bool = False,
) -> list[dict[str, Any]]:
    """Fetch every ticket via ``planfile ticket list --format json``.

    Used by the dashboard to show historical tickets (``done`` /
    ``in_progress``) when the "open" slice is empty — so the user sees
    *something* instead of a terminal "queue is idle" screen.
    Never raises; returns ``[]`` on any error.
    """
    try:
        proc = _run_planfile(
            project,
            ["ticket", "list", "--format", "json"],
            runner=runner,
        )
    except Exception:  # pragma: no cover — defensive
        return []
    if proc.returncode != 0:
        return []
    data = _safe_json(proc.stdout)
    if not isinstance(data, list):
        return []
    result = [t for t in data if isinstance(t, dict)]
    if not include_fixtures:
        result = [t for t in result if not _is_fixture_ticket(t)]
    return result


def _run_planfile(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [*_planfile_command_base(), *args]
    if runner is not None:
        return runner(command, project)
    return subprocess.run(
        command,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=_planfile_env(),
    )


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    # Retry with strict=False to tolerate control chars in ticket descriptions
    try:
        return json.loads(text, strict=False)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Environment probes — best-effort, never raise
# ---------------------------------------------------------------------------


def _git_probe(project: Path) -> dict[str, Any]:
    def _g(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
                timeout=3.0,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    branch = _g("rev-parse", "--abbrev-ref", "HEAD")
    head = _g("rev-parse", "HEAD")
    dirty_out = _g("status", "--porcelain")
    remote = _g("remote", "get-url", "origin")
    return {
        "branch": branch or None,
        "head": head[:12] if head else None,
        "dirty": bool(dirty_out),
        "remote": remote or None,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_ticket_args(
    ticket_id: str | None,
    queue_name: str | None,
) -> list[str]:
    """Build planfile ticket command arguments."""
    if ticket_id:
        return ["ticket", "show", ticket_id, "--format", "json"]
    else:
        args = ["ticket", "next", "--format", "json"]
        if queue_name:
            args.extend(["--queue", queue_name])
        return args


def _try_fallback_ticket_list(
    project: Path,
    planfile_runner: Callable | None,
) -> subprocess.CompletedProcess[str]:
    """Fallback to ticket list when ticket next is unavailable."""
    return _run_planfile(
        project,
        ["ticket", "list", "--format", "json"],
        runner=planfile_runner,
    )


def _process_list_payload(
    ticket_data: list[dict[str, Any]],
    include_fixtures: bool | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Process ticket list payload from planfile.

    Returns:
        Tuple of (active_ticket, open_tickets, ticket_history, error)
    """
    raw_list = [t for t in ticket_data if isinstance(t, dict)]
    open_tickets = [t for t in raw_list if t.get("status") in (None, "open", "ready", "todo")]
    include = _resolve_include_fixtures(include_fixtures)
    if not include:
        open_tickets = [t for t in open_tickets if not _is_fixture_ticket(t)]
        ticket_history = [t for t in raw_list if not _is_fixture_ticket(t)]
    else:
        ticket_history = list(raw_list)

    active_ticket = open_tickets[0] if open_tickets else None
    error = "queue is idle" if active_ticket is None else None
    return active_ticket, open_tickets, ticket_history, error


def _process_dict_payload(
    ticket_data: dict[str, Any],
    ticket_id: str | None,
    include_fixtures: bool | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    """Process single ticket dict payload from planfile.

    Returns:
        Tuple of (ticket_data, open_tickets, error)
    """
    if not _resolve_include_fixtures(include_fixtures) and not ticket_id and _is_fixture_ticket(ticket_data):
        return None, [], "queue has only fixture tickets"
    else:
        return ticket_data, [ticket_data], None


def _extract_error_from_stderr(stderr: str) -> str:
    """Extract the actual error message from stderr, filtering out warnings."""
    raw_err = stderr.strip()
    err_lines = [
        ln
        for ln in raw_err.splitlines()
        if not ln.startswith("/")
        and "UserWarning" not in ln
        and "warnings.warn" not in ln
        and "You may be able to resolve" not in ln
    ]
    return err_lines[0] if err_lines else raw_err.splitlines()[0]


def _execute_ticket_query(
    project: Path,
    ticket_id: str | None,
    queue_name: str | None,
    planfile_runner: Callable | None,
) -> subprocess.CompletedProcess:
    """Execute ticket query with fallback for older planfile versions."""
    ticket_args = _build_ticket_args(ticket_id, queue_name)
    ticket_proc = _run_planfile(project, ticket_args, runner=planfile_runner)

    # Fallback: if `ticket next` is not available (older planfile),
    # try `ticket list` and pick the first open ticket.
    if ticket_proc.returncode != 0 and not ticket_id and "Usage:" in (ticket_proc.stderr or ""):
        ticket_proc = _try_fallback_ticket_list(project, planfile_runner)

    return ticket_proc


def _handle_idle_queue(
    project: Path,
    planfile_runner: Callable | None,
    include_fixtures: bool | None,
) -> list[dict[str, Any]]:
    """Handle idle queue case by fetching all historical tickets."""
    return _fetch_all_tickets(
        project,
        runner=planfile_runner,
        include_fixtures=_resolve_include_fixtures(include_fixtures),
    )


def _parse_ticket_response(
    ticket_proc: subprocess.CompletedProcess,
    ticket_id: str | None,
    include_fixtures: bool | None,
    project: Path,
    planfile_runner: Callable | None,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse ticket response from planfile."""
    ticket_data: dict[str, Any] | None = None
    ticket_error: str | None = None
    open_tickets: list[dict[str, Any]] = []
    ticket_history: list[dict[str, Any]] = []

    ticket_data = _safe_json(ticket_proc.stdout)
    if ticket_data is None:
        stripped = (ticket_proc.stdout or "").strip()
        json_null_idle = False
        if stripped:
            with contextlib.suppress(TypeError, ValueError):
                json_null_idle = json.loads(stripped) is None
        if "No runnable ticket" in stripped or not stripped or json_null_idle:
            ticket_data = None
            ticket_error = "queue is idle"
            ticket_history = _handle_idle_queue(project, planfile_runner, include_fixtures)
        else:
            ticket_error = "planfile output was not JSON"
    elif isinstance(ticket_data, list):
        ticket_data, open_tickets, ticket_history, ticket_error = _process_list_payload(
            ticket_data,
            include_fixtures,
        )
    elif isinstance(ticket_data, dict):
        ticket_data, open_tickets, ticket_error = _process_dict_payload(
            ticket_data,
            ticket_id,
            include_fixtures,
        )
        if ticket_data is not None:
            ticket_history = _fetch_all_tickets(
                project,
                runner=planfile_runner,
                include_fixtures=_resolve_include_fixtures(include_fixtures),
            )

    return ticket_data, ticket_error, open_tickets, ticket_history


class _TicketFetch(NamedTuple):
    """Raw planfile ticket query result."""

    data: dict[str, Any] | None
    error: str | None
    open_tickets: list[dict[str, Any]]
    history: list[dict[str, Any]]


def _fetch_ticket_data(
    project: Path,
    ticket_id: str | None,
    queue_name: str | None,
    planfile_present: bool,
    planfile_runner: Callable | None,
    include_fixtures: bool | None,
) -> _TicketFetch:
    """Fetch ticket data from planfile.

    Returns:
        A ``_TicketFetch`` NamedTuple; its field order mirrors the
        ``(ticket_data, ticket_error, open_tickets, ticket_history)``
        tuple produced by ``_parse_ticket_response``.
    """
    if not planfile_present:
        return _TicketFetch(None, "project not initialised", [], [])

    ticket_proc = _execute_ticket_query(project, ticket_id, queue_name, planfile_runner)

    if ticket_proc.returncode == 0:
        return _TicketFetch(
            *_parse_ticket_response(
                ticket_proc,
                ticket_id,
                include_fixtures,
                project,
                planfile_runner,
            )
        )
    else:
        ticket_error = _extract_error_from_stderr(ticket_proc.stderr or "planfile error")
        return _TicketFetch(None, ticket_error, [], [])


def _planfile_is_initialised(project: Path) -> bool:
    """Pre-flight: a project is "initialised" only when BOTH the planfile
    config and at least one sprint YAML exist.

    Calling planfile when the project is not initialised is harmful —
    planfile auto-creates a half-state config.yaml and the user ends up in
    an ambiguous state where `--init` then refuses with "already exists".
    """
    pf = planfile_dir(project)
    sprints_dir = pf / "sprints"
    return (pf / "config.yaml").exists() and sprints_dir.is_dir() and any(sprints_dir.glob("*.yaml"))


class _TicketState(NamedTuple):
    """Ticket section of the brief after compatibility repair and filtering."""

    data: dict[str, Any] | None
    error: str | None
    open_tickets: list[dict[str, Any]]
    history: list[dict[str, Any]]
    compatibility: PlanfileCompatibilityReport


def _collect_ticket_state(
    project: Path,
    ticket_id: str | None,
    queue_name: str | None,
    planfile_present: bool,
    planfile_runner: Callable | None,
    include_fixtures: bool | None,
) -> _TicketState:
    """Fetch tickets and shape them for the brief.

    Older Planfile readers can return success while dropping records whose
    persisted status is no longer in the TicketStatus enum (notably
    ``skipped``). Recover those raw records for the historical/dashboard
    view and expose explicit counts so an operator can run the migration.
    """
    fetch = _fetch_ticket_data(
        project,
        ticket_id,
        queue_name,
        planfile_present,
        planfile_runner,
        include_fixtures,
    )
    history, compatibility = merge_missing_ticket_records(fetch.history, project)
    if not _resolve_include_fixtures(include_fixtures):
        history = [ticket for ticket in history if not _is_fixture_ticket(ticket)]
    return _TicketState(
        data=fetch.data,
        error=fetch.error,
        open_tickets=fetch.open_tickets,
        history=history,
        compatibility=compatibility,
    )


def _assemble_context(
    *,
    project: Path,
    tickets: _TicketState,
    policy: Policy,
    queue_name: str | None,
    planfile_present: bool,
    git_state: dict[str, Any],
    detected_environment: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the final brief dictionary from the collected state."""
    return {
        "schema_version": "1",
        "project": str(project),
        "ticket": tickets.data,
        "ticket_error": tickets.error,
        "open_tickets": tickets.open_tickets,
        "all_tickets": tickets.history,
        "ticket_compatibility": tickets.compatibility.to_dict(),
        "policy": policy.to_dict(),
        "environment": {
            "git": git_state,
            "planfile_initialised": planfile_present,
            "queue_name": queue_name,
            **detected_environment,
        },
        "instructions": _build_instructions(
            policy,
            tickets.data,
            planfile_initialised=planfile_present,
        ),
        "self_service": _build_self_service(
            policy,
            tickets.data,
            planfile_initialised=planfile_present,
        ),
        "project_pipeline": build_project_pipeline_brief(project),
        "autonomy_loop": build_autonomy_loop_brief(project),
    }


def build_context(
    *,
    project: Path,
    ticket_id: str | None = None,
    queue_name: str | None = None,
    planfile_runner: Callable[
        [Sequence[str], Path],
        subprocess.CompletedProcess[str],
    ]
    | None = None,
    git_probe: Callable[[Path], dict[str, Any]] | None = None,
    environment_probe: Callable[[Path], dict[str, Any]] | None = None,
    policy: Policy | None = None,
    include_fixtures: bool | None = None,
) -> dict[str, Any]:
    """Assemble the LLM brief for a project.

    The function is fully injectable to keep tests hermetic. In normal
    use, callers just pass ``project`` and let everything else default.
    """
    project = project.resolve()
    # Load project-local `.env` so capability probes (e.g.
    # OPENROUTER_API_KEY) see what the user already has on disk.
    # No-op when the file is absent; never overrides existing env.
    _load_project_dotenv(project)
    resolved_policy = policy if policy is not None else load_policy(project)

    planfile_present = _planfile_is_initialised(project)
    tickets = _collect_ticket_state(
        project,
        ticket_id,
        queue_name,
        planfile_present,
        planfile_runner,
        include_fixtures,
    )

    # Auto-promote blocking tickets to critical priority
    _auto_promote_blocking_tickets(project, runner=planfile_runner)

    git_state = (git_probe or _git_probe)(project)
    detected_environment = (environment_probe or detect_agent_environment)(project)

    return _assemble_context(
        project=project,
        tickets=tickets,
        policy=resolved_policy,
        queue_name=queue_name,
        planfile_present=planfile_present,
        git_state=git_state,
        detected_environment=detected_environment,
    )
