---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-028
---
# Participant: codex (AI agent)

## Understanding

The user wants future delivery optimized for continuous code streaming,
minimal stalls, fast isolation and deterministic conflict prevention, while
leaving the implementation already pushed to `main` untouched. At the audited
baseline the repository had no branch protection or ruleset, used old
new-project 0.11.0, permitted only one active ticket per workstream and lacked
managed continuity, allocation and worktree-overlap tooling.

The smallest coherent foundation is the latest final new-project 0.19.19
atomic adoption plus a protected GitHub `main` ruleset. Its managed AGENTS
contract already standardizes canonical durable worktrees, remote-aware ticket
allocation, overlap guards, checkpoints, one frozen publication HEAD,
automatic branch deletion and external lifecycle closure. Koru's existing
`koru ci publish` remains the publisher, avoiding a second orchestration path.

## Execution plan

1. Record terminal ticket-027 evidence and the user's session execution
   authorization for implementation and deployment.
2. Keep the branch in the canonical `<workspace>/.worktrees` location, record
   session authorization and migrate the intent to v3/L with exact
   `standardAdoption` revisions before implementation.
3. Make the four ignored managed targets trackable, run Goal 2.1.300 upgrade
   at exact SHA `43999c793a86084b4c3198fe07be350105db59ec`, and reconcile only
   the declared target-owned manifest/package/Docker requirements.
4. Exercise allocation, worktree overlap, continuity and standard-pack gates;
   open a draft PR early so intermediate commits stream without blocking.
5. Refresh once from current `main`, freeze one final HEAD, activate and verify
   the `main` ruleset, then use `koru ci publish --watch --merge` without any
   post-freeze push or repository closure PR.
6. Verify branch/worktree cleanup, close issue #41 from protected evidence and
   leave issue #37 ready for its own application ticket.

## Actual changes

- Read and audited the current manifest, roadmap, ticket index and active
  ticket 027 at base `703dc7a2`.
- Verified new-project 0.19.19 is the latest final release and its commit
  `43999c793a86084b4c3198fe07be350105db59ec` is verified.
- Ran a durable-clone Goal preflight: four ignored managed targets require
  explicit trackability changes, after which Goal reports 78 adoption
  operations.
- Applied the upgrade only in the durable audit clone and identified the
  deterministic target remediations: agent-host packaging declarations, hook
  activation and immutable Docker references.
- Migrated an externally-created dirty ticket-027 worktree out of `/tmp` to a
  durable location with identical staged diff hash and a retained recovery
  stash; no ticket-027 content was merged or discarded.
- Atomically committed and streamed the approved intent with the complete Goal
  0.19.19 adoption as `ec0a0663`; Draft PR #62 received the implementation
  without changing `main`.
- Added Koru's `packages/**` ownership overlay, four-way disjoint workstream
  concurrency, host packaging hooks and immutable root Docker/Compose inputs.
- Activated repository ruleset 22026679 for `main`: PR-only changes, one fresh
  approval, resolved discussions, no force/delete, strict OneDev and managed
  governance checks, with Validator App bypass limited to pull requests.
- Removed the verified merged 027 remote branch and two clean worktrees, then
  reran the failed remote-lifecycle job successfully. Recovery stashes remain.
- Removed the last Koru overlap by preserving the audit clone's dirty state in
  stash `7b521b61` and moving that duplicate clone to the system trash; the
  full 430-checkout overlap audit then passed with zero findings.
- Captured and verified continuity receipt
  `receipt:continuity.ticket-028.1.d6c68f77...` for clean head `ec0a0663`.
- Kept standard-pack routing in truthful audit mode. Seven HOME-pack S3/S4
  adoptions still require pack-specific locks and protected receipts; empty
  artifact lists and repository-authored URLs are not treated as evidence.

## Blockers

No implementation blocker. Final publication still requires the frozen PR #62
HEAD to pass the protected checks and Validator App review. The workspace-wide
terminal checker also reports unrelated repositories' historical worktrees;
the Koru-specific overlap and remote lifecycle projections are clean.
