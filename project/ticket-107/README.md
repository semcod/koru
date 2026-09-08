# Ticket 107: Separate plan ranking from ticket creation

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce ticket application complexity below 15 while preserving eligibility counts, stable score order, duplicate handling and successful-creation limits. Pass regression tests through koru, managed gates and independent publication.

Validation: 22 ranking/discovery tests passed before and after extraction. Broader todo2code and plan regressions plus Ruff, governance and Docker Compose passed through koru. Fresh code2llm analysis reduces autonomy hotspots from 11 to 10 with all extracted helpers below CC=15.
