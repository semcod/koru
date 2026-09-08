# Ticket 111: Separate terminal shell queue projection from reconciliation

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce reconcile_shell_cycle complexity below 15 while preserving live readback, failure precedence, canceled/done semantics, waiting order, completion deduplication, immutable input and telemetry/stagnation updates. Validate through koru and protected publication.

Validation: 21 focused tests passed before and after extraction; the broader koru regression run passed 130 tests (11 deselected by the repository configuration), Ruff, managed governance and Docker Compose. Fresh code2llm removes reconcile_shell_cycle (CC=16) from its hotspot list, reducing critical findings from 27 to 26 in the same scope.
