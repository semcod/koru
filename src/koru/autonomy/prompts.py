"""Prompt strategy for autopilot drive — builds a context-aware prompt
for the IDE-side LLM based on queue status, stagnation, and ticket data.

Goals (multi-hour autonomy):
  - Never send an empty / no-op prompt; always have a sensible fallback.
  - Escalate when the same (status, ticket_id) repeats: ask the LLM to
    explicitly resolve the blocker instead of silently retrying.
  - Keep the contract narrow: pure function of inputs, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from koru.autonomy.planfile_handoff import planfile_status_handoff_text

DriveKind = Literal[
    "drive_prompt",  # default outer prompt (idle / progressing)
    "ticket_prompt",  # waiting_input with concrete message from ticket
    "fallback_prompt",  # waiting_input with empty message — generic continue
    "escalation_prompt",  # repeated stagnation — ask LLM to unblock or report
    "handoff",  # explicit handoff action
]


@dataclass(frozen=True)
class PromptDecision:
    """Result of building a prompt for autopilot.send_chat."""

    prompt: str
    kind: DriveKind
    skip: bool = False
    skip_reason: str = ""


# Repeating the same (status, ticket_id) this many cycles triggers escalation.
DEFAULT_ESCALATION_THRESHOLD = 3


def _with_planfile_status_handoff(prompt: str, ticket_id: str | None) -> str:
    clean_ticket_id = (ticket_id or "").strip()
    if not clean_ticket_id:
        return prompt
    if f"planfile ticket done {clean_ticket_id}" in prompt:
        return prompt
    return f"{prompt.rstrip()}\n\n{planfile_status_handoff_text(clean_ticket_id)}"


def build_prompt(
    *,
    queue_status: str,
    last_message: str,
    waiting_ticket_id: str | None,
    drive_prompt: str,
    autopilot_action: str,
    stagnation_streak: int,
    escalation_threshold: int = DEFAULT_ESCALATION_THRESHOLD,
) -> PromptDecision:
    """Decide which prompt to send to the IDE LLM this cycle.

    Args:
        queue_status: Last status from QueueLoopResult (e.g. "idle", "waiting_input").
        last_message: Last message attached to the waiting ticket (may be empty).
        waiting_ticket_id: Ticket id currently blocking the queue.
        drive_prompt: User-configured default outer prompt.
        autopilot_action: "drive" | "handoff" | "off".
        stagnation_streak: Consecutive cycles seeing the same (status, ticket_id).
        escalation_threshold: After this many repeats, escalate.

    Returns:
        PromptDecision with the prompt to send and a `kind` for telemetry.
    """
    # Handoff is explicit: just send the configured prompt.
    if autopilot_action == "handoff":
        return PromptDecision(prompt=drive_prompt, kind="handoff")

    # Stagnation: escalate before retrying the same prompt indefinitely.
    if stagnation_streak >= escalation_threshold and waiting_ticket_id:
        original = last_message.strip() if last_message else ""
        task_line = f" Original ticket prompt: {original}" if original else ""
        handoff = planfile_status_handoff_text(waiting_ticket_id)
        escalation = (
            f"Ticket {waiting_ticket_id} has been stuck in status "
            f"'{queue_status}' for {stagnation_streak} cycles. "
            "Continue the actual implementation work for this ticket now. "
            "Run the relevant checks before closing it. "
            f"{handoff} "
            f"{task_line}"
        )
        return PromptDecision(prompt=escalation, kind="escalation_prompt")

    # Waiting on user input: prefer the ticket's own message if present.
    if queue_status == "waiting_input":
        ticket_msg = last_message.strip() if last_message else ""
        if ticket_msg:
            return PromptDecision(
                prompt=_with_planfile_status_handoff(ticket_msg, waiting_ticket_id),
                kind="ticket_prompt",
            )
        # Fallback: empty message must NOT result in a no-op. Send a
        # generic continue-prompt so the IDE LLM at least picks the
        # next ticket / progresses.
        ticket_ref = f" (ticket {waiting_ticket_id})" if waiting_ticket_id else ""
        fallback = (
            f"The queue is blocked on waiting_input{ticket_ref} but no "
            "message was attached. Pick the next pending ticket from the "
            "planfile and continue, or update the blocked ticket's status."
        )
        return PromptDecision(
            prompt=_with_planfile_status_handoff(fallback, waiting_ticket_id),
            kind="fallback_prompt",
        )

    # Default: outer drive prompt.
    return PromptDecision(prompt=drive_prompt, kind="drive_prompt")


__all__ = ["PromptDecision", "DriveKind", "build_prompt", "DEFAULT_ESCALATION_THRESHOLD"]
