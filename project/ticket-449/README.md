# Ticket 449: Contain patch verification filesystem and network effects

- **ID**: ticket-449
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user said "wykonaj" for Maskservice PLF-15923 standard/enforcement repairs. This bounded product slice isolates Koru patch verification before invoking any untrusted test or its child processes. Keep source, Git metadata, other repositories and host temporary directories read-only. Only a fresh repository-owned operational scratch directory is writable. Deny network and host Unix socket creation; no unsandboxed fallback when kernel support is missing.

This changes verification execution only. It grants no editing, lease, publication or MCP authority, does not resume blocked Willman ticket-217, and does not activate a global host policy. Other LLM tool routes and standard/adoption work remain under the parent plan.

## Acceptance criteria

- [x] AC-01: Baseline, staged and in-place patch verification all use the isolated runner. Missing bubblewrap/seccomp support refuses before callback execution.
- [x] AC-02: Real kernel tests preserve sentinels for out-of-scope, parent traversal, symlink and child-process writes; host temporary writes and sockets fail; private scratch remains usable.
- [x] AC-03: Focused transaction tests, required project checks and managed governance pass; test scratch stays inside this worktree.
- [ ] AC-04: Independent exact-head publication and separate delivery states are recorded. No global enforcement claim.

## Final scope and validation

Preserve the existing distinction between docs-only metadata and native project adoption. The first refinement treated every `.governance` directory as native; CI exposed that this reversed the deliberate docs-only behavior from commit 89488311. Restore the original production classifier and update the native-admission fixtures to create `manifest.json`. The 35 earlier failures came from fixtures missing that native marker, rather than a proven production admission bypass.

Focused tests and real kernel denials passed locally; final counts are recorded in the owning receipts. The required critical suite passed 257 tests. The broad queue run also confirmed two existing provider failures and five existing execution-plan fixture errors on baseline HEAD. Preserve foreign active ticket-446.

OneDev runs transaction unit tests on a host without the sandbox tools. Give those unit tests an explicit verifier test double; the separate kernel tests continue to run the real wrapper and real transaction. Production verification remains mandatory and fails closed when support is absent. This slice makes no secret-read, global LLM, MCP, editing authority or deployment claim.
