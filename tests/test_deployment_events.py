"""Tests for deployment event system."""

from __future__ import annotations

import json
import time
from pathlib import Path

from koru.deployment_events import (
    Component,
    DeploymentEvent,
    DeploymentEventAnalyzer,
    DeploymentEventBatch,
    DeploymentEventEmitter,
    DeploymentEventType,
    EventSource,
    Severity,
)


def test_deployment_event_creation() -> None:
    """Test creating a deployment event."""
    event = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_STARTED,
        source=EventSource.KORU_CLI,
        severity=Severity.INFO,
        message="Starting deployment",
        environment="production",
    )
    assert event.event_type == DeploymentEventType.DEPLOYMENT_STARTED
    assert event.source == EventSource.KORU_CLI
    assert event.severity == Severity.INFO
    assert event.message == "Starting deployment"
    assert event.environment == "production"


def test_deployment_event_to_dict() -> None:
    """Test converting event to dictionary."""
    component = Component(name="test-plugin", version="1.0.0", type="plugin")
    event = DeploymentEvent(
        event_type=DeploymentEventType.PLUGIN_INSTALLED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        component=component,
        plugin_ide="vscode",
        plugin_version="0.1.75",
        plugin_connected=True,
    )
    data = event.to_dict()
    assert data["event_type"] == "plugin.installed"
    assert data["source"] == "koru_daemon"
    assert data["severity"] == "info"
    assert data["component"]["name"] == "test-plugin"
    assert data["component"]["version"] == "1.0.0"
    assert data["plugin_ide"] == "vscode"
    assert data["plugin_version"] == "0.1.75"
    assert data["plugin_connected"] is True


def test_deployment_event_from_dict() -> None:
    """Test creating event from dictionary."""
    data = {
        "event_type": "plugin.installed",
        "source": "koru_daemon",
        "severity": "info",
        "component": {
            "name": "test-plugin",
            "version": "1.0.0",
            "type": "plugin",
            "metadata": {},
        },
        "plugin_ide": "vscode",
        "plugin_version": "0.1.75",
        "plugin_connected": True,
        "message": "Plugin installed successfully",
    }
    event = DeploymentEvent.from_dict(data)
    assert event.event_type == DeploymentEventType.PLUGIN_INSTALLED
    assert event.source == EventSource.KORU_DAEMON
    assert event.component is not None
    assert event.component.name == "test-plugin"
    assert event.plugin_ide == "vscode"
    assert event.plugin_version == "0.1.75"
    assert event.plugin_connected is True
    assert event.message == "Plugin installed successfully"


def test_deployment_event_to_json() -> None:
    """Test converting event to JSON."""
    event = DeploymentEvent(
        event_type=DeploymentEventType.SERVICE_STARTED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        component=Component(name="autopilot", type="service"),
        deployment_target="pi109",
        message="Service started",
    )
    json_str = event.to_json()
    data = json.loads(json_str)
    assert data["event_type"] == "service.started"
    assert data["deployment_target"] == "pi109"


def test_deployment_event_from_json() -> None:
    """Test creating event from JSON."""
    json_str = json.dumps(
        {
            "event_type": "plugin.installed",
            "source": "koru_daemon",
            "severity": "info",
            "component": {
                "name": "koru-autopilot-vscode",
                "version": "0.1.75",
                "type": "plugin",
                "metadata": {},
            },
            "plugin_ide": "vscode",
            "plugin_version": "0.1.75",
            "plugin_connected": True,
        }
    )
    event = DeploymentEvent.from_json(json_str)
    assert event.event_type == DeploymentEventType.PLUGIN_INSTALLED
    assert event.component is not None
    assert event.component.name == "koru-autopilot-vscode"


def test_deployment_event_to_dsl() -> None:
    """Test converting event to DSL format."""
    # Test plugin event
    event = DeploymentEvent(
        event_type=DeploymentEventType.PLUGIN_INSTALLED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        component=Component(name="koru-autopilot-vscode", version="0.1.75", type="plugin"),
        plugin_ide="vscode",
    )
    dsl = event.to_dsl()
    assert "plugin.installed:koru_daemon:info" in dsl
    assert "Plugin koru-autopilot-vscode" in dsl
    assert "v0.1.75" in dsl
    assert "vscode" in dsl

    # Test service event
    event = DeploymentEvent(
        event_type=DeploymentEventType.SERVICE_STARTED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        component=Component(name="autopilot", type="service"),
        deployment_target="pi109",
    )
    dsl = event.to_dsl()
    assert "service.started:koru_daemon:info" in dsl
    assert "Service autopilot" in dsl
    assert "pi109" in dsl

    # Test error event
    event = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_FAILED,
        source=EventSource.KORU_CLI,
        severity=Severity.ERROR,
        error_code="DEPLOY_ERROR",
        error_message="Deployment failed due to network error",
        duration_ms=5000,
    )
    dsl = event.to_dsl()
    assert "deployment.failed:koru_cli:error" in dsl
    assert "[DEPLOY_ERROR]" in dsl
    assert "error: Deployment failed due to network error" in dsl
    assert "(5000ms)" in dsl


def test_deployment_event_batch() -> None:
    """Test deployment event batch operations."""
    batch = DeploymentEventBatch()
    event1 = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_STARTED,
        source=EventSource.KORU_CLI,
    )
    event2 = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
        source=EventSource.KORU_CLI,
    )

    batch.add_event(event1)
    batch.add_event(event2)

    assert len(batch.events) == 2
    assert batch.batch_id is not None

    data = batch.to_dict()
    assert len(data["events"]) == 2
    assert data["batch_id"] == batch.batch_id


def test_deployment_event_batch_serialization() -> None:
    """Test batch serialization and deserialization."""
    batch = DeploymentEventBatch()
    batch.add_event(
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_INSTALLED,
            source=EventSource.KORU_DAEMON,
            component=Component(name="test", version="1.0.0", type="plugin"),
        )
    )

    json_str = batch.to_json()
    restored_batch = DeploymentEventBatch.from_json(json_str)

    assert len(restored_batch.events) == 1
    assert restored_batch.batch_id == batch.batch_id
    assert restored_batch.events[0].component is not None
    assert restored_batch.events[0].component.name == "test"


def test_deployment_event_emitter(tmp_path: Path) -> None:
    """Test deployment event emitter."""
    log_file = tmp_path / "deployment_events.log"
    emitter = DeploymentEventEmitter(
        log_file=log_file, enable_dsl_logging=False, enable_json_logging=False
    )

    event = DeploymentEvent(
        event_type=DeploymentEventType.PLUGIN_INSTALLED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        component=Component(name="test-plugin", version="1.0.0", type="plugin"),
    )

    emitter.emit(event, correlation_id="test-correlation", session_id="test-session")

    # Check that event was added to batch
    assert len(emitter._batch.events) == 1
    assert emitter._batch.events[0].correlation_id == "test-correlation"
    assert emitter._batch.events[0].session_id == "test-session"

    # Check that event was written to file
    assert log_file.exists()
    content = log_file.read_text()
    assert "plugin.installed:koru_daemon:info" in content


def test_deployment_event_emitter_flush(tmp_path: Path) -> None:
    """Test flushing emitter batch."""
    emitter = DeploymentEventEmitter(
        log_file=tmp_path / "events.log",
        enable_dsl_logging=False,
        enable_json_logging=False,
    )

    event1 = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_STARTED,
        source=EventSource.KORU_CLI,
    )
    event2 = DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
        source=EventSource.KORU_CLI,
    )

    emitter.emit(event1)
    emitter.emit(event2)

    batch = emitter.flush()
    assert len(batch.events) == 2
    assert len(emitter._batch.events) == 0


def test_deployment_event_analyzer() -> None:
    """Test deployment event analyzer."""
    events = [
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_STARTED,
            source=EventSource.KORU_CLI,
            correlation_id="test-1",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
            source=EventSource.KORU_CLI,
            correlation_id="test-1",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_INSTALLED,
            source=EventSource.KORU_DAEMON,
            severity=Severity.ERROR,
            plugin_ide="vscode",
        ),
    ]

    analyzer = DeploymentEventAnalyzer(events)

    # Test filtering
    deployment_events = analyzer.filter_by_type(DeploymentEventType.DEPLOYMENT_STARTED)
    assert len(deployment_events) == 1

    cli_events = analyzer.filter_by_source(EventSource.KORU_CLI)
    assert len(cli_events) == 2

    correlation_events = analyzer.filter_by_correlation("test-1")
    assert len(correlation_events) == 2

    # Test error detection
    errors = analyzer.get_errors()
    assert len(errors) == 1

    # Test plugin events
    plugin_events = analyzer.get_plugin_events("vscode")
    assert len(plugin_events) == 1


def test_deployment_event_analyzer_summary() -> None:
    """Test deployment event summary."""
    events = [
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_STARTED,
            source=EventSource.KORU_CLI,
            severity=Severity.INFO,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_INSTALLED,
            source=EventSource.KORU_DAEMON,
            severity=Severity.ERROR,
            plugin_ide="vscode",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
            severity=Severity.INFO,
        ),
    ]

    analyzer = DeploymentEventAnalyzer(events)
    summary = analyzer.get_deployment_summary()

    assert summary["total_events"] == 3
    assert summary["errors"] == 1
    assert summary["plugin_events"] == 1
    assert summary["by_type"]["deployment.started"] == 1
    assert summary["by_source"]["koru_cli"] == 1


def test_deployment_event_analyzer_flow_analysis() -> None:
    """Test deployment flow analysis."""
    correlation_id = "test-flow"
    events = [
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_STARTED,
            source=EventSource.KORU_CLI,
            correlation_id=correlation_id,
            timestamp=time.time() - 5,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
            source=EventSource.KORU_CLI,
            correlation_id=correlation_id,
            timestamp=time.time(),
        ),
    ]

    analyzer = DeploymentEventAnalyzer(events)
    flow = analyzer.analyze_deployment_flow(correlation_id)

    assert flow["correlation_id"] == correlation_id
    assert flow["status"] == "completed"
    assert flow["event_count"] == 2
    assert flow["duration_ms"] > 0


def test_deployment_event_analyzer_reflection() -> None:
    """Test development session reflection."""
    session_id = "test-session"
    events = [
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_CONNECTED,
            source=EventSource.KORU_DAEMON,
            session_id=session_id,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_VERSION_MISMATCH,
            source=EventSource.KORU_DAEMON,
            severity=Severity.WARNING,
            session_id=session_id,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_VERSION_MISMATCH,
            source=EventSource.KORU_DAEMON,
            severity=Severity.WARNING,
            session_id=session_id,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.PLUGIN_VERSION_MISMATCH,
            source=EventSource.KORU_DAEMON,
            severity=Severity.WARNING,
            session_id=session_id,
        ),
    ]

    analyzer = DeploymentEventAnalyzer(events)
    reflection = analyzer.reflect_on_development_session(session_id)

    assert reflection["session_id"] == session_id
    assert reflection["plugin_behavior"]["connections"] == 1
    assert reflection["plugin_behavior"]["version_mismatches"] == 3
    assert len(reflection["recommendations"]) > 0
    assert "version synchronization" in reflection["recommendations"][0].lower()


def test_deployment_event_analyzer_recommendations() -> None:
    """Test recommendation generation."""
    events = [
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_FAILED,
            source=EventSource.KORU_CLI,
            severity=Severity.ERROR,
            error_code="ERROR_1",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_FAILED,
            source=EventSource.KORU_CLI,
            severity=Severity.ERROR,
            error_code="ERROR_2",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_FAILED,
            source=EventSource.KORU_CLI,
            severity=Severity.ERROR,
            error_code="ERROR_3",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_FAILED,
            source=EventSource.KORU_CLI,
            severity=Severity.ERROR,
            error_code="ERROR_4",
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
            source=EventSource.KORU_CLI,
            duration_ms=6000,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
        DeploymentEvent(
            event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
            source=EventSource.SELF_DEPLOYMENT,
        ),
    ]

    analyzer = DeploymentEventAnalyzer(events)
    recommendations = analyzer._generate_recommendations(events)

    assert len(recommendations) > 0
    assert any("error rate" in r.lower() for r in recommendations)
    assert any("deployment performance" in r.lower() for r in recommendations)
    assert any("self-deployments" in r.lower() for r in recommendations)


def test_component_creation() -> None:
    """Test component creation."""
    component = Component(
        name="test-component",
        version="1.0.0",
        type="service",
        metadata={"key": "value"},
    )
    assert component.name == "test-component"
    assert component.version == "1.0.0"
    assert component.type == "service"
    assert component.metadata == {"key": "value"}


def test_event_enums() -> None:
    """Test event enum values."""
    assert DeploymentEventType.DEPLOYMENT_STARTED.value == "deployment.started"
    assert DeploymentEventType.PLUGIN_INSTALLED.value == "plugin.installed"
    assert EventSource.KORU_CLI.value == "koru_cli"
    assert EventSource.KORU_DAEMON.value == "koru_daemon"
    assert Severity.INFO.value == "info"
    assert Severity.ERROR.value == "error"


def test_event_with_all_fields() -> None:
    """Test event with all fields populated."""
    component = Component(
        name="test-plugin",
        version="1.0.0",
        type="plugin",
        metadata={"author": "test"},
    )
    event = DeploymentEvent(
        event_type=DeploymentEventType.PLUGIN_UPGRADED,
        source=EventSource.KORU_DAEMON,
        severity=Severity.INFO,
        correlation_id="test-corr",
        session_id="test-sess",
        component=component,
        environment="staging",
        deployment_target="test-host",
        message="Plugin upgraded",
        details={"previous_version": "0.9.0"},
        duration_ms=1500,
        metrics={"cpu_usage": 50.0, "memory_mb": 128.0},
        error_code="",
        error_message="",
        stack_trace=[],
        plugin_ide="cursor",
        plugin_version="0.1.75",
        plugin_connected=True,
        koru_version="1.0.0",
        koru_source_root="/path/to/koru",
    )

    data = event.to_dict()
    assert data["correlation_id"] == "test-corr"
    assert data["session_id"] == "test-sess"
    assert data["environment"] == "staging"
    assert data["deployment_target"] == "test-host"
    assert data["details"]["previous_version"] == "0.9.0"
    assert data["duration_ms"] == 1500
    assert data["metrics"]["cpu_usage"] == 50.0
    assert data["plugin_ide"] == "cursor"
    assert data["koru_version"] == "1.0.0"
