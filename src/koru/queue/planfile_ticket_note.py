"""Best-effort shell evidence: planfile ``ticket update`` note flags + artifact fallback."""


from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

from koru.queue.ticket import planfile_command
from koru.queue.types import CommandResult


def _stderr_unknown_option(stderr: str, flag: str) -> bool:
    """True when *stderr* looks like Typer/Click rejecting *flag*."""
    text = stderr or ""
    return "No such option" in text and flag in text


def append_shell_evidence_note(
    project: Path,
    ticket_id: str,
    note: str,
    *,
    run_id: str,
    planfile_runner: Callable[..., CommandResult],
) -> tuple[CommandResult, str]:
    """Append shell run evidence to a ticket, or write a run artifact.

    Tries ``planfile ticket update <id> --note`` then the same with ``-n``
    (supported on current planfile sources). Older planfile releases (e.g.
    some 0.1.x builds) omit both; then writes
    ``.planfile/.koru/runs/<ticket_id>-<run_id>.shell-evidence.txt``.

    Returns ``(result, kind)`` where *kind* is ``"cli"`` or ``"artifact"``.
    """
    project = project.resolve()
    flags = ("--note", "-n")
    for flag in flags:
        cmd = ["ticket", "update", ticket_id, flag, note]
        res = planfile_command(project, cmd, runner=planfile_runner)
        if res.returncode == 0:
            return res, "cli"
        if _stderr_unknown_option(res.stderr or "", flag):
            continue
        return res, "cli"

    runs = project / ".planfile" / ".koru" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / f"{ticket_id}-{run_id}.shell-evidence.txt"
    path.write_text(note, encoding="utf-8")
    synthetic: CommandResult = SimpleNamespace(
        returncode=0,
        stdout=str(path),
        stderr="",
    )
    return synthetic, "artifact"
