# Ticket 087: Bound workspace discovery

- **ID**: ticket-087
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

The autogrammar/* pilot discovered 45 checkouts instead of 38 by crossing slash boundaries into worktrees and vendor. Select the exact requested depth before any command can mutate a checkout. Measure baseline/candidate discovery and sequential refactoring correctness under wellmanifest/performance.

## Acceptance criteria

- [x] AC-01: Glob selection excludes implicit nested, generated and escaped repositories.
- [x] AC-02: Traversal has a finite budget and supports explicitly selected linked worktrees.
- [x] AC-03: Correctness tests and real pilot measurements pass; only failed tasks retry.

- [x] AC-04: POSIX commands have finite time and retained output; timeout, noisy output, inherited pipes and launch failures are tested.
