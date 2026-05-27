"""Planfile YAML IO helpers for task intake."""

from pathlib import Path
from typing import Any

import yaml


def _read_config(path: Path, *, project_name: str) -> dict[str, Any]:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            data.setdefault("project", project_name)
            data.setdefault("prefix", "PLF")
            data.setdefault("next_id", 1)
            return data
    return {"project": project_name, "prefix": "PLF", "next_id": 1}


def _read_sprint(path: Path, *, sprint: str) -> dict[str, Any]:
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
        }
    }


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
