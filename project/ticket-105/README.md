# Ticket 105: Decompose todo2code duplicate detection

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, testing and publication.

AC-01: Reduce duplicate collector complexity below 15, preserving key/title/files identities, best-effort YAML reading and existing malformed-ticket behavior. Pass regression tests through koru, managed gates and independent publication.

Validation: 29 dedupe/discovery tests passed before and after extraction. Broader discovery, rendering and plan regressions plus Ruff, governance and Docker Compose passed through koru. Fresh code2llm analysis reduces autonomy hotspots above CC=15 from 13 to 12 with no new hotspot.
