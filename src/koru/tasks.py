"""Natural-language task intake for koru."""

from __future__ import annotations

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
    text = text.strip()
    if not text:
        raise ValueError("task text cannot be empty")

    project = project.resolve()
    planfile_dir = project / ".planfile"
    sprints_dir = planfile_dir / "sprints"
    config_path = planfile_dir / "config.yaml"
    sprint_path = sprints_dir / f"{sprint}.yaml"

    sprints_dir.mkdir(parents=True, exist_ok=True)
    ticket_id, _config = _generate_ticket_id(config_path, project.name)

    sprint_data = _read_sprint(sprint_path, sprint=sprint)
    tickets = sprint_data["sprint"].setdefault("tickets", {})
    now = datetime.now(UTC).isoformat()
    scaffold = scaffold or {}
    scaffold_title = str(scaffold.get("title") or "").strip()
    name = scaffold_title or _title_from_text(text)

    labels = _build_ticket_labels(scaffold)
    source = _build_ticket_source(scaffold, text, now)
    inputs = _build_ticket_inputs(scaffold, text)

    executor_kind = str(scaffold.get("executor_kind") or "human")
    executor_mode = str(scaffold.get("executor_mode") or "interactive")
    files = [str(v) for v in (scaffold.get("files") or []) if str(v).strip()]

    tickets[ticket_id] = _build_ticket_dict(
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
    _write_yaml(sprint_path, sprint_data)
    try:
        from .activity_log import activity

        activity(
            "TICKET",
            f"utworzono {ticket_id} ({name}) kolejka={queue_name or 'default'} "
            f"executor={executor_kind}",
            preview=text,
        )
    except Exception:
        pass
    return CreatedTask(ticket_id=ticket_id, sprint=sprint, path=sprint_path, name=name)


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
