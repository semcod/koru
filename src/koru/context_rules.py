"""Instruction and self-service rule builders for LLM agent context briefs."""

from __future__ import annotations

from typing import Any

from koru.git_attribution import KORU_AGENT_COAUTHOR_TRAILER
from koru.policy import Policy


def _build_instructions(
    policy: Policy,
    ticket: dict[str, Any] | None,
    *,
    planfile_initialised: bool,
) -> list[str]:
    """Imperative, copy-paste-able rules for the LLM agent.

    Two flavours:
        - planfile_initialised=False => base rules + SETUP REQUIRED guide.
          The agent must NOT try to claim/start/complete tickets when
          there is no sprint file to claim from.
        - planfile_initialised=True  => base rules + the policy-derived
          DO NOT list + ticket-scope rule + escape hatches.
    """
    rules: list[str] = [
        "You are an LLM agent operating under koru. You MUST obey the "
        "policy embedded in this brief. Violations terminate the session.",
        "Use planfile commands for ALL state changes. Do not edit .planfile/sprints/*.yaml directly.",
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
        rules.append("DO NOT run raw `git push`. If pushing is explicitly requested, use `koru git push`.")
    if not policy.allow_branch_create:
        rules.append("DO NOT create or switch branches.")
    if not policy.allow_tag:
        rules.append("DO NOT create git tags.")
    if not policy.allow_destructive_shell:
        rules.append(
            ("DO NOT run destructive shell commands (rm -rf /, dd, mkfs, shutdown, force-pushes, …)."),
        )
    if policy.require_ci_pass_before_complete:
        if policy.ci_command:
            rules.append(
                f"Before completing a ticket, run `{policy.ci_command}` "
                "and verify exit code 0. Only then call `planfile ticket done <id>`.",
            )
        else:
            rules.append(
                "Before completing a ticket, ask the human operator to run the project's CI gate. Do not self-certify.",
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
        "When creating or preparing a Git commit, keep the human Git author "
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
            "autonomous_bootstrap": ("koru autonomous up --project . --max-cycles 1 --sleep-seconds 0 --no-autopilot"),
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


__all__ = [
    "_build_instructions",
    "_build_policy_rules",
    "_build_self_service",
    "_build_setup_instructions",
    "_build_shared_rules",
    "_build_ticket_rules",
]
