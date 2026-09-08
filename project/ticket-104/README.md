# Ticket 104: Decompose useful plan eligibility

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce is_useful_plan complexity below 15 while preserving changelog/high-risk review, action and filesystem preconditions, score threshold and short-circuit behavior. Pass regression tests through koru, managed gates and independent publication.

Validation: 117 eligibility/path/scoring tests passed before and after extraction. Broader discovery regressions, Ruff, governance and Docker Compose passed through koru. Fresh code2llm analysis reduces autonomy hotspots above CC=15 from 14 to 13; the eligibility entry point and extracted helpers remain below the threshold.
