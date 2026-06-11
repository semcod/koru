from __future__ import annotations

from pathlib import Path
from typing import Any

from env2llm.service.registry_service import RegistryService


def build_registry_service(root: Path | str, *, project_id: str | None = None, probe_desktop: bool | None = None, mqtt: bool | None = None) -> RegistryService:
    return RegistryService(root, project_id=project_id, probe_desktop=probe_desktop, mqtt=mqtt)
