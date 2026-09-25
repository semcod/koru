# Ticket 193: Reduce cyclomatic complexity: publish (CC=16)

- **ID**: ticket-193
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the planfile queue owner handed STARTER-612
to this session with explicit completion instructions (checks, commit,
`planfile ticket done STARTER-612`).

`project/analysis.toon.yaml` reports `publish` defined in
`src/koru/ticket_command/publication.py:9` with cyclomatic complexity 16
(limit 15). Extract exact-head verification, direct-main publication,
pull-request listing/creation/binding, the protected validator merge
invocation and post-merge observation into focused module-level helpers with
unchanged behaviour, bringing the function under the limit 15.

## Acceptance criteria

- [ ] AC-01: re-measured code2llm complexity for `publish` is below 15.
- [ ] AC-02: delivery and consumer suites pass unmodified; a new test pins
      the previously uncovered pull-request creation path.
- [ ] AC-03: ruff passes on the touched modules.
- [ ] AC-04: `project/governance-check.sh --base origin/main` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant
prose and raw command logs are not required delivery output.
