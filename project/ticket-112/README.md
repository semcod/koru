# Ticket 112: Separate shell finalization from drive outcome handling

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce apply_autopilot_drive_outcome complexity below 15 while preserving finalization routing, ticket binding, skipped telemetry, exception isolation and observability ordering. Validate through koru and protected publication.

Validation: Finalization characterization passed before extraction; final parameterized regressions passed 136 tests through koru, with Ruff, managed governance and Docker Compose. Fresh code2llm removes apply_autopilot_drive_outcome (CC=17) from its hotspot list, reducing critical findings from 26 to 25 in the same scope.
