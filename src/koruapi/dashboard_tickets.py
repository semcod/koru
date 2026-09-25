"""Ticket helpers for the koru dashboard HTTP API."""

from __future__ import annotations

import importlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple, cast

from koruide.ide import normalize_ide_id

from koru.queue.locking import ticket_claim_command_missing
from koru.queue.runners import run_process
from koru.queue.ticket import planfile_command

yaml = cast(Any, importlib.import_module("yaml"))


def run_planfile(command: Sequence[str], project: Path) -> Any:
    return run_process(list(command), project)


@dataclass(frozen=True)
class DashboardTicketQueries:
    """Read-only dashboard ticket queries."""

    def list_tickets(self, project: Path) -> list[dict[str, Any]]:
        result = planfile_command(project, ["ticket", "list", "--format", "json"], runner=run_planfile)
        if result.returncode != 0:
            return []
        try:
            payload = json.loads((result.stdout or "").strip() or "[]")
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return [payload] if isinstance(payload, dict) else []

    def waiting_input_ticket_ids(self, project: Path) -> set[str]:
        tickets = self.list_tickets(project)
        return {
            str(t.get("id"))
            for t in tickets
            if isinstance(t, dict)
            and (
                str(t.get("status") or "") == "waiting_input"
                or (
                    str(t.get("status") or "") == "open"
                    and str((t.get("executor") or {}).get("kind") or "human").strip().lower() in {"", "human"}
                )
            )
        }


@dataclass(frozen=True)
class DashboardTicketCommands:
    """Mutating dashboard ticket commands."""

    queries: DashboardTicketQueries = DashboardTicketQueries()

    def bulk_waiting_input_action(
        self,
        project: Path,
        *,
        ticket_ids: list[str],
        action: str,
        reason: str,
    ) -> dict[str, Any]:
        waiting = self.queries.waiting_input_ticket_ids(project)
        selected = [tid for tid in ticket_ids if tid in waiting]
        if not selected:
            return {"ok": False, "error": "no waiting_input tickets selected", "applied": []}

        applied: list[dict[str, Any]] = []
        for tid in selected:
            if action == "delegate":
                del_res = self.delegate_ticket_from_dashboard(
                    project,
                    ticket_id=tid,
                    executor_kind="llm",
                    notes=reason or "Bulk delegated to Koru from dashboard",
                )
                applied.append(
                    {
                        "id": tid,
                        "ok": del_res.get("ok", False),
                        "action": "delegate",
                    }
                )
                continue

            if action == "approve":
                claim = planfile_command(
                    project,
                    ["ticket", "claim", tid, "--assigned-to", "koru-web"],
                    runner=run_planfile,
                )
                if claim.returncode != 0:
                    if not ticket_claim_command_missing(claim):
                        applied.append({"id": tid, "ok": False, "step": "claim", "stderr": claim.stderr[-500:]})
                        continue
                start = planfile_command(project, ["ticket", "start", tid], runner=run_planfile)
                if start.returncode != 0:
                    applied.append({"id": tid, "ok": False, "step": "start", "stderr": start.stderr[-500:]})
                    continue
                done = planfile_command(project, ["ticket", "done", tid], runner=run_planfile)
                applied.append(
                    {
                        "id": tid,
                        "ok": done.returncode == 0,
                        "action": "approve",
                        "stderr": done.stderr[-500:],
                    },
                )
                continue

            block = planfile_command(
                project,
                ["ticket", "block", tid, "--reason", reason or "Rejected in koru web dashboard"],
                runner=run_planfile,
            )
            applied.append(
                {
                    "id": tid,
                    "ok": block.returncode == 0,
                    "action": "reject",
                    "stderr": block.stderr[-500:],
                },
            )

        return {"ok": True, "action": action, "requested": ticket_ids, "applied": applied}

    def create_ticket_from_dashboard(self, project: Path, body: dict[str, Any]) -> dict[str, Any]:
        return create_ticket_from_dashboard(project, body)

    def update_ticket_from_dashboard(
        self,
        project: Path,
        *,
        ticket_id: str,
        priority: str | None = None,
        queue_name: str | None = None,
    ) -> dict[str, Any]:
        return update_ticket_from_dashboard(
            project,
            ticket_id=ticket_id,
            priority=priority,
            queue_name=queue_name,
        )

    def reorder_ticket_from_dashboard(
        self,
        project: Path,
        *,
        ticket_id: str,
        direction: str,
    ) -> dict[str, Any]:
        return reorder_ticket_from_dashboard(
            project,
            ticket_id=ticket_id,
            direction=direction,
        )

    def delegate_ticket_from_dashboard(
        self,
        project: Path,
        *,
        ticket_id: str,
        executor_kind: str = "llm",
        executor_mode: str = "automatic",
        prompt_addition: str | None = None,
        notes: str | None = None,
        priority: str | None = None,
        queue_name: str | None = None,
    ) -> dict[str, Any]:
        return delegate_ticket_from_dashboard(
            project,
            ticket_id=ticket_id,
            executor_kind=executor_kind,
            executor_mode=executor_mode,
            prompt_addition=prompt_addition,
            notes=notes,
            priority=priority,
            queue_name=queue_name,
        )


_QUERY_HANDLERS = DashboardTicketQueries()
_COMMAND_HANDLERS = DashboardTicketCommands(queries=_QUERY_HANDLERS)


def list_tickets(project: Path) -> list[dict[str, Any]]:
    """Return all planfile tickets as JSON list (empty on errors)."""
    return _QUERY_HANDLERS.list_tickets(project)


def bulk_waiting_input_action(
    project: Path,
    *,
    ticket_ids: list[str],
    action: str,
    reason: str,
) -> dict[str, Any]:
    return _COMMAND_HANDLERS.bulk_waiting_input_action(
        project,
        ticket_ids=ticket_ids,
        action=action,
        reason=reason,
    )


def _build_ticket_scaffold(body: dict[str, Any], ide: str, executor_kind: str) -> dict[str, Any]:
    source_context: dict[str, Any] = {"ide": ide}
    dedupe_key = str(body.get("dedupe_key") or "").strip()
    if dedupe_key:
        source_context["dedupe_key"] = dedupe_key
    signal = str(body.get("signal") or "").strip()
    if signal:
        source_context["signal"] = signal

    scaffold: dict[str, Any] = {
        "executor_kind": executor_kind,
        "executor_mode": "interactive",
        "labels": ["koru", "dashboard", "llm-ready"],
        "source_context": source_context,
        "source_tool": "koru-dashboard",
    }
    title = str(body.get("title") or "").strip() or None
    if title:
        scaffold["title"] = title
    return scaffold


def create_ticket_from_dashboard(project: Path, body: dict[str, Any]) -> dict[str, Any]:
    description = str(body.get("description") or "").strip()
    if not description:
        raise ValueError("description is required")
    priority = str(body.get("priority") or "normal").strip()
    executor_kind = str(body.get("executor_kind") or "human").strip()
    queue_name = str(body.get("queue_name") or "default").strip()
    ide = normalize_ide_id(str(body.get("ide") or "auto").strip() or "auto")

    from koru.tasks import create_nl_task

    scaffold = _build_ticket_scaffold(body, ide, executor_kind)
    created = create_nl_task(
        project,
        description,
        queue_name=queue_name,
        priority=priority,
        scaffold=scaffold,
    )
    return {
        "ok": True,
        "ticket_id": created.ticket_id,
        "name": created.name,
        "sprint": created.sprint,
        "path": str(created.path),
        "project": str(project),
        "ide": ide,
        "reused": bool(created.reused),
    }


def _load_sprint_file(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _write_sprint_file(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


class _SprintTicketHit(NamedTuple):
    """A ticket located in one sprint file, with its containing documents."""

    path: Path
    data: dict[str, Any]
    tickets: dict[str, Any]
    ticket: dict[str, Any]


def _find_ticket_in_sprints(project: Path, ticket_id: str) -> _SprintTicketHit:
    sprints_dir = project / ".planfile" / "sprints"
    for path in sorted(sprints_dir.glob("*.yaml")):
        data = _load_sprint_file(path)
        sprint_raw = data.get("sprint")
        sprint = sprint_raw if isinstance(sprint_raw, dict) else {}
        tickets_raw = sprint.get("tickets")
        tickets = tickets_raw if isinstance(tickets_raw, dict) else {}
        ticket = tickets.get(ticket_id)
        if isinstance(ticket, dict):
            return _SprintTicketHit(path, data, tickets, ticket)
    raise ValueError(f"ticket not found: {ticket_id}")


def _append_dashboard_history(ticket: dict[str, Any], action: str, message: str) -> None:
    history = ticket.setdefault("history", [])
    if isinstance(history, list):
        history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "source": "koru dashboard",
                "message": message,
            }
        )
    ticket["updated_at"] = datetime.now(UTC).isoformat()


def _mapping_slot(target: dict[str, Any], key: str) -> dict[str, Any]:
    """Return ``target[key]`` as a dict, replacing a non-dict value in place."""
    slot = target.setdefault(key, {})
    if not isinstance(slot, dict):
        slot = {}
        target[key] = slot
    return slot


def _normalize_priority(priority: str) -> str:
    normalized = priority.strip().lower()
    if normalized not in {"critical", "high", "normal", "low"}:
        raise ValueError("priority must be critical|high|normal|low")
    return normalized


def update_ticket_from_dashboard(
    project: Path,
    *,
    ticket_id: str,
    priority: str | None = None,
    queue_name: str | None = None,
) -> dict[str, Any]:
    path, data, _tickets, ticket = _find_ticket_in_sprints(project, ticket_id)
    changes: list[str] = []
    if priority is not None:
        normalized = _normalize_priority(priority)
        if ticket.get("priority") != normalized:
            ticket["priority"] = normalized
            changes.append(f"priority={normalized}")
    if queue_name is not None:
        queue = queue_name.strip() or "default"
        execution = _mapping_slot(ticket, "execution")
        if execution.get("queue") != queue:
            execution["queue"] = queue
            changes.append(f"queue={queue}")
    if changes:
        _append_dashboard_history(ticket, "dashboard_update", ", ".join(changes))
        _write_sprint_file(path, data)
    return {"ok": True, "ticket_id": ticket_id, "changed": bool(changes), "changes": changes}


def reorder_ticket_from_dashboard(
    project: Path,
    *,
    ticket_id: str,
    direction: str,
) -> dict[str, Any]:
    path, data, tickets, _ticket = _find_ticket_in_sprints(project, ticket_id)
    items = list(tickets.items())
    index = next((idx for idx, (key, _value) in enumerate(items) if key == ticket_id), -1)
    if index < 0:
        raise ValueError(f"ticket not found: {ticket_id}")
    delta = -1 if direction == "up" else 1 if direction == "down" else 0
    if delta == 0:
        raise ValueError("direction must be up|down")
    new_index = max(0, min(len(items) - 1, index + delta))
    if new_index == index:
        return {"ok": True, "ticket_id": ticket_id, "changed": False, "position": index}
    item = items.pop(index)
    items.insert(new_index, item)
    sprint = data.setdefault("sprint", {})
    sprint["tickets"] = {key: value for key, value in items}
    _append_dashboard_history(item[1], "dashboard_reorder", f"position={new_index}")
    _write_sprint_file(path, data)
    return {"ok": True, "ticket_id": ticket_id, "changed": True, "position": new_index}


def _field_update(target: dict[str, Any], key: str, value: str, label: str) -> list[str]:
    """Set ``target[key]`` to ``value`` when it differs and report ``label=value``."""
    if target.get(key) == value:
        return []
    target[key] = value
    return [f"{label}={value}"]


def _normalized_executor_value(value: str | None, default: str) -> str:
    return (value or default).strip().lower()


def _apply_executor_target(
    ticket: dict[str, Any],
    executor_kind: str | None,
    executor_mode: str | None,
) -> list[str]:
    executor = _mapping_slot(ticket, "executor")
    kind = _normalized_executor_value(executor_kind, "llm")
    mode = _normalized_executor_value(executor_mode, "automatic")
    return [
        *_field_update(executor, "kind", kind, "executor.kind"),
        *_field_update(executor, "mode", mode, "executor.mode"),
    ]


def _apply_delegation_defaults(ticket: dict[str, Any]) -> list[str]:
    status_updates = _field_update(ticket, "status", "open", "status")
    execution = _mapping_slot(ticket, "execution")
    state_updates = _field_update(execution, "state", "ready", "execution.state")
    execution["attempt"] = 0
    return [*status_updates, *state_updates]


def _apply_prompt_addition(ticket: dict[str, Any], prompt_addition: str | None) -> list[str]:
    addition = (prompt_addition or "").strip()
    if not addition:
        return []
    inputs = _mapping_slot(ticket, "inputs")
    existing_prompt = str(inputs.get("prompt") or ticket.get("description") or ticket.get("name") or "").strip()
    inputs["prompt"] = f"{existing_prompt}\n\n[Operator Guidance]:\n{addition}" if existing_prompt else addition
    return ["prompt_updated"]


def _apply_operator_notes(ticket: dict[str, Any], notes: str | None) -> list[str]:
    text = (notes or "").strip()
    if not text:
        return []
    outputs = _mapping_slot(ticket, "outputs")
    notes_list = outputs.setdefault("notes", [])
    if not isinstance(notes_list, list):
        return []
    notes_list.append(f"Operator Delegation: {text}")
    return ["notes_appended"]


def _apply_delegation_routing(
    ticket: dict[str, Any],
    priority: str | None,
    queue_name: str | None,
) -> list[str]:
    if priority is None and queue_name is None:
        return []
    updates: list[str] = []
    if priority is not None:
        normalized = _normalize_priority(priority)
        updates += _field_update(ticket, "priority", normalized, "priority")
    if queue_name is not None:
        queue = queue_name.strip() or "default"
        execution = _mapping_slot(ticket, "execution")
        updates += _field_update(execution, "queue", queue, "queue")
    return updates


def _apply_llm_ready_label(record: dict[str, Any], executor_kind: str | None) -> list[str]:
    kind = _normalized_executor_value(executor_kind, "llm")
    if kind != "llm":
        return []
    labels = record.setdefault("labels", [])
    if not isinstance(labels, list) or "llm-ready" in labels:
        return []
    labels.append("llm-ready")
    return ["labels+=llm-ready"]


def _delegation_change_sets(
    ticket: dict[str, Any],
    *,
    executor_kind: str | None,
    executor_mode: str | None,
    prompt_addition: str | None,
    notes: str | None,
    priority: str | None,
    queue_name: str | None,
) -> list[list[str]]:
    return [
        _apply_executor_target(ticket, executor_kind, executor_mode),
        _apply_delegation_defaults(ticket),
        _apply_prompt_addition(ticket, prompt_addition),
        _apply_operator_notes(ticket, notes),
        _apply_delegation_routing(ticket, priority, queue_name),
        _apply_llm_ready_label(ticket, executor_kind),
    ]


def _delegation_result(
    ticket_id: str,
    ticket: dict[str, Any],
    changes: list[str],
) -> dict[str, Any]:
    return {
        "ok": True,
        "ticket_id": ticket_id,
        "changed": bool(changes),
        "changes": changes,
        "executor": ticket["executor"],
        "status": ticket.get("status"),
    }


def delegate_ticket_from_dashboard(
    project: Path,
    *,
    ticket_id: str,
    executor_kind: str = "llm",
    executor_mode: str = "automatic",
    prompt_addition: str | None = None,
    notes: str | None = None,
    priority: str | None = None,
    queue_name: str | None = None,
) -> dict[str, Any]:
    hit = _find_ticket_in_sprints(project, ticket_id)
    change_sets = _delegation_change_sets(
        hit.ticket,
        executor_kind=executor_kind,
        executor_mode=executor_mode,
        prompt_addition=prompt_addition,
        notes=notes,
        priority=priority,
        queue_name=queue_name,
    )
    changes = [item for chunk in change_sets for item in chunk]
    if changes:
        _append_dashboard_history(hit.ticket, "dashboard_delegate", ", ".join(changes))
        _write_sprint_file(hit.path, hit.data)
    return _delegation_result(ticket_id, hit.ticket, changes)
