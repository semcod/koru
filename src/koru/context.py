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

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from .agents import detect_agent_environment
from .dotenv_loader import load_dotenv as _load_dotenv_impl
from .policy import Policy, load_policy
from .runtime import planfile_dir


# Cache so we only load `.env` once per project per process (multiple
# `build_context` calls — e.g. dashboard auto-refresh — would otherwise
# re-read the file on every 5-second tick).
_DOTENV_LOADED: set[Path] = set()


def _load_project_dotenv(project: Path) -> None:
    if project in _DOTENV_LOADED:
        return
    try:
        _load_dotenv_impl(project)
    except Exception:  # pragma: no cover — never break the brief over .env
        pass
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


def build_context(
    *,
    project: Path,
    ticket_id: str | None = None,
    queue_name: str | None = None,
    planfile_runner: Callable[
        [Sequence[str], Path],
        subprocess.CompletedProcess[str],
    ] | None = None,
    git_probe: Callable[[Path], dict[str, Any]] | None = None,
    environment_probe: Callable[[Path], dict[str, Any]] | None = None,
    policy: Policy | None = None,
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
        (pf / "config.yaml").exists()
        and sprints_dir.is_dir()
        and any(sprints_dir.glob("*.yaml"))
    )

    ticket_data: dict[str, Any] | None = None
    ticket_error: str | None = None
    open_tickets: list[dict[str, Any]] = []

    if not planfile_present:
        ticket_error = "project not initialised"
    else:
        if ticket_id:
            ticket_args = ["ticket", "show", ticket_id, "--format", "json"]
        else:
            ticket_args = ["ticket", "next", "--format", "json"]
            if queue_name:
                ticket_args.extend(["--queue", queue_name])
        ticket_proc = _run_planfile(project, ticket_args, runner=planfile_runner)

        # Fallback: if `ticket next` is not available (older planfile),
        # try `ticket list` and pick the first open ticket.
        if (
            ticket_proc.returncode != 0
            and not ticket_id
            and "Usage:" in (ticket_proc.stderr or "")
        ):
            ticket_proc = _run_planfile(
                project,
                ["ticket", "list", "--format", "json"],
                runner=planfile_runner,
            )

        if ticket_proc.returncode == 0:
            ticket_data = _safe_json(ticket_proc.stdout)
            if ticket_data is None:
                stripped = (ticket_proc.stdout or "").strip()
                if "No runnable ticket" in stripped or not stripped:
                    ticket_data = None
                    ticket_error = "queue is idle"
                else:
                    ticket_error = "planfile output was not JSON"
            elif isinstance(ticket_data, list):
                # `ticket list` returns an array — keep the full list of
                # open tickets so the dashboard can show the whole queue,
                # then pick the first one as the active ticket.
                open_tickets = [
                    t for t in ticket_data
                    if isinstance(t, dict) and t.get("status") in (None, "open", "ready", "todo")
                ]
                ticket_data = open_tickets[0] if open_tickets else None  # type: ignore[assignment]
                if ticket_data is None:
                    ticket_error = "queue is idle"
            elif isinstance(ticket_data, dict):
                # Single-object payload (legacy `ticket next`). Treat as
                # a one-entry queue for dashboard consistency.
                open_tickets = [ticket_data]
        else:
            raw_err = (ticket_proc.stderr or "planfile error").strip()
            # Filter out Python warnings (e.g. pydantic UserWarning) that
            # leak into stderr but aren't the real error message.
            err_lines = [
                ln for ln in raw_err.splitlines()
                if not ln.startswith("/") and "UserWarning" not in ln
                and "warnings.warn" not in ln
                and "You may be able to resolve" not in ln
            ]
            ticket_error = (err_lines[0] if err_lines else raw_err.splitlines()[0])

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

    return {
        "schema_version": "1",
        "project": str(project),
        "ticket": ticket_data,
        "ticket_error": ticket_error,
        "open_tickets": open_tickets,
        "policy": resolved_policy.to_dict(),
        "environment": {
            "git": git_state,
            "planfile_initialised": planfile_present,
            "queue_name": queue_name,
            **detected_environment,
        },
        "instructions": instructions,
        "self_service": self_service,
    }


# ---------------------------------------------------------------------------
# Instruction & self-service text generators
# ---------------------------------------------------------------------------


def _auto_promote_blocking_tickets(project: Path, runner: Callable | None = None) -> None:
    """Automatically promote tickets that are blocking others to critical priority.
    
    Also ensures bugs are prioritized over features when they have the same priority.
    This ensures that blocking issues are resolved first, allowing the main
    workflow to continue without manual intervention.
    """
    from .runtime import planfile_dir
    
    pf = planfile_dir(project)
    sprint_file = pf / "sprints" / "current.yaml"
    
    if not sprint_file.exists():
        return
    
    try:
        import yaml
        with open(sprint_file, "r", encoding="utf-8") as f:
            sprint_data = yaml.safe_load(f)
        
        if not sprint_data or "sprint" not in sprint_data:
            return
        
        sprint_info = sprint_data["sprint"]
        if "tickets" not in sprint_info:
            return
        
        tickets = sprint_info["tickets"]
        blocking_tickets = set()
        
        # Find all tickets that are blocking others
        for ticket_id, ticket in tickets.items():
            if isinstance(ticket, dict):
                blocked_by = ticket.get("blocked_by", [])
                if blocked_by:
                    if isinstance(blocked_by, str):
                        blocking_tickets.add(blocked_by)
                    elif isinstance(blocked_by, list):
                        blocking_tickets.update(blocked_by)
        
        # Promote blocking tickets to critical priority
        promoted = False
        for blocking_id in blocking_tickets:
            if blocking_id in tickets and isinstance(tickets[blocking_id], dict):
                current_priority = tickets[blocking_id].get("priority", "normal")
                if current_priority != "critical":
                    tickets[blocking_id]["priority"] = "critical"
                    promoted = True
                    print(f"🔥 Auto-promoted {blocking_id} from {current_priority} to critical (blocking)")
        
        # Promote bugs over features within same priority level
        # Bugs get priority boost: critical stays, high→critical, normal→high, low→normal
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
                    # critical stays critical
                    
                    if new_priority and new_priority != current_priority:
                        ticket["priority"] = new_priority
                        promoted = True
                        print(f"🐛 Auto-promoted bug {ticket_id} from {current_priority} to {new_priority}")
        
        # Write back if any tickets were promoted
        if promoted:
            with open(sprint_file, "w", encoding="utf-8") as f:
                yaml.dump(sprint_data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        # Silently fail - priority promotion is nice-to-have, not critical
        print(f"⚠️ Auto-promotion failed: {e}")
        pass


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


def _build_shared_rules(policy: Policy, ticket: dict[str, Any] | None) -> list[str]:
    rules: list[str] = []
    if not policy.allow_commit:
        rules.append("DO NOT run `git commit`. Commits are made by CI/CD or a human reviewer.")
    if not policy.allow_push:
        rules.append("DO NOT run `git push`. Pushing is reserved for CI/CD.")
    if not policy.allow_branch_create:
        rules.append("DO NOT create or switch branches.")
    if not policy.allow_tag:
        rules.append("DO NOT create git tags.")
    if not policy.allow_destructive_shell:
        rules.append(
            "DO NOT run destructive shell commands "
            "(rm -rf /, dd, mkfs, shutdown, force-pushes, …)."
        )
    if policy.require_ci_pass_before_complete:
        if policy.ci_command:
            rules.append(
                f"Before completing a ticket, run `{policy.ci_command}` "
                "and verify exit code 0. Only then call `planfile ticket done <id>`."
            )
        else:
            rules.append(
                "Before completing a ticket, ask the human operator to "
                "run the project's CI gate. Do not self-certify."
            )
    if ticket and isinstance(ticket.get("files"), list) and ticket["files"]:
        scope = ", ".join(str(f) for f in ticket["files"][:10])
        rules.append(
            f"Limit edits to the ticket's declared files: {scope}. "
            "Touching anything else requires blocking the ticket first "
            "(`planfile ticket block <id> --reason \"out-of-scope edit needed\"`)."
        )
    # Auto-repair instructions for critical blocking tickets
    if ticket and ticket.get("priority") == "critical":
        rules.extend([
            "CRITICAL PRIORITY: This ticket is blocking other work.",
            "AUTO-REPAIR MODE: Fix this issue immediately to unblock the workflow.",
            "Do NOT ask for human input unless absolutely necessary.",
            "Use all available tools and knowledge to resolve the blocking issue.",
            "After fixing, immediately call `planfile ticket done <id>` to continue."
        ])
    else:
        rules.append(
            "If you are blocked or need a human decision, call "
            "`planfile ticket block <id> --reason \"<question>\"` and stop."
        )
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
            "refresh_brief": "koru --project .",
        }
    tid = ticket.get("id") if isinstance(ticket, dict) else None
    base = "planfile ticket"
    block: dict[str, Any] = {
        "next_brief": "koru --project .",
        "list_open": f"{base} list --status open --format json",
        "show_ticket": f"{base} show <id> --format json",
        "block_for_input": f"{base} block <id> --reason \"<question or blocker>\"",
    }
    if tid:
        block["start_this"] = f"{base} start {tid}"
        block["done_this"] = f"{base} done {tid}"
        block["block_this"] = f"{base} block {tid} --reason \"<question or blocker>\""
    if policy.ci_command:
        block["verify_ci"] = policy.ci_command
    return block


# ---------------------------------------------------------------------------
# Markdown rendering — for paste-into-IDE handoff
# ---------------------------------------------------------------------------


def render_markdown_handoff(context: dict[str, Any]) -> str:
    """Turn a context dict into a Markdown brief for the operator.

    Designed to be pasted into a Cascade/Cursor/aider chat to onboard
    the LLM with the policy and ticket scope in one shot.
    """
    lines: list[str] = []
    project = context.get("project", "?")
    ticket = context.get("ticket")
    policy = context.get("policy", {})

    lines.append(f"# koru handoff — {project}")
    lines.append("")
    lines.append("## What koru is")
    lines.append("")
    lines.append(
        "Koru is the project-local automation gate: it detects the repository "
        "context, exposes planfile tickets, gives the LLM exact operating rules, "
        "and keeps work traceable through ticket lifecycle events."
    )
    lines.append("")

    env = context.get("environment") or {}
    initialised = bool(env.get("planfile_initialised"))
    project_env = env.get("project") or {}
    markers = project_env.get("markers") or {}
    agents = env.get("llm_agents") or []
    recommended = env.get("recommended_agent") or {}
    semcod_tools = env.get("semcod_tools") or []

    lines.append("## Detected environment")
    lines.append("")
    lines.append(f"- **project**: `{project_env.get('name') or Path(project).name}`")
    lines.append(f"- **cwd**: `{project_env.get('cwd') or project}`")
    lines.append(f"- **python**: `{project_env.get('python', '?')}`")
    enabled_markers = [key for key, value in markers.items() if value]
    lines.append(
        "- **markers**: "
        + (", ".join(f"`{marker}`" for marker in enabled_markers) if enabled_markers else "`none`")
    )
    if recommended:
        lines.append(f"- **recommended agent**: `{recommended.get('label')}`")
    lines.append("")

    lines.append("## Available LLM/IDE lanes")
    lines.append("")
    if agents:
        lines.append("| lane | available | launchable | note |")
        lines.append("| --- | --- | --- | --- |")
        for agent in agents:
            lines.append(
                f"| `{agent.get('id')}` | `{agent.get('available')}` | "
                f"`{agent.get('launchable')}` | {agent.get('reason', '')} |"
            )
    else:
        lines.append(
            "No known LLM/IDE lanes detected. Paste this handoff into your preferred agent."
        )
    lines.append("")

    # Available semcod tools — installed CLIs / libraries from the
    # semcod ecosystem the LLM may invoke directly. The brief lists
    # them up-front so the agent never has to guess `which goal` /
    # `pip show pfix` to find out what's reachable.
    if semcod_tools:
        installed = [t for t in semcod_tools if t.get("available")]
        missing = [t for t in semcod_tools if not t.get("available")]
        lines.append("## Available semcod tools")
        lines.append("")
        if installed:
            lines.append("| tool | via | role | command |")
            lines.append("| --- | --- | --- | --- |")
            for tool in installed:
                cfg = " (configured)" if tool.get("config_present") else ""
                lines.append(
                    f"| `{tool.get('id')}` | `{tool.get('via')}`{cfg} | "
                    f"{tool.get('role', '')} | `{tool.get('command_hint', '')}` |"
                )
        else:
            lines.append("_No semcod tools detected on this machine._")
        if missing:
            lines.append("")
            missing_ids = ", ".join(f"`{t.get('id')}`" for t in missing)
            lines.append(
                f"_Not installed: {missing_ids}. Install with `pip install <name>` "
                "or skip — koru will not invoke them automatically._"
            )
        lines.append("")

    if not initialised:
        lines.append("## ⚠ Setup required")
        lines.append("")
        lines.append(
            "This project has no `.planfile/` directory yet, so there is "
            "no sprint to claim tickets from."
        )
        lines.append("")
        lines.append("Run **one** of these from the project root:")
        lines.append("")
        lines.append("```bash")
        lines.append("koru --init --project .                       # 2-ticket starter scaffold")
        lines.append(
            "koru --init --project . --from pipeline.yaml  # import an existing flat pipeline"
        )
        lines.append("```")
        lines.append("")
        lines.append("Then re-run `koru` to refresh this brief.")
        lines.append("")
    elif ticket:
        tid = ticket.get("id", "?")
        name = ticket.get("name", "")
        executor = (ticket.get("executor") or {}).get("kind", "?")
        lines.append(f"## Active ticket: `{tid}` — {name}")
        lines.append("")
        lines.append(f"- **executor**: `{executor}`")
        lines.append(f"- **status**: `{ticket.get('status', '?')}`")
        files = ticket.get("files") or []
        if files:
            lines.append(f"- **files in scope**: {', '.join(f'`{f}`' for f in files)}")
        prompt = (ticket.get("inputs") or {}).get("prompt")
        if prompt:
            lines.append("")
            lines.append("### Prompt")
            lines.append("")
            lines.append("> " + str(prompt).replace("\n", "\n> "))
    else:
        err = context.get("ticket_error") or "no ticket"
        lines.append(f"## No active ticket — {err}")
    lines.append("")

    # On-change gates — wup + regix + testql triad. Only render when at
    # least one of the three is configured, otherwise skip silently to
    # avoid noise in projects that don't use the pattern.
    gate_markers = {
        "wup": markers.get("wup_yaml", False),
        "regix": markers.get("regix_yaml", False),
        "testql": markers.get("testql_scenarios", False),
    }
    if any(gate_markers.values()):
        lines.append("## On-change gates")
        lines.append("")
        lines.append(
            "These packages run automatically (or on demand via "
            "`/koru-gate`) to detect regressions BEFORE you call "
            "`planfile ticket done <id>`. See "
            "`workflows/on-change-gates.md` for the full cycle."
        )
        lines.append("")
        lines.append("| gate | configured | role | command |")
        lines.append("| --- | --- | --- | --- |")
        lines.append(
            f"| `wup` | `{gate_markers['wup']}` | "
            "intelligent file watcher (3-layer: detect → quick → full) | "
            "`wup watch` (daemon) / `wup status` |"
        )
        lines.append(
            f"| `regix` | `{gate_markers['regix']}` | "
            "regression metrics (CC / MI / coverage delta) | "
            "`regix gates` (absolute) / `regix compare` (delta) |"
        )
        lines.append(
            f"| `testql` | `{gate_markers['testql']}` | "
            "behavioural HTTP probes (TOON YAML scenarios) | "
            "`testql run <scenario>` |"
        )
        lines.append("")
        missing = [name for name, present in gate_markers.items() if not present]
        if missing:
            lines.append(
                f"_Not yet configured: {', '.join(f'`{m}`' for m in missing)}. "
                "Bootstrap any of them with `task template:install:wup` "
                "(in koru) or follow `workflows/on-change-gates.md`._"
            )
            lines.append("")

    lines.append("## Policy (you MUST obey)")
    lines.append("")
    lines.append("| gate | value |")
    lines.append("| --- | --- |")
    for k in (
        "allow_commit",
        "allow_push",
        "allow_branch_create",
        "allow_branch_switch",
        "allow_tag",
        "allow_destructive_shell",
        "require_planfile_lifecycle",
        "require_ci_pass_before_complete",
    ):
        lines.append(f"| `{k}` | `{policy.get(k)}` |")
    if policy.get("ci_command"):
        lines.append(f"| `ci_command` | `{policy['ci_command']}` |")
    lines.append("")

    lines.append("## Rules")
    lines.append("")
    for rule in context.get("instructions", []):
        lines.append(f"- {rule}")
    lines.append("")

    lines.append("## Self-service commands")
    lines.append("")
    for k, v in (context.get("self_service") or {}).items():
        lines.append(f"- **{k}**: `{v}`")
    lines.append("- **add_nl_task**: `koru task \"Describe the next change\"`")
    lines.append("- **agent_prompt**: `koru agent`")
    lines.append("- **launch_agent**: `koru agent --launch`")
    lines.append(
        "- **scan_repo**: `koru scan` (dry-run) / `koru scan --apply` "
        "(create tickets from pytest collect errors, TODO/FIXME, missing "
        "gates and semcod tools)"
    )
    lines.append("")

    lines.append("## Dashboard")
    lines.append("")
    lines.append(
        "Uruchom lokalny dashboard koru z automatycznym otwarciem "
        "zakładki w przeglądarce:"
    )
    lines.append("")
    lines.append("```bash")
    lines.append("koru serve                        # http://127.0.0.1:8765 + auto-open tab")
    lines.append("koru serve --port 9000            # custom port")
    lines.append("koru serve --no-open              # start server, don't open browser")
    lines.append("```")
    lines.append("")
    lines.append(
        "Dashboard auto-odświeża co 5 s i pokazuje aktywny ticket, "
        "policy, agent lanes oraz on-change gates. Endpointy: "
        "`/api/context` (JSON), `/api/handoff` (markdown brief), "
        "`/health`."
    )
    lines.append("")

    return "\n".join(lines)
