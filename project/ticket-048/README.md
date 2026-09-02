# Ticket 048: Untrack root generated analysis artifacts

- **ID**: ticket-048
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Execute the first material slice of `repository.generated_state` from
`docs/architecture/volume-reduction-plan.yaml`. Remove the twelve tracked root,
coverage, Code2LLM and media outputs already covered by the governed artifact
registry and ignore policy delivered by ticket-045. No history is rewritten;
the removed baseline remains recoverable from the accepted base commit.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 delivery.

Ticket-049 resolved the gate's `GOV-WORKSTREAM-003` finding by assigning the
exact artifact-registry paths to integration. The initial deletion attempt was
fully restored before that prerequisite and is now being repeated from its
merged base.

## Acceptance criteria

- [x] AC-01: The twelve declared generated outputs are no longer tracked.
- [x] AC-02: Regenerating those outputs cannot dirty the checkout because the
  ticket-045 ignore boundary covers every removed path.
- [x] AC-03: The compact artifact registry retains the baseline hashes and
  reproduction commands for every removed output group.
- [x] AC-04: Governance, Docker Compose and diff checks pass before protected
  publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
