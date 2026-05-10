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

from .policy import Policy, load_policy
from .runtime import planfile_dir


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
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb"}


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
    planfile_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
    git_probe: Callable[[Path], dict[str, Any]] | None = None,
    policy: Policy | None = None,
) -> dict[str, Any]:
    """Assemble the LLM brief for a project.

    The function is fully injectable to keep tests hermetic. In normal
    use, callers just pass ``project`` and let everything else default.
    """
    project = project.resolve()
    resolved_policy = policy if policy is not None else load_policy(project)

    # Locate the ticket of interest.
    if ticket_id:
        ticket_args = ["ticket", "show", ticket_id, "--format", "json"]
    else:
        ticket_args = ["ticket", "next", "--format", "json"]
        if queue_name:
            ticket_args.extend(["--queue", queue_name])
    ticket_proc = _run_planfile(project, ticket_args, runner=planfile_runner)
    ticket_data: dict[str, Any] | None = None
    ticket_error: str | None = None
    if ticket_proc.returncode == 0:
        ticket_data = _safe_json(ticket_proc.stdout)
        if ticket_data is None:
            stripped = (ticket_proc.stdout or "").strip()
            if "No runnable ticket" in stripped or not stripped:
                ticket_data = None
                ticket_error = "queue is idle"
            else:
                ticket_error = "planfile output was not JSON"
    else:
        ticket_error = (ticket_proc.stderr or "planfile error").strip().splitlines()[0]

    git_state = (git_probe or _git_probe)(project)
    planfile_present = (planfile_dir(project) / "config.yaml").exists()

    instructions = _build_instructions(resolved_policy, ticket_data)
    self_service = _build_self_service(resolved_policy, ticket_data)

    return {
        "schema_version": "1",
        "project": str(project),
        "ticket": ticket_data,
        "ticket_error": ticket_error,
        "policy": resolved_policy.to_dict(),
        "environment": {
            "git": git_state,
            "planfile_initialised": planfile_present,
            "queue_name": queue_name,
        },
        "instructions": instructions,
        "self_service": self_service,
    }


# ---------------------------------------------------------------------------
# Instruction & self-service text generators
# ---------------------------------------------------------------------------


def _build_instructions(policy: Policy, ticket: dict[str, Any] | None) -> list[str]:
    """Imperative, copy-paste-able rules for the LLM agent."""
    rules: list[str] = []
    rules.append(
        "You are an LLM agent operating under koru. You MUST obey the "
        "policy embedded in this brief. Violations terminate the session."
    )
    rules.append(
        "Use planfile commands for ALL state changes. Do not edit "
        ".planfile/sprints/*.yaml directly."
    )
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
                "and verify exit code 0. Only then call `planfile ticket complete`."
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
            "Touching anything else requires `planfile ticket input`."
        )
    rules.append(
        "If you are blocked or need a human decision, call "
        "`planfile ticket input <id> --prompt \"<question>\"` and stop."
    )
    rules.extend(policy.notes)
    return rules


def _build_self_service(policy: Policy, ticket: dict[str, Any] | None) -> dict[str, Any]:
    """Concrete CLI invocations the LLM can use without guessing."""
    tid = ticket.get("id") if isinstance(ticket, dict) else None
    base = "planfile ticket"
    block: dict[str, Any] = {
        "next_brief": "koru --context --project . --format json",
        "show_ticket": f"{base} show <id> --format json",
        "request_input": f"{base} input <id> --prompt \"<question>\"",
        "fail_ticket": f"{base} fail <id> --error \"<reason>\"",
    }
    if tid:
        block["claim_this"] = f"{base} claim {tid} --assigned-to <agent>"
        block["start_this"] = f"{base} start {tid} --assigned-to <agent>"
        block["complete_this"] = f"{base} complete {tid} --note \"<summary>\""
        block["fail_this"] = f"{base} fail {tid} --error \"<reason>\""
        block["input_this"] = f"{base} input {tid} --prompt \"<question>\""
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

    if ticket:
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
    lines.append("")

    return "\n".join(lines)
