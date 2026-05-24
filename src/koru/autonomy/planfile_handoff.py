"""Shared Planfile handoff text for IDE-agent prompts."""

from __future__ import annotations


def planfile_status_handoff_lines(ticket_id: str) -> list[str]:
    """Return explicit Planfile status commands for an IDE-side agent."""
    clean_ticket_id = ticket_id.strip()
    if not clean_ticket_id:
        return [
            "Planfile status handoff:",
            "- When checks pass and the work is complete, update the ticket status to done in Planfile.",
            "- If blocked, update the ticket to waiting_input with the exact missing input.",
            "- If implementation fails after a real attempt, mark the ticket failed with the failure reason.",
            "- Do not leave completed IDE work in waiting_input.",
        ]

    return [
        "Planfile status handoff:",
        (
            "- When checks pass and the work is complete, run: "
            f"`planfile ticket done {clean_ticket_id}`"
        ),
        (
            "- If blocked or missing input, run: "
            f"`planfile ticket input {clean_ticket_id} "
            "--prompt \"<exact input needed>\" --note \"<what you verified>\"`"
        ),
        (
            "- If implementation fails after a real attempt, run: "
            f"`planfile ticket fail {clean_ticket_id} --error \"<short failure reason>\"`"
        ),
        "- Do not leave completed IDE work in waiting_input.",
    ]


def planfile_status_handoff_text(ticket_id: str) -> str:
    """Return explicit Planfile status commands as a compact prompt block."""
    return "\n".join(planfile_status_handoff_lines(ticket_id))


__all__ = ["planfile_status_handoff_lines", "planfile_status_handoff_text"]
