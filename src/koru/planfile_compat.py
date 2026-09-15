"""Compatibility reads for legacy Planfile ticket records.

Older Planfile versions reject a ticket whose persisted ``status`` is
``skipped``.  The rejection is lossy for read-only consumers: the CLI exits
successfully but omits the invalid record.  Koru must keep those records
visible until an operator deliberately migrates them.

This module never writes the Planfile store.  It compares the validated CLI
payload with a raw YAML snapshot and appends records the CLI could not parse,
while adding an explicit diagnostic marker for the operator-facing reports.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_TICKET_STATUSES = frozenset(
    {
        "open",
        "in_progress",
        "review",
        "done",
        "blocked",
        "canceled",
        "failed",
        # Koru/older Planfile readers accepted these compatibility values.
        "ready",
        "todo",
        # Retired value retained only for read compatibility.
        "skipped",
    },
)
LEGACY_STATUS = "skipped"
LEGACY_STATUS_DIAGNOSTIC = "legacy-status"


@dataclass(frozen=True)
class PlanfileCompatibilityReport:
    """Read-only evidence about records missing from the Planfile payload."""

    raw_ticket_count: int = 0
    reported_ticket_count: int = 0
    recovered_ticket_count: int = 0
    legacy_status_counts: dict[str, int] = field(default_factory=dict)
    unknown_status_count: int = 0
    read_errors: tuple[str, ...] = ()

    @property
    def migration_candidate_count(self) -> int:
        return self.legacy_status_counts.get(LEGACY_STATUS, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_ticket_count": self.raw_ticket_count,
            "reported_ticket_count": self.reported_ticket_count,
            "recovered_ticket_count": self.recovered_ticket_count,
            "migration_candidate_count": self.migration_candidate_count,
            "legacy_status_counts": dict(self.legacy_status_counts),
            "unknown_status_count": self.unknown_status_count,
            "read_errors": list(self.read_errors),
        }


def _yaml_loader() -> Any:
    import yaml

    return getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _raw_ticket_records(project: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Read ticket dictionaries from every sprint YAML without Pydantic."""
    import yaml

    sprint_dir = project / ".planfile" / "sprints"
    if not sprint_dir.is_dir():
        return [], ()

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for sprint_file in sorted(sprint_dir.glob("*.yaml")):
        try:
            with sprint_file.open(encoding="utf-8") as stream:
                document = yaml.load(stream, Loader=_yaml_loader())
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            errors.append(f"{sprint_file.name}: {exc}")
            continue
        if not isinstance(document, dict):
            continue
        sprint = document.get("sprint") if isinstance(document.get("sprint"), dict) else document
        tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
        if not isinstance(tickets, dict):
            continue
        for ticket_id, value in tickets.items():
            if not isinstance(value, dict):
                continue
            record = dict(value)
            record.setdefault("id", str(ticket_id))
            record.setdefault("_compat_sprint", sprint_file.stem)
            records.append(record)
    return records, tuple(errors)


def merge_missing_ticket_records(
    reported: list[dict[str, Any]],
    project: Path,
) -> tuple[list[dict[str, Any]], PlanfileCompatibilityReport]:
    """Append raw records omitted by a legacy Planfile reader.

    The validated payload remains authoritative when an id is present in both
    sources.  A raw-only record receives ``legacy_status`` and
    ``status_diagnostic`` fields, allowing dashboards and resume reports to
    explain why it was recovered.  The returned list is a new list and no
    filesystem state is changed.
    """
    raw_records, read_errors = _raw_ticket_records(project.resolve())
    reported_records = [item for item in reported if isinstance(item, dict)]
    reported_ids = {
        str(item.get("id") or item.get("ticket_id") or "").strip()
        for item in reported_records
        if str(item.get("id") or item.get("ticket_id") or "").strip()
    }
    merged = list(reported_records)
    recovered = 0
    status_counts: Counter[str] = Counter()
    seen_raw: set[str] = set()

    for raw in raw_records:
        ticket_id = str(raw.get("id") or raw.get("ticket_id") or "").strip()
        if not ticket_id or ticket_id in reported_ids or ticket_id in seen_raw:
            continue
        seen_raw.add(ticket_id)
        status = str(raw.get("status") or "").strip().lower()
        if status == LEGACY_STATUS or status not in SUPPORTED_TICKET_STATUSES:
            status_counts[status or "<missing>"] += 1
        recovered_record = dict(raw)
        recovered_record.pop("_compat_sprint", None)
        if status == LEGACY_STATUS:
            recovered_record["legacy_status"] = LEGACY_STATUS
            recovered_record["status_diagnostic"] = {
                "kind": LEGACY_STATUS_DIAGNOSTIC,
                "status": LEGACY_STATUS,
                "action": "run koru queue migrate-legacy-skipped --apply",
            }
        elif status not in SUPPORTED_TICKET_STATUSES:
            recovered_record["legacy_status"] = status or None
            recovered_record["status_diagnostic"] = {
                "kind": "unknown-status",
                "status": status or None,
                "action": "inspect and migrate explicitly; no automatic mutation",
            }
        merged.append(recovered_record)
        recovered += 1

    report = PlanfileCompatibilityReport(
        raw_ticket_count=len(raw_records),
        reported_ticket_count=len(reported_records),
        recovered_ticket_count=recovered,
        legacy_status_counts=dict(sorted(status_counts.items())),
        unknown_status_count=sum(
            count for status, count in status_counts.items() if status != LEGACY_STATUS
        ),
        read_errors=read_errors,
    )
    return merged, report


__all__ = [
    "LEGACY_STATUS",
    "LEGACY_STATUS_DIAGNOSTIC",
    "PlanfileCompatibilityReport",
    "SUPPORTED_TICKET_STATUSES",
    "merge_missing_ticket_records",
]
