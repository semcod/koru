"""Metadata + writer for koru runtime ``.env`` variables.

The dashboard ``Environment`` tab uses :data:`KORU_ENV_KEYS` to render
an editor for the well-known ``KORU_*`` runtime knobs and writes them
back via :func:`write_dotenv` (which preserves comments and the order
of existing lines in ``<project>/.env``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from koru.bounded_contexts.env_config.commands import (
    ApplyEnvUpdatesCommand,
    WriteEnvConfigCommand,
)
from koru.bounded_contexts.env_config.queries import LoadEnvConfigQuery
from koru.domain.env import (
    ENV_FILENAME,
    EnvKey,
    KORU_ENV_KEYS,
    _build_env_payload,
    _format_env_value,
    _write_env_file,
    env_path,
)


def env_config_payload(project: Path) -> dict[str, Any]:
    """Return current ``.env`` + ``os.environ`` snapshot for known koru keys."""
    from koru.bounded_contexts.env_config.application import EnvConfigQueryService
    return EnvConfigQueryService().load(LoadEnvConfigQuery(project=project, environ=os.environ))


def write_env_config(project: Path, updates: dict[str, str]) -> Path:
    """Merge ``updates`` into ``<project>/.env`` preserving comments and order."""
    from koru.bounded_contexts.env_config.application import EnvConfigCommandService
    from koru.cqrs import runtime_for_project

    return EnvConfigCommandService(runtime=runtime_for_project(project)).write(
        WriteEnvConfigCommand(project=project, updates=updates),
    )


def apply_env_updates(updates: dict[str, str]) -> None:
    """Push updated values into ``os.environ`` (skips empty strings to allow unset)."""
    from koru.bounded_contexts.env_config.application import EnvConfigCommandService
    from koru.cqrs import runtime_for_project

    EnvConfigCommandService(runtime=runtime_for_project(Path.cwd())).apply_updates(
        ApplyEnvUpdatesCommand(project=Path.cwd(), updates=updates, environ=os.environ),
    )


__all__ = [
    "ENV_FILENAME",
    "EnvKey",
    "KORU_ENV_KEYS",
    "apply_env_updates",
    "env_config_payload",
    "env_path",
    "write_env_config",
]
