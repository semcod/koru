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

## Accepted scope refinement

The broader queue regression run exposed that an empty or malformed `.governance` marker is treated as unmanaged when `manifest.json` is missing. The existing 35 refusal regressions fail before this slice. Include `workspace.py` to close that fail-open classification without granting editing authority. The rendered-profile assertion must check the command inside the sandbox envelope. Ownership of both paths was independently re-observed as free; preserve foreign ticket-446. Unrelated pre-existing provider/execution-plan failures remain outside this slice.

## Validation and limits

Final focused suite: 167 tests and 10 subtests passed, including real kernel denials and a real transaction whose attempted out-of-scope verifier write was denied and whose candidate patch was rolled back. The required critical suite passed 257 tests. Managed governance passed with zero errors/warnings. Test temporary files, JUnit and bounded receipts are kept in this checkout’s `.subactor` namespaces.

A broad queue run passed 390 tests and 28 subtests, with two existing provider tests failing and five existing execution-plan fixture errors. Replaying the original HEAD transaction modules reproduced those failures before the patch, along with the 35 partial-governance refusal failures now repaired. The two provider tests belong to foreign active ticket-446; no edits or takeover were made there. The full repository suite is not claimed clean.

This boundary requires Linux, a protected system bubblewrap binary and libseccomp. Missing support refuses execution. Verification is offline and source is read-only; only private repository-owned scratch is writable. It is a write/IPC boundary, not a claim of secret-read isolation, controller admission, global LLM coverage, MCP authorization or deployment. Independent exact-head publication remains pending.
