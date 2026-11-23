# Ticket 483: Bind pytest missing-module incidents to verified recovery and preserve them across sprint archival (PLF-20052)

- **ID**: ticket-483
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23

## Goal and scope

semcod/koru#748, PLF-20052. A missing module at collection must retain its incident through sprint archival. A successful full collection is the recovery boundary. Each separately identified missing module gets its own analytical diagnosis. Set URTLOG_STATE_DIR to deliver producer observations to a URTLog installation with check-fact support.

## Acceptance criteria

- [x] AC-01: A producer-level regression test creates the first diagnosis, archives it, rechecks the same and a different module, verifies recovery and reopens a fresh regression.

The scanner also retains undelivered first-failure and recovery observations in its project-local SQLite outbox. A configured URTLog instance consumes those observations on a later applied probe.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
