# Ticket 069: Resolve Goal targets in umbrella workspaces

- **ID**: ticket-069
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Prevent `koru goal` from treating a non-Git umbrella directory as a successful
Goal target. A direct Git repository continues to run unchanged. An umbrella
workspace selects its only dirty immediate child repository; zero or multiple
dirty repositories fail closed and require an explicit, path-confined
`--repo`. Target resolution happens before Goal or any remediation agent runs.

## Acceptance criteria

- [x] AC-01: The user's request to continue, implement and test records
      `SESSION_EXECUTION_AUTHORIZATION` for this bounded defect repair.
- [x] AC-02: A direct Git repository is selected without workspace scanning.
- [x] AC-03: An umbrella workspace automatically selects exactly one dirty
      immediate Git child, while zero or multiple dirty children return 2 and
      launch neither Goal nor an agent.
- [x] AC-04: `--repo` selects only a Git repository contained by the workspace
      and rejects absolute or escaping paths.
- [x] AC-05: Focused tests, Ruff, governance and Docker configuration pass.

## Evidence

Live execution in the local Autogrammar umbrella found 38 immediate child Git
repositories, including 16 dirty repositories. Goal returned zero from the
non-Git umbrella root, demonstrating the false-success regression without
launching a remediation agent or modifying Autogrammar.

## Validation

- 81 focused tests and 52 subtests pass across workspace resolution, Goal
  supervision and CLI dispatch.
- Live Autogrammar execution now returns 2 with the 16 sorted dirty candidates
  and does not invoke Goal or an agent.
- Scoped Ruff and compileall pass; managed governance, Docker Compose and diff
  checks are recorded in the participant log.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
