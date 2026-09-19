# Ticket 173: Track managed branch hygiene workflow

- **ID**: ticket-173
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Allow the managed branch-hygiene workflow required by released Wellmanifest
new-project 0.20.33 to be tracked and install its exact released template, so
the canonical adoption generator can run.

## Acceptance criteria

- [ ] AC-01: Git does not ignore the managed workflow target.
- [ ] AC-02: The 0.20.33 adoption planner passes ignored-target validation.
- [ ] AC-03: The tracked workflow matches release `a8245857259d8d42115108f191c586b76cb1e2bd`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
