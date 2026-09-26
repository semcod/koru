# Ticket 243: Park ticket after N post_run_verify reopen failures

- **ID**: ticket-243
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Bound the post_run_verify reopen loop. With `on_failure: reopen` a verify
failure reopens the ticket and the queue redrives it; when the failure is
structural (e.g. hardware verification the driven lane cannot perform) this
loops unbounded — observed 49 drives on one ticket. `PostRunVerifyConfig`
gains `max_reopens` (default 3; `queue.post_run_verify.max_reopens` or
`KORU_POST_RUN_VERIFY_MAX_REOPENS`, 0 disables). After the ticket accumulates
`max_reopens` `post_run_verify failed` notes, the failure action escalates to
terminal `blocked` (`action: parked`) instead of another reopen.

## Acceptance criteria

- [x] AC-01: Reopen path parks the ticket as `blocked` once the persisted
  `post_run_verify failed` note count reaches `max_reopens`.
- [x] AC-02: Under-budget failures and `max_reopens: 0` keep the legacy reopen
  behavior; `on_failure: block` is unchanged.
- [x] AC-03: No extra planfile runner calls for under-budget tickets —
  write/readback sequence preserved (persistence tests unchanged, green).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
