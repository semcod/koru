# Ticket 487: Reconcile Koru package version in uv.lock (PLF-25982)

- **ID**: ticket-487
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-24

## Goal and scope

PLF-25982 tracks the stale editable package version left by release 0.1.463. Match the Koru entry to the current project metadata and preserve all registry package pins, sources and hashes.

## Acceptance criteria

- [x] AC-01: `uv lock --check --offline` resolves the unchanged 240-package graph on Python 3.12 and 3.13.
- [x] AC-02: `uv sync --locked --extra dev --extra quality` installs 172 packages on Python 3.12 and 173 on Python 3.13. Offline sync and `uv pip check` pass in both environments.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
