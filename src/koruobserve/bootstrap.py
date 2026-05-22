"""Prepare config + mesh key before launching observation processes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.configurator import (
    CONFIG_REL_PATH,
    configure_project,
    load_project_config,
    migrate_project_config,
    toggle_feature_sections,
)
from korumesh.keys import write_mesh_key


def _config_has_v2_sections(config: dict[str, Any]) -> bool:
    return all(key in config for key in ("vision", "mesh"))


def ensure_observe_config(project: Path) -> dict[str, Any]:
    """Make sure ``.koru/config.json`` exists, is v2, and vision+mesh are enabled."""
    project = project.expanduser().resolve()
    config_path = project / CONFIG_REL_PATH
    if not config_path.is_file():
        configure_project(project=project, interactive=False)
    saved = load_project_config(project)
    if not _config_has_v2_sections(saved):
        migrate_project_config(project)
    toggle_feature_sections(project, enable=("vision", "mesh"))
    return load_project_config(project)


def ensure_mesh_key(project: Path, config: dict[str, Any]) -> Path:
    mesh = config.get("mesh") if isinstance(config.get("mesh"), dict) else {}
    psk_path = project / str(mesh.get("psk_path") or ".koru/keys/mesh.hmac")
    return write_mesh_key(psk_path, force=False)
