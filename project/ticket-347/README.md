# Ticket 347: fix koru src path in vdisplay subprocess env and ghost ticket check

- **ID**: ticket-347
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

1. Resolve `koru_src` dynamically to the repository `src` root in `src/koru/integrations/vdisplay/imgl_loader.py` to prevent poisoning `PYTHONPATH` with `src/koru`, which shadowed standard library `queue` in Python 3.13.
2. In `src/koru/autonomy/cycle/cycle_drive_retry.py`, ensure tool/module errors (`traceback`, `modulenotfounderror`, etc.) fail closed (`False`), and require explicit ticket-not-found patterns.
3. Fix long line in `tests/test_queue_living_status_fastpath.py`.
4. Add unit and regression tests.

## Acceptance criteria

- [x] AC-01: Unit tests in `tests/test_cycle_drive_missing.py` pass.
- [x] AC-02: Vdisplay env regression test in `tests/test_vdisplay_env_session.py` passes without shadowing stdlib `queue`.
- [x] AC-03: Governance check passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
