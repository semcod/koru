# Ticket 016: Stabilize Ruff korullm import classification

- **ID**: ticket-016
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-26

## Goal and scope

Make the Ruff import classifier deterministic for the published `korullm`
dependency. The cleanup request authorizes this narrow integration change.

## Acceptance criteria

- [x] AC-01: `ruff check src/koru` gives the same result in an editable local
  environment and GitHub Actions.

## Delivery

- PR #35 merged exact head `3badaebb` as `775baf65`.
- Protected review `5033302296` was created by
  `ifuri-validator-agent[bot]` for `ticket-016` at that exact head.
- The explicit `koru`/`korullm` Ruff classification remains present on current
  `main`; all four current Koru modules importing `korullm` pass Ruff locally.
- Later lint findings in `execution_plan.py` and `cli_work.py` are unrelated
  additions outside this ticket's one-file integration scope.
- Governance-only lifecycle closure is published as PR #49.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
