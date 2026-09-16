# Ticket 143: Promote Planfile backlog from monag before paid idle discovery

- **ID**: ticket-143
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user asked to investigate where monag
data can drive the autonomous loop, then said "wykonaj, scal, kontynuuj,
testuj" for the proposed Koru adapter.

`planfile ticket next` only serves the current sprint. When it is empty, the
idle fallback chain ends in the paid `nxdo` planner, which invents new tickets
even when the backlog sprint already holds open work. Before `nxdo`, read the
project-scoped `monag --json resume` inventory, move a bounded number of
unambiguous open backlog tickets into the current sprint and skip `nxdo` when
that promoted existing work. Unfinished ticket worktrees reported by monag are
listed read-only; Koru never resumes or takes them over.

## Acceptance criteria

- [x] AC-01: The user's explicit request approves the bounded scope.
- [ ] AC-02: Only open, non-conflicting tickets from the primary checkout's
      configured sprint files (default `backlog`) that are absent from the
      current sprint are promoted, highest priority first, capped by
      `KORU_MONAG_MAX_PROMOTIONS`.
- [ ] AC-03: A missing, disabled, failing or timed-out monag leaves the
      existing fallback order unchanged; `nxdo` runs only when monag promoted
      nothing.
- [ ] AC-04: Focused tests, deterministic tests, Ruff and governance
      validation pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
