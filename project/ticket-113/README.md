# Ticket 113: Share idle discovery fallback sequencing

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and GitHub publication. Runtime deployment target is awaiting clarification.

AC-01: Remove duplicated idle discovery sequencing and reduce _run_scan_after_idle complexity below 15 while preserving tool ordering, applied-ticket short circuits, useful-plan handling, scan scope and telemetry. Validate through koru and protected publication.

Validation: 16 scan-phase tests passed before and after extraction; 105 broader regressions, Ruff, managed governance and Docker Compose passed through koru. Fresh code2llm reduces critical findings from 25 to 24 in the same scope.
