---
participant-id: agent:gpt-5.6-sol
participant: gpt-5.6-sol
role: agent
ticket: ticket-017
---
# Participant: gpt-5.6-sol (AI agent)

## Understanding

MCP requires a ticket id but currently launches an untargeted single-shot
queue. The queue chooses the next open item and MCP echoes the requested id,
so execution and reporting can disagree. Separately, LLM route availability is
discovered only after Planfile claim/start, turning infrastructure faults into
consumed task attempts.

Current main routes LLM work through the public `korullm` package. Its
`probe_subllm_route` already provides the required non-model preflight, so Koru
only needs to call that boundary before lifecycle mutation.

## Execution plan

1. Thread the existing `--ticket` value through MCP argv, single-task CLI,
   CQRS command, and queue runner; reject targeted loop mode.
2. Select the exact requested ticket inside the queue lock and return a typed,
   non-mutating lifecycle result when unavailable.
3. Probe the default `korullm` queue route before claim/start while preserving
   injected custom/test runners.
4. Remove misleading MCP best-effort reporting and add regression tests.
5. Run focused pytest, Ruff, governance, Docker configuration, and diff checks;
   then repeat the isolated c2004 experiment.

## Actual changes

- Threaded exact ticket targeting from MCP through subprocess argv, CLI, CQRS,
  and locked queue selection.
- Added non-mutating `target_not_runnable` and `infrastructure_error` outcomes.
- Probed the public `korullm` queue route before Planfile claim/start for the
  default LLM executor.
- Removed misleading MCP best-effort success reporting.
- Added regression coverage for argv, MCP, CLI wiring, exact selection, and
  preflight lifecycle ordering.
- Treated preserved `executor.mode: patch` as a durable edit expectation when
  Planfile omits custom input flags and no refactor label is present.
- Reconciled already-merged ticket-015 from `IN_PROGRESS` to `DONE` so the
  application workstream accurately reflects repository state.

## Blockers

- None.
