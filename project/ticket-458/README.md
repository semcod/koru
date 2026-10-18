# Ticket 458: Fix new-file unified diff repair and enveloped manifest pinning in queue

- **ID**: ticket-458
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: User authorized autonomous diagnosis and repair of new-file unified diff repair and manifest pinning across `semcod/koru`.

## Goal and scope

1. Fix new-file unified diff normalization and project-aware diff repair in `src/koru/queue/diff_repair.py` so new-file diffs with bare blank lines, space-prefixed blank lines, missing `diff --git` / `new file mode 100644` / `--- /dev/null` headers (when the target file does not exist on disk), or single-file fenced new-file bodies produce clean unified diffs accepted by `git apply`.
2. Fix `_pin_base` in `src/koru/queue/patch_retry.py` to unwrap `ProposalEnvelope` replies (or reuse `transaction.plan.diff`) so `manifest.json` records the real `patch_sha256` instead of the empty-string SHA-256 on retry pinning.

## Acceptance criteria

- [x] AC-01: `extract_unified_diff` repairs new-file diffs (including `--- a/<path>` for non-existent target files and bare blank lines inside new-file hunks) into valid `new file mode 100644` / `--- /dev/null` diffs that pass `git apply --check`, and `_pin_base` records the non-empty `patch_sha256` for enveloped replies.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
