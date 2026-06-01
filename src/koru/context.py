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
from typing import Any

from koru.agents import detect_agent_environment
from koru.autonomy.telemetry_snapshot import build_autonomy_loop_brief
from koru.context_render import (
    _compact_ticket_error,
)
from koru.context_render import (
    render_active_ticket as _render_active_ticket,
    render_agent_lanes as _render_agent_lanes,
    render_ai_tool_support_2026 as _render_ai_tool_support_2026,
    render_autonomous_mode as _render_autonomous_mode,
    render_autonomy_loop_brief as _render_autonomy_loop_brief,
    render_dashboard as _render_dashboard,
    render_environment as _render_environment,
    render_gates as _render_gates,
    render_header as _render_header,
    render_markdown_handoff,
    render_no_active_ticket as _render_no_active_ticket,
    render_policy as _render_policy,
    render_project_pipeline as _render_project_pipeline,
    render_rules as _render_rules,
    render_self_service as _render_self_service,
    render_semcod_tools as _render_semcod_tools,
    render_setup_required as _render_setup_required,
)
from koru.dotenv_loader import load_dotenv as _load_dotenv_impl
from koru.git_attribution import KORU_AGENT_COAUTHOR_TRAILER
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
    if (
        not _resolve_include_fixtures(include_fixtures)
        and not ticket_id
        and _is_fixture_ticket(ticket_data)
    ):
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


def _fetch_ticket_data(
    project: Path,
    ticket_id: str | None,
    queue_name: str | None,
    planfile_present: bool,
    planfile_runner: Callable | None,
    include_fixtures: bool | None,
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch ticket data from planfile.

    Returns:
        Tuple of (ticket_data, ticket_error, open_tickets, ticket_history)
    """
    if not planfile_present:
        return None, "project not initialised", [], []

    ticket_proc = _execute_ticket_query(project, ticket_id, queue_name, planfile_runner)

    if ticket_proc.returncode == 0:
        return _parse_ticket_response(
            ticket_proc,
            ticket_id,
            include_fixtures,
            project,
            planfile_runner,
        )
    else:
        ticket_error = _extract_error_from_stderr(ticket_proc.stderr or "planfile error")
        return None, ticket_error, [], []


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

    # Pre-flight: a project is "initialised" only when BOTH the planfile
    # config and at least one sprint YAML exist. Calling planfile when
    # the project is not initialised is harmful — planfile auto-creates
    # a half-state config.yaml and the user ends up in an ambiguous
    # state where `--init` then refuses with "already exists".
    pf = planfile_dir(project)
    sprints_dir = pf / "sprints"
    planfile_present = (
        (pf / "config.yaml").exists() and sprints_dir.is_dir() and any(sprints_dir.glob("*.yaml"))
    )

    ticket_data, ticket_error, open_tickets, ticket_history = _fetch_ticket_data(
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

    instructions = _build_instructions(
        resolved_policy,
        ticket_data,
        planfile_initialised=planfile_present,
    )
    self_service = _build_self_service(
        resolved_policy,
        ticket_data,
        planfile_initialised=planfile_present,
    )
    project_pipeline = build_project_pipeline_brief(project)

    return {
        "schema_version": "1",
        "project": str(project),
        "ticket": ticket_data,
        "ticket_error": ticket_error,
        "open_tickets": open_tickets,
        "all_tickets": ticket_history,
        "policy": resolved_policy.to_dict(),
        "environment": {
            "git": git_state,
            "planfile_initialised": planfile_present,
            "queue_name": queue_name,
            **detected_environment,
        },
        "instructions": instructions,
        "self_service": self_service,
        "project_pipeline": project_pipeline,
        "autonomy_loop": build_autonomy_loop_brief(project),
    }


# ---------------------------------------------------------------------------
# Instruction & self-service text generators
# ---------------------------------------------------------------------------


def _load_sprint_data(project: Path) -> dict[str, Any] | None:
    """Load sprint data from current.yaml file."""
    from koru.runtime import planfile_dir

    pf = planfile_dir(project)
    sprint_file = pf / "sprints" / "current.yaml"

    if not sprint_file.exists():
        return None

    try:
        import yaml

        with open(sprint_file, encoding="utf-8") as f:
            sprint_data = yaml.safe_load(f)

        if not sprint_data or "sprint" not in sprint_data:
            return None

        sprint_info = sprint_data["sprint"]
        if "tickets" not in sprint_info:
            return None

        return sprint_data
    except Exception:
        return None


def _find_blocking_tickets(tickets: dict[str, Any]) -> set[str]:
    """Find all ticket IDs that are blocking other tickets."""
    blocking_tickets = set()
    for _ticket_id, ticket in tickets.items():
        if isinstance(ticket, dict):
            blocked_by = ticket.get("blocked_by", [])
            if blocked_by:
                if isinstance(blocked_by, str):
                    blocking_tickets.add(blocked_by)
                elif isinstance(blocked_by, list):
                    blocking_tickets.update(blocked_by)
    return blocking_tickets


def _promote_blocking_to_critical(
    tickets: dict[str, Any],
    blocking_tickets: set[str],
) -> bool:
    """Promote blocking tickets to critical priority. Returns True if any promoted."""
    promoted = False
    for blocking_id in blocking_tickets:
        if blocking_id in tickets and isinstance(tickets[blocking_id], dict):
            current_priority = tickets[blocking_id].get("priority", "normal")
            if current_priority != "critical":
                tickets[blocking_id]["priority"] = "critical"
                promoted = True
                print(
                    f"🔥 Auto-promoted {blocking_id} from {current_priority} to critical"
                    " (blocking)",
                )
    return promoted


def _promote_bug_priority(tickets: dict[str, Any]) -> bool:
    """Promote bugs to higher priority. Returns True if any promoted."""
    promoted = False
    for ticket_id, ticket in tickets.items():
        if isinstance(ticket, dict):
            labels = ticket.get("labels", [])
            if "bug" in labels and ticket.get("status") in ["open", "ready"]:
                current_priority = ticket.get("priority", "normal")
                new_priority = None

                if current_priority == "low":
                    new_priority = "normal"
                elif current_priority == "normal":
                    new_priority = "high"
                elif current_priority == "high":
                    new_priority = "critical"

                if new_priority and new_priority != current_priority:
                    ticket["priority"] = new_priority
                    promoted = True
                    print(
                        f"🐛 Auto-promoted bug {ticket_id} from {current_priority} "
                        f"to {new_priority}",
                    )
    return promoted


def _write_sprint_data(project: Path, sprint_data: dict[str, Any]) -> None:
    """Write sprint data back to current.yaml file."""
    from koru.runtime import planfile_dir

    pf = planfile_dir(project)
    sprint_file = pf / "sprints" / "current.yaml"

    try:
        import yaml

        with open(sprint_file, "w", encoding="utf-8") as f:
            yaml.dump(sprint_data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"⚠️ Failed to write sprint data: {e}")


def _auto_promote_blocking_tickets(project: Path, runner: Callable | None = None) -> None:
    """Automatically promote tickets that are blocking others to critical priority.

    Also ensures bugs are prioritized over features when they have the same priority.
    This ensures that blocking issues are resolved first, allowing the main
    workflow to continue without manual intervention.
    """
    sprint_data = _load_sprint_data(project)
    if not sprint_data:
        return

    tickets = sprint_data["sprint"]["tickets"]
    blocking_tickets = _find_blocking_tickets(tickets)

    promoted = _promote_blocking_to_critical(tickets, blocking_tickets)
    promoted = _promote_bug_priority(tickets) or promoted

    if promoted:
        _write_sprint_data(project, sprint_data)


def _build_instructions(
    policy: Policy,
    ticket: dict[str, Any] | None,
    *,
    planfile_initialised: bool,
) -> list[str]:
    """Imperative, copy-paste-able rules for the LLM agent.

    Two flavours:
        - planfile_initialised=False ⇒ base rules + SETUP REQUIRED guide.
          The agent must NOT try to claim/start/complete tickets when
          there is no sprint file to claim from.
        - planfile_initialised=True  ⇒ base rules + the policy-derived
          DO NOT list + ticket-scope rule + escape hatches.
    """
    rules: list[str] = [
        "You are an LLM agent operating under koru. You MUST obey the "
        "policy embedded in this brief. Violations terminate the session.",
        "Use planfile commands for ALL state changes. Do not edit "
        ".planfile/sprints/*.yaml directly.",
    ]
    if not planfile_initialised:
        rules.extend(_build_setup_instructions())
    else:
        rules.extend(_build_shared_rules(policy, ticket))
    return rules


def _build_setup_instructions() -> list[str]:
    """Instructions shown when ``.planfile/`` is missing.

    The LLM should NOT try to claim a ticket — it should ask the human
    operator to initialise the project (or, if it has shell rights,
    run ``koru --init`` itself).
    """
    return [
        "This project has not been initialised yet — there is no "
        "`.planfile/config.yaml` and no sprint to claim tickets from.",
        "Ask the human operator to run `koru --init` from the project "
        "root (or `koru --init --from <pipeline.yaml>` to import an "
        "existing flat pipeline). DO NOT create planfile files manually.",
        "After initialisation, re-run `koru` to refresh this brief.",
    ]


def _build_policy_rules(policy: Policy) -> list[str]:
    """Return rules derived from policy booleans and CI settings."""
    rules: list[str] = []
    if not policy.allow_commit:
        rules.append(
            "DO NOT run raw `git commit`. If committing is explicitly requested, "
            "use `koru git commit` so koru can enforce attribution."
        )
    if not policy.allow_push:
        rules.append(
            "DO NOT run raw `git push`. If pushing is explicitly requested, use `koru git push`."
        )
    if not policy.allow_branch_create:
        rules.append("DO NOT create or switch branches.")
    if not policy.allow_tag:
        rules.append("DO NOT create git tags.")
    if not policy.allow_destructive_shell:
        rules.append(
            (
                "DO NOT run destructive shell commands"
                " (rm -rf /, dd, mkfs, shutdown, force-pushes, …)."
            ),
        )
    if policy.require_ci_pass_before_complete:
        if policy.ci_command:
            rules.append(
                f"Before completing a ticket, run `{policy.ci_command}` "
                "and verify exit code 0. Only then call `planfile ticket done <id>`.",
            )
        else:
            rules.append(
                "Before completing a ticket, ask the human operator to "
                "run the project's CI gate. Do not self-certify.",
            )
    return rules


def _build_ticket_rules(ticket: dict[str, Any] | None) -> list[str]:
    """Return rules derived from ticket state and priority."""
    rules: list[str] = []
    if ticket and isinstance(ticket.get("files"), list) and ticket["files"]:
        scope = ", ".join(str(f) for f in ticket["files"][:10])
        rules.append(
            f"Limit edits to the ticket's declared files: {scope}. "
            "Touching anything else requires blocking the ticket first "
            '(`planfile ticket block <id> --reason "out-of-scope edit needed"`).',
        )
    if ticket is None:
        rules.extend(
            [
                "If there is no active ticket, DO NOT ask the human what to work on.",
                "Immediately run `koru scan --apply` to discover or create actionable tickets.",
                (
                    "After scan, run `planfile ticket next --format json`, "
                    "then `planfile ticket start <id>` and begin implementation."
                ),
            ],
        )
    # Auto-repair instructions for critical blocking tickets
    if ticket and ticket.get("priority") == "critical":
        rules.extend(
            [
                "CRITICAL PRIORITY: This ticket is blocking other work.",
                "AUTO-REPAIR MODE: Fix this issue immediately to unblock the workflow.",
                "Do NOT ask for human input unless absolutely necessary.",
                "Use all available tools and knowledge to resolve the blocking issue.",
                "After fixing, immediately call `planfile ticket done <id>` to continue.",
            ],
        )
    else:
        rules.append(
            "If you are blocked or need a human decision, call "
            '`planfile ticket block <id> --reason "<question>"` and stop.',
        )
    return rules


def _build_shared_rules(policy: Policy, ticket: dict[str, Any] | None) -> list[str]:
    rules = [
        f"When creating or preparing a Git commit, keep the human Git author "
        f"unchanged and include this trailer: `{KORU_AGENT_COAUTHOR_TRAILER}`.",
    ]
    rules.extend(_build_policy_rules(policy))
    rules.extend(_build_ticket_rules(ticket))
    rules.extend(policy.notes)
    return rules


def _build_self_service(
    policy: Policy,
    ticket: dict[str, Any] | None,
    *,
    planfile_initialised: bool,
) -> dict[str, Any]:
    """Concrete CLI invocations the LLM can use without guessing.

    When the project is not initialised, the only useful command is
    ``koru --init`` — surfacing planfile ticket commands would be
    misleading because there is no sprint to act on.
    """
    if not planfile_initialised:
        return {
            "init_project": "koru --init --project .",
            "init_from_pipeline": "koru --init --project . --from <pipeline.yaml>",
            "autonomous_bootstrap": (
                "koru autonomous up --project . --max-cycles 1 --sleep-seconds 0 --no-autopilot"
            ),
            "refresh_brief": "koru --project .",
        }
    tid = ticket.get("id") if isinstance(ticket, dict) else None
    ticket_command_prefix = "planfile ticket"
    block: dict[str, Any] = {
        "next_brief": "koru --project .",
        "autonomous_up": "koru autonomous up --project .",
        "autonomous_smoke": "koru autonomous up --project . --max-cycles 1 --sleep-seconds 0",
        "list_open": f"{ticket_command_prefix} list --status open --format json",
        "show_ticket": f"{ticket_command_prefix} show <id> --format json",
        "block_for_input": f'{ticket_command_prefix} block <id> --reason "<question or blocker>"',
    }
    if tid:
        block["start_this"] = f"{ticket_command_prefix} start {tid}"
        block["done_this"] = f"{ticket_command_prefix} done {tid}"
        block["block_this"] = f'{ticket_command_prefix} block {tid} --reason "<question or blocker>"'
    if policy.ci_command:
        block["verify_ci"] = policy.ci_command
    return block


# ---------------------------------------------------------------------------
# Markdown rendering — for paste-into-IDE handoff
# ---------------------------------------------------------------------------
