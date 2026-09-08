# Ticket 100: Decompose plan usefulness scoring

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Goal and scope
Reduce the measured complexity of plan_usefulness_score without changing scores or eligibility.

## Acceptance criteria
- [x] AC-01: Evidence, path and symbol scoring have cohesive helpers; fresh analysis confirms lower complexity.
- [x] AC-02: Exact score, filtering, filesystem and threshold regressions preserve existing behavior.
- [x] AC-03: Tests through koru, Ruff, managed governance and Docker checks pass before protected publication.

Validation: 50 characterization tests passed before and after the refactor; the latter ran through koru. Ruff, managed governance (0 errors, 0 warnings), Docker engine/Compose and whitespace checks pass. code2llm removes plan_usefulness_score (previous CC=37) from the >15 list; autonomy critical methods decrease from 17 to 16 with no new hotspot. Protected exact-head review and merge remain required.
