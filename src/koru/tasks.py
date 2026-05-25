"""Natural-language task intake for koru."""


import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CreatedTask:
    ticket_id: str
    sprint: str
    path: Path
    name: str
    reused: bool = False


def _validated_task_text(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise ValueError("task text cannot be empty")
    return normalized


def _prepare_nl_task_storage(
    project: Path,
    sprint: str,
) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
    project = project.resolve()
    planfile_dir = project / ".planfile"
    sprints_dir = planfile_dir / "sprints"
    config_path = planfile_dir / "config.yaml"
    sprint_path = sprints_dir / f"{sprint}.yaml"

    sprints_dir.mkdir(parents=True, exist_ok=True)
    sprint_data = _read_sprint(sprint_path, sprint=sprint)
    tickets = sprint_data["sprint"].setdefault("tickets", {})
    return project, config_path, sprint_path, sprint_data, tickets


def _resolve_nl_task_name(text: str, scaffold: dict[str, Any]) -> str:
    scaffold_title = str(scaffold.get("title") or "").strip()
    return scaffold_title or _title_from_text(text)


def _log_nl_task_creation(ticket_id: str, name: str, text: str, queue_name: str | None, executor_kind: str) -> None:
    try:
        from koru.activity_log import activity

        activity(
            "TICKET",
            f"utworzono {ticket_id} ({name}) kolejka={queue_name or 'default'} "
            f"executor={executor_kind}",
            preview=text,
        )
    except Exception:
        pass


def _build_nl_task_record(
    *,
    ticket_id: str,
    name: str,
    text: str,
    priority: str,
    sprint: str,
    queue_name: str | None,
    scaffold: dict[str, Any],
    now: str,
) -> tuple[dict[str, Any], str]:
    labels = _build_ticket_labels(scaffold)
    source = _build_ticket_source(scaffold, text, now)
    inputs = _build_ticket_inputs(scaffold, text)

    executor_kind = str(scaffold.get("executor_kind") or "human")
    executor_mode = str(scaffold.get("executor_mode") or "interactive")
    files = [str(v) for v in (scaffold.get("files") or []) if str(v).strip()]
    ticket = _build_ticket_dict(
        ticket_id,
        name,
        text,
        priority,
        sprint,
        queue_name,
        labels,
        source,
        inputs,
        executor_kind,
        executor_mode,
        files,
        now,
    )
    return ticket, executor_kind


def _create_nl_task_impl(
    project: Path,
    text: str,
    *,
    sprint: str = "current",
    queue_name: str | None = None,
    priority: str = "normal",
    scaffold: dict[str, Any] | None = None,
) -> CreatedTask:
    """Create a planfile ticket from a normal-language sentence."""
    text = _validated_task_text(text)
    project, config_path, sprint_path, sprint_data, tickets = _prepare_nl_task_storage(
        project, sprint
    )
    now = datetime.now(UTC).isoformat()
    scaffold = scaffold or {}
    name = _resolve_nl_task_name(text, scaffold)

    existing, scaffold = _maybe_reuse_existing_task(tickets, scaffold, name, sprint, sprint_path)
    if existing is not None:
        return existing

    ticket_id, _config = _generate_ticket_id(config_path, project.name)

    ticket, executor_kind = _build_nl_task_record(
        ticket_id=ticket_id,
        name=name,
        text=text,
        priority=priority,
        sprint=sprint,
        queue_name=queue_name,
        scaffold=scaffold,
        now=now,
    )
    tickets[ticket_id] = ticket
    _write_yaml(sprint_path, sprint_data)
    _log_nl_task_creation(ticket_id, name, text, queue_name, executor_kind)
    return CreatedTask(ticket_id=ticket_id, sprint=sprint, path=sprint_path, name=name)


def _generate_ticket_id(config_path: Path, project_name: str) -> tuple[str, dict]:
    """Generate a new ticket ID and update config."""
    config = _read_config(config_path, project_name=project_name)
    prefix = str(config.get("prefix") or "PLF")
    next_id = int(config.get("next_id") or 1)
    ticket_id = f"{prefix}-{next_id:03d}"
    config["next_id"] = next_id + 1
    _write_yaml(config_path, config)
    return ticket_id, config


def _build_ticket_labels(scaffold: dict[str, Any]) -> list[str]:
    """Build ticket labels from scaffold."""
    labels = ["koru", "nl-task", "llm-ready"]
    labels.extend(str(v) for v in (scaffold.get("labels") or []) if str(v).strip())
    return list(dict.fromkeys(labels))


def _build_ticket_source(scaffold: dict[str, Any], text: str, now: str) -> dict[str, Any]:
    """Build ticket source dict."""
    source_tool = str(scaffold.get("source_tool") or "koru-cli-nl")
    source_context: dict[str, Any] = {
        "input": text,
        **(
            scaffold.get("source_context")
            if isinstance(scaffold.get("source_context"), dict)
            else {}
        ),
    }
    return {"tool": source_tool, "timestamp": now, "context": source_context}


def _normalize_dedupe_part(value: object) -> str:
    return re.sub(r"[^a-z0-9._/-]+", "-", str(value).strip().lower()).strip("-")


def _source_context(scaffold: dict[str, Any]) -> dict[str, Any]:
    ctx = scaffold.get("source_context")
    return ctx if isinstance(ctx, dict) else {}


def _explicit_dedupe_key(scaffold: dict[str, Any]) -> str | None:
    explicit = _source_context(scaffold).get("dedupe_key")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return None


def _build_implicit_dedupe_key(scaffold: dict[str, Any], name: str) -> str | None:
    source_tool = str(scaffold.get("source_tool") or "koru-cli-nl")
    signal = _source_context(scaffold).get("signal")
    files = [str(v) for v in (scaffold.get("files") or []) if str(v).strip()]
    if source_tool == "koru-cli-nl" and not signal and not files:
        return None
    parts = [source_tool]
    if signal:
        parts.append(str(signal))
    parts.extend(files[:3])
    if not files:
        parts.append(name)
    return ":".join(_normalize_dedupe_part(part) for part in parts if str(part).strip())


def _dedupe_key_from_scaffold(scaffold: dict[str, Any], name: str) -> str | None:
    explicit = _explicit_dedupe_key(scaffold)
    if explicit is not None:
        return explicit
    return _build_implicit_dedupe_key(scaffold, name)


def _status_allows_dedupe_reuse(status: object) -> bool:
    return str(status or "").strip().lower() not in {"canceled", "cancelled", "closed"}


def _iter_ticket_entries(tickets: object) -> Any:
    if isinstance(tickets, dict):
        return tickets.items()
    if isinstance(tickets, list):
        return (
            (str(entry.get("id") or ""), entry)
            for entry in tickets
            if isinstance(entry, dict)
        )
    return iter([])


def _ticket_dedupe_key(ticket: dict[str, Any]) -> str | None:
    source = ticket.get("source")
    context = source.get("context") if isinstance(source, dict) else None
    return context.get("dedupe_key") if isinstance(context, dict) else None


def _find_existing_task_by_dedupe_key(
    tickets: object,
    *,
    dedupe_key: str,
    sprint: str,
    path: Path,
) -> CreatedTask | None:
    for ticket_id, ticket in _iter_ticket_entries(tickets):
        if not isinstance(ticket, dict) or not _status_allows_dedupe_reuse(ticket.get("status")):
            continue
        if _ticket_dedupe_key(ticket) != dedupe_key:
            continue
        return CreatedTask(
            ticket_id=str(ticket.get("id") or ticket_id),
            sprint=sprint,
            path=path,
            name=str(ticket.get("name") or ticket.get("title") or ticket_id),
            reused=True,
        )
    return None


def _build_ticket_inputs(scaffold: dict[str, Any], text: str) -> dict[str, Any]:
    """Build ticket inputs dict."""
    prompt_suffix = str(scaffold.get("prompt_suffix") or "").strip()
    full_prompt = text if not prompt_suffix else f"{text}\n\n{prompt_suffix}"
    inputs_extra = scaffold.get("inputs") if isinstance(scaffold.get("inputs"), dict) else {}
    return {
        "prompt": full_prompt,
        "env_keys": [],
        "api_method": "GET",
        "api_headers": {},
        "api_timeout_seconds": 30.0,
        **inputs_extra,
    }


def _build_ticket_dict(
    ticket_id: str,
    name: str,
    text: str,
    priority: str,
    sprint: str,
    queue_name: str | None,
    labels: list[str],
    source: dict[str, Any],
    inputs: dict[str, Any],
    executor_kind: str,
    executor_mode: str,
    files: list[str],
    now: str,
) -> dict[str, Any]:
    """Build the complete ticket dictionary."""
    return {
        "id": ticket_id,
        "name": name,
        "status": "open",
        "priority": priority,
        "sprint": sprint,
        "source": source,
        "description": text,
        "labels": labels,
        "blocked_by": [],
        "blocks": [],
        "files": files,
        "executor": {"kind": executor_kind, "mode": executor_mode},
        "execution": {
            "queue": queue_name or "default",
            "state": "ready",
            "attempt": 0,
            "max_attempts": 1,
        },
        "inputs": inputs,
        "outputs": {"artifacts": [], "notes": []},
        "sync": {},
        "history": [
            {
                "timestamp": now,
                "action": "created",
                "source": "koru task",
                "message": text,
            },
        ],
        "created_at": now,
        "updated_at": now,
    }


def _maybe_reuse_existing_task(
    tickets: object,
    scaffold: dict[str, Any],
    name: str,
    sprint: str,
    path: Path,
) -> tuple[CreatedTask | None, dict[str, Any]]:
    dedupe_key = _dedupe_key_from_scaffold(scaffold, name)
    if not dedupe_key:
        return None, scaffold
    existing = _find_existing_task_by_dedupe_key(
        tickets,
        dedupe_key=dedupe_key,
        sprint=sprint,
        path=path,
    )
    if existing is not None:
        return existing, scaffold
    source_context = dict(scaffold.get("source_context")) if isinstance(scaffold.get("source_context"), dict) else {}
    source_context["dedupe_key"] = dedupe_key
    return None, {**scaffold, "source_context": source_context}


def create_nl_task(
    project: Path,
    text: str,
    *,
    sprint: str = "current",
    queue_name: str | None = None,
    priority: str = "normal",
    scaffold: dict[str, Any] | None = None,
) -> CreatedTask:
    """Create a planfile ticket from a normal-language sentence."""
    from koru.bounded_contexts.tasks.application import TaskCommandService
    from koru.bounded_contexts.tasks.commands import CreateNlTaskCommand
    from koru.cqrs import runtime_for_project

    return TaskCommandService(runtime=runtime_for_project(project)).create_nl_task(
        CreateNlTaskCommand(
            project=project,
            text=text,
            sprint=sprint,
            queue_name=queue_name,
            priority=priority,
            scaffold=scaffold,
        )
    )


def _title_from_text(text: str) -> str:
    first = " ".join(text.split())
    return first[:117] + "..." if len(first) > 120 else first


def _read_config(path: Path, *, project_name: str) -> dict:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            data.setdefault("project", project_name)
            data.setdefault("prefix", "PLF")
            data.setdefault("next_id", 1)
            return data
    return {"project": project_name, "prefix": "PLF", "next_id": 1}


def _read_sprint(path: Path, *, sprint: str) -> dict:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            data.setdefault("sprint", {})
            data["sprint"].setdefault("id", sprint)
            data["sprint"].setdefault("name", sprint.title())
            data["sprint"].setdefault("status", "active")
            data["sprint"].setdefault("tickets", {})
            return data
    return {
        "sprint": {
            "id": sprint,
            "name": sprint.title(),
            "status": "active",
            "tickets": {},
        },
    }


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
