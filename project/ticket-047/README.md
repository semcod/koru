# Ticket 047: Scan layer hotspots include source paths for hygiene

- **ID**: ticket-047
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Layer hotspot tickets from `koru scan` must reference implementable source files,
not only `project/analysis.toon.yaml`, so `run_ticket_hygiene` does not archive them
as junk after refactors.

## Acceptance criteria

- [ ] AC-01: Layer hotspot suggestions include resolved source path when `calls.yaml` maps the module.
- [ ] AC-02: Existing scan tests pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
