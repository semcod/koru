"""ticket2dsl — convert open planfile tickets into a grounded work DSL.

After todo2code (or other discovery) creates planfile tickets, this stage:

1. Loads open tickets from ``.planfile/sprints/<sprint>.yaml``.
2. Keeps only useful code-change targets (same path policy as todo2code).
3. Emits a structured work-unit set for IDE / automation:

   - ``.planfile/.koru/ticket2dsl/work-units.json`` (``koru.ticket-work-unit-set/v1``)
   - ``.planfile/.koru/ticket2dsl/work-units.planfile.dsl`` (planfile DSL script)
   - ``.planfile/.koru/ticket2dsl/work-units.intent.jsonl`` (intent-ish records)

The runtime does **not** implement code. It turns tickets into an explicit,
hash-bound handoff that agents execute with planfile lifecycle commands.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autonomy.code_change_usefulness import (
    is_useful_code_change_path,
    useful_paths,
)

DEFAULT_SOURCE = "koru-ticket2dsl"
DEFAULT_SPRINT = "current"
DEFAULT_OUT_REL = Path(".planfile") / ".koru" / "ticket2dsl"
DEFAULT_MAX_UNITS = 20
OPEN_STATUSES = frozenset(
    {
        "open",
        "todo",
        "ready",
        "backlog",
        "in_progress",
        "in-progress",
        "doing",
        "blocked",
        "waiting",
        "waiting_input",
        "new",
        "",
    }
)


@dataclass
class Ticket2dslOutcome:
    ran: bool = False
    skipped_reason: str | None = None
    units_count: int = 0
    filtered_out_count: int = 0
    json_path: str | None = None
    dsl_path: str | None = None
    intent_path: str | None = None
    ticket_ids: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "units_count": self.units_count,
            "filtered_out_count": self.filtered_out_count,
            "json_path": self.json_path,
            "dsl_path": self.dsl_path,
            "intent_path": self.intent_path,
            "ticket_ids": list(self.ticket_ids),
            "error": self.error,
        }


def ticket2dsl_enabled(project: Path | None = None) -> bool:
    raw = (os.environ.get("KORU_TICKET2DSL_ENABLE") or "").strip().lower()
    if not raw and project is not None:
        try:
            text = (project / ".env").read_text(encoding="utf-8")
        except OSError:
            text = ""
        match = re.search(r"^\s*KORU_TICKET2DSL_ENABLE\s*=\s*(.+?)\s*$", text, re.M)
        raw = (match.group(1).strip().strip("'\"") if match else "").lower()
    if not raw:
        return True
    return raw in {"1", "true", "yes", "on"}


def _load_sprint_tickets(project: Path, *, sprint: str) -> dict[str, dict[str, Any]]:
    try:
        import yaml

        path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001
        return {}
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return {}
    return {
        str(ticket_id): ticket
        for ticket_id, ticket in tickets.items()
        if isinstance(ticket, dict)
    }


def _ticket_status(ticket: dict[str, Any]) -> str:
    return str(ticket.get("status") or ticket.get("state") or "").strip().lower()


def _ticket_files(ticket: dict[str, Any]) -> list[str]:
    raw = ticket.get("files") or ticket.get("paths") or []
    if isinstance(raw, str):
        raw = [raw]
    return useful_paths([str(item) for item in raw])


def _ticket_is_open(ticket: dict[str, Any]) -> bool:
    status = _ticket_status(ticket)
    if status in {"done", "closed", "cancelled", "canceled", "failed", "wontfix"}:
        return False
    return status in OPEN_STATUSES or not status


def _ticket_priority(ticket: dict[str, Any]) -> str:
    return str(ticket.get("priority") or "normal").strip().lower() or "normal"


def _ticket_text(ticket: dict[str, Any]) -> str:
    for key in ("description", "body", "text", "prompt", "name", "title"):
        value = str(ticket.get(key) or "").strip()
        if value:
            return value
    return ""


def _unit_id(ticket_id: str, files: list[str]) -> str:
    digest = hashlib.sha256(f"{ticket_id}|{','.join(files)}".encode()).hexdigest()[:16]
    return f"TWU-{digest}"


def _unit_score(ticket: dict[str, Any], files: list[str]) -> float:
    score = 5.0 + min(8.0, 2.0 * len(files))
    name = str(ticket.get("name") or "")
    if name.startswith("[todo2code]") or "todo2code" in str(ticket.get("source") or ""):
        score += 3.0
    if any(path.startswith("src/") or "/src/" in path for path in files):
        score += 4.0
    if any(Path(path).suffix in {".py", ".ts", ".tsx", ".js", ".go", ".rs"} for path in files):
        score += 3.0
    if any(path.endswith(".md") for path in files) and not any(
        Path(path).suffix in {".py", ".ts", ".tsx", ".js"} for path in files
    ):
        score -= 2.0
    priority = _ticket_priority(ticket)
    score += {"high": 3.0, "normal": 1.0, "low": 0.0}.get(priority, 1.0)
    return score


def build_work_units(
    project: Path,
    *,
    sprint: str = DEFAULT_SPRINT,
    max_units: int = DEFAULT_MAX_UNITS,
    only_todo2code: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    """Return (units, filtered_out_count)."""
    tickets = _load_sprint_tickets(project, sprint=sprint)
    candidates: list[tuple[float, dict[str, Any]]] = []
    filtered = 0
    for ticket_id, ticket in tickets.items():
        if not _ticket_is_open(ticket):
            continue
        files = _ticket_files(ticket)
        source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
        source_tool = str(source.get("tool") or "")
        name = str(ticket.get("name") or "")
        if only_todo2code and "todo2code" not in source_tool and not name.startswith("[todo2code]"):
            continue
        if not files:
            # Still allow pure operational tickets without files only when not only_todo2code
            # and they look like discovery follow-ups — skip empty code-change noise.
            filtered += 1
            continue
        if not all(is_useful_code_change_path(path) for path in files):
            filtered += 1
            continue
        score = _unit_score(ticket, files)
        context = source.get("context") if isinstance(source.get("context"), dict) else {}
        unit = {
            "schemaVersion": "koru.ticket-work-unit/v1",
            "id": _unit_id(ticket_id, files),
            "ticketId": ticket_id,
            "title": name or f"Work unit for {ticket_id}",
            "description": _ticket_text(ticket),
            "priority": _ticket_priority(ticket),
            "status": _ticket_status(ticket) or "open",
            "paths": files,
            "labels": [str(x) for x in (ticket.get("labels") or []) if str(x).strip()],
            "sourceTool": source_tool or None,
            "planId": context.get("plan_id"),
            "planHash": context.get("plan_hash"),
            "diagnosticIds": list(context.get("diagnostic_ids") or []),
            "usefulnessScore": round(score, 2),
            "planfileDsl": [
                f'start ticket {ticket_id}',
                f'show ticket {ticket_id}',
                f'# implement paths: {", ".join(files)}',
                f'done ticket {ticket_id}',
            ],
            "acceptanceHints": [
                "Implement only the declared paths.",
                "Re-run project checks / t2c evaluate-code-change when a planHash is present.",
                f"Close with planfile: done ticket {ticket_id}",
            ],
        }
        candidates.append((score, unit))

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [unit for _, unit in candidates[: max(1, max_units)]]
    return selected, filtered


def _render_planfile_dsl(units: list[dict[str, Any]]) -> str:
    lines = [
        "# Generated by koru ticket2dsl — review before bulk execution",
        "# Each unit maps one open planfile ticket to implementable paths.",
        "",
    ]
    for unit in units:
        ticket_id = unit["ticketId"]
        paths = ", ".join(unit.get("paths") or [])
        lines.append(f"# --- {ticket_id}: {unit.get('title')} ---")
        lines.append(f"# paths: {paths}")
        lines.append(f"show ticket {ticket_id}")
        lines.append(f"start ticket {ticket_id}")
        lines.append(f"# TODO: implement {paths}")
        lines.append(f"# done ticket {ticket_id}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_intent_jsonl(units: list[dict[str, Any]], *, project: Path) -> str:
    lines: list[str] = []
    for unit in units:
        record = {
            "schemaVersion": "t2c.intent/v1-lite",
            "id": unit["id"],
            "kind": "ticket_work_unit",
            "action": "implement",
            "object": unit.get("title"),
            "text": unit.get("description") or unit.get("title"),
            "lifecycle": "planned",
            "target": {
                "paths": unit.get("paths") or [],
                "tickets": [unit.get("ticketId")],
                "symbols": [],
                "versions": [],
            },
            "sourceKind": "planfile_ticket",
            "sourcePath": str(project / ".planfile" / "sprints" / "current.yaml"),
            "ticketId": unit.get("ticketId"),
            "planId": unit.get("planId"),
            "planHash": unit.get("planHash"),
            "diagnosticIds": unit.get("diagnosticIds") or [],
            "confidence": min(1.0, max(0.0, float(unit.get("usefulnessScore") or 0) / 30.0)),
        }
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def run_ticket2dsl(
    project: Path,
    *,
    sprint: str = DEFAULT_SPRINT,
    max_units: int | None = None,
    only_todo2code: bool = False,
) -> Ticket2dslOutcome:
    project = project.resolve()
    outcome = Ticket2dslOutcome()

    if not ticket2dsl_enabled(project):
        outcome.skipped_reason = "disabled via KORU_TICKET2DSL_ENABLE"
        return outcome

    if not (project / ".planfile" / "sprints" / f"{sprint}.yaml").is_file():
        outcome.skipped_reason = f"no planfile sprint {sprint}"
        return outcome

    try:
        limit = max_units if max_units is not None else int(
            os.environ.get("KORU_TICKET2DSL_MAX_UNITS") or DEFAULT_MAX_UNITS
        )
    except ValueError:
        limit = DEFAULT_MAX_UNITS

    try:
        units, filtered = build_work_units(
            project,
            sprint=sprint,
            max_units=max(1, limit),
            only_todo2code=only_todo2code,
        )
    except Exception as exc:  # noqa: BLE001
        outcome.error = f"ticket2dsl failed: {exc}"
        return outcome

    outcome.ran = True
    outcome.units_count = len(units)
    outcome.filtered_out_count = filtered
    outcome.ticket_ids = [str(u.get("ticketId")) for u in units]

    if not units:
        outcome.skipped_reason = "no useful open tickets with implementable paths"
        return outcome

    out_dir = project / DEFAULT_OUT_REL
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "schemaVersion": "koru.ticket-work-unit-set/v1",
            "generatedAt": generated_at,
            "project": str(project),
            "sprint": sprint,
            "source": DEFAULT_SOURCE,
            "units": units,
            "counts": {
                "units": len(units),
                "filteredOut": filtered,
            },
        }
        json_path = out_dir / "work-units.json"
        dsl_path = out_dir / "work-units.planfile.dsl"
        intent_path = out_dir / "work-units.intent.jsonl"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        dsl_path.write_text(_render_planfile_dsl(units), encoding="utf-8")
        intent_path.write_text(_render_intent_jsonl(units, project=project), encoding="utf-8")
        outcome.json_path = str(json_path)
        outcome.dsl_path = str(dsl_path)
        outcome.intent_path = str(intent_path)
    except OSError as exc:
        outcome.error = f"failed to write ticket2dsl artifacts: {exc}"
        return outcome

    return outcome


def format_ticket2dsl_summary(outcome: Ticket2dslOutcome) -> str:
    if outcome.skipped_reason and not outcome.units_count:
        return f"ticket2dsl skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"ticket2dsl error: {outcome.error}"
    pieces = [
        f"units={outcome.units_count}",
        f"filtered={outcome.filtered_out_count}",
    ]
    if outcome.json_path:
        pieces.append(f"json={outcome.json_path}")
    return "ticket2dsl: " + " ".join(pieces)


__all__ = [
    "Ticket2dslOutcome",
    "build_work_units",
    "format_ticket2dsl_summary",
    "run_ticket2dsl",
    "ticket2dsl_enabled",
]
