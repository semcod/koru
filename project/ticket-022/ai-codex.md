---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-022
---
# Participant: Codex (AI agent)

## Understanding

Current `main` contains the previously delivered work/decide implementation.
Its focused execution-plan and work-lifecycle tests pass, but two import-only
Ruff findings make the complete `src/koru` smoke gate fail. This ticket owns
only those two application files and preserves all runtime and authority
semantics.

## Execution plan

1. Record explicit approval of the amended intent.
2. Transition the ticket to `IN_PROGRESS / EDIT` and verify the accepted base.
3. Remove the unused execution-plan import and organize the CLI import block.
4. Run focused tests, full source Ruff, governance, diff and Docker checks.
5. Record exact-head evidence and use the protected validator boundary for
   publication.

## Actual changes

- The user approved the bounded plan and the ticket entered
  `IN_PROGRESS / EDIT` on the accepted base.
- Removed the unused project-pipeline import from the execution-plan module.
- Organized the work CLI imports without changing behavior.
- Full source Ruff passes and the six focused tests remain green.

## Blockers

- None.
