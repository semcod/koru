"""Ticket record builders used by natural-language task intake."""

from typing import Any


def _title_from_text(text: str) -> str:
    first = " ".join(text.split())
    return first[:117] + "..." if len(first) > 120 else first


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
