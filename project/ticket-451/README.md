# Ticket 451: fix(queue): allow loopback HTTP in pytest verification sandbox and enforce multi-file patch completeness

- **ID**: ticket-451
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: user requests autonomous execution to fix Koru verification sandbox loopback HTTP server support and multi-file patch completeness and context scaling.

## Goal and scope

Fix two concrete failure modes encountered when Koru (`glm-5.3`) executed multi-file `willman` console tickets (`PLF-255-server`, `PLF-255-server2`, `PLF-255-tests`):
1. Allow isolated loopback (`127.0.0.1` / `::1`) sockets inside `bwrap --unshare-all` when running `pytest` verification commands in `src/koru/queue/verification_sandbox.py`, while continuing to block `AF_UNIX` host sockets at the kernel seccomp layer via `seccomp_rule_add_array` (`scmp_arg_cmp` on `arg0 == AF_UNIX`).
2. Scale `build_project_context` budget and per-file section caps in `src/koru/queue/context.py` for multi-file specs so all declared target files remain visible in the prompt.
3. Enforce multi-file patch completeness across `src/koru/queue/patch_mode.py` and `src/koru/queue/patch_retry.py` by unioning declared ticket files into `_pin_base`, enabling 1 verify retry by default for multi-file tickets, including `VERIFY_BASELINE_FAILED` in `_is_verify_failure`, and listing untouched target files in `build_verify_retry_prompt`.
4. Add regression tests in `tests/test_queue_verification_sandbox.py`.

## Acceptance criteria

- [x] AC-01: `verification_sandbox.py` permits loopback HTTP servers during `pytest` verification inside `bwrap --unshare-all` while `socket(AF_UNIX, ...)` remains blocked by `libseccomp`.
- [x] AC-02: `context.py` scales context budget for multi-file requests and caps oversized per-file sections so all target files are included.
- [x] AC-03: `patch_mode.py` and `patch_retry.py` preserve all declared target files on retry and report untouched files when a multi-file patch is incomplete.
- [x] AC-04: Unit tests in `tests/test_queue_verification_sandbox.py` and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
