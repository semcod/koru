"""Minimal public env2llm service-factory contract used by Koru tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from .registry_service import RegistryService


@dataclass(frozen=True)
class ServiceFactoryRequest:
    project_dir: str | Path
    project_id: str | None = None
    probe_desktop: bool | None = None
    merge_existing: bool = True
    mqtt: bool | None = None
    kind: str = "registry"


@dataclass(frozen=True)
class _ServiceDescriptor:
    project_dir: str
    project_id: str
    mqtt: bool | None

    def to_dict(self) -> dict:
        return {
            "schema": "env2llm.service-descriptor.v1",
            "kind": "registry",
            "project_dir": self.project_dir,
            "project_id": self.project_id,
            "capabilities": ["commands", "desktop", "registry", "uris"],
            "mqtt_requested": self.mqtt,
            "mqtt_connected": False,
            "request_hash": "0" * 64,
            "descriptor_hash": "1" * 64,
        }


class RegistryServiceFactory:
    def create(self, request: ServiceFactoryRequest) -> SimpleNamespace:
        root = str(Path(request.project_dir).resolve())
        project_id = request.project_id or Path(root).name
        service = RegistryService(
            root,
            project_id=project_id,
            probe_desktop=request.probe_desktop,
            mqtt=request.mqtt,
        )
        return SimpleNamespace(
            service=service,
            descriptor=_ServiceDescriptor(root, project_id, request.mqtt),
        )
