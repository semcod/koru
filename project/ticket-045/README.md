# Ticket 045: Untrack generated analysis state

- **ID**: ticket-045
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Prepare the governance boundary for the first ready stage
(`repository.generated_state`, order 10) from
`docs/architecture/volume-reduction-plan.yaml`. Add explicit ignore rules and
a small artifact registry that records the generator commands, versions and
baseline content hashes needed by the dependent integration and
infrastructure deliveries. Remove the dead root link to the generated demo.

The user's 2026-09-02 instruction to execute the plan under `docs/*` is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded VOL-1 prerequisite. This
ticket does not delete generated files; those changes require separately
budgeted integration deliveries.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized execution of the documented
  plan; session execution authorization is recorded before implementation.
- [x] AC-02: Regenerating analysis, coverage, tree or media output cannot dirty
  the checkout after the dependent deliveries because every target output path
  is ignored.
- [x] AC-03: `config/artifact-registry.json` records reproducible commands,
  available generator versions and SHA-256 hashes for the removed baseline.
- [x] AC-04: The root README no longer links to generated media that will leave
  the source checkout.
- [x] AC-05: Governance, Docker Compose, JSON validation and diff checks pass
  before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
