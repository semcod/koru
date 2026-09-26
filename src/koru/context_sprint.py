"""Planfile sprint data caching and blocking/bug ticket auto-promotion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

# mtime/size-keyed cache for the sprint YAML. The dashboard re-requests
# /api/context every ~5s and each build_context call parsed the whole
# (1MB+, 300-ticket) current.yaml with the pure-Python loader — ~1.5s each,
# multiple times per request. Cache the parse and skip it entirely while the
# file is unchanged; use the libyaml C loader (≈8x faster) when present.
_SPRINT_YAML_CACHE: dict[str, tuple[int, int, dict[str, Any] | None]] = {}


def _fast_yaml_load(path: Path) -> Any:
    """Parse a YAML file with the C loader when available (much faster)."""
    import yaml

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=loader)


def _load_sprint_data(project: Path) -> dict[str, Any] | None:
    """Load sprint data from current.yaml, cached by file mtime+size."""
    from koru.runtime import planfile_dir

    pf = planfile_dir(project)
    sprint_file = pf / "sprints" / "current.yaml"

    try:
        stat = sprint_file.stat()
    except OSError:
        return None

    key = str(sprint_file)
    cached = _SPRINT_YAML_CACHE.get(key)
    if cached is not None and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return cached[2]

    try:
        sprint_data = _fast_yaml_load(sprint_file)
    except Exception:
        return None

    result: dict[str, Any] | None = None
    if (
        sprint_data
        and isinstance(sprint_data, dict)
        and isinstance(sprint_data.get("sprint"), dict)
        and "tickets" in sprint_data["sprint"]
    ):
        result = sprint_data

    _SPRINT_YAML_CACHE[key] = (stat.st_mtime_ns, stat.st_size, result)
    return result


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
                    f"🔥 Auto-promoted {blocking_id} from {current_priority} to critical (blocking)",
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
                        f"🐛 Auto-promoted bug {ticket_id} from {current_priority} to {new_priority}",
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


__all__ = [
    "_SPRINT_YAML_CACHE",
    "_auto_promote_blocking_tickets",
    "_fast_yaml_load",
    "_find_blocking_tickets",
    "_load_sprint_data",
    "_promote_blocking_to_critical",
    "_promote_bug_priority",
    "_write_sprint_data",
]
