# Ticket 465: Defer human and skip operator tickets in Planfile SDK queue selection

- **ID**: ticket-465
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-19

## Goal and scope

Ensure `Planfile` SDK `next_ticket` and `next_tickets` skip `operator`-queue human tickets during default autonomous drain and rank machine-runnable executors ahead of human or unspecified executors.

## Acceptance criteria

- [x] AC-01: `_next_ticket_or_result` via the Planfile SDK fast path skips `operator` human tickets and defers human/unspecified-executor tickets behind machine-runnable tickets.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
