# Ticket 145: Multi-agent orchestration auto N

- **ID**: ticket-145
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

## Goal and scope

Enable multi-agent orchestration via `koru auto <N>` (e.g. `koru auto 10`), allowing Koru to fan out across multiple sibling projects (such as `~/github/semcod/*`) or multiple actionable tickets within a workspace. Each agent is isolated to a project/ticket lane, respects project governance, optionally synchronizes Planfile with GitHub issues, and supports shell clients (crush, claude-code, aider, codex) via `tillm`.

## Acceptance criteria

- [ ] AC-01: `koru auto <N>` CLI accepts numeric worker count and options (`--workspace`, `--sync`, `--client`, `--provider`, `--dry-run`, `--max-tickets`).
- [ ] AC-02: Workspace project discovery identifies candidate projects under an organization directory (e.g. `~/github/semcod/*`).
- [ ] AC-03: Multi-agent worker pool manages up to N concurrent subprocess workers with clean lifecycle management, error isolation, and SIGINT/SIGTERM handling.
- [ ] AC-04: Optional Planfile ↔ GitHub synchronization executes before dispatching tasks on projects with GitHub integration configured.
- [ ] AC-05: `tillm_bridge` registers `crush` as a supported shell client and resolves local `autogrammar/tillm` checkout path.
- [ ] AC-06: Comprehensive unit tests and governance checks pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
