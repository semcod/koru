"""Shared Planfile handoff text for IDE-agent prompts."""

from __future__ import annotations


def git_discipline_lines() -> list[str]:
    """Git rules for the driven agent.

    Without these the agent free-styles ``git commit -a -m "refactoring"``:
    it absorbs the operator's unrelated uncommitted work, misses untracked
    files it created itself (broken HEAD for anyone doing a fresh checkout)
    and leaves meaningless history. Appended to every drive prompt alongside
    the Planfile handoff block.
    """
    return [
        "Git discipline:",
        (
            "- Commit only files you created or modified for this ticket; "
            "stage them explicitly by path (never `git add -A` or `git commit -a`)."
        ),
        (
            "- When you create a new file, `git add` it in the same commit as "
            "the code that imports it — never commit code that imports an "
            "uncommitted file."
        ),
        (
            "- Leave unrelated pre-existing modifications and untracked files "
            "exactly as you found them."
        ),
        (
            "- Write a descriptive conventional-commit message for the actual "
            'change (never a bare "refactoring").'
        ),
    ]


def planfile_status_handoff_lines(ticket_id: str) -> list[str]:
    """Return Planfile status commands + git discipline for an IDE-side agent.

    Every prompt path that hands work to the agent (ticket, fallback,
    escalation, ide_work) appends this block, so both contracts ride along.
    """
    clean_ticket_id = ticket_id.strip()
    if not clean_ticket_id:
        return [
            "Planfile status handoff:",
            "- When checks pass and the work is complete, update the ticket status to done in Planfile.",
            "- If blocked, update the ticket to waiting_input with the exact missing input.",
            "- If implementation fails after a real attempt, mark the ticket failed with the failure reason.",
            "- Do not leave completed IDE work in waiting_input.",
            "",
            *git_discipline_lines(),
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
        "",
        *git_discipline_lines(),
    ]


def planfile_status_handoff_text(ticket_id: str) -> str:
    """Return explicit Planfile status commands as a compact prompt block."""
    return "\n".join(planfile_status_handoff_lines(ticket_id))


__all__ = [
    "git_discipline_lines",
    "planfile_status_handoff_lines",
    "planfile_status_handoff_text",
]
