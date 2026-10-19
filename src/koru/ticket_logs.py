"""Per-ticket markdown logs under project/ticket-*/ (stdlib only).

Lower layers (koru.queue, koru.activity_log, bounded contexts) use these helpers;
they live outside koru.autonomy so the queue never imports the autonomy layer
(import contract "koru.queue is a lower layer", semcod/koru#731).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def find_ticket_dir(project: Path, ticket_id: str) -> Path | None:
    """Resolve only explicit Wellmanifest IDs; Planfile IDs are a separate namespace.

    Never infer ownership from a shared numeric suffix or choose an arbitrary
    slugged directory when several tickets match.
    """
    raw = ticket_id.strip().lower()
    if not re.fullmatch(r"ticket-[0-9]+(?:--?[a-z0-9]+(?:-[a-z0-9]+)*)?", raw):
        return None
    project_dir = project / "project"
    if not project_dir.is_dir():
        return None
    exact = project_dir / raw
    if exact.is_dir() and not exact.is_symlink():
        return exact
    if not re.fullmatch(r"ticket-[0-9]+", raw):
        return None
    matches = [
        path for path in project_dir.glob(f"{raw}-*")
        if path.is_dir() and not path.is_symlink()
    ]
    return matches[0] if len(matches) == 1 else None


def append_ticket_markdown_log(
    project: Path,
    waiting_ticket: str,
    record: Any,
) -> None:
    """Append decision trace to project/ticket-*/koru.log.md with markdown codeblocks."""
    ticket_dir = find_ticket_dir(project, waiting_ticket)
    if not ticket_dir:
        return

    log_file = ticket_dir / "koru.log.md"
    timestamp = getattr(record, "at", "")
    cycle = getattr(record, "cycle", 0)

    # Format trace as markdown with yaml codeblock
    content_blocks = [
        f"### Cycle {cycle} (`{timestamp}`)\n\n",
        "```yaml\n",
        f"uri: koru://cycle/{cycle}/decision/{record.action}\n",
        f"observed: {record.observed}\n",
        f"decided: {record.decided}\n",
        f"action: {record.action}\n",
        f"evidence: {record.evidence}\n",
    ]
    if getattr(record, "skip_because", ""):
        content_blocks.append(f"because: {record.skip_because}\n")
    if getattr(record, "next_step", ""):
        content_blocks.append(f"next: {record.next_step}\n")
    content_blocks.append("```\n\n")

    # Add alternating NL/DSL trace block
    content_blocks.extend([
        "```yaml\n",
        f'NL: "Cykl {cycle}: {record.decided} ({record.observed})"\n',
        f'DSL: "action: {record.action} [evidence: {record.evidence}]"\n',
        "```\n\n",
    ])

    try:
        if not log_file.exists():
            header = f"# Koru Autonomy Log: `{ticket_dir.name}`\n\n"
            log_file.write_text(header + "".join(content_blocks), encoding="utf-8")
        else:
            with log_file.open("a", encoding="utf-8") as f:
                f.write("".join(content_blocks))
    except OSError:
        pass


def append_queue_ticket_markdown_log(
    project: Path,
    result: Any,
) -> None:
    """Append queue execution event to project/ticket-*/koru.log.md if project has wellmanifest layout."""
    ticket_id = getattr(result, "ticket_id", None)
    if not ticket_id:
        return
    ticket_dir = find_ticket_dir(project, str(ticket_id))
    if not ticket_dir:
        return

    log_file = ticket_dir / "koru.log.md"
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    status = getattr(result, "status", "unknown")
    executor = getattr(result, "executor_kind", "unknown")
    exit_code = getattr(result, "exit_code", 0)
    message = getattr(result, "message", "")

    content_blocks = [
        f"### Queue Run (`{timestamp}`)\n\n",
        "```yaml\n",
        f"uri: koru://queue/task/{ticket_id}/{status}\n",
        f"ticket: {ticket_id}\n",
        f"executor: {executor}\n",
        f"status: {status}\n",
        f"exit_code: {exit_code}\n",
        "```\n\n",
    ]
    if message:
        content_blocks.extend([
            "```text\n",
            f"{message}\n",
            "```\n\n",
        ])

    try:
        if not log_file.exists():
            header = f"# Koru Autonomy Log: `{ticket_dir.name}`\n\n"
            log_file.write_text(header + "".join(content_blocks), encoding="utf-8")
        else:
            with log_file.open("a", encoding="utf-8") as f:
                f.write("".join(content_blocks))
    except OSError:
        pass
