from __future__ import annotations

from pathlib import Path
from typing import Any


class RegistryService:
    def __init__(self, root: Path | str, project_id: str | None = None, probe_desktop: bool | None = None, mqtt: bool | None = None):
        self.root = Path(root)
        self.project_id = project_id or self.root.name
        self.probe_desktop = probe_desktop

    def to_dict(self, refresh: bool = False) -> dict[str, Any]:
        return {"commands": [], "examples": []}

    def render(self, fmt: str = "json", refresh: bool = False) -> str:
        return "{}"

    def refresh(self, write: bool = False, publish_mqtt: bool = False, output_format: str | None = None, **_kwargs) -> Any:
        from types import SimpleNamespace

        class IR:
            example_id = None
            commands = [SimpleNamespace(name="nlp2oql_run")]
            capabilities = ["browser_automation"]

        return IR()

    def registry_path(self) -> Path | None:
        return None

    def desktop_payload(self) -> dict | None:
        return {}

    # Additional helpers expected by koru bridge tools
    def commands_payload(self, refresh: bool = False) -> list[dict[str, Any]]:
        return []

    def uris_payload(self, refresh: bool = False) -> dict[str, Any]:
        return {"uris": [], "project_id": self.project_id}

    def mqtt_status(self) -> dict[str, Any]:
        return {"enabled": False}
