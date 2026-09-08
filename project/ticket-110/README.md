# Ticket 110: Separate ticket work unit rendering from selection

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce build_work_units complexity below 15 while preserving complete work unit output, filtering counts, stable score ordering and minimum selection limit. Validate through koru, managed gates and independent publication.

Validation: 9 ticket2dsl characterization tests pass before and after extraction. The broader regression suite, Ruff, managed governance and Docker Compose pass through koru. Fresh code2llm removes build_work_units (previous CC=21) from the hotspot list; critical count changes from 28 to 27 in this scan scope.
