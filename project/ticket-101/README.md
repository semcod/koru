# Ticket 101: Decompose useful path filtering

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Goal and scope
Reduce measured CC=30 in is_useful_code_change_path without changing the accepted implementation paths.

## Acceptance criteria
- [x] AC-01: Concrete path syntax and generated-artifact classification have cohesive helpers below the analysis threshold.
- [x] AC-02: Path, governance and score regressions preserve existing behavior.
- [x] AC-03: Tests through koru, Ruff, managed governance and Docker checks pass before independent protected publication.

Validation: 94 tests passed before and after extraction; final verification ran through koru including Ruff, managed governance, Docker Compose and whitespace checks. Fresh code2llm removes is_useful_code_change_path (CC=30) from the >15 list; autonomy critical methods decrease from 16 to 15 with no new hotspot. Independent review and merge remain required.
