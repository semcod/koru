# Ticket 315: Update Koru documentation for v0.1.461 and wellmanifest standards

- **ID**: ticket-315
- **Owner**: Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

Update Koru documentation to active version 0.1.461 conforming strictly to canonical Wellmanifest standards:
- `wellmanifest/docs`: Adopt DOCS-009 Compact Profile v2 (`UPPER_SNAKE_CASE.md` in typed directories, 12-field frontmatter, $\le 120$ lines / 600 words / 12 KiB, 4 sections: summary, details, validation, risks).
- `wellmanifest/logs` & `wellmanifest/errors`: Document structured error taxonomy, correlation tracking (`corr=...`), and canonical SODL event model.
- `wellmanifest/wellman`: Document autonomous fleet management, per-lane socket isolation, and systemd user service lifecycles.
- `wellmanifest/worktrees`: Document Wellmanifest Worktrees v5 conformance, atomic leasing, and twin sandbox execution.

## Acceptance criteria

- [x] AC-01: Document autonomous fleet management and service lifecycle in `docs/SERVICE/AUTONOMOUS_FLEET_MANAGEMENT.md`.
- [x] AC-02: Document dynamic task model policy and routing in `docs/FEATURE/TASK_MODEL_POLICY.md`.
- [x] AC-03: Document Wellmanifest Worktrees v5 integration in `docs/INFORMATION/WELLMANIFEST_WORKTREES_INTEGRATION.md`.
- [x] AC-04: Document structured logging, SODL events, and error contracts in `docs/INFORMATION/LOGS_AND_ERROR_CONTRACTS.md`.
- [x] AC-05: Document Planfile outbound synchronization in `docs/FEATURE/PLANFILE_OUTBOUND_SYNC.md`.
- [x] AC-06: Document voice and NL control bridge in `docs/FEATURE/VOICE_AND_NL_CONTROL_BRIDGE.md`.
- [x] AC-07: Index all compact v2 documents in `docs/README.md`.
- [x] AC-08: Pass Wellmanifest governance checks and unit tests.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
