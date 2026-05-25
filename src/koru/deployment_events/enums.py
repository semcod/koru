"""Enums for deployment event tracking."""

from __future__ import annotations

from enum import Enum


class DeploymentEventType(str, Enum):  # noqa: UP042
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


class EventSource(str, Enum):  # noqa: UP042
    """Source of the deployment event."""

    UNKNOWN = "unknown"
    KORU_CLI = "koru_cli"
    KORU_DAEMON = "koru_daemon"
    AUTONOMOUS = "autonomous"
    PLUGIN = "plugin"
    EXTERNAL = "external"
    SELF_DEPLOYMENT = "self_deployment"


class Severity(str, Enum):  # noqa: UP042
    """Severity level for events."""

    UNKNOWN = "unknown"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


__all__ = [
    "DeploymentEventType",
    "EventSource",
    "Severity",
]