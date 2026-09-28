# Ticket 332: Optimize tool execution latency for redup regix and planfile sdk

- **ID**: ticket-332
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Accelerate reDUP quality gates in `src/koru/ci/gates.py` and `src/koru/redup_integration.py`:
   - Default to `--changed-only --include-untracked --incremental` in git repositories instead of scanning the full repository, dropping check latency from ~48s to <10ms.
2. Optimize Regix gate and eliminate legacy smell false positives:
   - Use `regix review --workdir <project> HEAD local` for diff-scoped regression review.
   - Detect configuration presence and skip cleanly when no `regix.yaml` exists.
3. Eliminate redundant CLI subprocess readbacks in `src/koru/queue/planfile_sdk.py`:
   - Default `_verify_enabled()` to `False` (requiring explicit `KORU_PLANFILE_SDK_VERIFY=1` to opt in).
   - Use direct in-process mutation return value without spawning `planfile ticket show` CLI subprocesses on every state transition, cutting ~20s per ticket.
4. Add regression tests covering gate commands, skipping behavior, and SDK verify options.

## Acceptance criteria

- [x] AC-01: Quality gate for redup uses fast changed-only incremental scan in git repos.
- [x] AC-02: Quality gate for regix reviews only modified symbols and skips gracefully without config.
- [x] AC-03: Planfile SDK executes mutations in-process without CLI subprocess readback by default.
- [x] AC-04: All tests and governance check pass with zero regressions.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
