# Ticket 355: Format line length in test queue pipelining

- **ID**: ticket-355
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

Wrap the function signature of `fake_next_tickets` in `tests/test_queue_pipelining.py` so that line length does not exceed 120 characters, resolving the Ruff E501 violation that blocks `post_run_verify`.

## Acceptance criteria

- [ ] AC-01: Line 26 in `tests/test_queue_pipelining.py` is wrapped to conform to 120 char limit.
- [ ] AC-02: `ruff check src tests` passes with 0 errors.
- [ ] AC-03: `tests/test_queue_pipelining.py` tests pass.

## Authorization

- Session execution authorization: user requested continuation of pilot test and autonomous delivery.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
