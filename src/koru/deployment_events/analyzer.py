"""Deployment event history analysis helpers."""

from __future__ import annotations

from typing import Any

from koru.deployment_events.enums import DeploymentEventType, EventSource, Severity
from koru.deployment_events.models import DeploymentEvent


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
            "by_severity": {
                s.value: len([e for e in self.events if e.severity == s])
                for s in Severity
            },
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
                (sorted_events[-1].timestamp - sorted_events[0].timestamp) * 1000
                if len(sorted_events) > 1
                else 0
            ),
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
                "disconnections": len(
                    self.filter_by_type(DeploymentEventType.PLUGIN_DISCONNECTED)
                ),
                "version_mismatches": len(
                    self.filter_by_type(DeploymentEventType.PLUGIN_VERSION_MISMATCH)
                ),
            },
            "koru_package_behavior": {
                "deployments": len(self.filter_by_type(DeploymentEventType.DEPLOYMENT_STARTED)),
                "self_deployments": len(
                    self.filter_by_type(DeploymentEventType.SELF_DEPLOYMENT_INITIATED)
                ),
            },
            "recommendations": self._generate_recommendations(session_events),
        }

    def _generate_recommendations(self, events: list[DeploymentEvent]) -> list[str]:
        """Generate recommendations based on event analysis."""
        recommendations = []

        version_mismatches = [
            e for e in events if e.event_type == DeploymentEventType.PLUGIN_VERSION_MISMATCH
        ]
        if len(version_mismatches) > 2:
            recommendations.append(
                "Multiple plugin version mismatches detected. Consider automating "
                "plugin version synchronization."
            )

        errors = self.get_errors()
        if len(errors) > 3:
            recommendations.append(
                f"High error rate ({len(errors)} errors). Review error patterns "
                "and improve error handling."
            )

        long_deployments = [
            e
            for e in events
            if e.duration_ms > 5000
            and e.event_type == DeploymentEventType.DEPLOYMENT_COMPLETED
        ]
        if long_deployments:
            recommendations.append(
                "Some deployments took >5 seconds. Consider optimizing deployment performance."
            )

        self_deployments = [
            e
            for e in events
            if e.event_type == DeploymentEventType.SELF_DEPLOYMENT_INITIATED
        ]
        if len(self_deployments) > 5:
            recommendations.append(
                "Frequent self-deployments detected. Consider batching changes "
                "or reviewing deployment strategy."
            )

        return recommendations


__all__ = ["DeploymentEventAnalyzer"]