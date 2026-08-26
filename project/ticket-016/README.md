# Ticket 016: Stabilize Ruff korullm import classification

- **ID**: ticket-016
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-26

## Goal and scope

Make the Ruff import classifier deterministic for the published `korullm`
dependency. The cleanup request authorizes this narrow integration change.

## Acceptance criteria

- [ ] AC-01: `ruff check src/koru` gives the same result in an editable local
  environment and GitHub Actions.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
