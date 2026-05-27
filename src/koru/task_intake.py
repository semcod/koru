"""Natural-language task creation implementation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.task_dedupe import _maybe_reuse_existing_task
from koru.task_io import _read_sprint, _write_yaml, _read_config
from koru.task_models import CreatedTask
from koru.task_ticket import _build_nl_task_record, _title_from_text


@dataclass(frozen=True)
class NlTaskStorage:
    project: Path
    config_path: Path
    sprint_path: Path
    sprint_data: dict[str, Any]
    tickets: dict[str, Any]


@dataclass(frozen=True)
class NlTaskPaths:
    project: Path
    config_path: Path
    sprint_path: Path


@dataclass(frozen=True)
class NlTaskRequest:
    text: str
    scaffold: dict[str, Any]
    name: str


def _validated_task_text(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise ValueError("task text cannot be empty")
    return normalized


def _prepare_nl_task_storage(project: Path, sprint: str) -> NlTaskStorage:
    return _load_nl_task_storage(_nl_task_paths(project, sprint), sprint)


def _nl_task_paths(project: Path, sprint: str) -> NlTaskPaths:
    project = project.resolve()
    planfile_dir = project / ".planfile"
    sprints_dir = planfile_dir / "sprints"
    sprints_dir.mkdir(parents=True, exist_ok=True)
    return NlTaskPaths(project, planfile_dir / "config.yaml", sprints_dir / f"{sprint}.yaml")


def _load_nl_task_storage(paths: NlTaskPaths, sprint: str) -> NlTaskStorage:
    sprint_data = _read_sprint(paths.sprint_path, sprint=sprint)
    tickets = sprint_data["sprint"].setdefault("tickets", {})
    return NlTaskStorage(
        paths.project,
        paths.config_path,
        paths.sprint_path,
        sprint_data,
        tickets,
    )


def _prepare_nl_task_request(text: str, scaffold: dict[str, Any] | None) -> NlTaskRequest:
    text = _validated_task_text(text)
    scaffold = scaffold or {}
    name = str(scaffold.get("title") or "").strip() or _title_from_text(text)
    return NlTaskRequest(text=text, scaffold=scaffold, name=name)


def _log_nl_task_creation(
    ticket_id: str,
    name: str,
    text: str,
    queue_name: str | None,
    executor_kind: str,
) -> None:
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
    return _create_or_reuse_nl_task(
        storage=_prepare_nl_task_storage(project, sprint),
        request=_prepare_nl_task_request(text, scaffold),
        sprint=sprint,
        queue_name=queue_name,
        priority=priority,
    )


def _create_or_reuse_nl_task(
    *,
    storage: NlTaskStorage,
    request: NlTaskRequest,
    sprint: str,
    queue_name: str | None,
    priority: str,
) -> CreatedTask:
    existing, scaffold = _maybe_reuse_existing_task(
        storage.tickets,
        request.scaffold,
        request.name,
        sprint,
        storage.sprint_path,
    )
    if existing is not None:
        return existing
    return _create_new_nl_task(
        storage=storage,
        request=NlTaskRequest(request.text, scaffold, request.name),
        sprint=sprint,
        queue_name=queue_name,
        priority=priority,
    )


def _create_new_nl_task(
    *,
    storage: NlTaskStorage,
    request: NlTaskRequest,
    sprint: str,
    queue_name: str | None,
    priority: str,
) -> CreatedTask:
    ticket_id = _next_nl_task_id(storage)
    ticket, executor_kind = _new_nl_ticket(ticket_id, request, sprint, queue_name, priority)
    return _persist_new_nl_task(
        storage,
        request,
        sprint,
        queue_name,
        ticket_id,
        ticket,
        executor_kind,
    )


def _next_nl_task_id(storage: NlTaskStorage) -> str:
    ticket_id, _config = _generate_ticket_id(storage.config_path, storage.project.name)
    return ticket_id


def _new_nl_ticket(
    ticket_id: str,
    request: NlTaskRequest,
    sprint: str,
    queue_name: str | None,
    priority: str,
) -> tuple[dict[str, Any], str]:
    now = datetime.now(UTC).isoformat()
    return _build_nl_task_record(
        ticket_id=ticket_id,
        name=request.name,
        text=request.text,
        priority=priority,
        sprint=sprint,
        queue_name=queue_name,
        scaffold=request.scaffold,
        now=now,
    )


def _persist_new_nl_task(
    storage: NlTaskStorage,
    request: NlTaskRequest,
    sprint: str,
    queue_name: str | None,
    ticket_id: str,
    ticket: dict[str, Any],
    executor_kind: str,
) -> CreatedTask:
    storage.tickets[ticket_id] = ticket
    _write_yaml(storage.sprint_path, storage.sprint_data)
    _log_nl_task_creation(ticket_id, request.name, request.text, queue_name, executor_kind)
    return CreatedTask(
        ticket_id=ticket_id,
        sprint=sprint,
        path=storage.sprint_path,
        name=request.name,
    )


def _generate_ticket_id(config_path: Path, project_name: str) -> tuple[str, dict[str, Any]]:
    """Generate a new ticket ID and update config."""
    config = _read_config(config_path, project_name=project_name)
    prefix = str(config.get("prefix") or "PLF")
    next_id = int(config.get("next_id") or 1)
    ticket_id = f"{prefix}-{next_id:03d}"
    config["next_id"] = next_id + 1
    _write_yaml(config_path, config)
    return ticket_id, config
