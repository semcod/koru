"""Load/save ``.koru/config.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from koru.configurator.schema import CONFIG_REL_PATH


def _config_path(project: Path) -> Path:
    return project.resolve() / CONFIG_REL_PATH


def load_project_config(project: Path) -> dict[str, Any]:
    path = _config_path(project)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_project_config(project: Path, config: dict[str, Any]) -> Path:
    path = _config_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
