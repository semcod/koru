"""Legacy ``skipped`` planfile ticket migration (STARTER-600).

Retires the invalid ``skipped`` status through a versioned,
auditable rule (``koru.queue.legacy-skipped-migration/v1``).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Legacy ``skipped`` ticket migration (STARTER-600)
# ---------------------------------------------------------------------------

LEGACY_SKIPPED_MIGRATION_SCHEMA = "koru.queue.legacy-skipped-migration/v1"
LEGACY_SKIPPED_MIGRATION_TAG = "KORU-LEGACY-SKIPPED-MIGRATION"


@dataclass(frozen=True)
class LegacySkippedMigrationRule:
    """Versioned mapping from a retired planfile status to a valid terminal."""

    schema: str
    source_status: str
    target_status: str
    reason: str


MIGRATION_RULE_V1 = LegacySkippedMigrationRule(
    schema=LEGACY_SKIPPED_MIGRATION_SCHEMA,
    source_status="skipped",
    target_status="canceled",
    reason=(
        "legacy planfile ticket status 'skipped' is not in TicketStatus; "
        "operator-declined code-smell backlog archived as canceled"
    ),
)


@dataclass(frozen=True)
class LegacySkippedCandidate:
    ticket_id: str
    name: str
    labels: tuple[str, ...]
    rule: LegacySkippedMigrationRule = MIGRATION_RULE_V1

    def explanation(self) -> str:
        labels = ",".join(self.labels) if self.labels else "(no labels)"
        return f"{self.ticket_id} skipped -> {self.rule.target_status} [{labels}] ({self.rule.schema})"


@dataclass
class LegacySkippedMigrationReport:
    candidates: list[LegacySkippedCandidate] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    dry_run: bool = True
    rule: LegacySkippedMigrationRule = MIGRATION_RULE_V1

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "schema": self.rule.schema,
            "source_status": self.rule.source_status,
            "target_status": self.rule.target_status,
            "candidate_count": len(self.candidates),
            "applied_count": len(self.applied),
            "failed_count": len(self.failed),
            "candidates": [
                {
                    "ticket_id": c.ticket_id,
                    "name": c.name,
                    "labels": list(c.labels),
                    "target_status": c.rule.target_status,
                }
                for c in self.candidates
            ],
            "applied": list(self.applied),
            "failed": [{"ticket_id": tid, "error": err} for tid, err in self.failed],
        }


def _current_sprint_file(project: Path) -> Path:
    return project / ".planfile" / "sprints" / "current.yaml"


def load_raw_sprint_tickets(project: Path) -> dict[str, Any]:
    """Read sprint tickets without planfile model validation."""
    import yaml

    sprint_file = _current_sprint_file(project)
    if not sprint_file.is_file():
        raise RuntimeError(f"sprint file missing: {sprint_file}")
    try:
        data = yaml.safe_load(sprint_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise RuntimeError(f"cannot read sprint file: {sprint_file}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"sprint file invalid: {sprint_file}")
    sprint_data = data.get("sprint") if isinstance(data.get("sprint"), dict) else data
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        raise RuntimeError(f"sprint tickets missing in: {sprint_file}")
    return tickets


def find_legacy_skipped_candidates(
    tickets: dict[str, Any],
    *,
    rule: LegacySkippedMigrationRule = MIGRATION_RULE_V1,
) -> list[LegacySkippedCandidate]:
    """Return tickets whose raw YAML status matches the retired ``skipped`` value."""
    candidates: list[LegacySkippedCandidate] = []
    for ticket_id, ticket in tickets.items():
        if not isinstance(ticket, dict):
            continue
        status = str(ticket.get("status") or "").strip().lower()
        if status != rule.source_status:
            continue
        labels = ticket.get("labels") or []
        candidates.append(
            LegacySkippedCandidate(
                ticket_id=str(ticket_id),
                name=str(ticket.get("name") or ""),
                labels=tuple(str(x) for x in (labels if isinstance(labels, list) else [])),
                rule=rule,
            ),
        )
    return sorted(candidates, key=lambda item: item.ticket_id)


def _build_legacy_skipped_note(candidate: LegacySkippedCandidate) -> str:
    payload = {
        "kind": "legacy_skipped_migration",
        "schema": candidate.rule.schema,
        "from_status": candidate.rule.source_status,
        "to_status": candidate.rule.target_status,
        "reason": candidate.rule.reason,
        "migrated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return f"{LEGACY_SKIPPED_MIGRATION_TAG} {json.dumps(payload, sort_keys=True)}"


def _migrate_ticket_via_planfile(project: Path, candidate: LegacySkippedCandidate) -> None:
    """Migrate one ticket through planfile store (raw YAML), not the CLI."""
    from planfile import Planfile

    pf = Planfile.auto_discover(str(project))
    note = _build_legacy_skipped_note(candidate)
    updated = pf.update_ticket(
        candidate.ticket_id,
        status=candidate.rule.target_status,
        reason=note,
        actor="koru.queue.migrate-legacy-skipped",
    )
    if updated is None:
        raise RuntimeError(f"ticket not found or update failed: {candidate.ticket_id}")


def migrate_legacy_skipped(
    project: Path,
    *,
    apply: bool = False,
    rule: LegacySkippedMigrationRule = MIGRATION_RULE_V1,
    migrator: Callable[[Path, LegacySkippedCandidate], None] | None = None,
) -> LegacySkippedMigrationReport:
    """Diagnose and optionally migrate legacy ``skipped`` tickets via planfile."""
    tickets = load_raw_sprint_tickets(project)
    candidates = find_legacy_skipped_candidates(tickets, rule=rule)
    report = LegacySkippedMigrationReport(
        candidates=candidates,
        dry_run=not apply,
        rule=rule,
    )
    if not apply:
        return report
    migrate = migrator or _migrate_ticket_via_planfile
    for candidate in candidates:
        try:
            migrate(project, candidate)
            report.applied.append(candidate.ticket_id)
        except Exception as exc:
            report.failed.append((candidate.ticket_id, str(exc)))
    return report
