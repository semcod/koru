---
participant-id: agent:cursor-auto
participant: cursor-auto
role: agent
ticket: ticket-027
---
# Participant: cursor-auto (AI agent)

## Understanding

The requested first delivery slice adds operator-visible LLM provenance and
desktop commit notifications while keeping profile selection data-driven.
Publication must bind the exact reviewed head and may not rely on an
unprotected direct push.

## Execution plan

1. Validate the ticket scope and acceptance evidence before implementation.
2. Add provenance and notification tests plus registry-driven profile order.
3. Run governance, focused stack checks, the full Python suite and Docker
   checks.
4. Publish the repair head through OneDev and validator-agent.

## Actual changes

- Added desktop notification support for Planfile/work commits.
- Added resolved LLM provenance to `koru work next` and execution-plan signals.
- Moved profile ordering and fallback selection into `task_profiles.yaml`.
- Made notification success reflect the actual `notify-send` exit code.
- Isolated provenance tests from inherited planning-model environment state.

## Blockers

- None. Protected PR #60 supplied exact-head review and merge evidence, and
  `main` now rejects direct pushes.
