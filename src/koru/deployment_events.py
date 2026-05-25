"""Deployment event system for tracking deployment and self-deployment operations.

This module provides:
- Protobuf-based event schema for structured event tracking
- DSL format for shortened log output
- Event emitter/writer for deployment events
- Reflection/analysis capabilities for event history
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# For now, we'll use dataclasses instead of generated protobuf code
# to avoid adding protobuf dependency immediately
# This can be migrated to generated protobuf code later


class DeploymentEventType(str, Enum):
    """Deployment event types for tracking deployment and self-deployment operations."""

    UNKNOWN = "unknown"

    # Deployment lifecycle events
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    DEPLOYMENT_ROLLED_BACK = "deployment.rolled_back"
    DEPLOYMENT_CANCELLED = "deployment.cancelled"

    # Self-deployment events
    SELF_DEPLOYMENT_INITIATED = "self_deployment.initiated"
    SELF_DEPLOYMENT_APPLIED = "self_deployment.applied"
    SELF_DEPLOYMENT_REJECTED = "self_deployment.rejected"
    SELF_DEPLOYMENT_VALIDATED = "self_deployment.validated"

    # Plugin events
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"
    PLUGIN_UPGRADED = "plugin.upgraded"
    PLUGIN_VERSION_MISMATCH = "plugin.version_mismatch"
    PLUGIN_CONNECTED = "plugin.connected"
    PLUGIN_DISCONNECTED = "plugin.disconnected"

    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_VALIDATED = "config.validated"
    CONFIG_RELOADED = "config.reloaded"

    # Service events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_RESTARTED = "service.restarted"
    SERVICE_HEALTH_CHECK = "service.health_check"

    # Dependency events
    DEPENDENCY_INSTALLED = "dependency.installed"
    DEPENDENCY_REMOVED = "dependency.removed"
    DEPENDENCY_UPDATED = "dependency.updated"


class EventSource(str, Enum):
    """Source of the deployment event."""

    UNKNOWN = "unknown"
    KORU_CLI = "koru_cli"
    KORU_DAEMON = "koru_daemon"
    AUTONOMOUS = "autonomous"
    PLUGIN = "plugin"
    EXTERNAL = "external"
    SELF_DEPLOYMENT = "self_deployment"


class Severity(str, Enum):
    """Severity level for events."""

    UNKNOWN = "unknown"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


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

    def to_dsl(self) -> str:
        """Convert event to shortened DSL format for logs.

        DSL format examples:
        - deployment.started:koru_cli:info -> "Deploy koru v1.0.0 to prod"
        - plugin.installed:plugin:info -> "Plugin vscode v0.1.75 installed"
        - service.started:koru_daemon:info -> "Service autopilot started on host:pi109"
        """
        parts = [
            self.event_type.value,
            self.source.value,
            self.severity.value,
        ]
        prefix = ":".join(parts)

        # Build message from available fields
        message_parts = []
        if self.message:
            message_parts.append(self.message)
        elif self.component:
            if self.component.type == "plugin":
                message_parts.append(f"Plugin {self.component.name}")
                if self.component.version:
                    message_parts.append(f"v{self.component.version}")
                if self.plugin_ide:
                    message_parts.append(f"for {self.plugin_ide}")
            elif self.component.type == "service":
                message_parts.append(f"Service {self.component.name}")
                if self.deployment_target:
                    message_parts.append(f"on {self.deployment_target}")
            else:
                message_parts.append(f"{self.component.type.capitalize()} {self.component.name}")
                if self.component.version:
                    message_parts.append(f"v{self.component.version}")

        # Add error information if present
        if self.error_code:
            message_parts.append(f"[{self.error_code}]")
        if self.error_message:
            message_parts.append(f"error: {self.error_message}")

        # Add duration if present
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
            event_type=DeploymentEventType(data.get("event_type", DeploymentEventType.UNKNOWN.value)),
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


@dataclass
class DeploymentEventBatch:
    """Batch of events for efficient transmission."""

    events: list[DeploymentEvent] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_timestamp: float = field(default_factory=time.time)

    def add_event(self, event: DeploymentEvent) -> None:
        """Add event to batch."""
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert batch to dictionary."""
        return {
            "batch_id": self.batch_id,
            "batch_timestamp": self.batch_timestamp,
            "events": [event.to_dict() for event in self.events],
        }

    def to_json(self) -> str:
        """Convert batch to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeploymentEventBatch:
        """Create batch from dictionary."""
        events = [DeploymentEvent.from_dict(e) for e in data.get("events", [])]
        return cls(
            batch_id=data.get("batch_id", str(uuid.uuid4())),
            batch_timestamp=data.get("batch_timestamp", time.time()),
            events=events,
        )

    @classmethod
    def from_json(cls, json_str: str) -> DeploymentEventBatch:
        """Create batch from JSON string."""
        return cls.from_dict(json.loads(json_str))


class DeploymentEventEmitter:
    """Emitter for deployment events with DSL logging and persistence."""

    def __init__(
        self,
        log_file: Path | None = None,
        enable_dsl_logging: bool = True,
        enable_json_logging: bool = True,
    ):
        self.log_file = log_file
        self.enable_dsl_logging = enable_dsl_logging
        self.enable_json_logging = enable_json_logging
        self._batch: DeploymentEventBatch = DeploymentEventBatch()

    def emit(
        self,
        event: DeploymentEvent,
        *,
        correlation_id: str = "",
        session_id: str = "",
    ) -> None:
        """Emit a deployment event."""
        if correlation_id:
            event.correlation_id = correlation_id
        if session_id:
            event.session_id = session_id

        # Add to batch
        self._batch.add_event(event)

        # Log in DSL format
        if self.enable_dsl_logging:
            print(event.to_dsl())

        # Log in JSON format
        if self.enable_json_logging:
            print(event.to_json())

        # Write to file if configured
        if self.log_file:
            self._write_to_file(event)

    def emit_batch(self, batch: DeploymentEventBatch) -> None:
        """Emit a batch of events."""
        for event in batch.events:
            self.emit(event)

    def flush(self) -> DeploymentEventBatch:
        """Flush the current batch and return it."""
        batch = self._batch
        self._batch = DeploymentEventBatch()
        return batch

    def _write_to_file(self, event: DeploymentEvent) -> None:
        """Write event to log file."""
        if not self.log_file:
            return

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(event.to_dsl() + "\n")


class DeploymentEventAnalyzer:
    """Analyzer for deployment event history with reflection capabilities."""

    def __init__(self, events: list[DeploymentEvent] | None = None):
        self.events = events or []

    def add_events(self, events: list[DeploymentEvent]) -> None:
        """Add events to analyzer."""
        self.events.extend(events)

    def filter_by_type(self, event_type: DeploymentEventType) -> list[DeploymentEvent]:
        """Filter events by type."""
        return [e for e in self.events if e.event_type == event_type]

    def filter_by_source(self, source: EventSource) -> list[DeploymentEvent]:
        """Filter events by source."""
        return [e for e in self.events if e.source == source]

    def filter_by_correlation(self, correlation_id: str) -> list[DeploymentEvent]:
        """Filter events by correlation ID."""
        return [e for e in self.events if e.correlation_id == correlation_id]

    def filter_by_time_range(
        self, start: float, end: float
    ) -> list[DeploymentEvent]:
        """Filter events by time range."""
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_errors(self) -> list[DeploymentEvent]:
        """Get all error events."""
        return [e for e in self.events if e.severity in (Severity.ERROR, Severity.CRITICAL)]

    def get_plugin_events(self, ide: str = "") -> list[DeploymentEvent]:
        """Get plugin events, optionally filtered by IDE."""
        if ide:
            return [e for e in self.events if e.plugin_ide == ide]
        return [e for e in self.events if e.plugin_ide]

    def get_deployment_summary(self) -> dict[str, Any]:
        """Get summary of deployment events."""
        return {
            "total_events": len(self.events),
            "by_type": {t.value: len(self.filter_by_type(t)) for t in DeploymentEventType},
            "by_source": {s.value: len(self.filter_by_source(s)) for s in EventSource},
            "by_severity": {s.value: len([e for e in self.events if e.severity == s]) for s in Severity},
            "errors": len(self.get_errors()),
            "plugin_events": len(self.get_plugin_events()),
        }

    def analyze_deployment_flow(self, correlation_id: str) -> dict[str, Any]:
        """Analyze deployment flow for a given correlation ID."""
        events = self.filter_by_correlation(correlation_id)
        if not events:
            return {"correlation_id": correlation_id, "status": "not_found"}

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        return {
            "correlation_id": correlation_id,
            "status": "completed" if not self.get_errors() else "failed",
            "event_count": len(sorted_events),
            "duration_ms": (
                sorted_events[-1].timestamp - sorted_events[0].timestamp
            ) * 1000 if len(sorted_events) > 1 else 0,
            "events": [e.to_dsl() for e in sorted_events],
        }

    def reflect_on_development_session(self, session_id: str) -> dict[str, Any]:
        """Reflect on a development session by analyzing its events."""
        session_events = [e for e in self.events if e.session_id == session_id]
        if not session_events:
            return {"session_id": session_id, "status": "not_found"}

        return {
            "session_id": session_id,
            "summary": self.get_deployment_summary(),
            "plugin_behavior": {
                "connections": len(self.filter_by_type(DeploymentEventType.PLUGIN_CONNECTED)),
                "disconnections": len(self.filter_by_type(DeploymentEventType.PLUGIN_DISCONNECTED)),
                "version_mismatches": len(self.filter_by_type(DeploymentEventType.PLUGIN_VERSION_MISMATCH)),
            },
            "koru_package_behavior": {
                "deployments": len(self.filter_by_type(DeploymentEventType.DEPLOYMENT_STARTED)),
                "self_deployments": len(self.filter_by_type(DeploymentEventType.SELF_DEPLOYMENT_INITIATED)),
            },
            "recommendations": self._generate_recommendations(session_events),
        }

    def _generate_recommendations(self, events: list[DeploymentEvent]) -> list[str]:
        """Generate recommendations based on event analysis."""
        recommendations = []

        # Check for frequent plugin version mismatches
        version_mismatches = [e for e in events if e.event_type == DeploymentEventType.PLUGIN_VERSION_MISMATCH]
        if len(version_mismatches) > 2:
            recommendations.append(
                "Multiple plugin version mismatches detected. Consider automating plugin version synchronization."
            )

        # Check for frequent errors
        errors = self.get_errors()
        if len(errors) > 3:
            recommendations.append(
                f"High error rate ({len(errors)} errors). Review error patterns and improve error handling."
            )

        # Check for long deployment durations
        long_deployments = [e for e in events if e.duration_ms > 5000 and e.event_type == DeploymentEventType.DEPLOYMENT_COMPLETED]
        if long_deployments:
            recommendations.append(
                "Some deployments took >5 seconds. Consider optimizing deployment performance."
            )

        # Check for frequent self-deployments
        self_deployments = [e for e in events if e.event_type == DeploymentEventType.SELF_DEPLOYMENT_INITIATED]
        if len(self_deployments) > 5:
            recommendations.append(
                "Frequent self-deployments detected. Consider batching changes or reviewing deployment strategy."
            )

        return recommendations


__all__ = [
    "DeploymentEventType",
    "EventSource",
    "Severity",
    "Component",
    "DeploymentEvent",
    "DeploymentEventBatch",
    "DeploymentEventEmitter",
    "DeploymentEventAnalyzer",
]
