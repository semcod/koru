# Deployment Event System

## Overview

The deployment event system provides structured event tracking for deployment and self-deployment operations in the koru project. It uses an abstract protobuf schema for event detection, a DSL format for shortened log output, and includes reflection/analysis capabilities for event history.

## Features

- **Protobuf-based schema**: Abstract event structure for type-safe event handling
- **DSL logging**: Shortened, human-readable log format for quick analysis
- **Event analysis**: Built-in reflection capabilities for development session analysis
- **Plugin tracking**: Monitor plugin installation, connection, and version events
- **Koru package tracking**: Track deployment, self-deployment, and configuration events

## Architecture

### Components

1. **DeploymentEvent**: Core event dataclass with serialization (dict, JSON, DSL)
2. **DeploymentEventEmitter**: Event emitter with DSL logging and file persistence
3. **DeploymentEventAnalyzer**: Event analyzer with filtering and reflection capabilities
4. **DeploymentEventBatch**: Batch operations for efficient event transmission

### Event Types

- **Deployment lifecycle**: `deployment.started`, `deployment.completed`, `deployment.failed`, `deployment.rolled_back`, `deployment.cancelled`
- **Self-deployment**: `self_deployment.initiated`, `self_deployment.applied`, `self_deployment.rejected`, `self_deployment.validated`
- **Plugin events**: `plugin.installed`, `plugin.uninstalled`, `plugin.upgraded`, `plugin.version_mismatch`, `plugin.connected`, `plugin.disconnected`
- **Configuration**: `config.changed`, `config.validated`, `config.reloaded`
- **Service events**: `service.started`, `service.stopped`, `service.restarted`, `service.health_check`
- **Dependency events**: `dependency.installed`, `dependency.removed`, `dependency.updated`

## DSL Format

The DSL format provides shortened, human-readable log output:

```
event_type:source:severity -> message

Examples:
- plugin.installed:koru_daemon:info -> Plugin koru-autopilot-vscode v0.1.75 for vscode
- service.started:koru_daemon:info -> Service autopilot on host:pi109
- deployment.failed:koru_cli:error -> [DEPLOY_ERROR] error: Deployment failed due to network error (5000ms)
```

## Usage Examples

### Basic Event Emission

```python
from koru.deployment_events import (
    DeploymentEvent,
    DeploymentEventEmitter,
    DeploymentEventType,
    EventSource,
    Severity,
    Component,
)

# Create emitter
emitter = DeploymentEventEmitter(
    log_file=Path("/var/log/koru/deployment_events.log"),
    enable_dsl_logging=True,
    enable_json_logging=False,
)

# Emit plugin installation event
event = DeploymentEvent(
    event_type=DeploymentEventType.PLUGIN_INSTALLED,
    source=EventSource.KORU_DAEMON,
    severity=Severity.INFO,
    component=Component(
        name="koru-autopilot-vscode",
        version="0.1.75",
        type="plugin",
    ),
    plugin_ide="vscode",
    plugin_version="0.1.75",
    plugin_connected=True,
    message="Plugin installed successfully",
)

emitter.emit(event, correlation_id="deploy-123", session_id="session-456")
```

### Batch Event Emission

```python
from koru.deployment_events import DeploymentEventBatch

# Create batch
batch = DeploymentEventBatch()

# Add events to batch
batch.add_event(DeploymentEvent(
    event_type=DeploymentEventType.DEPLOYMENT_STARTED,
    source=EventSource.KORU_CLI,
    message="Starting deployment",
))

batch.add_event(DeploymentEvent(
    event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
    source=EventSource.KORU_CLI,
    message="Deployment completed successfully",
    duration_ms=2500,
))

# Emit batch
emitter.emit_batch(batch)
```

### Event Analysis

```python
from koru.deployment_events import DeploymentEventAnalyzer

# Load events from log file or collect from emitter
events = [event1, event2, event3, ...]

# Create analyzer
analyzer = DeploymentEventAnalyzer(events)

# Filter events
deployment_events = analyzer.filter_by_type(DeploymentEventType.DEPLOYMENT_STARTED)
plugin_events = analyzer.get_plugin_events("vscode")
errors = analyzer.get_errors()

# Get summary
summary = analyzer.get_deployment_summary()
print(f"Total events: {summary['total_events']}")
print(f"Errors: {summary['errors']}")

# Analyze deployment flow
flow = analyzer.analyze_deployment_flow(correlation_id="deploy-123")
print(f"Flow status: {flow['status']}")
print(f"Duration: {flow['duration_ms']}ms")

# Reflect on development session
reflection = analyzer.reflect_on_development_session(session_id="session-456")
print(f"Plugin connections: {reflection['plugin_behavior']['connections']}")
print(f"Recommendations: {reflection['recommendations']}")
```

### Tracking Plugin Events

```python
# Plugin installation
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.PLUGIN_INSTALLED,
    source=EventSource.KORU_DAEMON,
    component=Component(name="koru-autopilot-vscode", version="0.1.75", type="plugin"),
    plugin_ide="vscode",
    plugin_version="0.1.75",
))

# Plugin connection
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.PLUGIN_CONNECTED,
    source=EventSource.PLUGIN,
    plugin_ide="vscode",
    plugin_connected=True,
))

# Plugin version mismatch
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.PLUGIN_VERSION_MISMATCH,
    source=EventSource.KORU_DAEMON,
    severity=Severity.WARNING,
    plugin_ide="vscode",
    plugin_version="0.1.74",
    details={"expected": "0.1.75", "actual": "0.1.74"},
))
```

### Tracking Self-Deployment Events

```python
# Self-deployment initiated
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.SELF_DEPLOYMENT_INITIATED,
    source=EventSource.SELF_DEPLOYMENT,
    message="Self-deployment initiated by autonomous system",
    koru_version="1.0.0",
    koru_source_root="/path/to/koru",
))

# Self-deployment validated
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.SELF_DEPLOYMENT_VALIDATED,
    source=EventSource.SELF_DEPLOYMENT,
    severity=Severity.INFO,
    message="Self-deployment validated successfully",
))

# Self-deployment applied
emitter.emit(DeploymentEvent(
    event_type=DeploymentEventType.SELF_DEPLOYMENT_APPLIED,
    source=EventSource.SELF_DEPLOYMENT,
    severity=Severity.INFO,
    message="Self-deployment applied successfully",
    duration_ms=1500,
))
```

### Event Serialization

```python
# Convert to dictionary
data = event.to_dict()

# Convert to JSON
json_str = event.to_json()

# Convert to DSL
dsl = event.to_dsl()

# Create event from dictionary
restored_event = DeploymentEvent.from_dict(data)

# Create event from JSON
restored_event = DeploymentEvent.from_json(json_str)
```

## Integration with Existing Deployment Flows

### Install Manager Integration

```python
from koru.autopilot.install_manager import collect_install_manager_report
from koru.deployment_events import (
    DeploymentEvent,
    DeploymentEventEmitter,
    DeploymentEventType,
    EventSource,
)

emitter = DeploymentEventEmitter(log_file=Path("/var/log/koru/deployment_events.log"))

# After plugin installation
report = collect_install_manager_report(ide="vscode")
if report.plugin.get("connected"):
    emitter.emit(DeploymentEvent(
        event_type=DeploymentEventType.PLUGIN_CONNECTED,
        source=EventSource.KORU_DAEMON,
        plugin_ide=report.plugin.get("ide"),
        plugin_version=report.plugin.get("connected_version"),
        plugin_connected=True,
        message=f"Plugin connected for {report.plugin.get('ide')}",
    ))
```

### Autonomous System Integration

```python
from koru.deployment_events import DeploymentEventEmitter

emitter = DeploymentEventEmitter(log_file=Path("/var/log/koru/deployment_events.log"))

# Track deployment events in autonomous cycle
def on_deployment_start():
    emitter.emit(DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_STARTED,
        source=EventSource.AUTONOMOUS,
        correlation_id=current_ticket_id,
        session_id=session_id,
    ))

def on_deployment_complete(duration_ms):
    emitter.emit(DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_COMPLETED,
        source=EventSource.AUTONOMOUS,
        correlation_id=current_ticket_id,
        session_id=session_id,
        duration_ms=duration_ms,
        message="Deployment completed successfully",
    ))

def on_deployment_error(error_code, error_message):
    emitter.emit(DeploymentEvent(
        event_type=DeploymentEventType.DEPLOYMENT_FAILED,
        source=EventSource.AUTONOMOUS,
        severity=Severity.ERROR,
        correlation_id=current_ticket_id,
        session_id=session_id,
        error_code=error_code,
        error_message=error_message,
    ))
```

## Reflection and Analysis

The system provides built-in reflection capabilities for analyzing development sessions:

### Development Session Reflection

```python
analyzer = DeploymentEventAnalyzer(events)
reflection = analyzer.reflect_on_development_session(session_id="session-456")

# Reflection includes:
# - Summary of all events
# - Plugin behavior (connections, disconnections, version mismatches)
# - Koru package behavior (deployments, self-deployments)
# - Recommendations based on event patterns
```

### Recommendations

The analyzer generates recommendations based on event patterns:

- **Multiple plugin version mismatches**: Suggest automating plugin version synchronization
- **High error rate**: Recommend reviewing error patterns and improving error handling
- **Long deployment durations**: Suggest optimizing deployment performance
- **Frequent self-deployments**: Recommend batching changes or reviewing deployment strategy

## Configuration

### Environment Variables

- `KORU_DEPLOYMENT_EVENT_LOG`: Path to deployment event log file (default: None)
- `KORU_DEPLOYMENT_EVENT_DSL_ENABLED`: Enable DSL logging (default: True)
- `KORU_DEPLOYMENT_EVENT_JSON_ENABLED`: Enable JSON logging (default: True)

### Log Format

Events are logged in DSL format by default:

```
plugin.installed:koru_daemon:info -> Plugin koru-autopilot-vscode v0.1.75 for vscode
service.started:koru_daemon:info -> Service autopilot on host:pi109
deployment.completed:koru_cli:info -> Deployment completed successfully (2500ms)
```

## Protobuf Schema

The protobuf schema is defined in `src/koru/deployment_events.proto` and includes:

- `DeploymentEventType`: Enum of all event types
- `EventSource`: Enum of event sources
- `Severity`: Enum of severity levels
- `Component`: Component information
- `DeploymentEvent`: Main event structure
- `DeploymentEventBatch`: Batch of events

The Python implementation uses dataclasses for now to avoid adding protobuf dependency immediately. This can be migrated to generated protobuf code later.

## Testing

Run tests with:

```bash
PYTHONPATH=src pytest tests/test_deployment_events.py -xvs
```

## Future Enhancements

- Migrate to generated protobuf code from `.proto` schema
- Add event persistence to database
- Add real-time event streaming
- Add event aggregation and metrics
- Add integration with external monitoring systems
- Add event replay capabilities for debugging
