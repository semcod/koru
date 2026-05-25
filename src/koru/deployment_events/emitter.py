"""Deployment event emitter with DSL logging and persistence."""

from __future__ import annotations

from pathlib import Path

from koru.deployment_events.batch import DeploymentEventBatch
from koru.deployment_events.models import DeploymentEvent


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

        self._batch.add_event(event)

        if self.enable_dsl_logging:
            print(event.to_dsl())

        if self.enable_json_logging:
            print(event.to_json())

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


__all__ = ["DeploymentEventEmitter"]