# CQRS + Event Sourcing (Step 1)

This repository now starts an incremental CQRS/Event-Sourcing rollout.

## Identified Bounded Contexts

1. `topology`
   - Responsibility: project topology state (`.koru/topology.yaml`) and enable/disable mutations.
   - Read model: topology listing and predicates (`is-enabled`, enabled components per pipeline).
   - Write model: component/pipeline toggles and topology persistence.

2. `local_manager`
   - Responsibility: localhost service state for queue actions and worker lifecycle.
   - Read model: health, queue snapshot, workers snapshot, combined state snapshot.
   - Write model: enqueue/claim/complete actions and register/heartbeat worker operations.

## Module Layout

- `src/koru/cqrs/`
  - `event_store.py` (append-only in-memory store)
  - `event_bus.py` (in-process pub/sub)
  - `__init__.py` (`EventSourcingRuntime`)

- `src/koru/bounded_contexts/topology/`
  - `commands/`
  - `queries/`
  - `events/`
  - `application.py`

- `src/koru/bounded_contexts/local_manager/`
  - `commands/`
  - `queries/`
  - `events/`
  - `application.py`

## Integration Points

- `src/koru/cli_topology.py` now routes through topology command/query services.
- `src/koru/local_service.py` now routes through local-manager command/query services.

This step keeps external CLI/HTTP contracts stable while introducing a structured
internal split between commands and queries, plus domain event capture.
