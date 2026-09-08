# Ticket 102: Decompose todo2code ticket rendering

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

SESSION_EXECUTION_AUTHORIZATION: User requested continued refactoring, tests and publication.

AC-01: Reduce the measured ticket renderer complexity below 15 while preserving exact output, malformed-input behavior and the declared-target-path restriction; verify with characterization tests, koru, managed governance and independent protected publication.

Validation: 31 characterization and discovery tests passed before and after extraction. The broader discovery, path and scoring regressions, Ruff, managed governance, Docker Compose and whitespace checks passed through `koru` (one repository, one round). Fresh code2llm analysis reduced autonomy functions above CC=15 from 15 to 14; the former CC=35 renderer and all extracted helpers are below the threshold.
