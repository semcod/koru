# Ticket 484: Set required inotify capacity on the GitHub-hosted Koru smoke runner

- **ID**: ticket-484
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23

## Goal and scope

The ephemeral ubuntu-latest runner on semcod/koru#749 reported 129238 inotify watches. The existing Koru doctor requires 524288. Raise the per-user capacity on the CI runner before running the unmodified CLI smoke check. PLF-25980, parent PLF-20052.

## Acceptance criteria

- [x] AC-01: The existing Ruff, pytest and doctor steps run. Configure only an ephemeral hosted runner below the documented minimum.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
