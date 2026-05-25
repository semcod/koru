"""Deployment event data models and serialization helpers."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from koru.deployment_events.enums import DeploymentEventType, EventSource, Severity


@dataclass
class Component:
    """Component being deployed or affected."""

    name: str
    version: str = ""
    type: str = ""  # e.g., "plugin", "service", "config", "dependency"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DeploymentEvent:
    """Deployment event payload."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    event_type: DeploymentEventType = DeploymentEventType.UNKNOWN
    source: EventSource = EventSource.UNKNOWN
    severity: Severity = Severity.INFO

    correlation_id: str = ""
    session_id: str = ""

    # Component information
    component: Component | None = None
    environment: str = ""  # e.g., "production", "staging", "development"
    deployment_target: str = ""  # e.g., hostname, container, service name

    # Event details
    message: str = ""
    details: dict[str, str] = field(default_factory=dict)

    # Performance metrics
    duration_ms: int = 0
    metrics: dict[str, float] = field(default_factory=dict)

    # Error information
    error_code: str = ""
    error_message: str = ""
    stack_trace: list[str] = field(default_factory=list)

    # Plugin-specific fields
    plugin_ide: str = ""  # IDE type (vscode, cursor, windsurf, jetbrains)
    plugin_version: str = ""
    plugin_connected: bool = False

    # Koru package information
    koru_version: str = ""
    koru_source_root: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result: dict[str, Any] = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "source": self.source.value,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "environment": self.environment,
            "deployment_target": self.deployment_target,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "plugin_ide": self.plugin_ide,
            "plugin_version": self.plugin_version,
            "plugin_connected": self.plugin_connected,
            "koru_version": self.koru_version,
            "koru_source_root": self.koru_source_root,
        }
        if self.component:
            result["component"] = {
                "name": self.component.name,
                "version": self.component.version,
                "type": self.component.type,
                "metadata": self.component.metadata,
            }
        return result

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def _component_dsl_message_parts(self) -> list[str]:
        if self.component is None:
            return []
        if self.component.type == "plugin":
            parts = [f"Plugin {self.component.name}"]
            if self.component.version:
                parts.append(f"v{self.component.version}")
            if self.plugin_ide:
                parts.append(f"for {self.plugin_ide}")
            return parts
        if self.component.type == "service":
            parts = [f"Service {self.component.name}"]
            if self.deployment_target:
                parts.append(f"on {self.deployment_target}")
            return parts
        parts = [f"{self.component.type.capitalize()} {self.component.name}"]
        if self.component.version:
            parts.append(f"v{self.component.version}")
        return parts

    def to_dsl(self) -> str:
        """Convert event to shortened DSL format for logs."""
        parts = [
            self.event_type.value,
            self.source.value,
            self.severity.value,
        ]
        prefix = ":".join(parts)

        message_parts = []
        if self.message:
            message_parts.append(self.message)
        else:
            message_parts.extend(self._component_dsl_message_parts())

        if self.error_code:
            message_parts.append(f"[{self.error_code}]")
        if self.error_message:
            message_parts.append(f"error: {self.error_message}")

        if self.duration_ms > 0:
            message_parts.append(f"({self.duration_ms}ms)")

        message = " ".join(message_parts) if message_parts else "No message"
        return f"{prefix} -> {message}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeploymentEvent:
        """Create event from dictionary."""
        component_data = data.get("component")
        component = Component(**component_data) if component_data else None

        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            event_type=DeploymentEventType(
                data.get("event_type", DeploymentEventType.UNKNOWN.value)
            ),
            source=EventSource(data.get("source", EventSource.UNKNOWN.value)),
            severity=Severity(data.get("severity", Severity.INFO.value)),
            correlation_id=data.get("correlation_id", ""),
            session_id=data.get("session_id", ""),
            component=component,
            environment=data.get("environment", ""),
            deployment_target=data.get("deployment_target", ""),
            message=data.get("message", ""),
            details=data.get("details", {}),
            duration_ms=data.get("duration_ms", 0),
            metrics=data.get("metrics", {}),
            error_code=data.get("error_code", ""),
            error_message=data.get("error_message", ""),
            stack_trace=data.get("stack_trace", []),
            plugin_ide=data.get("plugin_ide", ""),
            plugin_version=data.get("plugin_version", ""),
            plugin_connected=data.get("plugin_connected", False),
            koru_version=data.get("koru_version", ""),
            koru_source_root=data.get("koru_source_root", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> DeploymentEvent:
        """Create event from JSON string."""
        return cls.from_dict(json.loads(json_str))


__all__ = [
    "Component",
    "DeploymentEvent",
]